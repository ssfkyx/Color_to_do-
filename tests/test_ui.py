"""Tk integration smoke test for the real window, drag, and reminder popup."""

from __future__ import annotations

import tkinter as tk
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from colour_todo.config import AppConfig
from colour_todo.core.reminder_service import ReminderService
from colour_todo.core.time_slot import TimeSlot
from colour_todo.core.todo_service import TodoService
from colour_todo.core.view_mode import ViewMode
from colour_todo.infra.clock import SystemClock
from colour_todo.infra.json_repository import JsonTodoRepository
from colour_todo.ui.day_view import GUTTER, TOP
from colour_todo.ui.main_window import MainWindow
from colour_todo.ui.theme import THEME
from colour_todo.ui.todo_panel import PLACEHOLDER


class UiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data_path = Path(__file__).resolve().parent / ".ui-test.json"
        self._cleanup()
        config = AppConfig.default().with_data_dir(self.data_path.parent)
        # Keep the test data file isolated from any other test file.
        config = replace(config, data_path=self.data_path)
        self.config = config
        self.root = tk.Tk()
        self.root.geometry("1180x780+0+0")
        self.service = TodoService(JsonTodoRepository(self.data_path), SystemClock())
        self.reminders = ReminderService(self.service, SystemClock())
        self.clock = SystemClock()
        self.app = MainWindow(
            self.root,
            self.config,
            THEME,
            self.service,
            self.reminders,
            self.clock,
            enable_tray=False,
        )
        self.app._running = False
        if self.app._tick_job is not None:
            self.root.after_cancel(self.app._tick_job)
            self.app._tick_job = None
        self._pump()

    def tearDown(self) -> None:
        try:
            self.app.quit()
        except tk.TclError:
            pass
        self._cleanup()

    def _cleanup(self) -> None:
        for path in self.data_path.parent.glob(".ui-test*.json"):
            path.unlink(missing_ok=True)
        for path in self.data_path.parent.glob(".ui-test*.json.tmp"):
            path.unlink(missing_ok=True)

    def _pump(self, rounds: int = 4) -> None:
        for _ in range(rounds):
            self.root.update_idletasks()
            self.root.update()

    def test_placeholder_and_capture(self) -> None:
        self.assertEqual(self.app.panel.var.get(), PLACEHOLDER)
        self.assertTrue(self.app.panel._placeholder_active)
        self.app.panel.prefill("写周报")
        self._pump()
        self.assertEqual(len(self.service.all_todos), 1)
        self.assertEqual(self.service.all_todos[0].text, "写周报")
        self.assertEqual(self.app.panel.var.get(), PLACEHOLDER)

    def test_typing_clears_placeholder(self) -> None:
        entry = self.app.panel.entry
        entry.focus_force()
        self._pump()
        entry.event_generate("<KeyPress>", keysym="a")
        self._pump()
        self.assertEqual(self.app.panel.var.get(), "a")
        self.assertFalse(self.app.panel._placeholder_active)

    def test_frameless_traffic_lights_and_zoom(self) -> None:
        self.assertTrue(self.root.overrideredirect())
        self.assertEqual(len(self.app.titlebar._lights), 3)
        self.app.toggle_maximize()
        self._pump()
        self.assertTrue(self.app._maximized)
        self.app.toggle_maximize()
        self._pump()
        self.assertFalse(self.app._maximized)

    def test_enter_submits_actual_keypress(self) -> None:
        entry = self.app.panel.entry
        entry.focus_force()
        self._pump()
        entry.event_generate("<KeyPress>", keysym="a")
        self._pump()
        entry.event_generate("<Return>")
        self._pump()
        self.assertEqual(len(self.service.all_todos), 1)
        self.assertEqual(self.service.all_todos[0].text, "a")
        self.assertEqual(self.app.panel.var.get(), PLACEHOLDER)

    def test_ime_style_text_then_enter(self) -> None:
        # IME composition may update the StringVar without a KeyPress event.
        self.app.panel.var.set("中文待办")
        self._pump()
        self.app.panel.entry.event_generate("<Return>")
        self._pump()
        self.assertEqual(len(self.service.all_todos), 1)
        self.assertEqual(self.service.all_todos[0].text, "中文待办")

    def test_plus_button_also_captures(self) -> None:
        self.app.panel.var.set("按钮加入")
        self.app.panel._placeholder_active = False
        self.app.panel.add_button.invoke()
        self._pump()
        self.assertEqual(len(self.service.all_todos), 1)
        self.assertEqual(self.service.all_todos[0].text, "按钮加入")

    def test_close_without_tray_quits(self) -> None:
        self.assertIsNone(self.app.tray)
        self.app.hide_to_tray()
        self.assertFalse(self.app._running)

    def test_today_button_returns_to_day_view(self) -> None:
        self.app.calendar.set_mode(ViewMode.MONTH)
        self.app.calendar.go_today()
        self._pump()
        self.assertEqual(self.app.calendar.mode, ViewMode.DAY)
        self.assertEqual(self.app.calendar.selected_date, date.today())

    def test_edit_unscheduled_todo(self) -> None:
        todo = self.service.capture("旧标题")
        assert todo is not None
        self.app.refresh()
        with patch(
            "colour_todo.ui.main_window.EditTodoDialog.ask",
            return_value="新标题",
        ):
            self.app._edit_todo(todo)
        self._pump()
        self.assertEqual(todo.text, "新标题")
        self.assertEqual(self.service.all_todos[0].text, "新标题")

    def test_delete_scheduled_todo(self) -> None:
        todo = self.service.capture("删掉我")
        assert todo is not None
        self.service.schedule(todo.id, TimeSlot.at(date.today(), 9 * 60, 30))
        self.app.refresh()
        self.app._delete_todo(todo)
        self._pump()
        self.assertEqual(self.service.all_todos, ())
        self.assertFalse(
            self.app.calendar.day_view.canvas.find_withtag(f"todo-{todo.id}")
        )

    def test_three_views_render_and_switch(self) -> None:
        self.app.calendar.set_mode(ViewMode.WEEK)
        self.assertEqual(self.app.calendar.mode, ViewMode.WEEK)
        self.assertIn("周", self.app.calendar.subtitle.cget("text"))
        self.app.calendar.set_mode(ViewMode.MONTH)
        self.assertEqual(self.app.calendar.mode, ViewMode.MONTH)
        self.assertIn("月", self.app.calendar.title.cget("text"))
        self.app.calendar.open_day(date.today())
        self.assertEqual(self.app.calendar.mode, ViewMode.DAY)

    def test_drag_from_pool_schedules_todo(self) -> None:
        todo = self.service.capture("去散步")
        assert todo is not None
        self.app.refresh()
        self.app.calendar.set_mode(ViewMode.DAY)
        self._pump()
        self.root.geometry("1180x780+0+0")
        self._pump()
        self.app.calendar.day_view.scroll_to_minute(13 * 60)
        self._pump()

        card = self.app.panel._cards[todo.id]
        canvas = self.app.calendar.day_view.canvas
        target_minute = 14 * 60
        y_widget = TOP + target_minute * THEME.pixels_per_minute - canvas.canvasy(0)
        x_root = canvas.winfo_rootx() + int(canvas.winfo_width() * 0.55)
        y_root = canvas.winfo_rooty() + int(y_widget)
        root_x, root_y = self.root.winfo_rootx(), self.root.winfo_rooty()

        card.event_generate("<ButtonPress-1>", x=30, y=30)
        self._pump()
        self.root.event_generate("<B1-Motion>", x=x_root - root_x, y=y_root - root_y)
        self._pump()
        preview_ids = canvas.find_withtag("droppreview")
        self.assertTrue(preview_ids)
        preview_texts = [
            canvas.itemcget(item, "text")
            for item in preview_ids
            if canvas.type(item) == "text"
        ]
        self.assertIn("松开 · 14:00", preview_texts)
        self.root.event_generate("<ButtonRelease-1>", x=x_root - root_x, y=y_root - root_y)
        self._pump()
        self.assertFalse(canvas.find_withtag("droppreview"))

        self.assertIsNotNone(todo.slot)
        assert todo.slot is not None
        self.assertEqual(todo.slot.start.hour, 14)
        self.assertEqual(todo.slot.start.minute, 0)
        self.assertTrue(
            self.app.calendar.day_view.canvas.find_withtag(f"todo-{todo.id}")
        )

    def test_highlighted_event_still_receives_mouse_hits(self) -> None:
        todo = self.service.capture("高亮后还能点")
        assert todo is not None
        self.service.schedule(todo.id, TimeSlot.at(date.today(), 9 * 60, 60))
        self.app.refresh()
        day = self.app.calendar.day_view
        day.highlight(todo)
        self._pump()
        layout = next(item for item in day._layouts if item.todo.id == todo.id)
        center_x = GUTTER + 40
        center_y = layout.top + layout.height / 2
        closest = day.canvas.find_closest(center_x, center_y)
        self.assertTrue(closest)
        tags = day.canvas.gettags(closest[0])
        self.assertIn(f"todo-{todo.id}", tags)

    def test_event_drag_reschedules_from_timeline(self) -> None:
        todo = self.service.capture("改时间")
        assert todo is not None
        self.service.schedule(todo.id, TimeSlot.at(date.today(), 9 * 60, 30))
        self.app.refresh()
        self.app.calendar.set_mode(ViewMode.DAY)
        self.app.calendar.day_view.scroll_to_minute(8 * 60)
        self._pump()
        canvas = self.app.calendar.day_view.canvas
        target_minute = 16 * 60
        y_widget = TOP + target_minute * THEME.pixels_per_minute - canvas.canvasy(0)
        x_root = canvas.winfo_rootx() + int(canvas.winfo_width() * 0.5)
        y_root = canvas.winfo_rooty() + int(y_widget)

        class Press:
            pass

        press = Press()
        press.x_root = x_root
        press.y_root = y_root
        self.app._on_event_drag_start(todo, press)
        self._pump()
        root_x, root_y = self.root.winfo_rootx(), self.root.winfo_rooty()
        self.root.event_generate("<B1-Motion>", x=x_root - root_x, y=y_root - root_y)
        self.root.event_generate("<ButtonRelease-1>", x=x_root - root_x, y=y_root - root_y)
        self._pump()
        assert todo.slot is not None
        self.assertEqual(todo.slot.start.hour, 16)
        self.assertEqual(todo.slot.start.minute, 0)

    def test_reminder_do_marks_completed_and_records_it(self) -> None:
        todo = self.service.capture("提醒我")
        assert todo is not None
        now = datetime.now()
        self.service.schedule(
            todo.id,
            TimeSlot.at(date.today(), max(0, now.hour * 60 + now.minute - 1), 30),
        )
        self.service.claim_reminder(todo.id, 60, 5)
        self.app.reminders.show(todo)
        self._pump()
        self.assertTrue(self.app.reminders.knows(todo.id))
        popup = self.app.reminders._popups[todo.id]
        popup._finish("do")
        self._pump()
        self.assertTrue(todo.done)
        self.assertIsNotNone(todo.completed_at)
        self.assertFalse(self.app.reminders.knows(todo.id))
        self.app.panel.filter.set_value("done", notify=True)
        self._pump()
        self.assertIn(todo.id, self.app.panel._cards)

    def test_reminder_timeout_snoozes_five_minutes(self) -> None:
        todo = self.service.capture("稍后我")
        assert todo is not None
        now = datetime.now()
        self.service.schedule(
            todo.id,
            TimeSlot.at(date.today(), max(0, now.hour * 60 + now.minute - 1), 30),
        )
        self.service.claim_reminder(todo.id, 60, 5)
        self.app.reminders.show(todo)
        self._pump()
        before = datetime.now()
        self.app.reminders._popups[todo.id]._finish("timeout")
        self._pump()
        assert todo.remind_at is not None
        self.assertGreater(todo.remind_at, before + timedelta(minutes=4))
        self.assertLess(todo.remind_at, before + timedelta(minutes=6))

    def test_reminder_drag_opens_day_and_keeps_five_minute_grace(self) -> None:
        todo = self.service.capture("拖我")
        assert todo is not None
        now = datetime.now()
        self.service.schedule(
            todo.id,
            TimeSlot.at(date.today(), max(0, now.hour * 60 + now.minute - 1), 30),
        )
        self.service.claim_reminder(todo.id, 60, 5)
        self.app.reminders.show(todo)
        self._pump()
        self.app.reminders._popups[todo.id]._finish("drag")
        self._pump()
        self.assertEqual(self.app.calendar.mode, ViewMode.DAY)
        self.assertIsNotNone(todo.remind_at)
        self.assertEqual(
            self.app.calendar.day_view._highlight_id, todo.id,
        )


if __name__ == "__main__":
    unittest.main()
