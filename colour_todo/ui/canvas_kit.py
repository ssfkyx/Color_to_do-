"""Stock-Tk approximations of the visual language: rounded shapes, icons, time math."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from ..fp64 import FP64, fp64


def rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs: object,
) -> int:
    """A smooth polygon is the stock-Canvas way to draw a rounded rectangle."""
    r = min(fp64(radius), (fp64(x2) - fp64(x1)) / 2.0, (fp64(y2) - fp64(y1)) / 2.0)
    points = [
        x1 + r, y1,
        x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2,
        x1 + r, y2, x1, y2, x1, y2 - r,
        x1, y1 + r, x1, y1, x1 + r, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def fit_text(font: tkfont.Font, text: str, max_width: float) -> str:
    """Ellipsize with the real font metrics, not a character-count guess."""
    if max_width <= 4:
        return ""
    if font.measure(text) <= max_width:
        return text
    ellipsis = "…"
    left, right = 0, len(text)
    while left < right:
        mid = (left + right + 1) // 2
        if font.measure(text[:mid] + ellipsis) <= max_width:
            left = mid
        else:
            right = mid - 1
    return text[:left] + ellipsis


def y_for_minute(minute: int, top: float, pixels_per_minute: FP64) -> FP64:
    return fp64(top) + fp64(minute) * pixels_per_minute


def minute_at_canvas_y(
    canvas_y: float,
    top: float,
    pixels_per_minute: FP64,
    snap_minutes: int,
    max_minute: int = 1440,
) -> int:
    raw = (fp64(canvas_y) - fp64(top)) / pixels_per_minute
    snapped = int(round(raw / snap_minutes)) * snap_minutes
    return max(0, min(snapped, max_minute))


def format_minute(minute: int) -> str:
    minute = max(0, min(int(minute), 1439))
    return f"{minute // 60:02d}:{minute % 60:02d}"


def chevron(
    canvas: tk.Canvas,
    x: float,
    y: float,
    direction: str,
    colour: str,
    size: float = 4.0,
    width: float = 1.4,
) -> None:
    sign = -1 if direction == "left" else 1
    canvas.create_line(
        x - sign * size, y - size,
        x + sign * size, y,
        x - sign * size, y + size,
        fill=colour,
        width=width,
        capstyle="round",
        joinstyle="round",
    )


def check_mark(
    canvas: tk.Canvas,
    x: float,
    y: float,
    size: float,
    colour: str,
    width: float = 1.6,
) -> None:
    canvas.create_line(
        x - size, y,
        x - size * 0.25, y + size * 0.65,
        x + size, y - size * 0.75,
        fill=colour,
        width=width,
        capstyle="round",
        joinstyle="round",
    )


def bell(canvas: tk.Canvas, x: float, y: float, colour: str, scale: float = 1.0) -> None:
    s = scale
    canvas.create_arc(
        x - 8 * s, y - 9 * s, x + 8 * s, y + 6 * s,
        start=0, extent=180, style="arc", outline=colour, width=1.6,
    )
    canvas.create_line(x - 8 * s, y - 1 * s, x - 8 * s, y + 5 * s, fill=colour, width=1.6)
    canvas.create_line(x + 8 * s, y - 1 * s, x + 8 * s, y + 5 * s, fill=colour, width=1.6)
    canvas.create_line(x - 11 * s, y + 5 * s, x + 11 * s, y + 5 * s, fill=colour, width=1.6)
    canvas.create_oval(
        x - 2 * s, y + 7 * s, x + 2 * s, y + 11 * s,
        fill=colour, outline="",
    )
