from __future__ import annotations

import datetime as dt
import os
from typing import Iterable

from .monitor import DiskStats, InterfaceStats, MemoryStats, ProcessStats, Snapshot


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"


def clear_screen() -> str:
    return "\033[2J\033[H"


def terminal_width(default: int = 80) -> int:
    if not os.isatty(1):
        return default
    try:
        return max(72, min(os.get_terminal_size().columns, 88))
    except OSError:
        return default


def section_rule(title: str, width: int) -> str:
    label = f" {title} "
    return f"{DIM}{label}{'-' * max(0, width - len(title) - 2)}{RESET}"


def human_bytes(value: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(value)
    for unit in units:
        if abs(size) < 1024.0:
            return f"{size:5.1f} {unit}"
        size /= 1024.0
    return f"{size:5.1f} EB"


def human_rate(value: float) -> str:
    return f"{human_bytes(value)}/s"


def color_percent(value: float, warn: float) -> str:
    if value >= warn:
        color = RED
    elif value >= warn * 0.75:
        color = YELLOW
    else:
        color = GREEN
    return f"{color}{value:5.1f}%{RESET}"


def bar(value: float, width: int = 24) -> str:
    filled = max(0, min(width, int(round(width * value / 100.0))))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def render_snapshot(
    snapshot: Snapshot,
    warn_cpu: float,
    warn_memory: float,
    warn_disk: float,
    view: str = "all",
    top_count: int = 5,
) -> str:
    lines = []
    width = terminal_width()
    stamp = dt.datetime.fromtimestamp(snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"{BOLD}mac-monitor{RESET} {DIM}{stamp} | Ctrl-C quit | --view all|overview|top{RESET}")

    if view != "top":
        lines.append(section_rule("SYSTEM", width))
        cpu = snapshot.cpu
        lines.append(
            f"{CYAN}CPU{RESET} {bar(cpu.percent, 14)} {color_percent(cpu.percent, warn_cpu)} "
            f"load {cpu.load_1m:.2f}/{cpu.load_5m:.2f}/{cpu.load_15m:.2f} cores {cpu.cores}"
            f"{top_cpu_summary(snapshot.processes)}"
        )

        memory = snapshot.memory
        lines.append(render_memory(memory, warn_memory, snapshot.processes))
        lines.append(section_rule("IO", width))
        lines.extend(render_network(snapshot.network, compact=True))
        lines.extend(render_disks(snapshot.disks, warn_disk, compact=True))

    if view in {"all", "top"}:
        lines.append(section_rule("TOP", width))
        lines.extend(render_top_columns(snapshot, top_count, warn_disk))

    lines.append(section_rule("MENU", width))
    lines.append(f"{DIM}views: all overview top | --top-count N | --json | --print-config{RESET}")
    return "\n".join(lines)


def render_memory(memory: MemoryStats, warn: float, processes: Iterable[ProcessStats] = ()) -> str:
    return (
        f"{CYAN}RAM{RESET} {bar(memory.percent, 14)} {color_percent(memory.percent, warn)} "
        f"{human_bytes(memory.used_bytes)} used / {human_bytes(memory.total_bytes)}"
        f"{top_memory_summary(processes)}"
    )


def render_network(rows: Iterable[InterfaceStats], compact: bool = False) -> list:
    if compact:
        lines = [f"{CYAN}NET{RESET} iface        rx/s       tx/s       total"]
    else:
        lines = [f"{CYAN}NET{RESET}  interface       rx/s       tx/s      rx total    tx total"]
    any_rows = False
    for item in rows:
        any_rows = True
        if compact:
            lines.append(
                f"    {item.name:<8} {human_rate(item.rx_rate):>10} {human_rate(item.tx_rate):>10} "
                f"{human_bytes(item.rx_bytes + item.tx_bytes):>10}"
            )
        else:
            lines.append(
                f"     {item.name:<10} {human_rate(item.rx_rate):>10} {human_rate(item.tx_rate):>10} "
                f"{human_bytes(item.rx_bytes):>11} {human_bytes(item.tx_bytes):>11}"
            )
    if not any_rows:
        lines.append("    no interfaces matched")
    return lines


def render_disks(rows: Iterable[DiskStats], warn: float, compact: bool = False) -> list:
    if compact:
        lines = [f"{CYAN}DSK{RESET} mount                 used       free       pct"]
    else:
        lines = [f"{CYAN}DISK{RESET} mount                 used       free       total       pct"]
    any_rows = False
    for item in rows:
        any_rows = True
        mount = item.mount
        if mount == "/System/Volumes/Data":
            mount = "Data"
        elif len(mount) > 20:
            mount = "..." + mount[-17:]
        if compact:
            lines.append(
                f"    {mount:<20} {human_bytes(item.used_bytes):>9} {human_bytes(item.free_bytes):>9} "
                f"{color_percent(item.percent, warn)}"
            )
        else:
            lines.append(
                f"     {mount:<20} {human_bytes(item.used_bytes):>9} {human_bytes(item.free_bytes):>9} "
                f"{human_bytes(item.total_bytes):>9} {color_percent(item.percent, warn)}"
            )
    if not any_rows:
        lines.append("    no mounted disks found")
    return lines


def render_processes(rows: Iterable[ProcessStats]) -> list:
    lines = [f"{CYAN}PROC{RESET} pid       cpu     mem     command"]
    for item in rows:
        command = item.command
        width = max(20, os.get_terminal_size().columns - 31) if os.isatty(1) else 60
        if len(command) > width:
            command = command[: width - 1] + "..."
        lines.append(f"     {item.pid:<7} {item.cpu_percent:5.1f}% {item.memory_percent:5.1f}% {command}")
    return lines


def render_top_columns(snapshot: Snapshot, count: int, warn_disk: float) -> list:
    cpu_rows = [format_cpu_top(item) for item in top_by_cpu(snapshot.processes)[:count]]
    ram_rows = [format_memory_top(item) for item in top_by_memory(snapshot.processes)[:count]]
    disk_rows = [format_disk_top(item, warn_disk) for item in top_by_disk(snapshot.disks)[:count]]
    net_rows = [format_network_top(item) for item in top_by_network(snapshot.network)[:count]]
    height = max(len(cpu_rows), len(ram_rows), len(disk_rows), len(net_rows), 1)

    lines = [f"{'CPU':<20} {'RAM':<20} {'DISK':<20} {'NET':<20}"]
    for index in range(height):
        lines.append(
            f"{ranked_cell(index, cpu_rows):<20} "
            + f"{ranked_cell(index, ram_rows):<20} "
            + f"{ranked_cell(index, disk_rows):<20} "
            + f"{ranked_cell(index, net_rows):<20}"
        )
    return lines


def ranked_cell(index: int, rows: list) -> str:
    if index >= len(rows):
        return ""
    return truncate(f"{index + 1}. {rows[index]}", 20)


def format_cpu_top(item: ProcessStats) -> str:
    cores = item.cpu_percent / 100.0
    return f"{short_command(item.command)} {cores:.1f} cores"


def format_memory_top(item: ProcessStats) -> str:
    return f"{short_command(item.command)} {human_bytes(item.memory_bytes).strip()}"


def format_disk_top(item: DiskStats, warn_disk: float) -> str:
    label = item.mount
    if label == "/System/Volumes/Data":
        label = "Data"
    return f"{label} {human_bytes(item.used_bytes).strip()} {item.percent:.0f}%"


def format_network_top(item: InterfaceStats) -> str:
    rate = human_rate(item.rx_rate + item.tx_rate).strip()
    return f"{item.name} {rate}"


def top_cpu_summary(processes: Iterable[ProcessStats]) -> str:
    rows = top_by_cpu(processes)
    if not rows:
        return ""
    top = rows[0]
    return f" | top {short_command(top.command)} {top.cpu_percent:.1f}%"


def top_memory_summary(processes: Iterable[ProcessStats]) -> str:
    rows = top_by_memory(processes)
    if not rows:
        return ""
    top = rows[0]
    return f" | top {short_command(top.command)} {top.memory_percent:.1f}%"


def top_by_cpu(processes: Iterable[ProcessStats]) -> list:
    return sorted(processes, key=lambda item: item.cpu_percent, reverse=True)


def top_by_memory(processes: Iterable[ProcessStats]) -> list:
    return sorted(processes, key=lambda item: item.memory_percent, reverse=True)


def top_by_disk(disks: Iterable[DiskStats]) -> list:
    return sorted(disks, key=lambda item: item.percent, reverse=True)


def top_by_network(network: Iterable[InterfaceStats]) -> list:
    return sorted(network, key=lambda item: item.rx_rate + item.tx_rate, reverse=True)


def short_command(command: str) -> str:
    return command.rsplit("/", 1)[-1] or command


def truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    if width <= 1:
        return value[:width]
    return value[: width - 1] + "."
