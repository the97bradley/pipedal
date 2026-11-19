"""PIN compare helpers for PiPedal Bluetooth.

iOS keypad pairing does not deliver the typed digits to userspace. HCI
traces on bcm4345 show PIN Code Reply 001037 and 1037 both followed by
Authentication Failure in ~100ms. Software compare (HTTP on pan0) is the
path that can accept or reject 001037.
"""
import os

DEFAULT_PIN_FILE = "/run/pipedal/bt-pin"


def parse_pin_line(line):
    line = (line or "").strip()
    if line.startswith("* "):
        line = line[2:].strip()
    if line.isdigit() and 4 <= len(line) <= 8:
        return line
    return ""


def read_pin(pin_file=DEFAULT_PIN_FILE, environ=None):
    try:
        with open(pin_file, encoding="utf-8") as f:
            pin = parse_pin_line(f.readline())
            if pin:
                return pin
    except OSError:
        pass
    env = (environ if environ is not None else os.environ).get("PIPEDAL_BT_PIN", "").strip()
    return parse_pin_line(env)


def pin_variants(pin):
    if not pin:
        return []
    variants = [pin]
    stripped = pin.lstrip("0") or "0"
    if len(stripped) < 4:
        stripped = stripped.zfill(4)
    if stripped not in variants:
        variants.append(stripped)
    padded = pin.zfill(6)
    if padded not in variants:
        variants.append(padded)
    return variants


def pins_match(got, expected):
    if not got or not expected:
        return False
    if not str(got).isdigit() or not str(expected).isdigit():
        return False
    return str(got) == str(expected) or int(got) == int(expected)


def is_ios_legacy_pin_failure(pin_reply_ms, disconnect_ms, reason="Authentication Failure"):
    """True when the controller rejects the PIN faster than a human can type."""
    if "Authentication Failure" not in reason:
        return False
    if disconnect_ms is None or pin_reply_ms is None:
        return False
    return 0 <= (disconnect_ms - pin_reply_ms) <= 0.25


def must_not_touch_radio(handshake_active, action):
    """True when hciconfig/btmgmt during PIN Code Reply would drop the ACL."""
    return bool(handshake_active) and action in ("sspmode", "btmgmt", "hciconfig")
