"""Owns visible reminder popups and the queue beyond the stacking limit."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Callable

from ..core.todo import Todo
from ..config import AppConfig
from .reminder_popup import ReminderPopup
from .theme import Theme


class ReminderCenter:
    def __init__(
        self,
        master,
        theme: Theme,
        config: AppConfig,
        on_do: Callable[[Todo], None],
        on_drag: Callable[[Todo], None],
        on_timeout: Callable[[Todo], None],
    ) -> None:
        self.master = master
        self.theme = theme
        self.config = config
        self.on_do = on_do
        self.on_drag = on_drag
        self.on_timeout = on_timeout
        self._popups: dict[str, ReminderPopup] = {}
        self._slots: dict[str, int] = {}
        self._queue: deque[Todo] = deque()
        self._queued_ids: set[str] = set()

    def knows(self, todo_id: str) -> bool:
        return todo_id in self._popups or todo_id in self._queued_ids

    def show(self, todo: Todo) -> None:
        if self.knows(todo.id):
            return
        if len(self._popups) >= self.config.max_visible_reminders:
            self._queue.append(todo)
            self._queued_ids.add(todo.id)
            return
        self._create(todo)

    def close_for(self, todo_id: str) -> None:
        popup = self._popups.pop(todo_id, None)
        if popup is not None:
            popup.close()
            self._slots.pop(todo_id, None)
            self._show_next()
        if todo_id in self._queued_ids:
            self._queued_ids.discard(todo_id)
            self._queue = deque(t for t in self._queue if t.id != todo_id)

    def close_all(self) -> None:
        for popup in list(self._popups.values()):
            popup.close()
        self._popups.clear()
        self._slots.clear()
        self._queue.clear()
        self._queued_ids.clear()

    def _create(self, todo: Todo) -> None:
        used = set(self._slots.values())
        slot = 0
        while slot in used:
            slot += 1
        popup = ReminderPopup(
            self.master,
            self.theme,
            todo,
            deadline=datetime.now() + timedelta(seconds=self.config.reminder_visible_seconds),
            visible_seconds=self.config.reminder_visible_seconds,
            slot=slot,
            on_do=self._handle_do,
            on_drag=self._handle_drag,
            on_timeout=self._handle_timeout,
        )
        self._popups[todo.id] = popup
        self._slots[todo.id] = slot

    def _drop(self, todo_id: str) -> None:
        self._popups.pop(todo_id, None)
        self._slots.pop(todo_id, None)

    def _handle_do(self, todo: Todo) -> None:
        self._drop(todo.id)
        self.on_do(todo)
        self._show_next()

    def _handle_drag(self, todo: Todo) -> None:
        self._drop(todo.id)
        self.on_drag(todo)
        self._show_next()

    def _handle_timeout(self, todo: Todo) -> None:
        self._drop(todo.id)
        self.on_timeout(todo)
        self._show_next()

    def _show_next(self) -> None:
        while self._queue and len(self._popups) < self.config.max_visible_reminders:
            todo = self._queue.popleft()
            self._queued_ids.discard(todo.id)
            if todo.id not in self._popups:
                self._create(todo)
