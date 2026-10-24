"""Week view: seven day columns sharing one scrollable 24-hour grid."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable

from ..core.todo import Todo
from ..core.view_mode import week_days
from ..fp64 import FP64, fp64
from .canvas_kit import fit_text, format_minute, rounded_rect, y_for_minute
from .event_layout import layout_events
from .theme import Theme

TOP = 14.0
GUTTER = 46.0
WEEKDAY_SHORT = ("一", "二", "三", "四", "五", "六", "日")


class WeekView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        pixels_per_minute: FP64,
        on_open_day: Callable[[date], None],
    ) -> None:
        super().__init__(master, bg=theme.surface)
        self.theme = theme
        self.ppm = pixels_per_minute
        self.on_open_day = on_open_day
        self._todos: tuple[Todo, ...] = ()
        self._week_anchor = date.today()
        self._now = datetime.now()
        self._scroll_ready = False
        self._header_days: list[tuple[date, float, float]] = []

        self.hour_font = tkfont.Font(family=theme.number_font, size=7)
        self.time_font = tkfont.Font(family=theme.number_font, size=7, weight="bold")
        self.event_font = tkfont.Font(family=theme.font_family, size=8, weight="bold")
        self.head_font = tkfont.Font(family=theme.font_family, size=8, weight="bold")
        self.num_font = tkfont.Font(family=theme.number_font, size=12, weight="bold")
        self.now_font = tkfont.Font(family=theme.font_family, size=7, weight="bold")

        self.header = tk.Canvas(
            self, height=54, bg=theme.surface, highlightthickness=0, bd=0,
        )
        self.header.pack(fill="x", padx=22)
        self.header.bind("<Configure>", lambda e: self._draw_header())
        self.header.bind("<Button-1>", self._on_header_click)

        body = tk.Frame(self, bg=theme.surface)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=theme.surface, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self._draw_grid())
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _draw_header(self) -> None:
        t = self.theme
        self.header.delete("all")
        width = max(self.header.winfo_width(), 440)
        days = week_days(self._week_anchor)
        x = 6.0
        gap = 5
        column = (width - 12 - gap * 6) / 7
        self._header_days = []
        for index, day in enumerate(days):
            selected = day == self._week_anchor
            today = day == date.today()
            fill = t.accent if selected else "#FBF9F4"
            outline = t.accent if selected else t.soft_line
            rounded_rect(
                self.header, x, 5, x + column, 48, 11,
                fill=fill, outline=outline, width=1,
            )
            self.header.create_text(
                x + 10, 16, text=WEEKDAY_SHORT[index], anchor="w",
                fill="#FFF4EF" if selected else t.muted, font=self.head_font,
            )
            self.header.create_text(
                x + 10, 33, text=str(day.day), anchor="w",
                fill="#FFFFFF" if selected else (t.accent if today else t.ink),
                font=self.num_font,
            )
            if today and not selected:
                self.header.create_oval(
                    x + column - 12, 12, x + column - 8, 16,
                    fill=t.accent, outline="",
                )
            self._header_days.append((day, x, x + column))
            x += column + gap

    def _on_header_click(self, event: tk.Event) -> None:
        for day, x1, x2 in self._header_days:
            if x1 <= event.x <= x2:
                self.on_open_day(day)
                return

    def _draw_grid(self) -> None:
        t = self.theme
        c = self.canvas
        c.delete("all")
        width = max(c.winfo_width(), 500)
        days = week_days(self._week_anchor)
        gap = 5.0
        column = (width - GUTTER - 16 - gap * 6) / 7
        total = TOP + 24 * 60 * self.ppm + 26
        c.configure(scrollregion=(0, 0, width, total))

        for hour in range(24):
            y = y_for_minute(hour * 60, TOP, self.ppm)
            c.create_line(GUTTER, y, width - 12, y, fill=t.line if hour else "#DCD6CA")
            c.create_text(
                GUTTER - 9, y, text=f"{hour:02d}:00", anchor="e",
                fill=t.muted if hour else t.ink, font=self.hour_font,
            )

        for index, day in enumerate(days):
            x1 = GUTTER + 8 + index * (column + gap)
            x2 = x1 + column
            if index:
                c.create_line(x1 - gap / 2, 0, x1 - gap / 2, total, fill=t.soft_line)
            layouts = layout_events(self._todos, day, TOP, self.ppm, min_height=22)
            for layout in layouts:
                todo = layout.todo
                assert todo.slot is not None
                accent = t.accent_for(todo.accent_index)
                lane_width = (x2 - x1) / max(layout.lane_count, 1)
                ex1 = x1 + layout.lane * lane_width
                ex2 = ex1 + lane_width - 3
                y1, y2 = layout.top, layout.top + layout.height
                tag = f"todo-{todo.id}"
                items = [
                    rounded_rect(c, ex1, y1, ex2, y2, 7, fill=t.tint(accent), outline=""),
                    rounded_rect(c, ex1, y1, ex1 + 3, y2, 1.5, fill=accent, outline=""),
                    c.create_text(
                        ex1 + 7, y1 + 7,
                        text=format_minute(todo.slot.start_minute),
                        anchor="w", fill=accent, font=self.time_font,
                    ),
                    c.create_text(
                        ex1 + 7, y1 + 19,
                        text=fit_text(self.event_font, todo.text, max(ex2 - ex1 - 10, 20)),
                        anchor="w", fill=t.ink, font=self.event_font,
                    ),
                ]
                for item in items:
                    c.addtag_withtag(tag, item)
                c.tag_bind(tag, "<Button-1>", lambda e, td=todo: self.on_open_day(td.slot.day))
                c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
                c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor=""))

        self._draw_now(days, width, column, gap)
        if not self._scroll_ready and c.winfo_height() > 20:
            self._scroll_ready = True
            self.after_idle(self._initial_scroll)

    def _draw_now(self, days, width: float, column: float, gap: float) -> None:
        t = self.theme
        self.canvas.delete("nowline")
        if date.today() not in days:
            return
        now = self._now
        minute = now.hour * 60 + now.minute + fp64(now.second) / 60.0
        y = TOP + minute * self.ppm
        self.canvas.create_line(
            GUTTER, y, width - 12, y, fill=t.accent, width=1.5, tags="nowline",
        )
        index = days.index(date.today())
        x = GUTTER + 8 + index * (column + gap)
        self.canvas.create_oval(
            x - 3, y - 3, x + 3, y + 3, fill=t.accent, outline="", tags="nowline",
        )
        self.canvas.tag_lower("nowline")

    def _initial_scroll(self) -> None:
        now = datetime.now()
        minute = max(7 * 60, now.hour * 60 + now.minute - 180)
        total = TOP + 1440 * self.ppm + 26
        self.canvas.yview_moveto(max(0.0, (TOP + minute * self.ppm - 80) / total))

    def render(self, todos: tuple[Todo, ...], anchor: date, now: datetime) -> None:
        changed = anchor != self._week_anchor
        self._todos = todos
        self._week_anchor = anchor
        self._now = now
        if changed:
            self._scroll_ready = False
        self._draw_header()
        self._draw_grid()

    def update_now(self, now: datetime) -> None:
        self._now = now
        self._draw_grid()

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event: tk.Event) -> str:
        delta = int(-event.delta / 120)
        if delta:
            self.canvas.yview_scroll(delta, "units")
        return "break"
