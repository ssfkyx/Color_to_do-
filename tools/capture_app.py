"""Capture the real Tk UI for design review (development helper)."""

from __future__ import annotations

import sys
import time
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from colour_todo.config import AppConfig  # noqa: E402
from colour_todo.core.reminder_service import ReminderService  # noqa: E402
from colour_todo.core.todo_service import TodoService  # noqa: E402
from colour_todo.core.time_slot import TimeSlot  # noqa: E402
from colour_todo.core.view_mode import ViewMode  # noqa: E402
from colour_todo.infra.clock import SystemClock  # noqa: E402
from colour_todo.infra.json_repository import JsonTodoRepository  # noqa: E402
from colour_todo.ui.main_window import MainWindow  # noqa: E402
from colour_todo.ui.theme import THEME  # noqa: E402

DATA = ROOT / ".capture-data.json"
OUT = ROOT / "design"


def main() -> int:
    DATA.unlink(missing_ok=True)
    config = AppConfig.default().with_data_dir(ROOT)
    repo = JsonTodoRepository(DATA)
    clock = SystemClock()
    service = TodoService(repo, clock)
    reminders = ReminderService(service, clock)

    root = tk.Tk()
    root.geometry("+0+0")
    app = MainWindow(root, config, THEME, service, reminders, clock, enable_tray=False)
    root.update_idletasks()
    root.update()
    app._running = False
    if app._tick_job:
        root.after_cancel(app._tick_job)
        app._tick_job = None

    for text in [
        "整理产品需求",
        "去楼下散步 20 分钟",
        "设计评审",
        "给妈妈打电话",
        "买一束橙色郁金香",
        "回复设计评论",
    ]:
        service.capture(text)
    todos = list(service.all_todos)
    today = date.today()
    for todo, minute, duration in zip(todos[:4], [9 * 60, 11 * 60 + 30, 15 * 60, 18 * 60 + 30], [60, 45, 60, 45]):
        service.schedule(todo.id, TimeSlot.at(today, minute, duration))
    service.complete(todos[5].id)
    app.refresh()
    root.update_idletasks()
    root.update()
    app.calendar.day_view.scroll_to_minute(8 * 60)
    root.update_idletasks()
    root.update()
    root.attributes("-topmost", True)
    for _ in range(3):
        root.geometry("1180x780+0+0")
        root.update_idletasks()
        root.update()
        time.sleep(0.25)
    ImageGrab.grab(bbox=(0, 0, 1180, 780)).save(OUT / "ui_main.png")

    app.calendar.set_mode(ViewMode.WEEK)
    root.update_idletasks()
    root.update()
    ImageGrab.grab(bbox=(0, 0, 1180, 780)).save(OUT / "ui_week.png")

    app.calendar.set_mode(ViewMode.MONTH)
    root.update_idletasks()
    root.update()
    ImageGrab.grab(bbox=(0, 0, 1180, 780)).save(OUT / "ui_month.png")

    # One reminder popup over a clean warm backdrop, cropped for the design
    # sheet.  The real popup is still the widget under test.
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    backdrop = tk.Toplevel(root)
    backdrop.overrideredirect(True)
    backdrop.attributes("-topmost", True)
    bw, bh = 540, 340
    bx, by = screen_w - bw - 8, screen_h - bh - 8
    backdrop.geometry(f"{bw}x{bh}+{bx}+{by}")
    backdrop.configure(bg=THEME.background)
    backdrop.update_idletasks()
    backdrop.update()

    due = todos[4]
    service.schedule(due.id, TimeSlot.at(today, max(0, datetime.now().hour * 60 + datetime.now().minute - 2), 30))
    service.claim_reminder(due.id, config.reminder_visible_seconds, config.reminder_repeat_minutes)
    app.reminders.show(due)
    root.update_idletasks()
    root.update()
    screen = ImageGrab.grab()
    screen.crop((bx + 16, by + 16, bx + bw - 4, by + bh - 4)).save(OUT / "ui_reminder.png")

    app.reminders.close_all()
    backdrop.destroy()
    root.destroy()
    DATA.unlink(missing_ok=True)
    print("captured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
