"""Ports the application depends on; infrastructure supplies implementations."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from .todo import Todo


class TodoRepository(Protocol):
    def load(self) -> list[Todo]: ...

    def save(self, todos: Sequence[Todo]) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
