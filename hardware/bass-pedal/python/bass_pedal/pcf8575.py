"""PCF8575 16-bit quasi-bidirectional I/O expander.

Pin numbering matches the Adafruit / typical-breakout silk (P0–P15):

    P0–P7  = TI P00–P07 (written as the first I2C data byte)
    P8–P15 = TI P10–P17 (written as the second I2C data byte)

The part powers up with every pin high (weak current source). That is the
safe idle for active-low OLED CS/RES. Outputs can sink strongly but source
only ~30–300 µA, so CS/DC/RES should have 4.7 kΩ–10 kΩ pull-ups to 3.3 V.
"""

from __future__ import annotations

from typing import Protocol

DEFAULT_ADDRESS = 0x20
ALL_HIGH = 0xFFFF


class I2CDevice(Protocol):
    def write(self, addr: int, data: bytes) -> None: ...
    def read(self, addr: int, n: int) -> bytes: ...


class Pcf8575:
    """Tracks the 16-bit output latch and writes it as two I2C bytes."""

    def __init__(
        self,
        i2c: I2CDevice,
        address: int = DEFAULT_ADDRESS,
        *,
        init: bool = True,
    ) -> None:
        if not 0x20 <= address <= 0x27:
            raise ValueError(
                f"PCF8575 address must be 0x20-0x27 (A2/A1/A0 straps), got 0x{address:02x}"
            )
        self._i2c = i2c
        self.address = address
        self._latch = ALL_HIGH
        if init:
            self.write_latch(ALL_HIGH)

    @property
    def latch(self) -> int:
        return self._latch

    def write_latch(self, value: int) -> None:
        value &= 0xFFFF
        self._latch = value
        self._i2c.write(
            self.address,
            bytes((value & 0xFF, (value >> 8) & 0xFF)),
        )

    def update(self, clear_mask: int = 0, set_mask: int = 0) -> None:
        """Clear bits then set bits in one I2C write (DC/CS change together)."""
        self.write_latch((self._latch & ~clear_mask) | set_mask)

    def pin_high(self, pin: int) -> None:
        self._check_pin(pin)
        self.update(set_mask=1 << pin)

    def pin_low(self, pin: int) -> None:
        self._check_pin(pin)
        self.update(clear_mask=1 << pin)

    def read_pins(self) -> int:
        """Return live pin levels. Driven-low outputs read 0; floating inputs read 1."""
        data = self._i2c.read(self.address, 2)
        if len(data) != 2:
            raise OSError(f"PCF8575 read returned {len(data)} bytes, expected 2")
        return data[0] | (data[1] << 8)

    def pin_is_low(self, pin: int) -> bool:
        self._check_pin(pin)
        return (self.read_pins() & (1 << pin)) == 0

    @staticmethod
    def _check_pin(pin: int) -> None:
        if not 0 <= pin <= 15:
            raise ValueError(f"PCF8575 pin must be 0-15, got {pin}")
