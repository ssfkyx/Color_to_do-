"""Behaviour and path configuration.  Appearance lives in ui/theme.py."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

APP_DIR_NAME = "ColourTodo"


def default_data_dir() -> Path:
    override = os.environ.get("COLOURTODO_DATA_DIR")
    if override:
        return Path(override).expanduser()
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / ".local" / "share"
    return base / APP_DIR_NAME


def is_writable_dir(path: Path) -> bool:
    """Create the directory and prove that a file can be written inside it."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".colour-todo-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


@dataclass(frozen=True, slots=True)
class AppConfig:
    data_path: Path
    snap_minutes: int = 15
    default_duration_minutes: int = 30
    snooze_minutes: int = 5
    reminder_visible_seconds: int = 60
    reminder_repeat_minutes: int = 5
    tick_ms: int = 1000
    window_size: tuple[int, int] = (1180, 780)
    pool_width: int = 352
    max_visible_reminders: int = 3

    @classmethod
    def default(cls) -> "AppConfig":
        return cls(data_path=default_data_dir() / "todos.json")

    def with_data_dir(self, data_dir: Path) -> "AppConfig":
        return replace(self, data_path=Path(data_dir).expanduser() / "todos.json")

    @property
    def data_dir(self) -> Path:
        return self.data_path.parent
