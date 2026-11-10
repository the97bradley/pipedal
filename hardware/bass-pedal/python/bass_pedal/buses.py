"""SPI and I2C open helpers. Refuses the HiFiBerry I2C bus."""

from __future__ import annotations

import glob
import os
from typing import Any

HIFIBERRY_I2C_BUS = 1
ID_EEPROM_I2C_BUS = 0
FORBIDDEN_I2C_BUSES = {ID_EEPROM_I2C_BUS, HIFIBERRY_I2C_BUS}

# Preferred expander buses: Pi 5 i2c3-pi5, Pi 4 i2c6, i2c-gpio fallback.
PREFERRED_EXPANDER_BUSES = (3, 6, 4, 5, 2)


class FakeI2C:
    """In-memory PCF857x stand-in for tests and `--mock` bring-up."""

    def __init__(self) -> None:
        self.memory: dict[int, bytearray] = {}
        self.writes: list[tuple[int, bytes]] = []
        self.grounded: dict[int, int] = {}

    def write(self, addr: int, data: bytes) -> None:
        payload = bytes(data)
        self.writes.append((addr, payload))
        self.memory[addr] = bytearray(payload)

    def read(self, addr: int, n: int) -> bytes:
        latched = self.memory.get(addr, bytearray(b"\xff\xff"))
        value = int.from_bytes(latched[:2].ljust(2, b"\xff"), "little")
        value &= ~self.grounded.get(addr, 0)
        return value.to_bytes(2, "little")[:n]

    def ground_pins(self, mask: int, addr: int) -> None:
        self.grounded[addr] = mask & 0xFFFF


class FakeSPI:
    """Records SPI transfers and the expander latch at each transfer."""

    def __init__(self, latch_fn=None) -> None:
        self.no_cs = True
        self.mode = 0
        self.max_speed_hz = 0
        self.xfers: list[bytes] = []
        self.latch_at_xfer: list[int] = []
        self._latch_fn = latch_fn

    def xfer2(self, data) -> list[int]:
        payload = bytes(data)
        self.xfers.append(payload)
        if self._latch_fn is not None:
            self.latch_at_xfer.append(int(self._latch_fn()))
        return [0] * len(payload)

    writebytes = xfer2


class SmbusI2C:
    """Raw I2C for register-less devices (PCF8575 has no command byte)."""

    def __init__(self, bus: Any) -> None:
        self._bus = bus

    def write(self, addr: int, data: bytes) -> None:
        if not data:
            raise ValueError("I2C write requires at least one byte")
        from smbus2 import i2c_msg

        self._bus.i2c_rdwr(i2c_msg.write(addr, data))

    def read(self, addr: int, n: int) -> bytes:
        if n <= 0:
            return b""
        from smbus2 import i2c_msg

        msg = i2c_msg.read(addr, n)
        self._bus.i2c_rdwr(msg)
        return bytes(msg)


def assert_expander_bus(bus_id: int) -> None:
    if bus_id in FORBIDDEN_I2C_BUSES:
        raise RuntimeError(
            f"/dev/i2c-{bus_id} is reserved "
            f"({'HiFiBerry PCM5122/PCM1863' if bus_id == HIFIBERRY_I2C_BUS else 'HAT ID EEPROM'}). "
            "Put the PCF8575 on the dedicated BCM 22/23 bus."
        )


def available_i2c_buses() -> list[int]:
    buses = []
    for path in sorted(glob.glob("/dev/i2c-*")):
        suffix = path.rsplit("-", 1)[-1]
        if suffix.isdigit():
            buses.append(int(suffix))
    return buses


def detect_expander_bus(preferred: tuple[int, ...] = PREFERRED_EXPANDER_BUSES) -> int:
    present = set(available_i2c_buses())
    for bus_id in preferred:
        if bus_id in present and bus_id not in FORBIDDEN_I2C_BUSES:
            return bus_id
    candidates = [b for b in sorted(present) if b not in FORBIDDEN_I2C_BUSES]
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        "No expander I2C bus found. Enable i2c3-pi5 / i2c6 / i2c-gpio on BCM 22/23."
    )


def open_i2c(bus_id: int | None = None):
    if bus_id is None:
        bus_id = detect_expander_bus()
    assert_expander_bus(bus_id)
    try:
        from smbus2 import SMBus
    except ImportError as exc:
        raise ImportError("smbus2 is required on hardware (pip install smbus2)") from exc
    if not os.path.exists(f"/dev/i2c-{bus_id}"):
        raise FileNotFoundError(f"/dev/i2c-{bus_id} does not exist")
    return bus_id, SmbusI2C(SMBus(bus_id))


def open_spi(bus: int = 0, device: int = 0, speed_hz: int = 8_000_000):
    try:
        import spidev
    except ImportError as exc:
        raise ImportError("spidev is required on hardware (pip install spidev)") from exc
    spi = spidev.SpiDev()
    spi.open(bus, device)
    spi.mode = 0
    spi.no_cs = True
    spi.max_speed_hz = speed_hz
    spi.bits_per_word = 8
    return spi
