"""Pure overlap layout for timeline events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from ..core.time_slot import TimeSlot
from ..core.todo import Todo
from ..fp64 import FP64, fp64
from .canvas_kit import y_for_minute


@dataclass(slots=True)
class EventLayout:
    todo: Todo
    top: FP64
    height: FP64
    lane: int = 0
    lane_count: int = 1

    @property
    def slot(self) -> TimeSlot:
        assert self.todo.slot is not None
        return self.todo.slot


def layout_events(
    todos: Iterable[Todo],
    day: date,
    top: float,
    pixels_per_minute: FP64,
    min_height: float = 26.0,
) -> list[EventLayout]:
    events = [
        todo
        for todo in todos
        if todo.slot is not None and todo.slot.day == day and not todo.done
    ]
    events.sort(key=lambda todo: (todo.slot.start, todo.slot.end))  # type: ignore[union-attr]

    layouts: list[EventLayout] = []

    def flush(cluster: list[Todo]) -> None:
        lane_ends: list = []
        cluster_layouts: list[EventLayout] = []
        for todo in cluster:
            slot = todo.slot
            assert slot is not None
            lane = next(
                (index for index, end in enumerate(lane_ends) if slot.start >= end),
                None,
            )
            if lane is None:
                lane = len(lane_ends)
                lane_ends.append(slot.end)
            else:
                lane_ends[lane] = slot.end
            height = max(fp64(slot.duration_minutes) * pixels_per_minute - 3.0, fp64(min_height))
            cluster_layouts.append(
                EventLayout(
                    todo=todo,
                    top=y_for_minute(slot.start_minute, top, pixels_per_minute) + 1.0,
                    height=fp64(height),
                    lane=lane,
                )
            )
        lane_count = max(1, len(lane_ends))
        for layout in cluster_layouts:
            layout.lane_count = lane_count
        layouts.extend(cluster_layouts)

    cluster: list[Todo] = []
    cluster_end = None
    for todo in events:
        slot = todo.slot
        assert slot is not None
        if cluster and cluster_end is not None and slot.start >= cluster_end:
            flush(cluster)
            cluster = []
            cluster_end = None
        cluster.append(todo)
        cluster_end = slot.end if cluster_end is None else max(cluster_end, slot.end)
    if cluster:
        flush(cluster)
    return layouts
