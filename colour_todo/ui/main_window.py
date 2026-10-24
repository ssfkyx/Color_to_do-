"""Main window and composition of the Tk application."""

from __future__ import annotations

import ctypes
import logging
import queue
import tkinter as tk
from ctypes import wintypes
from datetime import date

from ..config import AppConfig
from ..core.time_slot import TimeSlot
from ..core.todo import Todo
from ..core.todo_service import TodoService
from ..core.view_mode import ViewMode
from ..infra.tray import TrayController
from ..resources import asset_path
from .calendar_view import CalendarView
from .drag_session import DragSession
from .edit_dialog import EditTodoDialog
from .reminder_center import ReminderCenter
from .theme import Theme
from .title_bar import TitleBar
from .todo_panel import TodoPanel

SW_MINIMIZE = 6
SW_RESTORE = 9
SPI_GETWORKAREA = 0x0030
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        config: AppConfig,
        theme: Theme,
        todo_service: TodoService,
        reminder_service,
        clock,
        enable_tray: bool = True,
    ) -> None:
        self.root = root
        self.config = config
        self.theme = theme
        self.todo_service = todo_service
        self.reminder_service = reminder_service
        self.clock = clock
        self._tick_job: str | None = None
        self._tray_job: str | None = None
        self._running = True
        self._tray_queue: queue.Queue[str] = queue.Queue()
        self._tray_hint_shown = False
        self._toast_job: str | None = None
        self._focus_job: str | None = None
        self._maximized = False
        self._normal_geometry: str | None = None
        self._resize_origin: tuple[int, int, int, int] | None = None

        self._configure_window()
        self._build()
        self.drag = DragSession(
            root,
            theme,
            hit_test=self.calendar.minute_at_screen,
            on_hover=self._on_drag_hover,
            on_drop=self._on_drop,
        )
        self.reminders = ReminderCenter(
            root,
            theme,
            config,
            on_do=self._reminder_do,
            on_drag=self._reminder_drag,
            on_timeout=self._reminder_timeout,
        )
        self.tray = TrayController(theme, self._tray_queue.put) if enable_tray else None
        if self.tray is not None:
            self.tray.start()

        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.bind_all("<Control-q>", self._quit_shortcut)
        root.bind_all("<Return>", self._global_return)
        root.bind_all("<KP_Enter>", self._global_return)
        self.refresh()
        self._tray_job = self.root.after(120, self._drain_tray_queue)
        self._schedule_tick()
        self._focus_job = self.root.after(150, self.panel.focus_input)

    # ------------------------------------------------------------------ window

    def _configure_window(self) -> None:
        t = self.theme
        self.root.title("色彩待办")
        self.root.configure(bg=t.background)
        # Frameless window: the custom title bar owns close/minimise/zoom.
        self.root.overrideredirect(True)
        icon = asset_path("colour_todo.ico")
        if icon.exists():
            try:
                self.root.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        width, height = self.config.window_size
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(980, 620)
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 20)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.update_idletasks()
        self._apply_native_window_tweaks()

    def _hwnd(self) -> int:
        try:
            return int(ctypes.windll.user32.GetParent(self.root.winfo_id()))
        except (AttributeError, OSError, ValueError):
            return 0

    def _apply_native_window_tweaks(self) -> None:
        """Keep a taskbar entry and ask Windows 11 for rounded corners."""
        hwnd = self._hwnd()
        if not hwnd:
            return
        try:
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_APPWINDOW)
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except (AttributeError, OSError):
            pass
        try:
            preference = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except (AttributeError, OSError):
            pass

    def _build(self) -> None:
        t = self.theme
        self.titlebar = TitleBar(
            self.root,
            self.root,
            t,
            on_close=self.hide_to_tray,
            on_minimise=self.minimise_window,
            on_zoom=self.toggle_maximize,
        )
        self.titlebar.pack(fill="x", side="top")

        self.shell = tk.Frame(self.root, bg=t.background)
        self.shell.pack(fill="both", expand=True, padx=18, pady=(8, 16))
        self.shell.grid_columnconfigure(0, minsize=self.config.pool_width, weight=0)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)

        self.panel = TodoPanel(
            self.shell,
            t,
            width=self.config.pool_width,
            on_capture=self._on_capture,
            on_drag_start=self._on_pool_drag_start,
            on_context_menu=self._show_pool_menu,
        )
        self.panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        board = tk.Frame(self.shell, bg=t.surface, highlightthickness=0)
        board.grid(row=0, column=1, sticky="nsew")
        board.grid_rowconfigure(0, weight=1)
        board.grid_columnconfigure(0, weight=1)
        self.calendar = CalendarView(
            board,
            t,
            t.pixels_per_minute,
            self.config.snap_minutes,
            self.config.default_duration_minutes,
            on_date_change=self._on_date_change,
            on_event_drag_start=self._on_event_drag_start,
            on_event_context=self._show_event_menu,
        )
        self.calendar.grid(row=0, column=0, sticky="nsew")

        self.toast = tk.Label(
            self.root,
            text="",
            bg=t.ink,
            fg="#FFFFFF",
            font=(t.font_family, 9),
            padx=16,
            pady=8,
        )
        self._build_resize_grip()

    def _build_resize_grip(self) -> None:
        t = self.theme
        self.grip = tk.Canvas(
            self.root,
            width=18,
            height=18,
            bg=t.background,
            highlightthickness=0,
            bd=0,
            cursor="size_nw_se",
        )
        for offset in (6, 10, 14):
            self.grip.create_line(offset, 17, 17, offset, fill=t.line)
        self.grip.bind("<ButtonPress-1>", self._resize_start)
        self.grip.bind("<B1-Motion>", self._resize_motion)
        self.grip.bind("<ButtonRelease-1>", self._resize_end)
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self.grip.tk.call("raise", self.grip._w)

    def _resize_start(self, event: tk.Event) -> None:
        if self._maximized:
            return
        self._resize_origin = (
            event.x_root,
            event.y_root,
            self.root.winfo_width(),
            self.root.winfo_height(),
        )

    def _resize_motion(self, event: tk.Event) -> None:
        if self._resize_origin is None:
            return
        start_x, start_y, width, height = self._resize_origin
        new_width = max(980, width + event.x_root - start_x)
        new_height = max(620, height + event.y_root - start_y)
        self.root.geometry(f"{new_width}x{new_height}")

    def _resize_end(self, _event: tk.Event) -> None:
        if not self._maximized:
            self._normal_geometry = self.root.geometry()
        self._resize_origin = None

    # ------------------------------------------------------------------ state

    def refresh(self) -> None:
        todos = self.todo_service.all_todos
        self.panel.render(todos, self.calendar.selected_date)
        self.calendar.render(todos, self.clock.now())

    def _on_date_change(self, day: date) -> None:
        self.panel.set_date(day)

    def _on_capture(self, text: str) -> None:
        try:
            todo = self.todo_service.capture(text)
        except Exception as exc:
            logging.exception("capture failed")
            self._show_toast(f"保存失败：{exc}")
            return
        if todo is not None:
            self.refresh()
            self.panel.focus_input()
            self._show_toast("已加入待安排")

    def _on_pool_drag_start(self, todo: Todo, event: tk.Event) -> None:
        if self.calendar.mode is not ViewMode.DAY:
            self.calendar.set_mode(ViewMode.DAY)
        self.drag.start(todo, event)

    def _on_event_drag_start(self, todo: Todo, event: tk.Event) -> None:
        self.drag.start(todo, event)

    def _on_drag_hover(self, minute: int | None) -> None:
        self.calendar.day_view.show_drop_preview(minute)

    def _on_drop(self, todo: Todo, minute: int) -> None:
        duration = (
            todo.slot.duration_minutes
            if todo.slot is not None
            else self.config.default_duration_minutes
        )
        slot = TimeSlot.at(self.calendar.selected_date, minute, duration)
        self.todo_service.schedule(todo.id, slot)
        self.reminders.close_for(todo.id)
        self.refresh()
        self.calendar.day_view.highlight(todo)
        self._show_toast(f"已安排到 {slot.start.strftime('%H:%M')}")

    # ------------------------------------------------------------------ context menus

    def _make_menu(self, items: list[tuple[str, object]]) -> tk.Menu:
        t = self.theme
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=t.surface,
            fg=t.ink,
            activebackground=t.soft_line,
            activeforeground=t.ink,
            font=(t.font_family, 9),
            borderwidth=1,
        )
        for label, command in items:
            menu.add_command(label=label, command=command)
        return menu

    def _popup_menu(self, menu: tk.Menu, event: tk.Event) -> None:
        self._context_menu = menu
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_pool_menu(self, todo: Todo, event: tk.Event) -> None:
        menu = self._make_menu([
            ("修改", lambda: self._edit_todo(todo)),
            ("删除", lambda: self._delete_todo(todo)),
        ])
        self._popup_menu(menu, event)

    def _show_event_menu(self, todo: Todo, event: tk.Event) -> None:
        menu = self._make_menu([
            ("删除", lambda: self._delete_todo(todo)),
        ])
        self._popup_menu(menu, event)

    def _edit_todo(self, todo: Todo) -> None:
        try:
            new_text = EditTodoDialog.ask(self.root, self.theme, todo.text)
        except tk.TclError:
            return
        if new_text is None or new_text == todo.text:
            return
        try:
            self.todo_service.update_text(todo.id, new_text)
        except Exception as exc:
            logging.exception("update failed")
            self._show_toast(f"修改失败：{exc}")
            return
        self.refresh()
        self._show_toast("已修改")

    def _delete_todo(self, todo: Todo) -> None:
        try:
            self.todo_service.delete(todo.id)
        except Exception as exc:
            logging.exception("delete failed")
            self._show_toast(f"删除失败：{exc}")
            return
        self.reminders.close_for(todo.id)
        self.refresh()
        self._show_toast(f"已删除 · {todo.text}")

    # ------------------------------------------------------------------ reminders

    def _schedule_tick(self) -> None:
        if self._running:
            self._tick_job = self.root.after(self.config.tick_ms, self._tick)

    def _tick(self) -> None:
        self._tick_job = None
        if not self._running:
            return
        now = self.clock.now()
        for todo in self.reminder_service.due_now():
            if self.reminders.knows(todo.id):
                continue
            self.todo_service.claim_reminder(
                todo.id,
                self.config.reminder_visible_seconds,
                self.config.reminder_repeat_minutes,
            )
            self.reminders.show(todo)
        self.calendar.update_now(now)
        self._schedule_tick()

    def _reminder_do(self, todo: Todo) -> None:
        self.todo_service.complete(todo.id)
        self.refresh()
        self._show_toast(f"已完成 · {todo.text}")

    def _reminder_drag(self, todo: Todo) -> None:
        self.todo_service.snooze(todo.id, self.config.reminder_repeat_minutes)
        self.show_window()
        self.calendar.open_todo(todo)
        self._show_toast("把高亮任务拖到新时间 · 不拖则 5 分钟后再提醒")

    def _reminder_timeout(self, todo: Todo) -> None:
        self.todo_service.snooze(todo.id, self.config.reminder_repeat_minutes)
        self._show_toast("已稍后 · 5 分钟后再提醒")

    # ------------------------------------------------------------------ tray

    def _drain_tray_queue(self) -> None:
        self._tray_job = None
        try:
            while True:
                command = self._tray_queue.get_nowait()
                if command == "open":
                    self.show_window()
                elif command == "today":
                    self.show_window()
                    self.calendar.open_day(date.today())
                elif command == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        if self._running:
            self._tray_job = self.root.after(120, self._drain_tray_queue)

    def show_window(self) -> None:
        hwnd = self._hwnd()
        if hwnd:
            try:
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            except (AttributeError, OSError):
                pass
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass
        self.panel.focus_input()

    def minimise_window(self) -> None:
        hwnd = self._hwnd()
        if not hwnd:
            return
        try:
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
        except (AttributeError, OSError):
            pass

    def toggle_maximize(self) -> None:
        if self._maximized:
            if self._normal_geometry:
                self.root.geometry(self._normal_geometry)
            self._maximized = False
            self.titlebar.set_zoomed(False)
            self.grip.place(relx=1.0, rely=1.0, anchor="se")
            self.grip.tk.call("raise", self.grip._w)
            return
        self._normal_geometry = self.root.geometry()
        rect = wintypes.RECT()
        try:
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_GETWORKAREA, 0, ctypes.byref(rect), 0,
            )
            width = rect.right - rect.left
            height = rect.bottom - rect.top
        except (AttributeError, OSError):
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight() - 48
        self.root.geometry(f"{width}x{height}+{rect.left}+{rect.top}")
        self._maximized = True
        self.titlebar.set_zoomed(True)
        self.grip.place_forget()

    def hide_to_tray(self) -> None:
        if self.tray is not None and self.tray.healthy:
            self.root.withdraw()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.notify("已收起到右下角 ^「显示隐藏的图标」")
        else:
            # No tray icon means no way to bring a hidden window back.
            self.quit()

    def _quit_shortcut(self, _event: tk.Event) -> str:
        self.quit()
        return "break"

    def _global_return(self, event: tk.Event) -> str | None:
        """Enter submits even if the Entry lost focus to the board/canvas."""
        try:
            if event.widget.winfo_toplevel() is not self.root:
                return None
            if event.widget is self.panel.entry:
                return None
        except (AttributeError, tk.TclError):
            return None
        self.panel._submit()
        return "break"

    def quit(self) -> None:
        self._running = False
        for job in (self._tick_job, self._tray_job, self._toast_job, self._focus_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self._tick_job = None
        self._tray_job = None
        self._toast_job = None
        self._focus_job = None
        try:
            self.reminders.close_all()
        except tk.TclError:
            pass
        if self.tray is not None:
            self.tray.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ toast

    def _show_toast(self, text: str) -> None:
        self.toast.configure(text=text)
        self.toast.place(relx=0.5, rely=0.965, anchor="s")
        self.toast.lift()
        if self._toast_job is not None:
            self.root.after_cancel(self._toast_job)
        self._toast_job = self.root.after(2200, self._hide_toast)

    def _hide_toast(self) -> None:
        self._toast_job = None
        self.toast.place_forget()

    # ------------------------------------------------------------------ run

    def run(self) -> None:
        self.root.mainloop()
