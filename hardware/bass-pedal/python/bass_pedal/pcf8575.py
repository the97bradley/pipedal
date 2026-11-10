"""PCF8575 16-bit I/O expander (PCF8574 also accepted).

This pedal uses two PCF8575s on the dedicated BCM 22/23 I2C bus:

    0x20  A0/A1/A2 low   OLED CS / DC / RESET
    0x21  A0 high        footswitches

Quasi-bidirectional: power-on all pins high (weak current source), strong sink.
CS/DC/RES want 4.7 kΩ–10 kΩ pull-ups to 3.3 V. Footswitches to GND can use the
weak pull-up plus an extra 10 kΩ.

PCF8575 addresses are 0x20–0x27 from A2/A1/A0. PCF8574 (8-bit) and PCF8574A
(0x38–0x3F) still construct if you have those instead.
"""

from __future__ import annotations

from typing import Protocol

DEFAULT_ADDRESS = 0x20
SWITCH_ADDRESS = 0x21
SWITCH_ADDRESS_8574A = 0x38
PCF8574_ADDRESSES = frozenset(range(0x20, 0x28)) | frozenset(range(0x38, 0x40))
PCF8575_ADDRESSES = frozenset(range(0x20, 0x28))


class I2CDevice(Protocol):
    def write(self, addr: int, data: bytes) -> None: ...
    def read(self, addr: int, n: int) -> bytes: ...


def _validate_address(bits: int, address: int) -> None:
    allowed = PCF8575_ADDRESSES if bits == 16 else PCF8574_ADDRESSES
    if address not in allowed:
        kind = "PCF8575" if bits == 16 else "PCF8574/PCF8574A"
        raise ValueError(f"{kind} address 0x{address:02x} is not valid")


class Pcf857x:
    """Tracks the output latch and writes 1 byte (8574) or 2 bytes (8575)."""

    def __init__(
        self,
        i2c: I2CDevice,
        address: int = DEFAULT_ADDRESS,
        *,
        bits: int = 16,
        init: bool = True,
    ) -> None:
        if bits not in (8, 16):
            raise ValueError(f"PCF857x width must be 8 or 16, got {bits}")
        _validate_address(bits, address)
        self._i2c = i2c
        self.address = address
        self.bits = bits
        self.width_mask = (1 << bits) - 1
        self._latch = self.width_mask
        if init:
            self.write_latch(self.width_mask)

    @property
    def latch(self) -> int:
        return self._latch

    def write_latch(self, value: int) -> None:
        value &= self.width_mask
        self._latch = value
        if self.bits == 8:
            self._i2c.write(self.address, bytes((value & 0xFF,)))
        else:
            self._i2c.write(self.address, bytes((value & 0xFF, (value >> 8) & 0xFF)))

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
        nbytes = 1 if self.bits == 8 else 2
        data = self._i2c.read(self.address, nbytes)
        if len(data) != nbytes:
            raise OSError(f"PCF857x read returned {len(data)} bytes, expected {nbytes}")
        value = data[0]
        if nbytes == 2:
            value |= data[1] << 8
        return value

    def pin_is_low(self, pin: int) -> bool:
        self._check_pin(pin)
        return (self.read_pins() & (1 << pin)) == 0

    def _check_pin(self, pin: int) -> None:
        if not 0 <= pin < self.bits:
            raise ValueError(f"PCF857x pin must be 0-{self.bits - 1}, got {pin}")


class Pcf8574(Pcf857x):
    def __init__(self, i2c: I2CDevice, address: int = DEFAULT_ADDRESS, **kwargs) -> None:
        super().__init__(i2c, address, bits=8, **kwargs)


class Pcf8575(Pcf857x):
    def __init__(self, i2c: I2CDevice, address: int = DEFAULT_ADDRESS, **kwargs) -> None:
        super().__init__(i2c, address, bits=16, **kwargs)


ALL_HIGH = 0xFFFF
