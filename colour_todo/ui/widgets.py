"""Small reusable visual widgets: scrolling list and segmented control."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Sequence

from .canvas_kit import rounded_rect
from .theme import Theme


class ScrollableColumn(tk.Frame):
    """A vertical Canvas + inner Frame, with a scrollbar shown only when needed."""

    def __init__(self, master: tk.Misc, bg: str) -> None:
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", padx=(4, 0))
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.inner.bind("<Enter>", self._bind_wheel)
        self.inner.bind("<Leave>", self._unbind_wheel)

    def clear(self) -> None:
        for child in self.inner.winfo_children():
            child.destroy()

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0.0)

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._sync_scrollbar()

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_scrollbar()

    def _on_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set(first, last)
        self._sync_scrollbar()

    def _sync_scrollbar(self) -> None:
        first, last = self.canvas.yview()
        if first <= 0.0 and last >= 1.0:
            self.scrollbar.pack_forget()
        elif not self.scrollbar.winfo_manager():
            self.scrollbar.pack(side="right", fill="y", padx=(4, 0))

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event: tk.Event) -> str:
        delta = int(-event.delta / 120)
        if delta:
            self.canvas.yview_scroll(delta, "units")
        return "break"


class SegmentedControl(tk.Canvas):
    """A compact rounded segmented control drawn on a Canvas."""

    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        options: Sequence[tuple[str, str]],
        value: str,
        on_change: Callable[[str], None] | None = None,
        width: int = 156,
        height: int = 30,
        font_size: int = 9,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg=master.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.theme = theme
        self.options = list(options)
        self.value = value
        self.on_change = on_change
        self._width = width
        self._height = height
        self._font = tkfont.Font(family=theme.font_family, size=font_size, weight="bold")
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", lambda e: self.redraw())
        self.redraw()

    def set_value(self, value: str, notify: bool = False) -> None:
        if value == self.value:
            return
        self.value = value
        self.redraw()
        if notify and self.on_change:
            self.on_change(value)

    def set_labels(self, labels: dict[str, str]) -> None:
        self.options = [(value, labels.get(value, label)) for value, label in self.options]
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), self._width)
        height = max(self.winfo_height(), self._height)
        radius = height / 2
        rounded_rect(self, 0, 0, width, height, radius, fill=self.theme.soft_line, outline="")
        segment = width / max(len(self.options), 1)
        for index, (value, label) in enumerate(self.options):
            x1 = index * segment
            x2 = x1 + segment
            selected = value == self.value
            if selected:
                rounded_rect(
                    self, x1 + 2, 2, x2 - 2, height - 2, radius - 2,
                    fill=self.theme.surface, outline="",
                )
            self.create_text(
                (x1 + x2) / 2,
                height / 2,
                text=label,
                fill=self.theme.accent if selected else self.theme.muted,
                font=self._font,
            )

    def _on_click(self, event: tk.Event) -> None:
        width = max(self.winfo_width(), self._width)
        segment = width / max(len(self.options), 1)
        index = min(int(event.x / segment), len(self.options) - 1)
        value = self.options[index][0]
        if value != self.value:
            self.set_value(value, notify=True)
