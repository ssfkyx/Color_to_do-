"""Topmost one-minute reminder with exactly two actions: 做 / 拖."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import font as tkfont
from typing import Callable

from ..core.todo import Todo
from ..fp64 import fp64
from .canvas_kit import bell, rounded_rect
from .theme import Theme


class ReminderPopup(tk.Toplevel):
    WIDTH = 408
    HEIGHT = 202

    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        todo: Todo,
        deadline: datetime,
        visible_seconds: int,
        slot: int,
        on_do: Callable[[Todo], None],
        on_drag: Callable[[Todo], None],
        on_timeout: Callable[[Todo], None],
    ) -> None:
        super().__init__(master)
        self.theme = theme
        self.todo = todo
        self.deadline = deadline
        self.visible_seconds = max(1, visible_seconds)
        self.on_do = on_do
        self.on_drag = on_drag
        self.on_timeout = on_timeout
        self._closed = False
        self._job: str | None = None
        self._hover_button: str | None = None

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=theme.background)
        try:
            self.attributes("-transparentcolor", theme.background)
        except tk.TclError:
            pass
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - self.WIDTH - 26
        y = screen_h - self.HEIGHT - 76 - slot * (self.HEIGHT + 10)
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        self.canvas = tk.Canvas(
            self,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=theme.background,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._build()
        self._tick()

    def _fonts(self) -> None:
        t = self.theme
        self.label_font = tkfont.Font(family=t.font_family, size=9, weight="bold")
        self.title_font = tkfont.Font(family=t.font_family, size=13, weight="bold")
        self.small_font = tkfont.Font(family=t.font_family, size=8)
        self.time_font = tkfont.Font(family=t.number_font, size=9)
        self.button_font = tkfont.Font(family=t.font_family, size=10, weight="bold")

    def _build(self) -> None:
        self._fonts()
        t = self.theme
        c = self.canvas
        accent = t.accent_for(self.todo.accent_index)
        primary = t.accent
        rounded_rect(c, 1, 1, self.WIDTH - 1, self.HEIGHT - 1, 19,
                     fill=t.surface, outline=t.line)

        rounded_rect(c, 3, 8, 9, self.HEIGHT - 8, 3, fill=accent, outline="")
        c.create_oval(22, 22, 54, 54, fill=t.tint(accent, 0.83), outline="")
        bell(c, 38, 38, accent, 0.9)

        c.create_text(66, 31, text="到时间了", anchor="w", fill=primary, font=self.label_font)
        c.create_text(
            66, 48,
            text=f"原定 {self.todo.slot.start.strftime('%H:%M') if self.todo.slot else ''}",
            anchor="w", fill=t.muted, font=self.small_font,
        )
        c.create_text(
            self.WIDTH - 24, 28, text="现在", anchor="e", fill=t.faint, font=self.small_font,
        )
        c.create_text(
            self.WIDTH - 24, 44, text=datetime.now().strftime("%H:%M"),
            anchor="e", fill=t.muted, font=self.time_font,
        )

        c.create_text(
            26, 78,
            text=self.todo.text[:80] + ("…" if len(self.todo.text) > 80 else ""),
            anchor="w", fill=t.ink, font=self.title_font,
            width=self.WIDTH - 52,
        )

        self._bar_track = rounded_rect(
            c, 26, 112, self.WIDTH - 26, 117, 2.5, fill=t.soft_line, outline="",
        )
        self._bar_fill = c.create_rectangle(
            26, 112, self.WIDTH - 26, 117, fill=primary, outline="",
        )
        self._countdown_text = c.create_text(
            self.WIDTH - 26, 132, text="", anchor="e", fill=t.muted, font=self.small_font,
        )
        c.create_text(
            26, 132, text="1 分钟无操作 · 5 分钟后再提醒",
            anchor="w", fill=t.faint, font=self.small_font,
        )

        self._button(c, 26, 148, 164, 184, "做", t.surface, primary, "do")
        self._button(c, 174, 148, 312, 184, "拖", t.ink, t.soft_line, "drag")

        c.tag_bind("btn-do", "<Button-1>", lambda e: self._finish("do"))
        c.tag_bind("btn-drag", "<Button-1>", lambda e: self._finish("drag"))
        c.tag_bind("btn-do", "<Enter>", lambda e: c.configure(cursor="hand2"))
        c.tag_bind("btn-drag", "<Enter>", lambda e: c.configure(cursor="hand2"))
        c.tag_bind("btn-do", "<Leave>", lambda e: c.configure(cursor=""))
        c.tag_bind("btn-drag", "<Leave>", lambda e: c.configure(cursor=""))
        self.lift()

    def _button(
        self,
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        label: str,
        fg: str,
        fill: str,
        tag: str,
    ) -> None:
        items = [
            rounded_rect(canvas, x1, y1, x2, y2, 10, fill=fill, outline=""),
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label, fill=fg, font=self.button_font),
        ]
        for item in items:
            canvas.addtag_withtag(f"btn-{tag}", item)

    def _tick(self) -> None:
        if self._closed:
            return
        now = datetime.now()
        remaining = (self.deadline - now).total_seconds()
        fraction = max(0.0, min(fp64(remaining / self.visible_seconds), 1.0))
        left = max(0, self.WIDTH - 52)
        self.canvas.coords(
            self._bar_fill,
            26, 112, 26 + left * fraction, 117,
        )
        seconds = max(0, int(remaining))
        self.canvas.itemconfigure(
            self._countdown_text,
            text=f"{seconds // 60}:{seconds % 60:02d} 后自动稍后",
        )
        if remaining <= 0:
            self._finish("timeout")
            return
        self._job = self.after(200, self._tick)

    def _finish(self, action: str) -> None:
        if self._closed:
            return
        self._closed = True
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        try:
            self.destroy()
        finally:
            if action == "do":
                self.on_do(self.todo)
            elif action == "drag":
                self.on_drag(self.todo)
            else:
                self.on_timeout(self.todo)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        try:
            self.destroy()
        except tk.TclError:
            pass
