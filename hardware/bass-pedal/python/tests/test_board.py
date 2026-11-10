import unittest

from bass_pedal.board import BassPedalBoard, PedalConfig
from bass_pedal.buses import FakeI2C, FakeSPI
from bass_pedal.oled import CS_MASK, FOOTSWITCH_MASK, OledBus
from bass_pedal.pcf8575 import Pcf8575


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class BoardTests(unittest.TestCase):
    def test_initialize_writes_cs_high_before_any_spi(self):
        board, i2c, spi = BassPedalBoard.mock()
        self.assertTrue(i2c.writes, "expander must be programmed before SPI")
        self.assertEqual(i2c.writes[0][1], b"\xff\xff")
        self.assertEqual(spi.xfers, [])
        board.initialize()
        self.assertTrue(spi.xfers)
        first_latch = spi.latch_at_xfer[0]
        active = CS_MASK & ~first_latch
        self.assertEqual(active.bit_count(), 1)

    def test_only_one_cs_low_per_spi_transfer(self):
        board, _i2c, spi = BassPedalBoard.mock()
        board.initialize()
        board.show_labels()
        for latch in spi.latch_at_xfer:
            low = CS_MASK & ~latch
            self.assertEqual(low.bit_count(), 1, hex(latch))
            self.assertEqual(latch & FOOTSWITCH_MASK, FOOTSWITCH_MASK)

    def test_footswitch_bits_stay_high_in_the_output_latch(self):
        board, i2c, _spi = BassPedalBoard.mock()
        board.initialize()
        i2c.ground_pins(1 << 8)
        self.assertEqual(board.expander.latch & FOOTSWITCH_MASK, FOOTSWITCH_MASK)
        self.assertEqual(board.read_pressed(), [0])

    def test_debounce_emits_one_press_and_one_release(self):
        clock = Clock()
        config = PedalConfig(debounce_seconds=0.020)
        i2c = FakeI2C()
        expander = Pcf8575(i2c)
        spi = FakeSPI(latch_fn=lambda: expander.latch)
        oleds = OledBus(expander, spi)
        board = BassPedalBoard(expander, oleds, config=config, clock=clock)

        self.assertEqual(board.poll_switches(), [])
        i2c.ground_pins(1 << 9)
        self.assertEqual(board.poll_switches(), [])
        clock.advance(0.010)
        self.assertEqual(board.poll_switches(), [])
        clock.advance(0.015)
        events = board.poll_switches()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].index, 1)
        self.assertTrue(events[0].pressed)

        i2c.ground_pins(0)
        self.assertEqual(board.poll_switches(), [])
        clock.advance(0.025)
        events = board.poll_switches()
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].pressed)

    def test_show_labels_writes_every_display(self):
        board, _i2c, _spi = BassPedalBoard.mock()
        board.initialize()
        board.show_labels(("OD", "DIST", "MOD", "DLY", "REV", "TUNER"))
        displays = {display for _phase, display, _payload in board.oleds.transfers if _phase == "data"}
        self.assertEqual(displays, {0, 1, 2, 3, 4, 5})


if __name__ == "__main__":
    unittest.main()
