"""Windows single-instance guard (named mutex, no IPC)."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183


class SingleInstanceGuard:
    def __init__(self, name: str = "Local\\ColourTodo.SingleInstance") -> None:
        self._handle = None
        self.already_running = False
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            self._handle = kernel32.CreateMutexW(None, False, name)
            self.already_running = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
        except (AttributeError, OSError):
            self.already_running = False

    def release(self) -> None:
        if self._handle:
            try:
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except (AttributeError, OSError):
                pass
            self._handle = None


def show_already_running_message() -> None:
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            "色彩待办已经在托盘中运行。\n请点击任务栏通知区域的图标打开。",
            "色彩待办",
            0x40,
        )
    except (AttributeError, OSError):
        pass


def activate_existing_window(title: str = "色彩待办") -> bool:
    """Bring the already-running frameless window back, even if withdrawn."""
    try:
        user32 = ctypes.windll.user32
        hwnd = int(user32.FindWindowW(None, title))
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
        user32.SetForegroundWindow(hwnd)
        return True
    except (AttributeError, OSError, ValueError):
        return False
