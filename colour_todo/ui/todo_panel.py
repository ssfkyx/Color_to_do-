"""Left pane: capture input, unscheduled pool, and the completed record."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import font as tkfont
from typing import Callable

from ..core.todo import Todo
from .canvas_kit import check_mark, fit_text, rounded_rect
from .theme import Theme
from .widgets import ScrollableColumn, SegmentedControl

PLACEHOLDER = "下一件想做的事…"
WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


class TodoPanel(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        width: int,
        on_capture: Callable[[str], None],
        on_drag_start: Callable[[Todo, tk.Event], None],
        on_context_menu: Callable[[Todo, tk.Event], None],
    ) -> None:
        super().__init__(
            master,
            bg=theme.panel,
            width=width,
            highlightthickness=0,
            bd=0,
        )
        self.theme = theme
        self.on_capture = on_capture
        self.on_drag_start = on_drag_start
        self.on_context_menu = on_context_menu
        self.filter_value = "pool"
        self._selected_date = date.today()
        self._todos: tuple[Todo, ...] = ()
        self._cards: dict[str, tk.Canvas] = {}
        self._build()
        self.pack_propagate(False)

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        t = self.theme
        self.title_font = tkfont.Font(family=t.font_family, size=26, weight="bold")
        self.date_font = tkfont.Font(family=t.font_family, size=9)
        self.card_title = tkfont.Font(family=t.font_family, size=10, weight="bold")
        self.card_hint = tkfont.Font(family=t.font_family, size=8)
        self.card_done = tkfont.Font(family=t.font_family, size=10, overstrike=1)
        self.count_font = tkfont.Font(family=t.number_font, size=9, weight="bold")

        tk.Label(
            self, text="今天", bg=t.panel, fg=t.ink, font=self.title_font,
        ).pack(anchor="w", padx=28, pady=(20, 0))
        self.date_label = tk.Label(
            self, text="", bg=t.panel, fg=t.muted, font=self.date_font,
        )
        self.date_label.pack(anchor="w", padx=28, pady=(2, 14))

        self.input_shell = tk.Frame(
            self,
            bg=t.surface,
            highlightthickness=1,
            highlightbackground=t.line,
            highlightcolor=t.accent,
        )
        self.input_shell.pack(fill="x", padx=28)
        self.var = tk.StringVar(value=PLACEHOLDER)
        self._placeholder_active = True
        self.entry = tk.Entry(
            self.input_shell,
            textvariable=self.var,
            relief="flat",
            borderwidth=0,
            bg=t.surface,
            fg=t.muted,
            insertbackground=t.accent,
            font=(t.font_family, 11),
            highlightthickness=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=(10, 9))
        self.add_button = tk.Button(
            self.input_shell,
            text="＋",
            command=self._submit,
            relief="flat",
            borderwidth=0,
            bg=t.surface,
            fg=t.accent,
            activebackground=t.soft_line,
            activeforeground=t.accent_dark,
            font=(t.font_family, 13, "bold"),
            cursor="hand2",
            padx=6,
            pady=0,
        )
        self.add_button.pack(side="right", padx=(2, 8), pady=(6, 6))
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<KP_Enter>", self._submit)
        self.entry.bind("<KeyPress>", self._on_key)
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.var.trace_add("write", self._on_var_write)
        tk.Frame(self.input_shell, bg=t.accent, height=2).pack(fill="x", side="bottom")

        tk.Label(
            self,
            text="Enter / ＋ 加入 · 拖动卡片到右侧安排时间",
            bg=t.panel,
            fg=t.muted,
            font=(t.font_family, 8),
        ).pack(anchor="w", padx=28, pady=(7, 12))

        self.filter = SegmentedControl(
            self,
            t,
            options=[("pool", "待安排"), ("done", "已完成")],
            value="pool",
            on_change=self._on_filter,
            width=296,
            height=30,
            font_size=9,
        )
        self.filter.pack(fill="x", padx=28, pady=(0, 10))

        self.list = ScrollableColumn(self, t.panel)
        self.list.pack(fill="both", expand=True, padx=28, pady=(0, 8))

        footer = tk.Frame(self, bg=t.panel)
        footer.pack(fill="x", padx=28, pady=(0, 16))
        tk.Label(
            footer, text="仅保存在本机 · 无需登录", bg=t.panel, fg=t.faint,
            font=(t.font_family, 7),
        ).pack(side="left")
        tk.Label(
            footer, text="v0.1", bg=t.panel, fg=t.faint,
            font=(t.number_font, 7),
        ).pack(side="right")

        self.entry.focus_set()

    # ----------------------------------------------------------------- inputs

    def _focus_in(self, _event: tk.Event) -> None:
        if not self.var.get().strip():
            self.var.set(PLACEHOLDER)
            self._placeholder_active = True
            self.entry.configure(fg=self.theme.muted)
        self.input_shell.configure(highlightbackground=self.theme.accent)

    def _focus_out(self, _event: tk.Event) -> None:
        if not self.var.get().strip():
            self.var.set(PLACEHOLDER)
            self._placeholder_active = True
            self.entry.configure(fg=self.theme.muted)
        self.input_shell.configure(highlightbackground=self.theme.line)

    def _on_key(self, _event: tk.Event) -> None:
        if self._placeholder_active:
            self.var.set("")
            self._placeholder_active = False
            self.entry.configure(fg=self.theme.ink)

    def _on_var_write(self, *_args: object) -> None:
        value = self.var.get()
        if value and value != PLACEHOLDER:
            self._placeholder_active = False
            self.entry.configure(fg=self.theme.ink)

    def _submit(self, _event: tk.Event | None = None) -> str:
        # Do not trust the placeholder flag alone: IME composition can update
        # the StringVar without firing the key handler.  Real text always wins.
        text = self.var.get().strip()
        if not text or text == PLACEHOLDER:
            return "break"
        self._placeholder_active = False
        self.on_capture(text)
        self.var.set(PLACEHOLDER)
        self._placeholder_active = True
        self.entry.configure(fg=self.theme.muted)
        self.entry.focus_set()
        return "break"

    def _on_filter(self, value: str) -> None:
        self.filter_value = value
        self._render_list()
        self.list.scroll_to_top()

    def set_date(self, day: date) -> None:
        self._selected_date = day
        self.date_label.configure(
            text=f"{day.year} 年 {day.month:02d} 月 {day.day:02d} 日 · {WEEKDAY_CN[day.weekday()]}"
        )

    def focus_input(self) -> None:
        self.entry.focus_set()

    def prefill(self, text: str) -> None:
        """Test/automation helper; keeps the placeholder semantics intact."""
        self._placeholder_active = False
        self.var.set(text)
        self.entry.configure(fg=self.theme.ink)
        self._submit()

    # ---------------------------------------------------------------- render

    def render(self, todos: tuple[Todo, ...], selected_date: date) -> None:
        self._todos = todos
        self.set_date(selected_date)
        active = sum(1 for todo in todos if not todo.done and todo.slot is None)
        done = sum(1 for todo in todos if todo.done)
        self.filter.set_labels({"pool": f"待安排 {active}", "done": f"已完成 {done}"})
        self._render_list()

    def _render_list(self) -> None:
        self.list.clear()
        self._cards.clear()
        t = self.theme
        if self.filter_value == "pool":
            items = [todo for todo in self._todos if not todo.done and todo.slot is None]
            items.sort(key=lambda todo: todo.created_at)
            if not items:
                self._empty("还没有待办", "写一句，按 Enter\n拖到右侧时间轴，就算排好了")
                return
            for todo in items:
                card = tk.Canvas(
                    self.list.inner, height=64, bg=t.panel,
                    highlightthickness=0, bd=0, cursor="hand2",
                )
                card.pack(fill="x", pady=(0, 9))
                self._cards[todo.id] = card
                card.bind("<Configure>", lambda e, td=todo: self._draw_pool_card(td))
                card.bind("<ButtonPress-1>", lambda e, td=todo: self.on_drag_start(td, e))
                card.bind("<Button-3>", lambda e, td=todo: self.on_context_menu(td, e))
                self._draw_pool_card(todo)
        else:
            items = [todo for todo in self._todos if todo.done]
            items.sort(key=lambda todo: todo.completed_at or todo.created_at, reverse=True)
            if not items:
                self._empty("还没有完成记录", "完成的事会留在这里\n数据很小，可以一直攒着")
                return
            for todo in items:
                card = tk.Canvas(
                    self.list.inner, height=62, bg=t.panel,
                    highlightthickness=0, bd=0,
                )
                card.pack(fill="x", pady=(0, 9))
                self._cards[todo.id] = card
                card.bind("<Configure>", lambda e, td=todo: self._draw_done_card(td))
                self._draw_done_card(todo)

    def _empty(self, title: str, hint: str) -> None:
        t = self.theme
        box = tk.Frame(self.list.inner, bg=t.panel)
        box.pack(fill="x", pady=(4, 0))
        tk.Label(
            box, text=title, bg=t.panel, fg=t.faint,
            font=(t.font_family, 10, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Label(
            box, text=hint, bg=t.panel, fg=t.faint,
            font=(t.font_family, 8), justify="left", anchor="w",
        ).pack(fill="x", pady=(4, 0))

    def _draw_pool_card(self, todo: Todo) -> None:
        card = self._cards.get(todo.id)
        if card is None:
            return
        width = max(card.winfo_width(), 260)
        t = self.theme
        accent = t.accent_for(todo.accent_index)
        card.delete("all")
        rounded_rect(card, 1, 1, width - 2, 62, 14, fill=t.surface, outline=t.line)
        card.create_oval(16, 24, 26, 34, fill=accent, outline="")
        title = fit_text(self.card_title, todo.text, width - 80)
        card.create_text(
            34, 22, text=title, anchor="w", fill=t.ink, font=self.card_title,
        )
        card.create_text(
            34, 43, text="待安排 · 拖到右侧", anchor="w", fill=t.muted,
            font=self.card_hint,
        )
        for row in range(3):
            for col in range(2):
                x = width - 24 + col * 5
                y = 25 + row * 5
                card.create_oval(x, y, x + 2, y + 2, fill=t.line, outline="")

    def _draw_done_card(self, todo: Todo) -> None:
        card = self._cards.get(todo.id)
        if card is None:
            return
        width = max(card.winfo_width(), 260)
        t = self.theme
        accent = t.accent_for(todo.accent_index)
        card.delete("all")
        rounded_rect(card, 1, 1, width - 2, 60, 13, fill=t.panel, outline=t.line)
        card.create_oval(16, 20, 34, 38, fill=t.tint(accent, 0.82), outline="")
        check_mark(card, 25, 29, 5, accent)
        title = fit_text(self.card_done, todo.text, width - 100)
        card.create_text(
            44, 22, text=title, anchor="w", fill=t.muted, font=self.card_done,
        )
        when = todo.completed_at.strftime("%m-%d %H:%M") if todo.completed_at else ""
        card.create_text(
            44, 43, text=f"完成于 {when}" if when else "已完成", anchor="w",
            fill=t.faint, font=self.card_hint,
        )
