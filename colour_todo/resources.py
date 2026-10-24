"""Resolve bundled assets in development and inside a PyInstaller one-file exe."""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "assets" / name
    return Path(__file__).resolve().parent.parent / "assets" / name
