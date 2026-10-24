"""JSON file repository with atomic replace and corrupt-file recovery."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from ..core.time_slot import TimeSlot
from ..core.todo import Todo


class JsonTodoRepository:
    VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.last_error: str | None = None

    def load(self) -> list[Todo]:
        self.last_error = None
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.last_error = f"cannot read {self.path.name}: {exc}"
            self._backup_corrupt()
            return []
        if not isinstance(raw, dict) or raw.get("version") != self.VERSION:
            self.last_error = f"unsupported schema in {self.path.name}"
            self._backup_corrupt()
            return []
        todos: list[Todo] = []
        for item in raw.get("todos", []):
            try:
                todos.append(self._parse_todo(item))
            except (KeyError, TypeError, ValueError) as exc:
                self.last_error = f"skipped malformed todo: {exc}"
        return todos

    def save(self, todos: Sequence[Todo]) -> None:
        payload = {
            "version": self.VERSION,
            "todos": [self._todo_to_dict(todo) for todo in todos],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def _backup_corrupt(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.path.with_name(f"{self.path.stem}.corrupt-{stamp}{self.path.suffix}")
        try:
            self.path.replace(target)
        except OSError:
            pass

    @staticmethod
    def _todo_to_dict(todo: Todo) -> dict[str, Any]:
        slot = None
        if todo.slot is not None:
            slot = {
                "start": todo.slot.start.isoformat(timespec="minutes"),
                "duration_minutes": todo.slot.duration_minutes,
            }
        return {
            "id": todo.id,
            "text": todo.text,
            "accent_index": todo.accent_index,
            "created_at": todo.created_at.isoformat(timespec="seconds"),
            "slot": slot,
            "done": todo.done,
            "completed_at": todo.completed_at.isoformat(timespec="seconds")
            if todo.completed_at
            else None,
            "remind_at": todo.remind_at.isoformat(timespec="seconds")
            if todo.remind_at
            else None,
            "reminded_at": todo.reminded_at.isoformat(timespec="seconds")
            if todo.reminded_at
            else None,
        }

    @staticmethod
    def _parse_todo(item: dict[str, Any]) -> Todo:
        created_at = _dt(item["created_at"])
        slot_raw = item.get("slot")
        slot = None
        if slot_raw:
            slot = TimeSlot(
                start=_dt(slot_raw["start"]),
                duration_minutes=int(slot_raw.get("duration_minutes", 30)),
            ).clamped()
        remind_at = _dt(item["remind_at"]) if item.get("remind_at") else None
        if remind_at is None and slot is not None and not item.get("done", False):
            remind_at = slot.start
        return Todo(
            id=str(item["id"]),
            text=str(item["text"]),
            accent_index=int(item.get("accent_index", 0)),
            created_at=created_at,
            slot=slot,
            done=bool(item.get("done", False)),
            completed_at=_dt(item["completed_at"]) if item.get("completed_at") else None,
            remind_at=remind_at,
            reminded_at=_dt(item["reminded_at"]) if item.get("reminded_at") else None,
        )


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(str(value))
