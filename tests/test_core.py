"""Core tests: model, services, persistence and view navigation."""

from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from colour_todo.core.reminder_service import ReminderService
from colour_todo.core.time_slot import TimeSlot
from colour_todo.core.todo import Todo
from colour_todo.core.todo_service import TodoService
from colour_todo.core.view_mode import (
    ViewMode,
    month_days,
    shift_date,
    week_days,
)
from colour_todo.infra.json_repository import JsonTodoRepository


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)


class MemoryRepository:
    def __init__(self) -> None:
        self.saved: list[Todo] = []
        self.saves = 0

    def load(self) -> list[Todo]:
        return list(self.saved)

    def save(self, todos) -> None:  # noqa: ANN001
        self.saved = list(todos)
        self.saves += 1


class TodoServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2026, 10, 19, 8, 0))
        self.repo = MemoryRepository()
        self.service = TodoService(self.repo, self.clock)

    def test_capture_trims_and_ignores_blank(self) -> None:
        self.assertIsNone(self.service.capture("   "))
        todo = self.service.capture("  写周报  ")
        self.assertIsNotNone(todo)
        assert todo is not None
        self.assertEqual(todo.text, "写周报")
        self.assertEqual(todo.accent_index, 0)
        self.assertIsNone(todo.slot)
        self.assertEqual(self.repo.saves, 1)

    def test_schedule_arms_reminder_and_complete_clears_it(self) -> None:
        todo = self.service.capture("写周报")
        assert todo is not None
        slot = TimeSlot.at(date(2026, 10, 19), 9 * 60, 45)
        self.service.schedule(todo.id, slot)
        self.assertEqual(todo.remind_at, slot.start)
        self.assertFalse(todo.is_due(self.clock.now()))
        self.clock.advance(hours=1)
        self.assertTrue(todo.is_due(self.clock.now()))
        self.service.complete(todo.id)
        self.assertTrue(todo.done)
        self.assertIsNotNone(todo.completed_at)
        self.assertIsNone(todo.remind_at)

    def test_claim_snooze_and_rearm(self) -> None:
        todo = self.service.capture("打电话")
        assert todo is not None
        self.clock.advance(hours=1)
        self.service.schedule(todo.id, TimeSlot.at(date(2026, 10, 19), 9 * 60, 30))
        self.service.claim_reminder(todo.id, 60, 5)
        self.assertEqual(todo.remind_at, self.clock.now() + timedelta(minutes=6))
        self.assertIsNotNone(todo.reminded_at)
        self.service.snooze(todo.id, 5)
        self.assertEqual(todo.remind_at, self.clock.now() + timedelta(minutes=5))
        self.assertFalse(todo.done)

    def test_reminder_service_due_query(self) -> None:
        reminders = ReminderService(self.service, self.clock)
        due = self.service.capture("due")
        later = self.service.capture("later")
        assert due is not None and later is not None
        self.service.schedule(due.id, TimeSlot.at(date(2026, 10, 19), 8 * 60, 30))
        self.service.schedule(later.id, TimeSlot.at(date(2026, 10, 19), 9 * 60, 30))
        self.assertEqual([todo.id for todo in reminders.due_now()], [due.id])
        self.clock.advance(hours=1)
        self.assertEqual(len(reminders.due_now()), 2)

    def test_accent_index_cycles_by_creation_order(self) -> None:
        for index in range(3):
            todo = self.service.capture(f"item {index}")
            assert todo is not None
            self.assertEqual(todo.accent_index, index)

    def test_update_text_and_delete(self) -> None:
        todo = self.service.capture("旧标题")
        assert todo is not None
        self.service.update_text(todo.id, "  新标题  ")
        self.assertEqual(todo.text, "新标题")
        self.service.delete(todo.id)
        self.assertEqual(self.service.all_todos, ())
        self.assertEqual(self.repo.saved, [])
        with self.assertRaises(ValueError):
            self.service.update_text(todo.id, "   ")


class TimeSlotTests(unittest.TestCase):
    def test_clamps_inside_day(self) -> None:
        slot = TimeSlot.at(date(2026, 10, 19), 23 * 60 + 50, 30)
        self.assertEqual(slot.start_minute, 23 * 60 + 30)
        self.assertLessEqual(slot.end.hour, 23)

    def test_rejects_cross_midnight(self) -> None:
        with self.assertRaises(ValueError):
            TimeSlot(start=datetime(2026, 10, 19, 23, 50), duration_minutes=30)

    def test_overlaps(self) -> None:
        first = TimeSlot.at(date(2026, 10, 19), 9 * 60, 60)
        second = TimeSlot.at(date(2026, 10, 19), 9 * 60 + 30, 60)
        third = TimeSlot.at(date(2026, 10, 19), 10 * 60, 60)
        self.assertTrue(first.overlaps(second))
        self.assertFalse(first.overlaps(third))


class JsonRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path(__file__).resolve().parent / ".todos-test.json"
        self._cleanup()

    def tearDown(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        for path in self.path.parent.glob(".todos-test*.json"):
            path.unlink(missing_ok=True)
        for path in self.path.parent.glob(".todos-test*.json.tmp"):
            path.unlink(missing_ok=True)

    def test_round_trip_preserves_slot_and_completion(self) -> None:
        clock = FakeClock(datetime(2026, 10, 19, 9, 30))
        repo = JsonTodoRepository(self.path)
        service = TodoService(repo, clock)
        todo = service.capture("写周报")
        assert todo is not None
        service.schedule(todo.id, TimeSlot.at(date(2026, 10, 19), 9 * 60, 60))
        clock.advance(minutes=10)
        service.complete(todo.id)

        loaded = JsonTodoRepository(self.path).load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].text, "写周报")
        self.assertTrue(loaded[0].done)
        self.assertIsNotNone(loaded[0].slot)
        self.assertIsNotNone(loaded[0].completed_at)

    def test_corrupt_file_is_renamed_and_load_is_empty(self) -> None:
        self.path.write_text("{not json", encoding="utf-8")
        repo = JsonTodoRepository(self.path)
        self.assertEqual(repo.load(), [])
        self.assertIsNotNone(repo.last_error)
        self.assertFalse(self.path.exists())
        self.assertTrue(any(self.path.parent.glob(".todos-test.corrupt-*.json")))

    def test_version_mismatch_is_preserved(self) -> None:
        self.path.write_text(json.dumps({"version": 999, "todos": []}), encoding="utf-8")
        repo = JsonTodoRepository(self.path)
        self.assertEqual(repo.load(), [])
        self.assertFalse(self.path.exists())


class ViewModeTests(unittest.TestCase):
    def test_shift_day_week_month(self) -> None:
        day = date(2026, 10, 19)
        self.assertEqual(shift_date(day, ViewMode.DAY, 1), date(2026, 10, 20))
        self.assertEqual(shift_date(day, ViewMode.WEEK, 1), date(2026, 10, 26))
        self.assertEqual(shift_date(date(2026, 1, 31), ViewMode.MONTH, 1), date(2026, 2, 28))
        self.assertEqual(shift_date(date(2026, 1, 31), ViewMode.MONTH, -1), date(2025, 12, 31))

    def test_week_and_month_shapes(self) -> None:
        days = week_days(date(2026, 10, 21))
        self.assertEqual(days[0], date(2026, 10, 19))
        self.assertEqual(len(days), 7)
        cells = month_days(date(2026, 10, 19))
        self.assertEqual(len(cells), 42)
        self.assertEqual(cells[0], None)
        self.assertEqual(cells[3], date(2026, 10, 1))


class EventLayoutTests(unittest.TestCase):
    def test_overlap_uses_two_lanes(self) -> None:
        from colour_todo.ui.event_layout import layout_events

        day = date(2026, 10, 19)
        first = Todo("a", "A", 0, datetime(2026, 10, 19, 8), TimeSlot.at(day, 9 * 60, 60))
        second = Todo("b", "B", 1, datetime(2026, 10, 19, 8), TimeSlot.at(day, 9 * 60 + 30, 60))
        third = Todo("c", "C", 2, datetime(2026, 10, 19, 8), TimeSlot.at(day, 11 * 60, 30))
        layouts = layout_events([first, second, third], day, 0.0, 1.0)
        self.assertEqual(len(layouts), 3)
        self.assertEqual(layouts[0].lane_count, 2)
        self.assertEqual(layouts[1].lane_count, 2)
        self.assertEqual(layouts[2].lane_count, 1)
        self.assertNotEqual(layouts[0].lane, layouts[1].lane)


if __name__ == "__main__":
    unittest.main()
