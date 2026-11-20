#!/usr/bin/env python3
"""Bluetooth PIN tests. No adapter required."""
import os
import sys
import tempfile
import unittest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "scripts"))
sys.path.insert(0, SCRIPTS)

import pipedal_bt_pin as pin  # noqa: E402


class ParsePinTest(unittest.TestCase):
    def test_star_prefix_from_nap_file(self):
        self.assertEqual(pin.parse_pin_line("* 001037"), "001037")

    def test_rejects_short_and_long(self):
        self.assertEqual(pin.parse_pin_line("123"), "")
        self.assertEqual(pin.parse_pin_line("123456789"), "")

    def test_rejects_non_digits(self):
        self.assertEqual(pin.parse_pin_line("10ab"), "")

    def test_read_pin_file_and_env(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("* 001037\n")
            path = f.name
        try:
            self.assertEqual(pin.read_pin(path), "001037")
            self.assertEqual(pin.read_pin("/no/such/pin", {"PIPEDAL_BT_PIN": "2468"}), "2468")
        finally:
            os.unlink(path)


class VariantsTest(unittest.TestCase):
    def test_001037_includes_stripped_1037(self):
        v = pin.pin_variants("001037")
        self.assertEqual(v[0], "001037")
        self.assertIn("1037", v)

    def test_1037_includes_padded_001037(self):
        v = pin.pin_variants("1037")
        self.assertIn("1037", v)
        self.assertIn("001037", v)


class MatchTest(unittest.TestCase):
    def test_exact_and_leading_zeros(self):
        self.assertTrue(pin.pins_match("001037", "001037"))
        self.assertTrue(pin.pins_match("1037", "001037"))
        self.assertTrue(pin.pins_match("001037", "1037"))

    def test_wrong_pin_rejected(self):
        self.assertFalse(pin.pins_match("0000", "001037"))
        self.assertFalse(pin.pins_match("", "001037"))
        self.assertFalse(pin.pins_match("abcd", "001037"))
        self.assertFalse(pin.pins_match("001038", "001037"))


class IosLegacyFailureTest(unittest.TestCase):
    """From the Pi btmon log: both spellings die in ~100ms after PIN Reply."""

    def test_001037_auth_failure_is_legacy_ios_breakage(self):
        self.assertTrue(pin.is_ios_legacy_pin_failure(1458.896267, 1458.999870))

    def test_1037_auth_failure_is_the_same_breakage(self):
        self.assertTrue(pin.is_ios_legacy_pin_failure(1471.945240, 1472.053847))

    def test_both_lengths_fail_so_length_is_not_the_bug(self):
        self.assertTrue(pin.is_ios_legacy_pin_failure(1458.896, 1458.999))
        self.assertTrue(pin.is_ios_legacy_pin_failure(1471.945, 1472.053))

    def test_slow_disconnect_is_not_that_pattern(self):
        self.assertFalse(pin.is_ios_legacy_pin_failure(0.0, 5.0))
        self.assertFalse(pin.is_ios_legacy_pin_failure(1.0, 1.05, "Remote User Terminated"))


class RadioPolicyTest(unittest.TestCase):
    def test_no_hciconfig_during_handshake(self):
        self.assertTrue(pin.must_not_touch_radio(True, "sspmode"))
        self.assertTrue(pin.must_not_touch_radio(True, "hciconfig"))
        self.assertFalse(pin.must_not_touch_radio(False, "sspmode"))

    def test_agent_source_does_not_call_hciconfig(self):
        with open(os.path.join(SCRIPTS, "pipedal-bt-agent"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("subprocess", src)
        self.assertNotIn("force_legacy_pin", src)
        self.assertNotIn("timeout_add_seconds(30", src)
        self.assertIn('CAPABILITY = "KeyboardDisplay"', src)
        pin_fn = src[src.find("def RequestPinCode"): src.find("def RequestPasskey")]
        self.assertIn("raise Rejected", pin_fn)
        self.assertNotIn("sleep", pin_fn)
        self.assertNotIn("timeout_add", pin_fn)
        self.assertNotIn("_next_pin", src)
        conf = src[src.find("def RequestConfirmation"): src.find("def DisplayPinCode")]
        self.assertIn("def RequestConfirmation", conf)
        self.assertNotIn("raise Rejected", conf)

    def test_nap_keeps_ssp_on(self):
        with open(os.path.join(SCRIPTS, "pipedal-bt-nap"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("ssp on", src)
        self.assertIn("sspmode 1", src)
        self.assertNotIn("ssp off", src)
        self.assertNotIn("sspmode 0", src)


if __name__ == "__main__":
    unittest.main()
