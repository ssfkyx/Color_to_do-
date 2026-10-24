"""Month view: a six-week Monday-first calendar with compact event chips."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import font as tkfont
from typing import Callable

from ..core.todo import Todo
from ..core.view_mode import month_days
from .canvas_kit import fit_text, format_minute, rounded_rect
from .theme import Theme

WEEKDAY_SHORT = ("一", "二", "三", "四", "五", "六", "日")


class MonthView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        on_open_day: Callable[[date], None],
    ) -> None:
        super().__init__(master, bg=theme.surface)
        self.theme = theme
        self.on_open_day = on_open_day
        self._todos: tuple[Todo, ...] = ()
        self._selected = date.today()
        self._now = datetime.now()
        self._cells: list[tuple[date, float, float, float, float]] = []

        self.week_font = tkfont.Font(family=theme.font_family, size=8, weight="bold")
        self.num_font = tkfont.Font(family=theme.number_font, size=10, weight="bold")
        self.event_font = tkfont.Font(family=theme.font_family, size=7)
        self.more_font = tkfont.Font(family=theme.font_family, size=7, weight="bold")

        self.header = tk.Canvas(
            self, height=30, bg=theme.surface, highlightthickness=0, bd=0,
        )
        self.header.pack(fill="x", padx=22)
        self.header.bind("<Configure>", lambda e: self._draw_header())

        self.canvas = tk.Canvas(self, bg=theme.surface, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True, padx=22, pady=(0, 14))
        self.canvas.bind("<Configure>", lambda e: self._draw_grid())
        self.canvas.bind("<Button-1>", self._on_click)

    def _draw_header(self) -> None:
        t = self.theme
        self.header.delete("all")
        width = max(self.header.winfo_width(), 440)
        cell = (width - 12) / 7
        for index, label in enumerate(WEEKDAY_SHORT):
            self.header.create_text(
                index * cell + cell / 2 + 6, 16,
                text=label, fill=t.muted, font=self.week_font,
            )

    def _draw_grid(self) -> None:
        t = self.theme
        c = self.canvas
        c.delete("all")
        width = max(c.winfo_width(), 440)
        height = max(c.winfo_height(), 320)
        cell_w = (width - 12) / 7
        cell_h = (height - 8) / 6
        cells = month_days(self._selected)
        self._cells = []

        for index, day in enumerate(cells):
            row, col = divmod(index, 7)
            x1 = 6 + col * cell_w
            y1 = 4 + row * cell_h
            x2, y2 = x1 + cell_w, y1 + cell_h
            if day is None:
                continue
            self._cells.append((day, x1, y1, x2, y2))
            selected = day == self._selected
            today = day == date.today()
            if selected:
                rounded_rect(c, x1 + 2, y1 + 2, x2 - 2, y2 - 2, 9,
                             fill="#FFF8F5", outline=t.accent, width=1)
            elif today:
                rounded_rect(c, x1 + 2, y1 + 2, x2 - 2, y2 - 2, 9,
                             fill=t.soft_line, outline="")
            c.create_line(x1, y1, x2, y1, fill=t.soft_line)
            c.create_line(x1, y1, x1, y2, fill=t.soft_line)

            num_colour = t.accent if today else t.ink
            if selected:
                c.create_oval(x1 + 8, y1 + 7, x1 + 30, y1 + 29, fill=t.accent, outline="")
                num_colour = "#FFFFFF"
            c.create_text(
                x1 + 19, y1 + 18, text=str(day.day),
                fill=num_colour, font=self.num_font,
            )

            events = [
                todo for todo in self._todos
                if todo.slot is not None and todo.slot.day == day and not todo.done
            ]
            events.sort(key=lambda todo: todo.slot.start)  # type: ignore[union-attr]
            for event_index, todo in enumerate(events[:2]):
                assert todo.slot is not None
                accent = t.accent_for(todo.accent_index)
                cy = y1 + 34 + event_index * 18
                rounded_rect(c, x1 + 6, cy, x2 - 6, cy + 15, 5,
                             fill=t.tint(accent, 0.9), outline="")
                c.create_oval(x1 + 10, cy + 6, x1 + 14, cy + 10, fill=accent, outline="")
                label = f"{format_minute(todo.slot.start_minute)} {todo.text}"
                c.create_text(
                    x1 + 18, cy + 7,
                    text=fit_text(self.event_font, label, max(cell_w - 34, 20)),
                    anchor="w", fill=t.ink, font=self.event_font,
                )
            if len(events) > 2:
                c.create_text(
                    x2 - 10, y2 - 10,
                    text=f"+{len(events) - 2}", anchor="e",
                    fill=t.muted, font=self.more_font,
                )

    def _on_click(self, event: tk.Event) -> None:
        for day, x1, y1, x2, y2 in self._cells:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.on_open_day(day)
                return

    def render(self, todos: tuple[Todo, ...], selected_date: date, now: datetime) -> None:
        self._todos = todos
        self._selected = selected_date
        self._now = now
        self._draw_header()
        self._draw_grid()

    def update_now(self, now: datetime) -> None:
        self._now = now
