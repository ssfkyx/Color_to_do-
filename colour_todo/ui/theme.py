"""Visual language: palette, type, radii and timeline scale.

No business rules and no paths here.  The core stores only accent indexes;
this module turns an index into a colour.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..fp64 import FP64


@dataclass(frozen=True, slots=True)
class Theme:
    background: str = "#F6F3EC"
    panel: str = "#FBFAF6"
    surface: str = "#FFFFFF"
    ink: str = "#23262F"
    muted: str = "#8C8F99"
    faint: str = "#B3AFA6"
    line: str = "#ECE7DD"
    soft_line: str = "#F3EFE8"
    accent: str = "#F26B5E"
    accent_dark: str = "#D95448"
    accents: tuple[str, ...] = (
        "#F26B5E",
        "#E9A23B",
        "#2FAE9B",
        "#5B7CFA",
        "#9C6BF2",
        "#E56AA6",
    )
    font_family: str = "Microsoft YaHei UI"
    number_font: str = "Segoe UI"
    pixels_per_minute: FP64 = FP64(0.78)
    card_radius: int = 14
    event_radius: int = 9
    popup_radius: int = 19
    pool_width: int = 352

    def accent_for(self, index: int) -> str:
        return self.accents[index % len(self.accents)]

    def tint(self, colour: str, amount: FP64 = FP64(0.88)) -> str:
        return blend(colour, self.surface, amount)


def blend(colour: str, other: str, amount: FP64) -> str:
    a = FP64(amount)
    c1 = tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
    c2 = tuple(int(other[i : i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(int(round(FP64(x) * (1.0 - a) + FP64(y) * a)) for x, y in zip(c1, c2))
    return "#{:02X}{:02X}{:02X}".format(*mixed)


THEME = Theme()
