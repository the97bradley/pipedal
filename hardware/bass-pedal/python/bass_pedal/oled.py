"""SSD1306 / SH1106 128x64 4-wire SPI, with CS/DC owned by the PCF8575.

DC is never changed while a SPI transfer is in flight. Shared RES is pulsed
once before any chip-select is asserted.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Iterable, Protocol, Sequence

from . import font as bitmap_font
from .pcf8575 import Pcf857x

WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8
FRAMEBUFFER_SIZE = WIDTH * PAGES

CS_PINS = (0, 1, 2, 3, 4, 5)
CS_MASK = 0x3F
DC_PIN = 6
DC_MASK = 1 << DC_PIN
RES_PIN = 7
RES_MASK = 1 << RES_PIN
FOOTSWITCH_MASK = 0xFF00

# SH1106 GDDRAM is 132 columns; a 128-wide panel is centered at column 2.
SH1106_COLUMN_OFFSET = 2


class OledController(str, Enum):
    SSD1306 = "ssd1306"
    SH1106 = "sh1106"


class SpiDevice(Protocol):
    def xfer2(self, data) -> list[int]: ...


SSD1306_INIT = (
    0xAE,  # display off
    0xD5, 0x80,  # clock
    0xA8, 0x3F,  # multiplex 1/64
    0xD3, 0x00,  # offset
    0x40,  # start line 0
    0x8D, 0x14,  # charge pump on
    0x20, 0x02,  # page addressing (matches SH1106 write loop)
    0xA1,  # segment remap
    0xC8,  # COM scan remapped
    0xDA, 0x12,  # COM pins
    0x81, 0xCF,  # contrast
    0xD9, 0xF1,  # precharge
    0xDB, 0x40,  # VCOM
    0xA4,  # resume RAM
    0xA6,  # normal (not inverted)
    0x2E,  # deactivate scroll
    0xAF,  # display on
)

SH1106_INIT = (
    0xAE,
    0xD5, 0x80,
    0xA8, 0x3F,
    0xD3, 0x00,
    0x40,
    0xAD, 0x8B,  # DC-DC on (SH1106)
    0xA1,
    0xC8,
    0xDA, 0x12,
    0x81, 0xCF,
    0xD9, 0xF1,
    0xDB, 0x40,
    0xA4,
    0xA6,
    0xAF,
)


class OledBus:
    """Serialized expander + SPI access for six displays."""

    def __init__(
        self,
        expander: Pcf857x,
        spi: SpiDevice,
        controller: OledController = OledController.SSD1306,
        display_count: int = 6,
        reset_seconds: float = 0.010,
        sleep=time.sleep,
    ) -> None:
        if not 1 <= display_count <= 6:
            raise ValueError("display_count must be 1-6")
        self.expander = expander
        self.spi = spi
        self.controller = OledController(controller)
        self.display_count = display_count
        self._reset_seconds = reset_seconds
        self._sleep = sleep
        self.transfers: list[tuple[str, int, bytes]] = []
        self._idle()

    def _hold_mask(self) -> int:
        """Keep unused high-byte pins as inputs on a 16-bit display PCF."""
        return FOOTSWITCH_MASK & self.expander.width_mask

    def _idle(self) -> None:
        # All CS high, DC=data, RES=released. High byte (if any) left as inputs.
        self.expander.update(
            clear_mask=0,
            set_mask=CS_MASK | DC_MASK | RES_MASK | self._hold_mask(),
        )

    def hardware_reset(self) -> None:
        """Pulse shared RES with every CS held inactive."""
        self.expander.update(
            clear_mask=RES_MASK,
            set_mask=CS_MASK | self._hold_mask(),
        )
        self._sleep(self._reset_seconds)
        self.expander.update(set_mask=RES_MASK | CS_MASK)
        self._sleep(self._reset_seconds)

    def _begin(self, display: int, data_mode: bool) -> None:
        if not 0 <= display < self.display_count:
            raise IndexError(f"display {display} out of range")
        cs_low = 1 << CS_PINS[display]
        set_mask = self._hold_mask() | RES_MASK | (CS_MASK & ~cs_low)
        if data_mode:
            set_mask |= DC_MASK
            clear_mask = cs_low
        else:
            clear_mask = cs_low | DC_MASK
        self.expander.update(clear_mask=clear_mask, set_mask=set_mask)

    def _end(self) -> None:
        self.expander.update(set_mask=CS_MASK | self._hold_mask())

    def _xfer(self, phase: str, display: int, payload: Sequence[int]) -> None:
        data = bytes(payload)
        if not data:
            return
        self.transfers.append((phase, display, data))
        # Chunk to stay within typical spidev BUFSIZ (4096).
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            self.spi.xfer2(view[offset : offset + 4096].tobytes())
            offset += 4096

    def command(self, display: int, bytes_or_ints: Iterable[int]) -> None:
        payload = list(bytes_or_ints)
        self._begin(display, data_mode=False)
        try:
            self._xfer("cmd", display, payload)
        finally:
            self._end()

    def data(self, display: int, bytes_or_ints: Iterable[int]) -> None:
        payload = list(bytes_or_ints)
        self._begin(display, data_mode=True)
        try:
            self._xfer("data", display, payload)
        finally:
            self._end()

    def init_display(self, display: int) -> None:
        sequence = SH1106_INIT if self.controller is OledController.SH1106 else SSD1306_INIT
        self.command(display, sequence)

    def init_all(self) -> None:
        self.hardware_reset()
        for index in range(self.display_count):
            self.init_display(index)

    def _set_address(self, display: int, page: int, column: int) -> None:
        if self.controller is OledController.SH1106:
            column += SH1106_COLUMN_OFFSET
            self.command(
                display,
                (0xB0 | (page & 0x07), 0x10 | ((column >> 4) & 0x0F), column & 0x0F),
            )
        else:
            self.command(
                display,
                (0xB0 | (page & 0x07), 0x00 | (column & 0x0F), 0x10 | ((column >> 4) & 0x0F)),
            )
            # Horizontal mode also accepts column/page range; page addressing is
            # used here so SSD1306 and SH1106 share the same write loop.

    def write_framebuffer(self, display: int, buf: bytes | bytearray) -> None:
        if len(buf) != FRAMEBUFFER_SIZE:
            raise ValueError(f"framebuffer must be {FRAMEBUFFER_SIZE} bytes")
        for page in range(PAGES):
            start = page * WIDTH
            self._set_address(display, page, 0)
            self.data(display, buf[start : start + WIDTH])


class Framebuffer:
    def __init__(self, width: int = WIDTH, height: int = HEIGHT) -> None:
        if height % 8:
            raise ValueError("height must be a multiple of 8")
        self.width = width
        self.height = height
        self.buf = bytearray(width * (height // 8))

    def clear(self) -> None:
        self.buf[:] = b"\x00" * len(self.buf)

    def fill(self, on: bool = True) -> None:
        self.buf[:] = (b"\xff" if on else b"\x00") * len(self.buf)

    def pixel(self, x: int, y: int, on: bool = True) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = (y >> 3) * self.width + x
        bit = 1 << (y & 7)
        if on:
            self.buf[index] |= bit
        else:
            self.buf[index] &= ~bit

    def text(self, x: int, y: int, message: str, on: bool = True) -> None:
        cursor = x
        for ch in message:
            glyph = bitmap_font.glyph(ch)
            for col, column_bits in enumerate(glyph):
                for row in range(bitmap_font.HEIGHT):
                    if column_bits & (1 << row):
                        self.pixel(cursor + col, y + row, on)
            cursor += bitmap_font.ADVANCE

    def invert(self) -> None:
        for i, value in enumerate(self.buf):
            self.buf[i] = value ^ 0xFF
