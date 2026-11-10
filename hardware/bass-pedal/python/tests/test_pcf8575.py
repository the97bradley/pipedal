import unittest

from bass_pedal.buses import FakeI2C, assert_expander_bus
from bass_pedal.pcf8575 import ALL_HIGH, Pcf8574, Pcf8575


class Pcf8575Tests(unittest.TestCase):
    def test_startup_writes_all_high(self):
        i2c = FakeI2C()
        chip = Pcf8575(i2c, 0x20)
        self.assertEqual(i2c.writes, [(0x20, b"\xff\xff")])
        self.assertEqual(chip.latch, ALL_HIGH)

    def test_rejects_non_pcf8575_address(self):
        with self.assertRaises(ValueError):
            Pcf8575(FakeI2C(), 0x4D)

    def test_8574_writes_one_byte(self):
        i2c = FakeI2C()
        Pcf8574(i2c, 0x20)
        self.assertEqual(i2c.writes, [(0x20, b"\xff")])

    def test_update_is_one_write_clear_then_set(self):
        i2c = FakeI2C()
        chip = Pcf8575(i2c)
        i2c.writes.clear()
        chip.update(clear_mask=0x05, set_mask=0x40)
        self.assertEqual(len(i2c.writes), 1)
        low, high = i2c.writes[0][1]
        value = low | (high << 8)
        self.assertEqual(value & 0x05, 0)
        self.assertEqual(value & 0x40, 0x40)
        self.assertEqual(value & 0xFF00, 0xFF00)

    def test_read_follows_latch_and_grounded_inputs(self):
        i2c = FakeI2C()
        chip = Pcf8575(i2c, 0x21)
        i2c.ground_pins(1 << 0, addr=0x21)
        pins = chip.read_pins()
        self.assertEqual(pins & (1 << 0), 0)
        self.assertEqual(chip.latch & (1 << 0), 1 << 0)

    def test_hifiberry_i2c_bus_is_forbidden(self):
        with self.assertRaises(RuntimeError):
            assert_expander_bus(1)
        with self.assertRaises(RuntimeError):
            assert_expander_bus(0)


if __name__ == "__main__":
    unittest.main()
