"""Pure reminder query: which Todos are due right now?"""

from __future__ import annotations

from .ports import Clock
from .todo import Todo
from .todo_service import TodoService


class ReminderService:
    def __init__(self, todo_service: TodoService, clock: Clock) -> None:
        self._todo_service = todo_service
        self._clock = clock

    def due_now(self) -> list[Todo]:
        now = self._clock.now()
        due = [todo for todo in self._todo_service.all_todos if todo.is_due(now)]
        due.sort(key=lambda todo: todo.remind_at or todo.created_at)
        return due
