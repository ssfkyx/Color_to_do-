"""Small modal dialog for renaming an unscheduled Todo."""

from __future__ import annotations

import tkinter as tk

from .theme import Theme


class EditTodoDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, theme: Theme, initial: str) -> None:
        super().__init__(master)
        self.theme = theme
        self.result: str | None = None
        self.title("修改待办")
        self.configure(bg=theme.background)
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._save())

        body = tk.Frame(self, bg=theme.surface)
        body.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(
            body, text="修改待办", bg=theme.surface, fg=theme.ink,
            font=(theme.font_family, 12, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 10))

        self.var = tk.StringVar(value=initial)
        shell = tk.Frame(
            body, bg=theme.surface, highlightthickness=1,
            highlightbackground=theme.accent, highlightcolor=theme.accent,
        )
        shell.pack(fill="x", padx=20)
        self.entry = tk.Entry(
            shell, textvariable=self.var, relief="flat", borderwidth=0,
            bg=theme.surface, fg=theme.ink, insertbackground=theme.accent,
            font=(theme.font_family, 11), highlightthickness=0,
        )
        self.entry.pack(fill="x", padx=10, pady=8)

        actions = tk.Frame(body, bg=theme.surface)
        actions.pack(fill="x", padx=20, pady=(14, 16))
        tk.Button(
            actions, text="取消", command=self._cancel,
            relief="flat", borderwidth=0, bg=theme.soft_line, fg=theme.ink,
            activebackground=theme.line, font=(theme.font_family, 9),
            padx=16, pady=5, cursor="hand2",
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            actions, text="保存", command=self._save,
            relief="flat", borderwidth=0, bg=theme.accent, fg="#FFFFFF",
            activebackground=theme.accent_dark, activeforeground="#FFFFFF",
            font=(theme.font_family, 9, "bold"), padx=16, pady=5,
            cursor="hand2",
        ).pack(side="right")

        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()
        master.update_idletasks()
        x = master.winfo_rootx() + max(0, (master.winfo_width() - width) // 2)
        y = master.winfo_rooty() + max(0, (master.winfo_height() - height) // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.entry.focus_force()
        self.entry.selection_range(0, "end")

    @classmethod
    def ask(cls, master: tk.Misc, theme: Theme, initial: str) -> str | None:
        dialog = cls(master, theme, initial)
        master.wait_window(dialog)
        return dialog.result

    def _save(self) -> str:
        text = self.var.get().strip()
        if not text:
            self.bell()
            self.entry.focus_set()
            return "break"
        self.result = text
        self.destroy()
        return "break"

    def _cancel(self) -> str:
        self.result = None
        self.destroy()
        return "break"
