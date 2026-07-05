from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_CONFIG_PATH = Path("~/.config/mac-monitor/config.json").expanduser()


@dataclass
class Config:
    interval: float = 1.0
    interfaces: List[str] = None  # type: ignore[assignment]
    top_processes: int = 5
    top_count: int = 5
    disk_limit: int = 5
    view: str = "all"
    show_loopback: bool = False
    show_logical_interfaces: bool = False
    warn_cpu_percent: float = 85.0
    warn_memory_percent: float = 85.0
    warn_disk_percent: float = 90.0

    def __post_init__(self) -> None:
        if self.interfaces is None:
            self.interfaces = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(path: Optional[str]) -> Config:
    config_path = Path(path).expanduser() if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Config()

    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"Config file must contain a JSON object: {config_path}")

    defaults = Config().to_dict()
    defaults.update({key: value for key, value in raw.items() if key in defaults})
    return Config(**defaults)


def default_config_json() -> str:
    return json.dumps(Config().to_dict(), indent=2, sort_keys=True)


def resolve_config_path(path: Optional[str]) -> str:
    return os.fspath(Path(path).expanduser() if path else DEFAULT_CONFIG_PATH)
