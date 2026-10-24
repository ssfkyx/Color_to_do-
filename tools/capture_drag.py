"""Capture the drag-preview line for design review (development helper)."""

from __future__ import annotations

import sys
import time
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from colour_todo.config import AppConfig  # noqa: E402
from colour_todo.core.reminder_service import ReminderService  # noqa: E402
from colour_todo.core.todo_service import TodoService  # noqa: E402
from colour_todo.infra.clock import SystemClock  # noqa: E402
from colour_todo.infra.json_repository import JsonTodoRepository  # noqa: E402
from colour_todo.ui.day_view import TOP  # noqa: E402
from colour_todo.ui.main_window import MainWindow  # noqa: E402
from colour_todo.ui.theme import THEME  # noqa: E402

DATA = ROOT / ".drag-capture.json"


def main() -> int:
    DATA.unlink(missing_ok=True)
    root = tk.Tk()
    config = AppConfig.default().with_data_dir(ROOT)
    service = TodoService(JsonTodoRepository(DATA), SystemClock())
    app = MainWindow(
        root,
        config,
        THEME,
        service,
        ReminderService(service, SystemClock()),
        SystemClock(),
        enable_tray=False,
    )
    root.attributes("-topmost", True)
    service.capture("买一束橙色郁金香")
    app.refresh()
    root.geometry("1180x780+0+0")
    for _ in range(6):
        root.update_idletasks()
        root.update()
        time.sleep(0.15)
    app.calendar.day_view.scroll_to_minute(13 * 60)
    root.update()

    todo = service.all_todos[0]
    canvas = app.calendar.day_view.canvas
    target_minute = 14 * 60
    y_widget = TOP + target_minute * THEME.pixels_per_minute - canvas.canvasy(0)
    x_root = canvas.winfo_rootx() + int(canvas.winfo_width() * 0.55)
    y_root = canvas.winfo_rooty() + int(y_widget)

    app.drag.start(todo, SimpleNamespace(x_root=x_root, y_root=y_root))
    app.drag._on_motion(SimpleNamespace(x_root=x_root, y_root=y_root))
    for _ in range(4):
        root.update_idletasks()
        root.update()
        time.sleep(0.1)
    ImageGrab.grab(bbox=(0, 0, 1180, 780)).save(ROOT / "design" / "ui_drag_preview.png")
    app.drag.cancel()
    app.quit()
    DATA.unlink(missing_ok=True)
    print("captured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
