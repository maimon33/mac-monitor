from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class InterfaceStats:
    name: str
    rx_bytes: int
    tx_bytes: int
    rx_rate: float = 0.0
    tx_rate: float = 0.0


@dataclass
class CpuStats:
    percent: float
    load_1m: float
    load_5m: float
    load_15m: float
    cores: int


@dataclass
class MemoryStats:
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float


@dataclass
class DiskStats:
    mount: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float


@dataclass
class ProcessStats:
    pid: int
    cpu_percent: float
    memory_percent: float
    memory_bytes: int
    command: str


@dataclass
class Snapshot:
    timestamp: float
    cpu: CpuStats
    memory: MemoryStats
    disks: List[DiskStats]
    network: List[InterfaceStats]
    processes: List[ProcessStats]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def run_command(args: List[str]) -> str:
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        return result.stdout
    except OSError:
        return ""


def get_network_counters(
    include_interfaces: Optional[Iterable[str]] = None,
    show_loopback: bool = False,
    show_logical_interfaces: bool = False,
) -> Dict[str, Tuple[int, int]]:
    wanted = set(include_interfaces or [])
    if not wanted and not show_logical_interfaces:
        wanted = set(get_physical_interfaces())
    output = run_command(["netstat", "-ibn"])
    counters: Dict[str, Tuple[int, int]] = {}

    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 10 or parts[0] == "Name":
            continue

        name = parts[0]
        if "." in name:
            name = name.split(".", 1)[0]
        if wanted and name not in wanted:
            continue
        if not show_loopback and name == "lo0":
            continue
        if not wanted and not show_logical_interfaces and not is_physical_interface_name(name):
            continue

        try:
            rx = int(parts[6])
            tx = int(parts[9])
        except (ValueError, IndexError):
            continue

        old_rx, old_tx = counters.get(name, (0, 0))
        counters[name] = (max(old_rx, rx), max(old_tx, tx))

    return counters


def get_physical_interfaces() -> List[str]:
    output = run_command(["ifconfig"])
    blocks = re.split(r"\n(?=\S)", output)
    names: List[str] = []

    for block in blocks:
        first_line = block.splitlines()[0] if block else ""
        match = re.match(r"([A-Za-z0-9]+):", first_line)
        if not match:
            continue

        name = match.group(1)
        if not is_physical_interface_name(name):
            continue
        if "status: active" not in block:
            continue

        names.append(name)

    return names


def is_physical_interface_name(name: str) -> bool:
    return bool(re.fullmatch(r"en\d+", name))


def build_network_stats(
    current: Dict[str, Tuple[int, int]],
    previous: Optional[Dict[str, Tuple[int, int]]],
    elapsed: float,
) -> List[InterfaceStats]:
    rows: List[InterfaceStats] = []
    for name, (rx, tx) in current.items():
        rx_rate = 0.0
        tx_rate = 0.0
        if previous and elapsed > 0 and name in previous:
            old_rx, old_tx = previous[name]
            rx_rate = max(0.0, (rx - old_rx) / elapsed)
            tx_rate = max(0.0, (tx - old_tx) / elapsed)
        rows.append(InterfaceStats(name=name, rx_bytes=rx, tx_bytes=tx, rx_rate=rx_rate, tx_rate=tx_rate))
    return sorted(rows, key=lambda item: item.rx_rate + item.tx_rate, reverse=True)


def get_cpu_stats() -> CpuStats:
    output = run_command(["ps", "-A", "-o", "%cpu="])
    total_process_cpu = 0.0
    for line in output.splitlines():
        try:
            total_process_cpu += float(line.strip())
        except ValueError:
            pass

    cores = os.cpu_count() or 1
    percent = min(100.0, total_process_cpu / cores)
    load_1m, load_5m, load_15m = os.getloadavg()
    return CpuStats(percent=percent, load_1m=load_1m, load_5m=load_5m, load_15m=load_15m, cores=cores)


def get_memory_stats() -> MemoryStats:
    total_output = run_command(["sysctl", "-n", "hw.memsize"]).strip()
    total = int(total_output) if total_output.isdigit() else 0
    output = run_command(["vm_stat"])

    page_size = 4096
    first_line = output.splitlines()[0] if output else ""
    match = re.search(r"page size of (\d+) bytes", first_line)
    if match:
        page_size = int(match.group(1))

    pages: Dict[str, int] = {}
    for line in output.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        digits = re.sub(r"[^0-9]", "", value)
        if digits:
            pages[key.strip()] = int(digits)

    if not total:
        total_pages = sum(
            pages.get(name, 0)
            for name in (
                "Pages free",
                "Pages active",
                "Pages inactive",
                "Pages speculative",
                "Pages wired down",
                "Pages occupied by compressor",
            )
        )
        total = total_pages * page_size

    free_pages = pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
    free = min(total, free_pages * page_size)
    used = max(0, total - free)
    percent = (used / total * 100.0) if total else 0.0
    return MemoryStats(total_bytes=total, used_bytes=used, free_bytes=free, percent=percent)


def get_disk_stats(limit: int) -> List[DiskStats]:
    output = run_command(["df", "-k"])
    rows: List[DiskStats] = []
    seen = set()

    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 9:
            continue

        filesystem = parts[0]
        mount = parts[-1]
        if should_skip_mount(filesystem, mount) or mount in seen:
            continue
        seen.add(mount)

        try:
            total = int(parts[1]) * 1024
            used = int(parts[2]) * 1024
            free = int(parts[3]) * 1024
        except (ValueError, IndexError):
            try:
                usage = shutil.disk_usage(mount)
            except OSError:
                continue
            total = int(usage.total)
            used = int(usage.used)
            free = int(usage.free)

        if total <= 0:
            continue

        percent = used / total * 100.0
        rows.append(DiskStats(mount=mount, filesystem=filesystem, total_bytes=total, used_bytes=used, free_bytes=free, percent=percent))

    return sorted(rows, key=lambda item: item.percent, reverse=True)[:limit]


def should_skip_mount(filesystem: str, mount: str) -> bool:
    if filesystem in {"devfs", "map"}:
        return True
    if mount.startswith("/System/Volumes/Data/"):
        return True
    if mount.startswith("/System/Volumes/") and mount != "/System/Volumes/Data":
        return True
    return False


def get_top_processes(limit: int) -> List[ProcessStats]:
    output = run_command(["ps", "-axo", "pid=,%cpu=,%mem=,rss=,comm="])
    rows: List[ProcessStats] = []

    for line in output.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue
        try:
            rows.append(
                ProcessStats(
                    pid=int(parts[0]),
                    cpu_percent=float(parts[1]),
                    memory_percent=float(parts[2]),
                    memory_bytes=int(parts[3]) * 1024,
                    command=parts[4],
                )
            )
        except ValueError:
            continue

    top_cpu = sorted(rows, key=lambda item: item.cpu_percent, reverse=True)[:limit]
    top_memory = sorted(rows, key=lambda item: item.memory_percent, reverse=True)[:limit]
    by_pid: Dict[int, ProcessStats] = {}
    for row in top_cpu + top_memory:
        by_pid[row.pid] = row
    return sorted(by_pid.values(), key=lambda item: item.cpu_percent, reverse=True)


class Monitor:
    def __init__(
        self,
        interfaces: List[str],
        show_loopback: bool,
        show_logical_interfaces: bool,
        top_processes: int,
        disk_limit: int,
    ):
        self.interfaces = interfaces
        self.show_loopback = show_loopback
        self.show_logical_interfaces = show_logical_interfaces
        self.top_processes = top_processes
        self.disk_limit = disk_limit
        self._last_network: Optional[Dict[str, Tuple[int, int]]] = None
        self._last_time: Optional[float] = None

    def sample(self) -> Snapshot:
        now = time.time()
        current_network = get_network_counters(self.interfaces, self.show_loopback, self.show_logical_interfaces)
        elapsed = now - self._last_time if self._last_time else 0.0
        network = build_network_stats(current_network, self._last_network, elapsed)
        self._last_network = current_network
        self._last_time = now

        return Snapshot(
            timestamp=now,
            cpu=get_cpu_stats(),
            memory=get_memory_stats(),
            disks=get_disk_stats(self.disk_limit),
            network=network,
            processes=get_top_processes(self.top_processes),
        )
