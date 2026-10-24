"""All floating-point values in this project are IEEE-754 binary64 (FP64)."""

from __future__ import annotations

FP64 = float


def fp64(value: int | float | str) -> float:
    """Cross the FP64 boundary explicitly.

    Python's ``float`` is already binary64 on CPython/Windows x64.  Keeping a
    named alias and a conversion helper prevents accidental Decimal/numpy
    mixing and makes the requirement visible in code review.
    """
    return FP64(value)
