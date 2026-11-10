"""Top-level bass-pedal board: six OLEDs + PCF footswitches."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .buses import FakeI2C, FakeSPI, open_i2c, open_spi
from .oled import CS_MASK, Framebuffer, OledBus, OledController
from .pcf8575 import DEFAULT_ADDRESS, SWITCH_ADDRESS, Pcf8574, Pcf8575, Pcf857x

DEFAULT_LABELS = ("SLOT 1", "SLOT 2", "SLOT 3", "SLOT 4", "SLOT 5", "SLOT 6")


def _pcf_class(bits: int) -> type[Pcf857x]:
    return Pcf8575 if bits == 16 else Pcf8574


@dataclass
class PedalConfig:
    i2c_bus: int | None = None
    i2c_address: int = DEFAULT_ADDRESS
    switch_address: int = SWITCH_ADDRESS
    display_bits: int = 16
    switch_bits: int = 16
    switch_count: int = 6
    spi_bus: int = 0
    spi_device: int = 0
    spi_hz: int = 8_000_000
    controller: OledController = OledController.SSD1306
    display_count: int = 6
    debounce_seconds: float = 0.020
    labels: tuple[str, ...] = DEFAULT_LABELS

    def __post_init__(self) -> None:
        if self.display_bits not in (8, 16) or self.switch_bits not in (8, 16):
            raise ValueError("PCF width must be 8 (8574/8574A) or 16 (8575)")
        if not 1 <= self.switch_count <= 8:
            raise ValueError("switch_count must be 1-8")


@dataclass
class SwitchEvent:
    pin: int
    index: int
    pressed: bool
    timestamp: float = field(default_factory=time.monotonic)


class BassPedalBoard:
    """Owns display PCF, optional switch PCF, SPI OLEDs, and debounce.

    Display and switch I/O share one lock so the I2C bus stays serialized.
    Run this in a process that is *not* the PiPedal audio thread.
    """

    def __init__(
        self,
        expander: Pcf857x,
        oleds: OledBus,
        *,
        switch_expander: Pcf857x | None = None,
        config: PedalConfig | None = None,
        clock=time.monotonic,
    ) -> None:
        self.config = config or PedalConfig()
        self.expander = expander
        self.switch_expander = switch_expander or expander
        self.oleds = oleds
        self._lock = threading.RLock()
        self._clock = clock
        same_chip = self.switch_expander.address == self.expander.address
        if same_chip:
            if self.expander.bits != 16:
                raise ValueError("A single PCF8574 cannot drive OLEDs and footswitches")
            self._switch_pins = tuple(range(8, 8 + self.config.switch_count))
        else:
            self._switch_pins = tuple(range(self.config.switch_count))
        n = len(self._switch_pins)
        self._switch_stable = [True] * n
        self._switch_raw = [True] * n
        self._switch_since = [self._clock()] * n
        self.framebuffers = [Framebuffer() for _ in range(self.config.display_count)]

    @classmethod
    def mock(cls, config: PedalConfig | None = None) -> tuple["BassPedalBoard", FakeI2C, FakeSPI]:
        config = config or PedalConfig()
        i2c = FakeI2C()
        display_cls = _pcf_class(config.display_bits)
        switch_cls = _pcf_class(config.switch_bits)
        expander = display_cls(i2c, config.i2c_address)
        switch = (
            expander
            if config.switch_address == config.i2c_address
            else switch_cls(i2c, config.switch_address)
        )
        spi = FakeSPI(latch_fn=lambda: expander.latch)
        oleds = OledBus(expander, spi, controller=config.controller, display_count=config.display_count)
        board = cls(expander, oleds, switch_expander=switch, config=config)
        return board, i2c, spi

    @classmethod
    def open_hardware(cls, config: PedalConfig | None = None) -> "BassPedalBoard":
        config = config or PedalConfig()
        _bus_id, i2c = open_i2c(config.i2c_bus)
        display_cls = _pcf_class(config.display_bits)
        switch_cls = _pcf_class(config.switch_bits)
        expander = display_cls(i2c, config.i2c_address)
        switch = (
            expander
            if config.switch_address == config.i2c_address
            else switch_cls(i2c, config.switch_address)
        )
        spi = open_spi(config.spi_bus, config.spi_device, config.spi_hz)
        oleds = OledBus(expander, spi, controller=config.controller, display_count=config.display_count)
        return cls(expander, oleds, switch_expander=switch, config=config)

    def initialize(self) -> None:
        with self._lock:
            if (self.expander.latch & CS_MASK) != CS_MASK:
                self.expander.update(set_mask=CS_MASK)
            if self.switch_expander is not self.expander:
                self.switch_expander.write_latch(self.switch_expander.width_mask)
            self.oleds.init_all()

    def show_labels(self, labels: Iterable[str] | None = None) -> None:
        texts = tuple(labels) if labels is not None else self.config.labels
        with self._lock:
            for index, fb in enumerate(self.framebuffers):
                fb.clear()
                title = texts[index] if index < len(texts) else f"SLOT {index + 1}"
                fb.text(2, 2, title[:16])
                fb.text(2, 18, f"FS{index + 1}")
                self.oleds.write_framebuffer(index, fb.buf)

    def draw_text(self, display: int, line0: str, line1: str = "") -> None:
        with self._lock:
            fb = self.framebuffers[display]
            fb.clear()
            fb.text(2, 8, line0[:21])
            if line1:
                fb.text(2, 24, line1[:21])
            self.oleds.write_framebuffer(display, fb.buf)

    def poll_switches(self) -> list[SwitchEvent]:
        """Return edge events after debounce. Pressed = pin pulled to GND."""
        with self._lock:
            pins = self.switch_expander.read_pins()
        now = self._clock()
        events: list[SwitchEvent] = []
        for index, pin in enumerate(self._switch_pins):
            high = bool(pins & (1 << pin))
            if high != self._switch_raw[index]:
                self._switch_raw[index] = high
                self._switch_since[index] = now
                continue
            if now - self._switch_since[index] < self.config.debounce_seconds:
                continue
            if high != self._switch_stable[index]:
                self._switch_stable[index] = high
                events.append(
                    SwitchEvent(pin=pin, index=index, pressed=not high, timestamp=now)
                )
        return events

    def read_pressed(self) -> list[int]:
        with self._lock:
            pins = self.switch_expander.read_pins()
        return [i for i, pin in enumerate(self._switch_pins) if (pins & (1 << pin)) == 0]

    def run_poll_loop(
        self,
        on_event: Callable[[SwitchEvent], None],
        *,
        interval: float = 0.005,
        stop: Callable[[], bool] | None = None,
        sleep=time.sleep,
    ) -> None:
        while stop is None or not stop():
            for event in self.poll_switches():
                on_event(event)
            sleep(interval)
