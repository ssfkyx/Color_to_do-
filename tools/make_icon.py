"""Generate the app/tray .ico from the theme without external art files."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from colour_todo.ui.theme import THEME  # noqa: E402


def make(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = max(1, round(size * 0.06))
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=max(2, round(size * 0.28)),
        fill=THEME.accent,
    )
    width = max(1, round(size * 0.11))
    draw.line(
        [
            (size * 0.27, size * 0.52),
            (size * 0.43, size * 0.68),
            (size * 0.74, size * 0.33),
        ],
        fill="#FFFFFF",
        width=width,
        joint="curve",
    )
    return image


def main() -> int:
    out = ROOT / "assets" / "colour_todo.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [make(size) for size in sizes]
    images[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes])
    images[-1].save(ROOT / "design" / "app_icon.png")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
