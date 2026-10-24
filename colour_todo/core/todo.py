"""The Todo entity and its reminder state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .time_slot import TimeSlot


@dataclass(slots=True)
class Todo:
    id: str
    text: str
    accent_index: int
    created_at: datetime
    slot: TimeSlot | None = None
    done: bool = False
    completed_at: datetime | None = None
    # The next time a reminder should be shown.  It is persisted so sleeping,
    # restarting, and hiding to the tray do not lose the reminder.
    remind_at: datetime | None = None
    # Last time a reminder was shown; useful for diagnostics and history.
    reminded_at: datetime | None = None

    def schedule(self, slot: TimeSlot) -> None:
        """Place the Todo and arm its reminder at the new start."""
        self.slot = slot.clamped()
        self.remind_at = self.slot.start
        self.reminded_at = None
        if self.done:
            self.done = False
            self.completed_at = None

    def complete(self, now: datetime) -> None:
        self.done = True
        self.completed_at = now
        self.remind_at = None

    def snooze_until(self, when: datetime) -> None:
        if not self.done:
            self.remind_at = when

    def claim_reminder(
        self,
        now: datetime,
        visible_seconds: int = 60,
        repeat_minutes: int = 5,
    ) -> None:
        """Mark a popup as shown and schedule the next attempt.

        The next attempt is visible_seconds + repeat_minutes away: if the user
        ignores the popup it disappears after one minute and comes back five
        minutes later.  If they act earlier, scheduling/complete overwrite it.
        """
        self.reminded_at = now
        self.remind_at = now + timedelta(seconds=visible_seconds, minutes=repeat_minutes)

    def is_due(self, now: datetime) -> bool:
        return bool(
            not self.done
            and self.slot is not None
            and self.remind_at is not None
            and now >= self.remind_at
        )

    @property
    def is_scheduled(self) -> bool:
        return self.slot is not None

    @property
    def is_overdue(self) -> bool:
        return bool(self.remind_at and not self.done and self.remind_at < datetime.now())
