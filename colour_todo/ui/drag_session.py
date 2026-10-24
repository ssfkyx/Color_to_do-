"""One drag gesture: a floating ghost and a screen-point drop target."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from ..core.todo import Todo
from .theme import Theme


class DragSession:
    def __init__(
        self,
        root: tk.Tk,
        theme: Theme,
        hit_test: Callable[[int, int], int | None],
        on_hover: Callable[[int | None], None],
        on_drop: Callable[[Todo, int], None],
    ) -> None:
        self.root = root
        self.theme = theme
        self.hit_test = hit_test
        self.on_hover = on_hover
        self.on_drop = on_drop
        self._todo: Todo | None = None
        self._ghost: tk.Toplevel | None = None
        self._moved = False

    @property
    def active(self) -> bool:
        return self._todo is not None

    def start(self, todo: Todo, event: tk.Event) -> None:
        if self._todo is not None:
            self.cancel()
        self.on_hover(None)
        self._todo = todo
        self._moved = False
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.attributes("-alpha", 0.95)
        ghost.configure(bg=self.theme.accent_for(todo.accent_index))
        shell = tk.Frame(ghost, bg=self.theme.surface)
        shell.pack(padx=2, pady=2)
        tk.Frame(
            shell, bg=self.theme.accent_for(todo.accent_index), width=4,
        ).pack(side="left", fill="y")
        tk.Label(
            shell,
            text=todo.text,
            bg=self.theme.surface,
            fg=self.theme.ink,
            font=(self.theme.font_family, 9, "bold"),
            padx=10,
            pady=8,
        ).pack(side="left")
        self._ghost = ghost
        self._move(event.x_root, event.y_root)
        self.root.bind_all("<B1-Motion>", self._on_motion, add="+")
        self.root.bind_all("<ButtonRelease-1>", self._on_release, add="+")

    def cancel(self) -> None:
        self.root.unbind_all("<B1-Motion>")
        self.root.unbind_all("<ButtonRelease-1>")
        if self._ghost is not None:
            self._ghost.destroy()
            self._ghost = None
        self._todo = None
        self.on_hover(None)

    def _move(self, x_root: int, y_root: int) -> None:
        if self._ghost is not None:
            self._ghost.geometry(f"+{x_root + 16}+{y_root + 12}")

    def _on_motion(self, event: tk.Event) -> None:
        if self._todo is not None:
            self._moved = True
            self._move(event.x_root, event.y_root)
            self.on_hover(self.hit_test(event.x_root, event.y_root))

    def _on_release(self, event: tk.Event) -> None:
        todo = self._todo
        moved = self._moved
        self.cancel()
        if todo is None or not moved:
            return
        minute = self.hit_test(event.x_root, event.y_root)
        if minute is not None:
            self.on_drop(todo, minute)
