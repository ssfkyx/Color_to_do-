"""Frameless title bar with macOS-style traffic lights on the left."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from .theme import Theme

CLOSE = "#FF5F57"
CLOSE_EDGE = "#E0443E"
MINIMISE = "#FEBC2E"
MINIMISE_EDGE = "#DEA123"
ZOOM = "#28C840"
ZOOM_EDGE = "#1DAF35"


class TitleBar(tk.Canvas):
    HEIGHT = 40
    LIGHT_SIZE = 13

    def __init__(
        self,
        master: tk.Misc,
        root: tk.Tk,
        theme: Theme,
        on_close: Callable[[], None],
        on_minimise: Callable[[], None],
        on_zoom: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            height=self.HEIGHT,
            bg=theme.background,
            highlightthickness=0,
            bd=0,
            cursor="fleur",
        )
        self.root = root
        self.theme = theme
        self.on_close = on_close
        self.on_minimise = on_minimise
        self.on_zoom = on_zoom
        self._maximized = False
        self._drag_origin: tuple[int, int, int, int] | None = None
        self._lights: dict[str, int] = {}
        self._photos = self._make_light_photos()
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag_origin", None))
        self.bind("<Double-Button-1>", self._double_click)
        self.redraw()

    def _make_light_photos(self) -> dict[str, object]:
        """Supersample the dots so Tk does not draw jagged ovals."""
        try:
            from PIL import Image, ImageDraw, ImageTk
        except ImportError:
            return {}
        scale = 4
        size = self.LIGHT_SIZE
        canvas_size = size * scale
        specs = {
            "close": (CLOSE, CLOSE_EDGE),
            "min": (MINIMISE, MINIMISE_EDGE),
            "zoom": (ZOOM, ZOOM_EDGE),
        }
        photos: dict[str, object] = {}
        for name, (fill, edge) in specs.items():
            image = Image.new("RGB", (canvas_size, canvas_size), self.theme.background)
            draw = ImageDraw.Draw(image)
            draw.ellipse([0, 0, canvas_size - 1, canvas_size - 1], fill=edge)
            inset = scale
            draw.ellipse(
                [inset, inset, canvas_size - 1 - inset, canvas_size - 1 - inset],
                fill=fill,
            )
            image = image.resize((size, size), Image.Resampling.LANCZOS)
            photos[name] = ImageTk.PhotoImage(image, master=self)
        return photos

    def set_zoomed(self, value: bool) -> None:
        self._maximized = value
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        self._lights.clear()
        width = max(self.winfo_width(), 200)
        y = self.HEIGHT / 2
        # Three macOS traffic lights, left-aligned, with generous spacing.
        for index, name in enumerate(("close", "min", "zoom")):
            x = 20 + index * 22
            if name in self._photos:
                item = self.create_image(
                    x, y, image=self._photos[name], anchor="center", tags=("light", f"light-{name}"),
                )
            else:
                colour = {"close": CLOSE, "min": MINIMISE, "zoom": ZOOM}[name]
                item = self.create_oval(
                    x - 6.5, y - 6.5, x + 6.5, y + 6.5,
                    fill=colour, outline="", tags=("light", f"light-{name}"),
                )
            tag = f"light-{name}"
            self._lights[name] = item
            self.tag_bind(tag, "<Button-1>", lambda e, n=name: self._click(n))
            self.tag_bind(tag, "<Enter>", lambda e: self.configure(cursor="hand2"))
            self.tag_bind(tag, "<Leave>", lambda e: self.configure(cursor="fleur"))

        # A very quiet divider; it makes the frameless edge readable.
        self.create_line(0, self.HEIGHT - 1, width, self.HEIGHT - 1, fill=self.theme.soft_line)

    def _click(self, name: str) -> None:
        if name == "close":
            self.on_close()
        elif name == "min":
            self.on_minimise()
        else:
            self.on_zoom()
        return "break"

    def _double_click(self, _event: tk.Event) -> str | None:
        if any(str(tag).startswith("light-") for tag in self.gettags("current")):
            return "break"
        self._drag_origin = None
        self.on_zoom()
        return None

    def _on_press(self, event: tk.Event) -> None:
        tags = self.gettags("current")
        if any(str(tag).startswith("light-") for tag in tags):
            return
        if self._maximized:
            return
        self._drag_origin = (
            event.x_root,
            event.y_root,
            self.root.winfo_x(),
            self.root.winfo_y(),
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_origin is None:
            return
        start_x, start_y, win_x, win_y = self._drag_origin
        self.root.geometry(
            f"+{win_x + event.x_root - start_x}+{win_y + event.y_root - start_y}"
        )
