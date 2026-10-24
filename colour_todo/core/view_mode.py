"""Calendar view modes and date navigation."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from enum import Enum


class ViewMode(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


def shift_date(day: date, mode: ViewMode, direction: int) -> date:
    if direction == 0:
        return day
    if mode is ViewMode.DAY:
        return day + timedelta(days=direction)
    if mode is ViewMode.WEEK:
        return day + timedelta(days=7 * direction)
    # Month: keep the day-of-month where possible, clamp at month end.
    month_index = day.year * 12 + (day.month - 1) + direction
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_days(day: date) -> list[date]:
    start = week_start(day)
    return [start + timedelta(days=offset) for offset in range(7)]


def month_days(day: date) -> list[date | None]:
    """Six Monday-first weeks, padded with None outside the month."""
    first = date(day.year, day.month, 1)
    last = date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])
    cells: list[date | None] = []
    cursor = week_start(first)
    while cursor <= last or len(cells) % 7:
        cells.append(cursor if first <= cursor <= last else None)
        cursor += timedelta(days=1)
    while len(cells) < 42:
        cells.append(None)
    return cells
