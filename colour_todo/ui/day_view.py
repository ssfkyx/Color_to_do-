"""Day view: 7-day strip plus a scrollable 24-hour timeline."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable

from ..core.todo import Todo
from ..core.view_mode import week_days
from ..fp64 import FP64, fp64
from .canvas_kit import (
    fit_text,
    format_minute,
    minute_at_canvas_y,
    rounded_rect,
    y_for_minute,
)
from .event_layout import EventLayout, layout_events
from .theme import Theme

WEEKDAY_SHORT = ("一", "二", "三", "四", "五", "六", "日")
TOP = 16.0
GUTTER = 58.0


class DayView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        pixels_per_minute: FP64,
        snap_minutes: int,
        default_duration: int,
        on_date_change: Callable[[date], None],
        on_event_drag_start: Callable[[Todo, tk.Event], None],
        on_event_context: Callable[[Todo, tk.Event], None],
    ) -> None:
        super().__init__(master, bg=theme.surface)
        self.theme = theme
        self.ppm = pixels_per_minute
        self.snap_minutes = snap_minutes
        self.default_duration = default_duration
        self.on_date_change = on_date_change
        self.on_event_drag_start = on_event_drag_start
        self.on_event_context = on_event_context
        self._todos: tuple[Todo, ...] = ()
        self._date = date.today()
        self._now = datetime.now()
        self._highlight_id: str | None = None
        self._drop_minute: int | None = None
        self._scroll_ready = False
        self._strip_days: list[tuple[date, float, float]] = []
        self._layouts: list[EventLayout] = []

        self._fonts()
        self.strip = tk.Canvas(
            self, height=66, bg=theme.surface, highlightthickness=0, bd=0,
        )
        self.strip.pack(fill="x", padx=22, pady=(0, 0))
        self.strip.bind("<Configure>", lambda e: self._draw_strip())
        self.strip.bind("<Button-1>", self._on_strip_click)

        body = tk.Frame(self, bg=theme.surface)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=theme.surface, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self._draw_timeline())
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _fonts(self) -> None:
        t = self.theme
        self.hour_font = tkfont.Font(family=t.number_font, size=8)
        self.time_font = tkfont.Font(family=t.number_font, size=8, weight="bold")
        self.event_font = tkfont.Font(family=t.font_family, size=9, weight="bold")
        self.event_small = tkfont.Font(family=t.font_family, size=8)
        self.strip_day = tkfont.Font(family=t.font_family, size=8, weight="bold")
        self.strip_num = tkfont.Font(family=t.number_font, size=14, weight="bold")
        self.now_font = tkfont.Font(family=t.font_family, size=8, weight="bold")

    # -------------------------------------------------------------- week strip

    def _draw_strip(self) -> None:
        t = self.theme
        self.strip.delete("all")
        width = max(self.strip.winfo_width(), 420)
        days = week_days(self._date)
        gap = 6
        chip_w = (width - 12 - gap * 6) / 7
        x = 6.0
        self._strip_days = []
        for index, day in enumerate(days):
            selected = day == self._date
            is_today = day == date.today()
            fill = t.accent if selected else "#FBF9F4"
            outline = t.accent if selected else t.soft_line
            rounded_rect(
                self.strip, x, 6, x + chip_w, 60, 12,
                fill=fill, outline=outline, width=1,
            )
            self.strip.create_text(
                x + 13, 20, text=WEEKDAY_SHORT[index], anchor="w",
                fill="#FFF4EF" if selected else t.muted, font=self.strip_day,
            )
            self.strip.create_text(
                x + 13, 42, text=str(day.day), anchor="w",
                fill="#FFFFFF" if selected else (t.accent if is_today else t.ink),
                font=self.strip_num,
            )
            scheduled = [
                todo for todo in self._todos
                if todo.slot is not None and todo.slot.day == day and not todo.done
            ]
            if scheduled:
                count_colour = "#FFFFFF" if selected else t.accent
                self.strip.create_text(
                    x + chip_w - 12, 43,
                    text=str(len(scheduled)),
                    anchor="e",
                    fill=count_colour,
                    font=self.strip_day,
                )
            if is_today and not selected:
                self.strip.create_oval(
                    x + chip_w - 12, 14, x + chip_w - 8, 18,
                    fill=t.accent, outline="",
                )
            self._strip_days.append((day, x, x + chip_w))
            x += chip_w + gap

    def _on_strip_click(self, event: tk.Event) -> None:
        for day, x1, x2 in self._strip_days:
            if x1 <= event.x <= x2:
                if day != self._date:
                    self.on_date_change(day)
                return

    # ------------------------------------------------------------------ timeline

    def _draw_timeline(self) -> None:
        t = self.theme
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 480)
        track_x1 = GUTTER
        track_x2 = width - 22
        total = TOP + 24 * 60 * self.ppm + 28
        canvas.configure(scrollregion=(0, 0, width, total))

        for hour in range(24):
            y = y_for_minute(hour * 60, TOP, self.ppm)
            canvas.create_line(
                track_x1, y, track_x2, y,
                fill=t.line if hour else "#DCD6CA",
            )
            canvas.create_text(
                track_x1 - 12, y,
                text=f"{hour:02d}:00",
                anchor="e",
                fill=t.muted if hour else t.ink,
                font=self.hour_font,
            )
            if hour < 23:
                half = y_for_minute(hour * 60 + 30, TOP, self.ppm)
                canvas.create_line(
                    track_x1, half, track_x2, half,
                    fill=t.soft_line, dash=(1, 4),
                )

        self._layouts = layout_events(self._todos, self._date, TOP, self.ppm)
        for layout in self._layouts:
            self._draw_event(layout, track_x1, track_x2)

        self._draw_now_line()
        self._draw_drop_preview()

        if not self._layouts:
            canvas.create_text(
                track_x1 + 18, y_for_minute(7 * 60, TOP, self.ppm) + 16,
                text="从左侧拖一张卡片到这里，安排它",
                anchor="w", fill=t.faint, font=self.event_small,
            )

        if not self._scroll_ready and canvas.winfo_height() > 20:
            self._scroll_ready = True
            self.after_idle(self._initial_scroll)

    def _draw_event(self, layout: EventLayout, track_x1: float, track_x2: float) -> None:
        t = self.theme
        todo = layout.todo
        assert todo.slot is not None
        accent = t.accent_for(todo.accent_index)
        track_width = track_x2 - track_x1 - 10
        lane_width = track_width / max(layout.lane_count, 1)
        x1 = track_x1 + 8 + layout.lane * lane_width
        x2 = x1 + lane_width - 4
        y1 = layout.top
        y2 = layout.top + layout.height
        tag = f"todo-{todo.id}"

        # Draw the selection outline first; otherwise its (empty-fill) polygon
        # sits above the card and steals mouse hits from the card's tag.
        highlight_item = None
        if self._highlight_id == todo.id:
            highlight_item = rounded_rect(
                self.canvas, x1 - 2, y1 - 2, x2 + 2, y2 + 2, 10,
                fill="", outline=accent, width=2, dash=(4, 3),
            )

        items = [
            rounded_rect(self.canvas, x1, y1, x2, y2, 9, fill=t.tint(accent), outline=""),
            rounded_rect(self.canvas, x1, y1, x1 + 4, y2, 2, fill=accent, outline=""),
        ]
        if highlight_item is not None:
            items.append(highlight_item)
        if layout.height < 30:
            items.append(
                self.canvas.create_text(
                    x1 + 11, (y1 + y2) / 2,
                    text=f"{format_minute(todo.slot.start_minute)}  {fit_text(self.event_font, todo.text, max(x2 - x1 - 24, 40))}",
                    anchor="w", fill=t.ink, font=self.event_small,
                )
            )
        else:
            items.append(
                self.canvas.create_text(
                    x1 + 12, y1 + 10,
                    text=format_minute(todo.slot.start_minute),
                    anchor="w", fill=accent, font=self.time_font,
                )
            )
            items.append(
                self.canvas.create_text(
                    x1 + 12, y1 + 25,
                    text=fit_text(self.event_font, todo.text, max(x2 - x1 - 22, 40)),
                    anchor="w", fill=t.ink, font=self.event_font,
                )
            )
        for item in items:
            self.canvas.addtag_withtag(tag, item)
        self.canvas.tag_bind(
            tag, "<ButtonPress-1>", lambda e, td=todo: self.on_event_drag_start(td, e)
        )
        self.canvas.tag_bind(
            tag, "<Button-3>", lambda e, td=todo: self.on_event_context(td, e)
        )
        self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.configure(cursor="hand2"))
        self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.configure(cursor=""))

    def _draw_now_line(self) -> None:
        t = self.theme
        self.canvas.delete("nowline")
        if self._date != date.today():
            return
        now = self._now
        minute = now.hour * 60 + now.minute + fp64(now.second) / 60.0
        y = y_for_minute(0, TOP, self.ppm) + minute * self.ppm
        width = max(self.canvas.winfo_width(), 480)
        track_x1, track_x2 = GUTTER, width - 22
        self.canvas.create_line(
            track_x1, y, track_x2, y, fill=t.accent, width=2, tags="nowline",
        )
        self.canvas.create_oval(
            track_x1 - 4, y - 4, track_x1 + 4, y + 4,
            fill=t.accent, outline="", tags="nowline",
        )
        self.canvas.create_text(
            track_x2 - 4, y - 9,
            text=f"现在 {now.strftime('%H:%M')}",
            anchor="e", fill=t.accent, font=self.now_font, tags="nowline",
        )
        self.canvas.tag_lower("nowline")

    def _initial_scroll(self) -> None:
        now = datetime.now()
        minute = now.hour * 60 + now.minute if self._date == date.today() else 7 * 60
        minute = max(7 * 60, minute - 180)
        self.scroll_to_minute(minute)

    # ------------------------------------------------------------------ public

    def render(self, todos: tuple[Todo, ...], selected_date: date, now: datetime) -> None:
        date_changed = selected_date != self._date
        self._todos = todos
        self._date = selected_date
        self._now = now
        self._drop_minute = None
        if date_changed:
            self._scroll_ready = False
        self._draw_strip()
        self._draw_timeline()

    def show_drop_preview(self, minute: int | None) -> None:
        """Draw the snapped drop time while the mouse is still held."""
        self._drop_minute = minute
        self._draw_drop_preview()

    def clear_drop_preview(self) -> None:
        self._drop_minute = None
        self.canvas.delete("droppreview")

    def _draw_drop_preview(self) -> None:
        self.canvas.delete("droppreview")
        if self._drop_minute is None:
            return
        t = self.theme
        width = max(self.canvas.winfo_width(), 480)
        track_x1, track_x2 = GUTTER, width - 22
        y = y_for_minute(self._drop_minute, TOP, self.ppm)
        self.canvas.create_line(
            track_x1, y, track_x2, y,
            fill=t.accent, width=2, dash=(6, 4), tags="droppreview",
        )
        self.canvas.create_oval(
            track_x1 - 4, y - 4, track_x1 + 4, y + 4,
            fill=t.accent, outline="", tags="droppreview",
        )
        pill_x1 = track_x1 + 8
        pill_x2 = track_x1 + 100
        rounded_rect(
            self.canvas, pill_x1, y - 11, pill_x2, y + 11, 8,
            fill=t.accent, outline="", tags="droppreview",
        )
        self.canvas.create_text(
            (pill_x1 + pill_x2) / 2, y,
            text=f"松开 · {format_minute(self._drop_minute)}",
            fill="#FFFFFF", font=self.now_font, tags="droppreview",
        )
        self.canvas.tag_raise("droppreview")

    def update_now(self, now: datetime) -> None:
        self._now = now
        self._draw_now_line()

    def minute_at_screen(self, x_root: int, y_root: int) -> int | None:
        cx = self.canvas.winfo_rootx()
        cy = self.canvas.winfo_rooty()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = x_root - cx
        y = y_root - cy
        if not (0 <= x <= cw and 0 <= y <= ch):
            return None
        canvas_y = self.canvas.canvasy(y)
        if canvas_y < TOP or canvas_y > TOP + 1440 * self.ppm:
            return None
        return minute_at_canvas_y(
            canvas_y,
            TOP,
            self.ppm,
            self.snap_minutes,
            max_minute=1440 - self.default_duration,
        )

    def scroll_to_minute(self, minute: int) -> None:
        total = TOP + 1440 * self.ppm + 28
        top_y = TOP + max(0, min(minute, 1439)) * self.ppm
        self.canvas.yview_moveto(max(0.0, (top_y - 80.0) / total))

    def scroll_to_todo(self, todo: Todo) -> None:
        if todo.slot is not None:
            self.scroll_to_minute(todo.slot.start_minute)

    def highlight(self, todo: Todo) -> None:
        self._highlight_id = todo.id
        self.scroll_to_todo(todo)
        self._draw_timeline()

    def clear_highlight(self) -> None:
        if self._highlight_id is not None:
            self._highlight_id = None
            self._draw_timeline()

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event: tk.Event) -> str:
        delta = int(-event.delta / 120)
        if delta:
            self.canvas.yview_scroll(delta, "units")
        return "break"
