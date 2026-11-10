"""Top-level bass-pedal board: six OLEDs + eight footswitches."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .buses import FakeI2C, FakeSPI, open_i2c, open_spi
from .oled import (
    CS_MASK,
    FOOTSWITCH_MASK,
    Framebuffer,
    OledBus,
    OledController,
)
from .pcf8575 import DEFAULT_ADDRESS, Pcf8575

FOOTSWITCH_PINS = tuple(range(8, 16))
DEFAULT_LABELS = ("SLOT 1", "SLOT 2", "SLOT 3", "SLOT 4", "SLOT 5", "SLOT 6")


@dataclass
class PedalConfig:
    i2c_bus: int | None = None
    i2c_address: int = DEFAULT_ADDRESS
    spi_bus: int = 0
    spi_device: int = 0
    spi_hz: int = 8_000_000
    controller: OledController = OledController.SSD1306
    display_count: int = 6
    debounce_seconds: float = 0.020
    labels: tuple[str, ...] = DEFAULT_LABELS


@dataclass
class SwitchEvent:
    pin: int
    index: int
    pressed: bool
    timestamp: float = field(default_factory=time.monotonic)


class BassPedalBoard:
    """Owns the expander, SPI OLED bus, and debounced footswitch polling.

    Display and switch I/O share one lock so CS/DC cannot change mid-transfer.
    Run this in a process that is *not* the PiPedal audio thread.
    """

    def __init__(
        self,
        expander: Pcf8575,
        oleds: OledBus,
        *,
        config: PedalConfig | None = None,
        clock=time.monotonic,
    ) -> None:
        self.config = config or PedalConfig()
        self.expander = expander
        self.oleds = oleds
        self._lock = threading.RLock()
        self._clock = clock
        self._switch_stable = [True] * len(FOOTSWITCH_PINS)  # released = high
        self._switch_raw = [True] * len(FOOTSWITCH_PINS)
        self._switch_since = [self._clock()] * len(FOOTSWITCH_PINS)
        self.framebuffers = [Framebuffer() for _ in range(self.config.display_count)]

    @classmethod
    def mock(cls, config: PedalConfig | None = None) -> tuple["BassPedalBoard", FakeI2C, FakeSPI]:
        config = config or PedalConfig()
        i2c = FakeI2C()
        expander = Pcf8575(i2c, config.i2c_address)
        spi = FakeSPI(latch_fn=lambda: expander.latch)
        oleds = OledBus(expander, spi, controller=config.controller, display_count=config.display_count)
        board = cls(expander, oleds, config=config)
        return board, i2c, spi

    @classmethod
    def open_hardware(cls, config: PedalConfig | None = None) -> "BassPedalBoard":
        config = config or PedalConfig()
        _bus_id, i2c = open_i2c(config.i2c_bus)
        expander = Pcf8575(i2c, config.i2c_address)
        spi = open_spi(config.spi_bus, config.spi_device, config.spi_hz)
        oleds = OledBus(expander, spi, controller=config.controller, display_count=config.display_count)
        return cls(expander, oleds, config=config)

    def initialize(self) -> None:
        with self._lock:
            if (self.expander.latch & CS_MASK) != CS_MASK:
                self.expander.update(set_mask=CS_MASK | FOOTSWITCH_MASK)
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
            pins = self.expander.read_pins()
        now = self._clock()
        events: list[SwitchEvent] = []
        for index, pin in enumerate(FOOTSWITCH_PINS):
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
            pins = self.expander.read_pins()
        return [i for i, pin in enumerate(FOOTSWITCH_PINS) if (pins & (1 << pin)) == 0]

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
