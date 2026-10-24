"""Composition root and process entry point."""

from __future__ import annotations

import argparse
import ctypes
import logging
import sys
import traceback
from pathlib import Path

import tkinter as tk

from .config import AppConfig, is_writable_dir
from .core.reminder_service import ReminderService
from .core.todo_service import TodoService
from .infra.clock import SystemClock
from .infra.json_repository import JsonTodoRepository
from .infra.single_instance import (
    SingleInstanceGuard,
    activate_existing_window,
    show_already_running_message,
)
from .ui.main_window import MainWindow
from .ui.theme import THEME


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def _setup_logging(data_dir: Path) -> None:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=data_dir / "app.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            encoding="utf-8",
        )
    except OSError:
        logging.basicConfig(level=logging.INFO)


def _resolve_data_dir(config: AppConfig, explicit: bool) -> AppConfig | None:
    if is_writable_dir(config.data_dir):
        return config
    if explicit:
        return None
    candidates = [
        Path.home() / "ColourTodoData",
        Path(sys.executable).resolve().parent / "ColourTodoData",
        Path.cwd() / "ColourTodoData",
    ]
    for candidate in candidates:
        if candidate == config.data_dir:
            continue
        if is_writable_dir(candidate):
            return config.with_data_dir(candidate)
    return None


def _show_fatal_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "色彩待办", 0x10)
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ColourTodo", description="色彩待办")
    parser.add_argument("--data-dir", type=Path, default=None, help="数据目录（默认 %LOCALAPPDATA%\\ColourTodo）")
    parser.add_argument("--no-tray", action="store_true", help="不启用托盘，关闭窗口即退出（调试用）")
    args = parser.parse_args(argv)

    config = AppConfig.default()
    explicit_data_dir = args.data_dir is not None
    if args.data_dir is not None:
        config = config.with_data_dir(args.data_dir)
    resolved = _resolve_data_dir(config, explicit_data_dir)
    if resolved is None:
        _show_fatal_error(
            "无法写入数据目录。\n\n"
            f"尝试过：{config.data_dir}\n"
            "请把程序放到可写目录，或用 --data-dir 指定一个可写目录。"
        )
        return 1
    config = resolved
    _setup_logging(config.data_dir)
    logging.info("data_path=%s", config.data_path)
    enable_dpi_awareness()

    guard = SingleInstanceGuard()
    if guard.already_running:
        if not activate_existing_window():
            show_already_running_message()
        guard.release()
        return 0

    root: tk.Tk | None = None
    try:
        root = tk.Tk()
        repository = JsonTodoRepository(config.data_path)
        clock = SystemClock()
        todo_service = TodoService(repository, clock)
        reminder_service = ReminderService(todo_service, clock)
        window = MainWindow(
            root,
            config,
            THEME,
            todo_service,
            reminder_service,
            clock,
            enable_tray=not args.no_tray,
        )
        root.report_callback_exception = _report_callback_exception
        if repository.last_error:
            logging.warning("repository: %s", repository.last_error)
        window.run()
        return 0
    except Exception:
        logging.exception("fatal error")
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
        return 1
    finally:
        guard.release()


def _report_callback_exception(exc_type, exc_value, exc_tb) -> None:  # noqa: ANN001
    logging.error(
        "Tk callback failed: %s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )
    if sys.stderr is not None:
        sys.stderr.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
