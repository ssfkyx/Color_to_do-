"""End-to-end smoke test for the tracer bullet.

Run:  python tracer/smoke_test.py
It opens a real Tk window briefly, drives it with synthetic mouse/keyboard
events, and asserts the full slice: input -> drag -> schedule -> popup ->
snooze -> complete -> reload from disk.
"""

from __future__ import annotations

import struct
import sys
import tkinter as tk
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tracer_app import (  # noqa: E402
    DAY_MINUTES,
    PX_PER_MINUTE,
    SNAP_MINUTES,
    TracerApp,
)

CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(f"FAIL {label}")
    CHECKS += 1
    print(f"PASS {label}")


def pump(root: tk.Tk, rounds: int = 3) -> None:
    for _ in range(rounds):
        root.update_idletasks()
        root.update()


def stop_timer(app: TracerApp) -> None:
    app._suppress_tick = True
    if app._tick_job is not None:
        app.root.after_cancel(app._tick_job)
        app._tick_job = None


def main() -> int:
    check(struct.calcsize("<d") == 8, "Python float is IEEE-754 FP64 (8 bytes)")
    check(isinstance(PX_PER_MINUTE, float), "timeline scale is an FP64 value")

    data_path = Path(__file__).resolve().parent / f".tracer-test-{uuid.uuid4().hex[:8]}.json"
    try:
        root = tk.Tk()
        root.geometry("+80+80")
        app = TracerApp(root, data_path=data_path)
        stop_timer(app)
        pump(root)
        check(root.winfo_ismapped() == 1, "main window is mapped")

        # 1. Free text + Enter becomes a Todo.
        app.entry.insert(0, "写周报")
        app.entry.event_generate("<Return>")
        pump(root)
        check(len(app.store.todos) == 1, "Enter captures exactly one Todo")
        todo = app.store.todos[0]
        check(todo.text == "写周报", "Todo keeps the free text")
        check(todo.scheduled is None, "new Todo starts unscheduled")
        check(data_path.exists(), "Todo is persisted immediately")
        check(todo.id in app.pool_cards, "unscheduled Todo appears in the left pool")

        # 2. Drag the card onto 09:30 on the 24h day board.
        target_minute = 9 * 60 + 30
        app.canvas.yview_moveto((7 * 60 * PX_PER_MINUTE) / (DAY_MINUTES * PX_PER_MINUTE))
        pump(root)
        card = app.pool_cards[todo.id]
        target_y_canvas = 16.0 + target_minute * PX_PER_MINUTE
        target_y_widget = target_y_canvas - app.canvas.canvasy(0)
        target_x_widget = app.canvas.winfo_width() * 0.55
        target_x_root = app.canvas.winfo_rootx() + int(target_x_widget)
        target_y_root = app.canvas.winfo_rooty() + int(target_y_widget)
        root_x = root.winfo_rootx()
        root_y = root.winfo_rooty()
        check(0 < target_y_widget < app.canvas.winfo_height(), "09:30 is in the visible timeline")

        card.event_generate("<ButtonPress-1>", x=30, y=30)
        pump(root)
        root.event_generate(
            "<B1-Motion>", x=target_x_root - root_x, y=target_y_root - root_y
        )
        root.event_generate(
            "<ButtonRelease-1>", x=target_x_root - root_x, y=target_y_root - root_y
        )
        pump(root)

        check(todo.scheduled is not None, "drag-and-drop schedules the Todo")
        assert todo.scheduled is not None
        check(
            todo.scheduled.hour == 9 and abs(todo.scheduled.minute - 30) <= SNAP_MINUTES,
            f"drop snaps to 09:30 (got {todo.scheduled.strftime('%H:%M')})",
        )
        check(
            todo.scheduled.date() == app.selected_date,
            "Todo is placed on the selected calendar day",
        )
        check(todo.id not in app.pool_cards, "scheduled Todo leaves the left pool")
        check(
            app.canvas.find_withtag(f"todo-{todo.id}"),
            "scheduled Todo is drawn on the timeline",
        )
        saved = data_path.read_text(encoding="utf-8")
        check("09:30" in saved, "scheduled time survives in the JSON file")

        # 3. A due Todo raises a real always-on-top popup exactly once.
        due_at = datetime.now() - timedelta(minutes=1)
        app._schedule(todo, due_at.hour * 60 + due_at.minute)
        pump(root)
        due = app._show_due(datetime.now())
        pump(root)
        check(len(due) == 1, "tick detects a due Todo")
        check(len(app.popups) == 1, "due Todo opens one reminder popup")
        popup = app.popups[0]
        check(popup.winfo_exists() == 1, "popup is a real Tk window")
        check(popup.attributes("-topmost") == 1, "popup is always on top")
        check(todo.reminded_at is not None, "Todo is marked as reminded")
        check(app._show_due(datetime.now()) == [], "same Todo does not notify twice")
        check(len(app.popups) == 1, "no duplicate popup is created")

        # 4. Snooze from the popup moves the reminder ten minutes out.
        before = datetime.now()
        popup._snooze()
        pump(root)
        assert todo.scheduled is not None
        check(
            timedelta(minutes=9) < todo.scheduled - before < timedelta(minutes=11),
            "snooze moves the reminder ten minutes into the future",
        )
        check(todo.reminded_at is None, "snooze re-arms the reminder")
        check(app.popups == [], "snoozing closes the popup")
        check(app._show_due(datetime.now()) == [], "snoozed Todo is not due yet")

        # 5. Complete from a popup stamps done and removes it from the day board.
        app._schedule(todo, max(0, datetime.now().hour * 60 + datetime.now().minute - 2))
        app._show_due(datetime.now())
        pump(root)
        check(len(app.popups) == 1, "re-armed Todo pops again")
        app.popups[0]._done()
        pump(root)
        check(todo.done is True, "complete marks the Todo done")
        check(app.popups == [], "complete closes the popup")
        check(
            not app.canvas.find_withtag(f"todo-{todo.id}"),
            "completed Todo disappears from the timeline",
        )

        # 6. Restart and reload the same file: state is durable.
        root.destroy()
        root2 = tk.Tk()
        root2.geometry("+80+80")
        app2 = TracerApp(root2, data_path=data_path)
        stop_timer(app2)
        pump(root2)
        check(len(app2.store.todos) == 1, "restart reloads the Todo from JSON")
        reloaded = app2.store.todos[0]
        check(reloaded.text == "写周报", "reloaded text matches")
        check(reloaded.done is True, "reloaded completion state matches")
        check(reloaded.scheduled is not None, "reloaded schedule matches")
        root2.destroy()
    finally:
        data_path.unlink(missing_ok=True)
        data_path.with_suffix(".tmp").unlink(missing_ok=True)

    print(f"\nTRACER PASS: {CHECKS} checks")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"\n{exc}", file=sys.stderr)
        sys.exit(1)
