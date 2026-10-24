"""A scheduled span of time inside one local calendar day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MIN_DURATION_MINUTES = 5
MAX_DURATION_MINUTES = 24 * 60


@dataclass(frozen=True, slots=True)
class TimeSlot:
    """Start + duration; ``end`` and minute-of-day are derived."""

    start: datetime
    duration_minutes: int = 30

    def __post_init__(self) -> None:
        if not isinstance(self.start, datetime):
            raise TypeError("TimeSlot.start must be a datetime")
        if self.duration_minutes < MIN_DURATION_MINUTES:
            raise ValueError("duration_minutes must be at least 5")
        if self.duration_minutes > MAX_DURATION_MINUTES:
            raise ValueError("duration_minutes cannot exceed one day")
        day_end = datetime.combine(self.start.date() + timedelta(days=1), time.min)
        if self.end > day_end:
            raise ValueError("TimeSlot cannot cross midnight")

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def start_minute(self) -> int:
        return self.start.hour * 60 + self.start.minute

    @property
    def end_minute(self) -> int:
        return self.start_minute + self.duration_minutes

    @property
    def day(self) -> date:
        return self.start.date()

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.start < other.end and other.start < self.end

    def clamped(self) -> "TimeSlot":
        """Keep the span inside its local day, preserving duration where possible."""
        day_start = datetime.combine(self.start.date(), time.min)
        day_end = datetime.combine(self.start.date() + timedelta(days=1), time.min)
        duration = max(MIN_DURATION_MINUTES, min(self.duration_minutes, MAX_DURATION_MINUTES))
        latest_start = day_end - timedelta(minutes=duration)
        start = min(max(self.start, day_start), latest_start)
        return TimeSlot(start=start, duration_minutes=duration)

    @classmethod
    def at(cls, day: date, minute: int, duration_minutes: int = 30) -> "TimeSlot":
        """Build a slot from a minute-of-day; negative/overflow minutes clamp."""
        duration = max(MIN_DURATION_MINUTES, min(duration_minutes, MAX_DURATION_MINUTES))
        latest = 24 * 60 - duration
        minute = max(0, min(int(minute), latest))
        start = datetime.combine(day, time.min) + timedelta(minutes=minute)
        return cls(start=start, duration_minutes=duration)
