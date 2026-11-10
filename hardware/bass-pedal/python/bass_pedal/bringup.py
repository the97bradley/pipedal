"""Hardware bring-up: init six OLEDs, print footswitch edges.

Run on the Pi after the config.txt overlays are loaded:

    cd hardware/bass-pedal/python
    python3 -m bass_pedal.bringup

Use --mock on a laptop to exercise the same path without SPI/I2C hardware.
"""

from __future__ import annotations

import argparse
import sys

from .board import BassPedalBoard, PedalConfig, SwitchEvent
from .buses import FORBIDDEN_I2C_BUSES, available_i2c_buses, detect_expander_bus
from .oled import OledController
from .pcf8575 import DEFAULT_ADDRESS, SWITCH_ADDRESS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PiPedal bass-pedal OLED/footswitch bring-up")
    parser.add_argument("--mock", action="store_true", help="Use in-memory I2C/SPI (no hardware)")
    parser.add_argument("--bus", type=int, default=None, help="Expander I2C bus number (not 0 or 1)")
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=DEFAULT_ADDRESS,
        help="Display PCF8575 address (default 0x20, A0/A1/A2 low)",
    )
    parser.add_argument(
        "--switch-address",
        type=lambda value: int(value, 0),
        default=SWITCH_ADDRESS,
        help="Switch PCF8575 address (default 0x21, A0 high)",
    )
    parser.add_argument(
        "--controller",
        choices=[item.value for item in OledController],
        default=OledController.SSD1306.value,
        help="OLED controller. 0.96in modules are usually ssd1306; 1.3in often sh1106.",
    )
    parser.add_argument("--once", action="store_true", help="Init displays and exit (no switch loop)")
    parser.add_argument("--scan", action="store_true", help="List I2C buses and refuse bus 0/1, then exit")
    return parser.parse_args(argv)


def scan_buses() -> int:
    buses = available_i2c_buses()
    print("I2C buses:", ", ".join(f"/dev/i2c-{b}" for b in buses) or "(none)")
    for bus in buses:
        note = " FORBIDDEN" if bus in FORBIDDEN_I2C_BUSES else ""
        print(f"  {bus}:{note}")
    try:
        detected = detect_expander_bus()
        print(f"expander bus candidate: /dev/i2c-{detected}")
        print("expect PCF8575 at 0x20 (OLEDs) and 0x21 (switches)")
    except FileNotFoundError as exc:
        print(exc)
        return 1
    return 0


def _on_event(event: SwitchEvent) -> None:
    state = "pressed" if event.pressed else "released"
    print(f"footswitch {event.index + 1} (P{event.pin}) {state}", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.scan:
        return scan_buses()

    config = PedalConfig(
        i2c_bus=args.bus,
        i2c_address=args.address,
        switch_address=args.switch_address,
        controller=OledController(args.controller),
    )
    if args.mock:
        board, _i2c, _spi = BassPedalBoard.mock(config)
        print("mock buses — no hardware access")
    else:
        board = BassPedalBoard.open_hardware(config)

    print("initializing PCF8575s (OLEDs 0x%02x, switches 0x%02x)…" % (
        config.i2c_address, config.switch_address
    ))
    board.initialize()
    board.show_labels()
    print("displays initialized.")
    if args.once:
        return 0
    if args.mock:
        print("mock mode: no switches will fire unless grounded in code")
        return 0
    print("Press footswitches (Ctrl-C to exit).")
    try:
        board.run_poll_loop(_on_event)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
