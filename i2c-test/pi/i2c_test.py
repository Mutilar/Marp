"""Utility helpers for bringing up Raspberry Pi ↔ Arduino I2C link.

The script exposes a small CLI for sending smoke-test commands to the
Arduino-based motion co-processor described in the project README.

Example usage (run on Raspberry Pi):

    python3 i2c_test.py ping
    python3 i2c_test.py status
    python3 i2c_test.py watch --interval 2.0
    python3 i2c_test.py led on

Requires the "smbus2" package which can be installed with pip:

    pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import struct
import sys
import time
from dataclasses import dataclass
from typing import Tuple

try:
    from smbus2 import SMBus
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise SystemExit(
        "Missing dependency smbus2. Install with `pip install smbus2` or use "
        "`pip install -r requirements.txt`."
    ) from exc


I2C_ADDRESS = 0x08
PING_RESPONSE_SIZE = 2
TELEMETRY_SIZE = 6

CMD_PING = 0x01
CMD_GET_TELEMETRY = 0x02
CMD_SET_LED = 0x10

LED_AUTO = 0
LED_OFF = 1
LED_ON = 2

FLAG_PAN_LIMIT = 0x01
FLAG_SHUTTER_LIMIT = 0x02
FLAG_LED_STATE = 0x80


@dataclass(frozen=True)
class Telemetry:
    """Decoded telemetry snapshot from the Arduino co-processor."""

    major_version: int
    minor_version: int
    uptime_seconds: int
    pan_limit_triggered: bool
    shutter_limit_triggered: bool
    led_is_on: bool
    heartbeat_counter: int

    @classmethod
    def from_bytes(cls, payload: bytes) -> "Telemetry":
        if len(payload) != TELEMETRY_SIZE:
            raise ValueError(
                f"Telemetry payload must be {TELEMETRY_SIZE} bytes, got {len(payload)}"
            )
        major, minor, uptime_seconds, status_flags, heartbeat = struct.unpack(
            "<BBHBB", payload
        )
        return cls(
            major_version=major,
            minor_version=minor,
            uptime_seconds=uptime_seconds,
            pan_limit_triggered=bool(status_flags & FLAG_PAN_LIMIT),
            shutter_limit_triggered=bool(status_flags & FLAG_SHUTTER_LIMIT),
            led_is_on=bool(status_flags & FLAG_LED_STATE),
            heartbeat_counter=heartbeat,
        )


class I2CTestClient:
    """Simple wrapper around smbus2 for exchanging framed commands."""

    def __init__(self, bus_id: int, address: int = I2C_ADDRESS) -> None:
        self._bus_id = bus_id
        self._address = address
        self._bus = SMBus(bus_id)

    def close(self) -> None:
        self._bus.close()

    # Context manager helpers -------------------------------------------------
    def __enter__(self) -> "I2CTestClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Command helpers ---------------------------------------------------------
    def ping(self) -> bytes:
        self._bus.write_byte(self._address, CMD_PING)
        time.sleep(0.005)
        data = self._bus.read_i2c_block_data(self._address, 0x00, PING_RESPONSE_SIZE)
        return bytes(data)

    def read_telemetry(self) -> Tuple[Telemetry, bytes]:
        self._bus.write_byte(self._address, CMD_GET_TELEMETRY)
        time.sleep(0.005)
        raw_values = self._bus.read_i2c_block_data(self._address, 0x00, TELEMETRY_SIZE)
        payload = bytes(raw_values)
        return Telemetry.from_bytes(payload), payload

    def get_telemetry(self) -> Telemetry:
        telemetry, _ = self.read_telemetry()
        return telemetry

    def set_led(self, mode: int) -> None:
        self._bus.write_i2c_block_data(self._address, CMD_SET_LED, [mode])


def parse_args(argv: Tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bus",
        type=int,
        default=1,
        help="I2C bus number (Raspberry Pi 4/5 uses bus 1 for the 40-pin header).",
    )
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),
        default=I2C_ADDRESS,
        help="I2C slave address for the Arduino (default 0x08). Accepts hex like 0x08.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ping", help="Send ping command and print ASCII response.")

    parser_status = subparsers.add_parser(
        "status", help="Fetch a single telemetry snapshot and print the decoded fields."
    )
    parser_status.add_argument(
        "--raw",
        action="store_true",
        help="Show the raw bytes in addition to the decoded telemetry.",
    )

    parser_watch = subparsers.add_parser(
        "watch",
        help="Continuously poll telemetry and print updates until interrupted.",
    )
    parser_watch.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between polls (default: 1.0).",
    )

    parser_led = subparsers.add_parser(
        "led", help="Override or release the Arduino status LED heartbeat."
    )
    parser_led.add_argument(
        "mode",
        choices=("auto", "off", "on"),
        help="Select automatic heartbeat, force off, or force on.",
    )

    return parser.parse_args(argv)


def command_ping(client: I2CTestClient) -> int:
    response = client.ping()
    try:
        text = response.decode("ascii")
    except UnicodeDecodeError:
        text = "".join(f"\\x{b:02x}" for b in response)
    print(f"Ping response ({len(response)} bytes): {text}")
    return 0


def format_telemetry_table(data: Telemetry, raw: bytes | None = None) -> str:
    lines = [
        f"Firmware version  : {data.major_version}.{data.minor_version}",
        f"Uptime (s)        : {data.uptime_seconds}",
        f"Pan limit switch  : {'TRIGGERED' if data.pan_limit_triggered else 'open'}",
        f"Shutter limit     : {'TRIGGERED' if data.shutter_limit_triggered else 'open'}",
        f"Status LED        : {'ON' if data.led_is_on else 'off'}",
        f"Heartbeat counter : {data.heartbeat_counter}",
    ]
    if raw:
        lines.append(f"Raw bytes        : {' '.join(f'{b:02x}' for b in raw)}")
    return "\n".join(lines)


def command_status(client: I2CTestClient, *, raw: bool) -> int:
    if raw:
        telemetry, payload = client.read_telemetry()
    else:
        telemetry = client.get_telemetry()
        payload = None
    print(format_telemetry_table(telemetry, raw=payload))
    return 0


def command_watch(client: I2CTestClient, *, interval: float) -> int:
    print("Press Ctrl+C to stop telemetry watch...")
    try:
        while True:
            telemetry = client.get_telemetry()
            print(format_telemetry_table(telemetry))
            print("-" * 40)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatch stopped by user.")
        return 0


def command_led(client: I2CTestClient, *, mode: str) -> int:
    mapping = {"auto": LED_AUTO, "off": LED_OFF, "on": LED_ON}
    client.set_led(mapping[mode])
    print(f"LED control set to {mode} (value {mapping[mode]}).")
    return 0


def main(argv: Tuple[str, ...] | None = None) -> int:
    args = parse_args(tuple(sys.argv[1:] if argv is None else argv))
    try:
        with I2CTestClient(args.bus, args.address) as client:
            if args.command == "ping":
                return command_ping(client)
            if args.command == "status":
                return command_status(client, raw=getattr(args, "raw", False))
            if args.command == "watch":
                return command_watch(client, interval=getattr(args, "interval", 1.0))
            if args.command == "led":
                return command_led(client, mode=getattr(args, "mode"))
            raise AssertionError(f"Unhandled command {args.command}")
    except OSError as exc:
        print(
            "I2C communication failed. Ensure wiring is correct, the Arduino sketch "
            "is flashed, and you have permission to access /dev/i2c-*.",
            file=sys.stderr,
        )
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
