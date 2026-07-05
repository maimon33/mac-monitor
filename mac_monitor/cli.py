from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import __version__
from .config import default_config_json, load_config, resolve_config_path
from .console import TerminalScreen
from .monitor import Monitor
from .render import render_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mac-monitor",
        description="Show macOS network traffic plus CPU, RAM, disk, and top process stats.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", help="Path to a JSON config file.")
    parser.add_argument("--print-config", action="store_true", help="Print the default config and exit.")
    parser.add_argument("--once", action="store_true", help="Print one snapshot and exit.")
    parser.add_argument("--json", action="store_true", help="Print snapshots as JSON.")
    parser.add_argument("--screen", action="store_true", help="Force full-screen terminal console mode.")
    parser.add_argument("--no-screen", action="store_true", help="Disable full-screen terminal console mode.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the screen between watch updates.")
    parser.add_argument("--interval", type=float, help="Seconds between samples.")
    parser.add_argument("--interface", action="append", dest="interfaces", help="Interface to include, repeatable.")
    parser.add_argument("--all-interfaces", action="store_true", help="Show logical, virtual, VPN, and bridge interfaces too.")
    parser.add_argument("--show-loopback", action="store_true", help="Include lo0.")
    parser.add_argument("--top", type=int, dest="top_processes", help="Number of top CPU processes.")
    parser.add_argument("--top-count", type=int, help="Rows to show in each TOP column.")
    parser.add_argument("--disk-limit", type=int, help="Number of mounted disks to show.")
    parser.add_argument("--view", choices=("all", "overview", "top"), help="Console view to render.")
    parser.add_argument("--no-top", action="store_true", help="Shortcut for --view overview.")
    parser.add_argument("--warn-cpu", type=float, dest="warn_cpu_percent", help="CPU warning threshold percent.")
    parser.add_argument("--warn-memory", type=float, dest="warn_memory_percent", help="Memory warning threshold percent.")
    parser.add_argument("--warn-disk", type=float, dest="warn_disk_percent", help="Disk warning threshold percent.")
    return parser


def apply_args(config, args):
    for name in (
        "interval",
        "interfaces",
        "top_processes",
        "top_count",
        "disk_limit",
        "view",
        "warn_cpu_percent",
        "warn_memory_percent",
        "warn_disk_percent",
    ):
        value = getattr(args, name)
        if value is not None:
            setattr(config, name, value)
    if args.show_loopback:
        config.show_loopback = True
    if args.all_interfaces:
        config.show_logical_interfaces = True
    if args.no_top:
        config.view = "overview"
    return config


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_config:
        print(default_config_json())
        print(f"\nDefault path: {resolve_config_path(args.config)}", file=sys.stderr)
        return 0

    try:
        config = apply_args(load_config(args.config), args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"mac-monitor: {exc}", file=sys.stderr)
        return 2

    if config.interval <= 0:
        print("mac-monitor: interval must be greater than 0", file=sys.stderr)
        return 2

    monitor = Monitor(
        interfaces=config.interfaces,
        show_loopback=config.show_loopback,
        show_logical_interfaces=config.show_logical_interfaces,
        top_processes=max(0, config.top_processes, config.top_count),
        disk_limit=max(0, config.disk_limit),
    )

    try:
        if args.once:
            snapshot = monitor.sample()
            emit(snapshot, config, args.json, clear=False)
            return 0

        use_screen = should_use_screen(args)
        with TerminalScreen(use_screen) as screen:
            while True:
                snapshot = monitor.sample()
                emit(snapshot, config, args.json, prefix=screen.frame_prefix(), clear=not args.no_clear and not args.json and not use_screen)
                time.sleep(config.interval)
    except KeyboardInterrupt:
        return 0
    except BrokenPipeError:
        return 0


def should_use_screen(args) -> bool:
    if args.once or args.json or args.no_clear or args.no_screen:
        return False
    if args.screen:
        return True
    return os.isatty(sys.stdout.fileno())


def emit(snapshot, config, as_json: bool, prefix: str = "", clear: bool = False) -> None:
    if as_json:
        print(json.dumps(snapshot.to_dict(), sort_keys=True), flush=True)
        return

    if clear:
        prefix = "\033[2J\033[H" + prefix
    sys.stdout.write(
        prefix
        + render_snapshot(
            snapshot,
            warn_cpu=config.warn_cpu_percent,
            warn_memory=config.warn_memory_percent,
            warn_disk=config.warn_disk_percent,
            view=config.view,
            top_count=max(0, config.top_count),
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
