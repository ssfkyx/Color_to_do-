"""Calendar host: header, 日/周/月 switch, and the three view widgets."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import font as tkfont
from typing import Callable

from ..core.todo import Todo
from ..core.view_mode import ViewMode, shift_date, week_days, week_start
from ..fp64 import FP64
from .day_view import DayView
from .month_view import MonthView
from .theme import Theme
from .week_view import WeekView
from .widgets import SegmentedControl

WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


class CalendarView(tk.Frame):
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
        self.snap_minutes = snap_minutes
        self.default_duration = default_duration
        self.on_date_change = on_date_change
        self.on_event_drag_start = on_event_drag_start
        self.on_event_context = on_event_context
        self.mode = ViewMode.DAY
        self.selected_date = date.today()
        self._todos: tuple[Todo, ...] = ()
        self._now = datetime.now()

        self.title_font = tkfont.Font(family=theme.font_family, size=21, weight="bold")
        self.sub_font = tkfont.Font(family=theme.font_family, size=9)
        self.nav_font = tkfont.Font(family=theme.number_font, size=14)

        header = tk.Frame(self, bg=theme.surface)
        header.pack(fill="x", padx=24, pady=(16, 6))
        self.title = tk.Label(
            header, text="", bg=theme.surface, fg=theme.ink, font=self.title_font,
        )
        self.title.pack(side="left")
        self.subtitle = tk.Label(
            header, text="", bg=theme.surface, fg=theme.muted, font=self.sub_font,
        )
        self.subtitle.pack(side="left", padx=(10, 0), pady=(8, 0))

        self.mode_switch = SegmentedControl(
            header,
            theme,
            options=[("day", "日"), ("week", "周"), ("month", "月")],
            value="day",
            on_change=self._on_mode_change,
            width=136,
            height=30,
            font_size=9,
        )
        self.mode_switch.pack(side="right", padx=(10, 0))

        today_btn = tk.Button(
            header, text="今天", command=self.go_today, relief="flat", borderwidth=0,
            bg=theme.soft_line, fg=theme.ink, activebackground=theme.line,
            font=(theme.font_family, 9, "bold"), padx=14, pady=5, cursor="hand2",
        )
        today_btn.pack(side="right", padx=(8, 0))

        next_btn = self._nav_button(header, "›", lambda: self.shift(1))
        next_btn.pack(side="right")
        prev_btn = self._nav_button(header, "‹", lambda: self.shift(-1))
        prev_btn.pack(side="right", padx=(0, 4))

        tk.Frame(self, bg=theme.line, height=1).pack(fill="x", padx=24, pady=(4, 0))

        self.content = tk.Frame(self, bg=theme.surface)
        self.content.pack(fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.day_view = DayView(
            self.content, theme, pixels_per_minute, snap_minutes, default_duration,
            on_date_change=self._select_day,
            on_event_drag_start=self.on_event_drag_start,
            on_event_context=self.on_event_context,
        )
        self.week_view = WeekView(
            self.content, theme, pixels_per_minute, on_open_day=self.open_day,
        )
        self.month_view = MonthView(
            self.content, theme, on_open_day=self.open_day,
        )
        for view in (self.day_view, self.week_view, self.month_view):
            view.grid(row=0, column=0, sticky="nsew")
        self._show_current()
        self._update_title()

    def _nav_button(self, master: tk.Misc, text: str, command: Callable[[], None]) -> tk.Button:
        t = self.theme
        return tk.Button(
            master, text=text, command=command, relief="flat", borderwidth=0,
            bg=t.surface, fg=t.muted, activebackground=t.soft_line,
            font=self.nav_font, width=2, cursor="hand2",
        )

    # ------------------------------------------------------------------ state

    def render(self, todos: tuple[Todo, ...], now: datetime) -> None:
        self._todos = todos
        self._now = now
        self._update_title()
        if self.mode is ViewMode.DAY:
            self.day_view.render(todos, self.selected_date, now)
        elif self.mode is ViewMode.WEEK:
            self.week_view.render(todos, self.selected_date, now)
        else:
            self.month_view.render(todos, self.selected_date, now)

    def set_mode(self, mode: ViewMode) -> None:
        if mode is self.mode:
            return
        self.mode = mode
        self.mode_switch.set_value(mode.value)
        self._show_current()
        self._update_title()
        self.render(self._todos, self._now)

    def set_date(self, day: date) -> None:
        self.selected_date = day
        self._update_title()
        self.render(self._todos, self._now)

    def shift(self, direction: int) -> None:
        self.selected_date = shift_date(self.selected_date, self.mode, direction)
        self._update_title()
        self.render(self._todos, self._now)
        self.on_date_change(self.selected_date)

    def go_today(self) -> None:
        # "今天" always returns to today's Day view, not merely today's date
        # inside a week/month view.
        self.open_day(date.today())

    def open_day(self, day: date) -> None:
        self.selected_date = day
        self.mode = ViewMode.DAY
        self.mode_switch.set_value("day")
        self._show_current()
        self._update_title()
        self.render(self._todos, self._now)
        self.on_date_change(day)

    def open_todo(self, todo: Todo) -> None:
        if todo.slot is None:
            return
        self.open_day(todo.slot.day)
        self.day_view.highlight(todo)

    def _select_day(self, day: date) -> None:
        self.selected_date = day
        self._update_title()
        self.render(self._todos, self._now)
        self.on_date_change(day)

    def _on_mode_change(self, value: str) -> None:
        self.set_mode(ViewMode(value))

    def _show_current(self) -> None:
        view = {
            ViewMode.DAY: self.day_view,
            ViewMode.WEEK: self.week_view,
            ViewMode.MONTH: self.month_view,
        }[self.mode]
        view.tkraise()

    # ------------------------------------------------------------------ title

    def _update_title(self) -> None:
        day = self.selected_date
        if self.mode is ViewMode.DAY:
            title = f"{day.month} 月 {day.day} 日"
            subtitle = WEEKDAY_CN[day.weekday()]
        elif self.mode is ViewMode.WEEK:
            days = week_days(day)
            first, last = days[0], days[-1]
            if first.month == last.month:
                title = f"{first.month} 月 {first.day} – {last.day} 日"
            else:
                title = f"{first.month} 月 {first.day} 日 – {last.month} 月 {last.day} 日"
            subtitle = f"第 {week_start(day).isocalendar().week} 周"
        else:
            title = f"{day.year} 年 {day.month} 月"
            subtitle = "点击某天查看"
        self.title.configure(text=title)
        self.subtitle.configure(text=subtitle)

    def minute_at_screen(self, x_root: int, y_root: int) -> int | None:
        if self.mode is not ViewMode.DAY:
            return None
        return self.day_view.minute_at_screen(x_root, y_root)

    def highlight(self, todo: Todo) -> None:
        self.open_todo(todo)

    def update_now(self, now: datetime) -> None:
        self._now = now
        if self.mode is ViewMode.DAY:
            self.day_view.update_now(now)
        elif self.mode is ViewMode.WEEK:
            self.week_view.update_now(now)
        else:
            self.month_view.update_now(now)
