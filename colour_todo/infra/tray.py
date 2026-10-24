"""System tray icon.

``pystray`` runs its own thread.  Menu callbacks must never touch Tk directly;
they post a short command string into the Tk-owned queue instead.
"""

from __future__ import annotations

import ctypes
import logging
import threading
import time
from typing import Callable

from ..ui.theme import Theme


def _make_image(theme: Theme, size: int = 64):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [3, 3, size - 3, size - 3],
        radius=18,
        fill=theme.accent,
    )
    draw.line(
        [(17, 33), (27, 43), (47, 21)],
        fill="#FFFFFF",
        width=7,
        joint="curve",
    )
    return image


def _patch_restricted_message_filter() -> None:
    """Keep the tray alive in restricted Windows sessions.

    pystray calls ChangeWindowMessageFilterEx to opt into WM_TASKBARCREATED.
    Some locked-down processes (including a DSH sandbox) deny that call even
    for a normal user.  The filter is an optimization for restarts of Explorer,
    not a requirement for showing the icon, so a denial is non-fatal.
    """
    try:
        from pystray import _win32 as backend
    except Exception:
        return
    original = getattr(backend.win32, "ChangeWindowMessageFilterEx", None)
    if original is None or getattr(original, "_colour_todo_safe", False):
        return

    def safe(*args):  # noqa: ANN002
        try:
            return original(*args)
        except OSError:
            return True

    safe._colour_todo_safe = True  # type: ignore[attr-defined]
    backend.win32.ChangeWindowMessageFilterEx = safe  # type: ignore[assignment]


def _patch_tray_identity() -> None:
    """Give the notification icon a stable GUID and remember whether it was added.

    pystray's default identity is ``id(self)`` (the window handle changes every
    run), so Windows may treat every launch as a brand-new icon and hide it in
    a different place.  A stable GUID lets Windows remember the user's chosen
    slot (visible tray or the hidden-icons overflow).
    """
    try:
        from pystray._util import win32
        from pystray._win32 import Icon
    except Exception:
        return
    if getattr(Icon, "_colour_todo_identity", False):
        return
    guid = win32.NOTIFYICONDATAW.GUID(
        Data1=0x5E2B7C1A,
        Data2=0x4D3E,
        Data3=0x4F6A,
        Data4=(ctypes.c_ubyte * 8)(0x8B, 0x21, 0x9C, 0x7D, 0xE4, 0x5A, 0x10, 0x33),
    )
    original = Icon._message

    def message(self, code, flags, **kwargs):  # noqa: ANN001
        legacy = getattr(self, "_colour_todo_legacy", False)
        uflags = flags if legacy else flags | win32.NIF_GUID
        data = win32.NOTIFYICONDATAW(
            cbSize=ctypes.sizeof(win32.NOTIFYICONDATAW),
            hWnd=self._hwnd,
            uID=id(self) if legacy else 0,
            uFlags=uflags,
            **kwargs,
        )
        if not legacy:
            data.guidItem = guid
        result = win32.Shell_NotifyIcon(code, data)
        if code == win32.NIM_ADD and not result and not legacy:
            # Old Windows shells may reject GUID identity; retry the legacy
            # hWnd/hID identity so the icon still appears.
            legacy_data = win32.NOTIFYICONDATAW(
                cbSize=ctypes.sizeof(win32.NOTIFYICONDATAW),
                hWnd=self._hwnd,
                uID=id(self),
                uFlags=flags,
                **kwargs,
            )
            result = win32.Shell_NotifyIcon(code, legacy_data)
            self._colour_todo_legacy = bool(result)
        if code == win32.NIM_ADD:
            self._colour_todo_added = bool(result)
        return result

    Icon._message = message
    Icon._colour_todo_identity = True


class TrayController:
    def __init__(self, theme: Theme, post: Callable[[str], None]) -> None:
        self.theme = theme
        self.post = post
        self.available = False
        self._icon = None
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None

    def start(self) -> bool:
        try:
            import pystray
        except ImportError:
            self.available = False
            return False
        _patch_restricted_message_filter()
        _patch_tray_identity()
        try:
            menu = pystray.Menu(
                pystray.MenuItem("打开色彩待办", lambda *_: self.post("open"), default=True),
                pystray.MenuItem("今天", lambda *_: self.post("today")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", lambda *_: self.post("quit")),
            )
            self._icon = pystray.Icon(
                "ColourTodo", _make_image(self.theme), "色彩待办", menu,
            )
            self._thread = threading.Thread(
                target=self._run, name="colour-todo-tray", daemon=True,
            )
            self._thread.start()
            for _ in range(100):
                added = getattr(self._icon, "_colour_todo_added", None)
                if added is False:
                    break
                if added and self._icon.visible and self._thread.is_alive():
                    self.available = True
                    identity = "legacy" if getattr(self._icon, "_colour_todo_legacy", False) else "guid"
                    logging.info("tray started (%s identity)", identity)
                    return True
                if not self._thread.is_alive():
                    break
                time.sleep(0.02)
            self.available = False
            logging.warning("tray did not register with the notification area")
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
            return False
        except Exception as exc:
            self._error = exc
            self.available = False
            self._icon = None
            logging.exception("tray start failed")
            return False

    def _run(self) -> None:
        try:
            assert self._icon is not None
            self._icon.run()
        except Exception as exc:
            self._error = exc
            self.available = False
            logging.exception("tray thread failed")

    @property
    def healthy(self) -> bool:
        return bool(
            self.available
            and self._thread is not None
            and self._thread.is_alive()
        )

    def notify(self, message: str, title: str = "色彩待办") -> None:
        if self._icon is None:
            return
        try:
            self._icon.notify(message, title)
        except Exception:
            pass

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self.available = False
