"""Application service for capturing, scheduling, completing and snoozing."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Sequence

from .ports import Clock, TodoRepository
from .time_slot import TimeSlot
from .todo import Todo


class TodoNotFound(KeyError):
    pass


class TodoService:
    """Every mutating method is one transaction boundary and persists."""

    def __init__(self, repository: TodoRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock
        self._todos: list[Todo] = list(repository.load())

    @property
    def all_todos(self) -> tuple[Todo, ...]:
        return tuple(self._todos)

    def get(self, todo_id: str) -> Todo:
        for todo in self._todos:
            if todo.id == todo_id:
                return todo
        raise TodoNotFound(todo_id)

    def capture(self, text: str) -> Todo | None:
        text = text.strip()
        if not text:
            return None
        todo = Todo(
            id=uuid.uuid4().hex[:10],
            text=text,
            accent_index=len(self._todos),
            created_at=self._clock.now(),
        )
        self._todos.append(todo)
        self._persist()
        return todo

    def schedule(self, todo_id: str, slot: TimeSlot) -> None:
        todo = self.get(todo_id)
        todo.schedule(slot)
        self._persist()

    def complete(self, todo_id: str) -> None:
        todo = self.get(todo_id)
        if todo.done:
            return
        todo.complete(self._clock.now())
        self._persist()

    def update_text(self, todo_id: str, text: str) -> None:
        text = text.strip()
        if not text:
            raise ValueError("todo text cannot be empty")
        todo = self.get(todo_id)
        todo.text = text
        self._persist()

    def delete(self, todo_id: str) -> None:
        self._todos = [todo for todo in self._todos if todo.id != todo_id]
        self._persist()

    def snooze(self, todo_id: str, minutes: int) -> None:
        if minutes < 1:
            raise ValueError("snooze must be at least one minute")
        todo = self.get(todo_id)
        todo.snooze_until(self._clock.now() + timedelta(minutes=minutes))
        self._persist()

    def claim_reminder(
        self,
        todo_id: str,
        visible_seconds: int = 60,
        repeat_minutes: int = 5,
    ) -> None:
        todo = self.get(todo_id)
        todo.claim_reminder(self._clock.now(), visible_seconds, repeat_minutes)
        self._persist()

    def _persist(self) -> None:
        self._repository.save(self._todos)
