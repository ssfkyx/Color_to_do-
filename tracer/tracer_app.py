"""Tracer bullet: one thin, end-to-end slice of the colour todo app.

It deliberately lives in a single file.  The slice proves the risky path:

    free text --Enter--> Todo --drag--> 24h day board --tick--> popup
                              |                                  |
                              +---------- JSON file <-----------+

Everything here is a probe, not the final module layout.  The final
architecture is recorded in ../pre_architecture.md.

Run:  python tracer/tracer_app.py
Data: %LOCALAPPDATA%\\ColourTodo\\tracer-todos.json
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import ttk

# The product asks for FP64 everywhere a float is used.  Python's float is
# IEEE-754 binary64, i.e. FP64.  Keep the alias and the explicit conversions
# so the intent is visible at every geometric boundary.
FP64 = float

PX_PER_MINUTE: FP64 = FP64(0.78)
DAY_MINUTES = 24 * 60
SNAP_MINUTES = 15
DEFAULT_DURATION_MINUTES = 30
SNOOZE_MINUTES = 10

BG = "#F6F3EC"
PANEL = "#FBFAF6"
SURFACE = "#FFFFFF"
INK = "#23262F"
MUTED = "#8C8F99"
LINE = "#E7E3DA"
ACCENT = "#F26B5E"
ACCENT_DARK = "#D95448"
DONE = "#B9BCC4"
FONT = "Microsoft YaHei UI"
FONT_NUM = "Segoe UI"

ACCENTS = ["#F26B5E", "#E9A23B", "#2FAE9B", "#5B7CFA", "#9C6BF2", "#E56AA6"]


def fp64(value: int | float | str) -> float:
    """Convert once, at the boundary; every float in this app is FP64."""
    return FP64(value)


def to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def blend(colour: str, other: str, amount: FP64) -> str:
    """Blend `colour` toward `other`; amount is FP64 in [0, 1]."""
    a = fp64(amount)
    c1 = tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
    c2 = tuple(int(other[i : i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(int(round(fp64(x) * (1.0 - a) + fp64(y) * a)) for x, y in zip(c1, c2))
    return to_hex(mixed)


def rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs: Any,
) -> int:
    """A smooth polygon is the stock-Canvas way to draw a rounded rectangle."""
    r = min(fp64(radius), (fp64(x2) - fp64(x1)) / 2, (fp64(y2) - fp64(y1)) / 2)
    points = [
        x1 + r, y1,
        x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2,
        x1 + r, y2, x1, y2, x1, y2 - r,
        x1, y1 + r, x1, y1, x1 + r, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


@dataclass
class Todo:
    id: str
    text: str
    accent: str
    created_at: str
    scheduled_at: str | None = None
    duration_minutes: int = DEFAULT_DURATION_MINUTES
    done: bool = False
    reminded_at: str | None = None

    @property
    def scheduled(self) -> datetime | None:
        if not self.scheduled_at:
            return None
        return datetime.fromisoformat(self.scheduled_at)

    def is_due(self, now: datetime) -> bool:
        start = self.scheduled
        return bool(
            start
            and not self.done
            and self.reminded_at is None
            and now >= start
        )


class TracerStore:
    """One JSON file, written atomically.  A probe-grade repository."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.todos: list[Todo] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.todos = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.todos = []
            return
        self.todos = [Todo(**item) for item in raw.get("todos", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "todos": [asdict(todo) for todo in self.todos]}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def add(self, text: str) -> Todo:
        todo = Todo(
            id=uuid.uuid4().hex[:10],
            text=text,
            accent=ACCENTS[len(self.todos) % len(ACCENTS)],
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.todos.append(todo)
        self.save()
        return todo

    def find(self, todo_id: str) -> Todo | None:
        return next((todo for todo in self.todos if todo.id == todo_id), None)


class ReminderPopup(tk.Toplevel):
    """A non-modal, always-on-top card.  Deliberately not messagebox()."""

    WIDTH = 356
    HEIGHT = 132

    def __init__(
        self,
        master: tk.Misc,
        todo: Todo,
        on_done: Any,
        on_snooze: Any,
        slot: int = 0,
    ) -> None:
        super().__init__(master)
        self.todo = todo
        self.on_done = on_done
        self.on_snooze = on_snooze
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=blend(todo.accent, SURFACE, 0.12))
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - self.WIDTH - 28
        y = screen_h - self.HEIGHT - 36 - slot * (self.HEIGHT + 12)
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        shell = tk.Frame(self, bg=SURFACE, highlightthickness=0)
        shell.pack(fill="both", expand=True, padx=2, pady=2)
        tk.Frame(shell, bg=todo.accent, width=6).pack(side="left", fill="y")
        body = tk.Frame(shell, bg=SURFACE)
        body.pack(side="left", fill="both", expand=True, padx=16, pady=13)

        top = tk.Frame(body, bg=SURFACE)
        top.pack(fill="x")
        tk.Label(
            top, text="到时间了", bg=SURFACE, fg=todo.accent,
            font=(FONT, 10, "bold"),
        ).pack(side="left")
        tk.Label(
            top, text=todo.scheduled.strftime("%H:%M") if todo.scheduled else "",
            bg=SURFACE, fg=MUTED, font=(FONT_NUM, 10),
        ).pack(side="right")

        tk.Label(
            body, text=todo.text, bg=SURFACE, fg=INK, font=(FONT, 12, "bold"),
            anchor="w", justify="left", wraplength=300,
        ).pack(fill="x", pady=(6, 10))

        actions = tk.Frame(body, bg=SURFACE)
        actions.pack(fill="x")
        done_btn = tk.Button(
            actions, text="完成", command=self._done, relief="flat", borderwidth=0,
            bg=todo.accent, fg="white", activebackground=ACCENT_DARK,
            activeforeground="white", font=(FONT, 9, "bold"), padx=14, pady=4,
            cursor="hand2",
        )
        done_btn.pack(side="left")
        snooze_btn = tk.Button(
            actions, text=f"{SNOOZE_MINUTES} 分钟后", command=self._snooze,
            relief="flat", borderwidth=0, bg="#F0EEE8", fg=INK,
            activebackground="#E6E2D9", font=(FONT, 9), padx=12, pady=4,
            cursor="hand2",
        )
        snooze_btn.pack(side="left", padx=(8, 0))

    def _done(self) -> None:
        self.destroy()
        self.on_done(self.todo)

    def _snooze(self) -> None:
        self.destroy()
        self.on_snooze(self.todo)


class TracerApp:
    def __init__(self, root: tk.Tk, data_path: Path | None = None) -> None:
        self.root = root
        self.store = TracerStore(data_path or self.default_data_path())
        self.selected_date: date = date.today()
        self.popups: list[ReminderPopup] = []
        self.pool_cards: dict[str, tk.Canvas] = {}
        self._drag: dict[str, Any] | None = None
        self._ghost: tk.Toplevel | None = None
        self._tick_job: str | None = None
        self._suppress_tick = False

        self._build_window()
        self._build_left_panel()
        self._build_day_board()
        self.refresh()
        self._schedule_tick()

    @staticmethod
    def default_data_path() -> Path:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "ColourTodo" / "tracer-todos.json"

    # ---------------------------------------------------------------- window

    def _build_window(self) -> None:
        self.root.title("色彩待办 · Tracer")
        self.root.configure(bg=BG)
        self.root.geometry("1180x780")
        self.root.minsize(980, 620)
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - 1180) // 2)
        y = max(0, (screen_h - 780) // 2 - 20)
        self.root.geometry(f"1180x780+{x}+{y}")

        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill="both", expand=True, padx=22, pady=20)
        self.shell.grid_columnconfigure(0, weight=0)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)

    # ------------------------------------------------------------- left pane

    def _build_left_panel(self) -> None:
        self.left = tk.Frame(self.shell, bg=PANEL, width=352)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        self.left.grid_propagate(False)

        head = tk.Frame(self.left, bg=PANEL)
        head.pack(fill="x", padx=22, pady=(22, 2))
        tk.Label(
            head, text="今天", bg=PANEL, fg=INK, font=(FONT, 24, "bold"),
        ).pack(side="left")
        tk.Label(
            head, text="先把事情写下来", bg=PANEL, fg=MUTED, font=(FONT, 9),
        ).pack(side="right", pady=(10, 0))

        tk.Label(
            self.left,
            text=self.selected_date.strftime("%Y 年 %m 月 %d 日 · %A").replace(
                "Monday", "星期一").replace("Tuesday", "星期二").replace(
                "Wednesday", "星期三").replace("Thursday", "星期四").replace(
                "Friday", "星期五").replace("Saturday", "星期六").replace(
                "Sunday", "星期日"),
            bg=PANEL, fg=MUTED, font=(FONT, 9),
        ).pack(fill="x", padx=22, pady=(0, 18))

        input_shell = tk.Frame(
            self.left, bg=SURFACE, highlightthickness=1,
            highlightbackground=LINE, highlightcolor=ACCENT,
        )
        input_shell.pack(fill="x", padx=22)
        self.entry = tk.Entry(
            input_shell, relief="flat", borderwidth=0, bg=SURFACE, fg=INK,
            insertbackground=ACCENT, font=(FONT, 11), highlightthickness=0,
        )
        self.entry.pack(fill="x", padx=12, pady=(10, 9))
        self.entry.bind("<Return>", self._on_enter)
        tk.Frame(input_shell, bg=ACCENT, height=2).pack(fill="x", side="bottom")
        self.entry.focus_set()

        tk.Label(
            self.left, text="Enter 加入 · 拖动卡片到右侧安排时间",
            bg=PANEL, fg=MUTED, font=(FONT, 8),
        ).pack(fill="x", padx=24, pady=(7, 18))

        self.pool = tk.Frame(self.left, bg=PANEL)
        self.pool.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        self.pool_empty = tk.Label(
            self.pool, text="还没有待办\n写一句，按 Enter",
            bg=PANEL, fg="#B4B1A8", font=(FONT, 10), justify="left",
        )
        self.pool_empty.pack(anchor="w", pady=(6, 0))

    def _on_enter(self, event: tk.Event | None = None) -> str:
        text = self.entry.get().strip()
        if not text:
            return "break"
        self.store.add(text)
        self.entry.delete(0, "end")
        self.refresh()
        return "break"

    def _render_pool(self) -> None:
        for child in self.pool.winfo_children():
            child.destroy()
        self.pool_cards.clear()
        active = [t for t in self.store.todos if t.scheduled is None and not t.done]
        if not active:
            tk.Label(
                self.pool, text="待安排的事情会在这里\n拖到右侧时间轴，就算排好了",
                bg=PANEL, fg="#B4B1A8", font=(FONT, 10),
                justify="left", anchor="w",
            ).pack(fill="x", pady=(6, 0))
            return

        for todo in active:
            card = tk.Canvas(
                self.pool, height=62, bg=PANEL, highlightthickness=0, bd=0,
                cursor="hand2",
            )
            card.pack(fill="x", pady=(0, 9))
            self.pool_cards[todo.id] = card
            card.bind("<Configure>", lambda e, t=todo: self._draw_pool_card(t))
            card.bind("<ButtonPress-1>", lambda e, t=todo: self._start_drag(t, e))
            card.bind("<Enter>", lambda e, c=card: c.configure(cursor="hand2"))
            self._draw_pool_card(todo)

    def _draw_pool_card(self, todo: Todo) -> None:
        card = self.pool_cards.get(todo.id)
        if card is None:
            return
        width = max(card.winfo_width(), 280)
        card.delete("all")
        rounded_rect(card, 1, 1, width - 2, 60, 12, fill=SURFACE, outline=LINE)
        card.create_oval(14, 27, 22, 35, fill=todo.accent, outline="")
        card.create_text(
            32, 20, text=todo.text, anchor="w", fill=INK,
            font=(FONT, 10, "bold"), width=width - 60,
        )
        card.create_text(
            32, 42, text="待安排 · 拖动到右侧", anchor="w", fill=MUTED,
            font=(FONT, 8),
        )

    # --------------------------------------------------------------- day board

    def _build_day_board(self) -> None:
        self.board = tk.Frame(self.shell, bg=SURFACE, highlightthickness=0)
        self.board.grid(row=0, column=1, sticky="nsew")
        self.board.grid_columnconfigure(0, weight=1)
        self.board.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self.board, bg=SURFACE)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 14))
        header.grid_columnconfigure(1, weight=1)

        left = tk.Frame(header, bg=SURFACE)
        left.grid(row=0, column=0, sticky="w")
        tk.Label(
            left, text=self.selected_date.strftime("%m 月 %d 日"),
            bg=SURFACE, fg=INK, font=(FONT, 17, "bold"),
        ).pack(side="left")
        tk.Label(
            left, text=" 星期四" if self.selected_date.weekday() == 3 else " · 今天",
            bg=SURFACE, fg=MUTED, font=(FONT, 10),
        ).pack(side="left", pady=(4, 0))
        tk.Label(
            header, text="24 小时 · 拖动即排期", bg=SURFACE, fg=MUTED,
            font=(FONT, 9),
        ).grid(row=0, column=2, sticky="e")

        tk.Frame(self.board, bg=LINE, height=1).grid(row=1, column=0, sticky="new")

        body = tk.Frame(self.board, bg=SURFACE)
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            body, bg=SURFACE, highlightthickness=0, bd=0,
            scrollregion=(0, 0, 700, 1440 * PX_PER_MINUTE + 40),
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)
        self._scroll = scroll
        self.canvas.bind("<Configure>", lambda e: self._draw_timeline())

    def _draw_timeline(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 560)
        gutter = 62.0
        track_x1 = gutter
        track_x2 = width - 22
        top = 16.0
        total_h = 1440 * PX_PER_MINUTE

        for hour in range(24):
            y = top + hour * 60 * PX_PER_MINUTE
            canvas.create_line(
                track_x1, y, track_x2, y,
                fill=LINE if hour else "#D8D3C8", width=1,
            )
            canvas.create_text(
                gutter - 14, y, text=f"{hour:02d}:00", anchor="e",
                fill=MUTED if hour else INK,
                font=(FONT_NUM, 8, "bold" if hour == 0 else "normal"),
            )

        now = datetime.now()
        now_y = top + (now.hour * 60 + now.minute + fp64(now.second) / 60.0) * PX_PER_MINUTE
        canvas.create_line(track_x1, now_y, track_x2, now_y, fill=ACCENT, width=2)
        canvas.create_oval(track_x1 - 4, now_y - 4, track_x1 + 4, now_y + 4,
                           fill=ACCENT, outline="")
        if now.date() == self.selected_date:
            canvas.create_text(
                track_x2 - 4, now_y - 9, text=f"现在 {now.strftime('%H:%M')}",
                anchor="e", fill=ACCENT, font=(FONT, 8, "bold"),
            )

        scheduled = sorted(
            (t for t in self.store.todos if t.scheduled and t.scheduled.date() == self.selected_date and not t.done),
            key=lambda t: t.scheduled,  # type: ignore[arg-type,return-value]
        )
        for todo in scheduled:
            start = todo.scheduled
            assert start is not None
            start_minute = start.hour * 60 + start.minute
            y1 = top + start_minute * PX_PER_MINUTE + 1
            y2 = y1 + max(todo.duration_minutes * PX_PER_MINUTE - 3, 28)
            fill = blend(todo.accent, "#FFFFFF", 0.88)
            items = [
                rounded_rect(canvas, track_x1 + 8, y1, track_x2 - 4, y2, 9,
                             fill=fill, outline=""),
                rounded_rect(canvas, track_x1 + 8, y1, track_x1 + 13, y2, 3,
                             fill=todo.accent, outline=""),
                canvas.create_text(
                    track_x1 + 22, y1 + 9, text=start.strftime("%H:%M"),
                    anchor="w", fill=todo.accent, font=(FONT_NUM, 8, "bold"),
                ),
                canvas.create_text(
                    track_x1 + 22, y1 + 25, text=todo.text, anchor="w",
                    fill=INK, font=(FONT, 10, "bold"),
                    width=max(track_x2 - track_x1 - 50, 100),
                ),
            ]
            tag = f"todo-{todo.id}"
            for item in items:
                canvas.addtag_withtag(tag, item)
            canvas.tag_bind(tag, "<Double-Button-1>", lambda e, t=todo: self._complete(t))

        if self.selected_date == date.today():
            view_top = max(0.0, 7 * 60 * PX_PER_MINUTE)
            if not getattr(self, "_scrolled_once", False):
                self._scrolled_once = True
                self.canvas.yview_moveto(view_top / total_h)

    # ------------------------------------------------------------------ drag

    def _start_drag(self, todo: Todo, event: tk.Event) -> None:
        self._drag = {"todo": todo, "moved": False}
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.attributes("-alpha", 0.94)
        ghost.configure(bg=todo.accent)
        tk.Label(
            ghost, text=todo.text, bg=SURFACE, fg=INK, font=(FONT, 9, "bold"),
            padx=12, pady=8,
        ).pack(padx=2, pady=2)
        self._ghost = ghost
        self._move_ghost(event.x_root, event.y_root)
        self.root.bind_all("<B1-Motion>", self._on_drag_motion, add="+")
        self.root.bind_all("<ButtonRelease-1>", self._on_drag_release, add="+")

    def _move_ghost(self, x_root: int, y_root: int) -> None:
        if self._ghost is not None:
            self._ghost.geometry(f"+{x_root + 14}+{y_root + 12}")

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag:
            self._drag["moved"] = True
            self._move_ghost(event.x_root, event.y_root)

    def _on_drag_release(self, event: tk.Event) -> None:
        drag = self._drag
        self._drag = None
        self.root.unbind_all("<B1-Motion>")
        self.root.unbind_all("<ButtonRelease-1>")
        if self._ghost is not None:
            self._ghost.destroy()
            self._ghost = None
        if not drag:
            return
        minute = self._minute_at(event.x_root, event.y_root)
        if minute is not None:
            self._schedule(drag["todo"], minute)

    def _minute_at(self, x_root: int, y_root: int) -> int | None:
        """Map a screen point to a snapped minute-of-day, or None if outside."""
        cx = self.canvas.winfo_rootx()
        cy = self.canvas.winfo_rooty()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = x_root - cx
        y = y_root - cy
        if not (0 <= x <= cw and 0 <= y <= ch):
            return None
        canvas_y = self.canvas.canvasy(y) - 16.0
        if canvas_y < 0 or canvas_y > 1440 * PX_PER_MINUTE:
            return None
        raw = canvas_y / PX_PER_MINUTE
        snapped = int(round(raw / SNAP_MINUTES)) * SNAP_MINUTES
        return max(0, min(DAY_MINUTES - DEFAULT_DURATION_MINUTES, snapped))

    def _schedule(self, todo: Todo, minute: int | None) -> None:
        if minute is None:
            return
        start = datetime.combine(self.selected_date, time.min) + timedelta(minutes=minute)
        todo.scheduled_at = start.isoformat(timespec="minutes")
        todo.reminded_at = None
        self.store.save()
        self.refresh()
        self._scroll_to(start)

    def _scroll_to(self, start: datetime) -> None:
        minute = start.hour * 60 + start.minute
        self.canvas.yview_moveto(max(0.0, (minute * PX_PER_MINUTE - 120) / (1440 * PX_PER_MINUTE)))

    # -------------------------------------------------------------- reminders

    def _schedule_tick(self) -> None:
        if self._suppress_tick:
            return
        self._tick_job = self.root.after(1000, self._tick)

    def _tick(self) -> None:
        self._tick_job = None
        now = datetime.now()
        self._show_due(now)
        self._draw_timeline()
        self._schedule_tick()

    def _show_due(self, now: datetime) -> list[Todo]:
        due = [todo for todo in self.store.todos if todo.is_due(now)]
        for todo in due:
            todo.reminded_at = now.isoformat(timespec="seconds")
            popup = ReminderPopup(
                self.root, todo,
                on_done=self._complete,
                on_snooze=self._snooze,
                slot=len(self.popups),
            )
            self.popups.append(popup)
        if due:
            self.store.save()
        return due

    def _complete(self, todo: Todo) -> None:
        todo.done = True
        self.store.save()
        self._close_popup_for(todo)
        self.refresh()

    def _snooze(self, todo: Todo) -> None:
        start = datetime.now() + timedelta(minutes=SNOOZE_MINUTES)
        todo.scheduled_at = start.isoformat(timespec="seconds")
        todo.reminded_at = None
        self.store.save()
        self._close_popup_for(todo)
        self.refresh()

    def _close_popup_for(self, todo: Todo) -> None:
        remaining = []
        for popup in self.popups:
            if popup.todo.id == todo.id:
                if popup.winfo_exists():
                    popup.destroy()
            else:
                remaining.append(popup)
        self.popups = remaining

    # ------------------------------------------------------------------ view

    def refresh(self) -> None:
        self._render_pool()
        self._draw_timeline()

    def run(self) -> None:
        self.root.mainloop()
        if self._tick_job is not None:
            self.root.after_cancel(self._tick_job)


def main() -> int:
    root = tk.Tk()
    TracerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
