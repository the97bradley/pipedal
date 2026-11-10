import unittest

from bass_pedal.buses import FakeI2C, FakeSPI
from bass_pedal.oled import (
    CS_MASK,
    DC_MASK,
    FRAMEBUFFER_SIZE,
    RES_MASK,
    Framebuffer,
    OledBus,
    OledController,
    SH1106_COLUMN_OFFSET,
)
from bass_pedal.pcf8575 import Pcf8575


def _make_bus(controller=OledController.SSD1306):
    i2c = FakeI2C()
    expander = Pcf8575(i2c)
    spi = FakeSPI(latch_fn=lambda: expander.latch)
    bus = OledBus(expander, spi, controller=controller)
    return bus, expander, spi, i2c


class OledBusTests(unittest.TestCase):
    def test_reset_holds_all_chip_selects_inactive(self):
        bus, expander, spi, i2c = _make_bus()
        i2c.writes.clear()
        levels = []

        def sleep(_seconds):
            levels.append(expander.latch)

        bus._sleep = sleep
        bus.hardware_reset()
        self.assertTrue(levels)
        for latch in levels:
            self.assertEqual(latch & CS_MASK, CS_MASK, "a CS line went active during RESET")
        self.assertEqual(expander.latch & RES_MASK, RES_MASK)
        self.assertEqual(spi.xfers, [])

    def test_command_asserts_one_cs_and_dc_low(self):
        bus, _expander, spi, _i2c = _make_bus()
        bus.command(2, (0xAE, 0xAF))
        self.assertEqual(spi.xfers, [bytes((0xAE, 0xAF))])
        latch = spi.latch_at_xfer[0]
        self.assertEqual(latch & CS_MASK, CS_MASK & ~(1 << 2))
        self.assertEqual(latch & DC_MASK, 0)
        self.assertEqual(latch & RES_MASK, RES_MASK)
        self.assertEqual(bus.expander.latch & CS_MASK, CS_MASK)

    def test_data_asserts_dc_high(self):
        bus, _expander, spi, _i2c = _make_bus()
        bus.data(0, (0x00, 0xFF))
        latch = spi.latch_at_xfer[0]
        self.assertEqual(latch & CS_MASK, CS_MASK & ~(1 << 0))
        self.assertEqual(latch & DC_MASK, DC_MASK)

    def test_dc_does_not_change_during_a_transfer(self):
        bus, expander, spi, _i2c = _make_bus()
        seen = []
        original = spi.xfer2

        def wrapped(data):
            seen.append(expander.latch & DC_MASK)
            return original(data)

        spi.xfer2 = wrapped
        bus.command(1, bytes(range(64)))
        self.assertTrue(seen)
        self.assertEqual(set(seen), {0})

    def test_spi_failure_still_releases_cs(self):
        bus, expander, spi, _i2c = _make_bus()

        def boom(_data):
            raise OSError("spi NAK")

        spi.xfer2 = boom
        with self.assertRaises(OSError):
            bus.command(4, (0xAE,))
        self.assertEqual(expander.latch & CS_MASK, CS_MASK)

    def test_sh1106_column_offset(self):
        bus, _expander, _spi, _i2c = _make_bus(OledController.SH1106)
        bus._set_address(0, page=3, column=0)
        cmd = next(payload for phase, _display, payload in bus.transfers if phase == "cmd")
        self.assertEqual(cmd[0], 0xB3)
        column = ((cmd[1] & 0x0F) << 4) | (cmd[2] & 0x0F)
        self.assertEqual(column, SH1106_COLUMN_OFFSET)

    def test_ssd1306_column_starts_at_zero(self):
        bus, _expander, _spi, _i2c = _make_bus(OledController.SSD1306)
        bus._set_address(0, page=0, column=0)
        cmd = bus.transfers[-1][2]
        column = (cmd[1] & 0x0F) | ((cmd[2] & 0x0F) << 4)
        self.assertEqual(column, 0)

    def test_framebuffer_text_sets_pixels(self):
        fb = Framebuffer()
        fb.text(0, 0, "A")
        self.assertNotEqual(bytes(fb.buf), b"\x00" * FRAMEBUFFER_SIZE)
        fb.clear()
        self.assertEqual(bytes(fb.buf), b"\x00" * FRAMEBUFFER_SIZE)


if __name__ == "__main__":
    unittest.main()
