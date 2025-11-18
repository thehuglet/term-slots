from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Callable, ClassVar

import numpy as np
from blessed import Terminal

# A cell is (character, style)
ScreenCell = tuple[str, str]


@dataclass
class RGB:
    r: float
    g: float
    b: float

    WHITE: ClassVar[RGB]
    BLACK: ClassVar[RGB]
    RED: ClassVar[RGB]
    GREEN: ClassVar[RGB]
    BLUE: ClassVar[RGB]
    ORANGE: ClassVar[RGB]
    LIGHT_BLUE: ClassVar[RGB]
    GOLD: ClassVar[RGB]
    CYAN: ClassVar[RGB]

    def __mul__(self, other: float | RGB):
        if isinstance(other, RGB):
            return RGB(
                self.r * other.r,
                self.g * other.g,
                self.b * other.b,
            )

        return RGB(
            self.r * other,
            self.g * other,
            self.b * other,
        )


# Color constants
RGB.WHITE = RGB(1.0, 1.0, 1.0)
RGB.BLACK = RGB(0.0, 0.0, 0.0)
RGB.RED = RGB(1.0, 0.0, 0.0)
RGB.GREEN = RGB(0.0, 1.0, 0.0)
RGB.BLUE = RGB(0.0, 0.0, 1.0)
RGB.ORANGE = RGB(1.0, 0.5, 0.0)
RGB.LIGHT_BLUE = RGB(0.65, 0.85, 0.9)
RGB.GOLD = RGB(1.0, 0.85, 0.0)
RGB.CYAN = RGB(0.0, 1.0, 1.0)

BACKGROUND_COLOR = RGB.BLACK


@dataclass
class RichText:
    text: str
    text_color: RGB = field(default_factory=lambda: RGB.WHITE)
    bg_color: RGB = field(default_factory=lambda: BACKGROUND_COLOR)
    bold: bool = False


@dataclass
class ScreenBuffer:
    width: int
    height: int
    chars: np.ndarray  # shape (height, width), dtype='<U1'
    styles: np.ndarray  # shape (height, width), dtype=object


@dataclass
class Screen:
    width: int
    height: int
    old_buffer: ScreenBuffer = field(init=False)
    new_buffer: ScreenBuffer = field(init=False)

    def __post_init__(self):
        self.old_buffer = create_buffer(self.width, self.height)
        self.new_buffer = create_buffer(self.width, self.height)


@dataclass
class FPSCounter:
    ema: float = 0.0
    alpha: float = 0.08


def lerp_rgb(a: RGB, b: RGB, t: float) -> RGB:
    """
    Linear interpolation between two RGB colors.
    t = 0 → returns a
    t = 1 → returns b
    """
    # Optional: clamp t for safety
    if t <= 0.0:
        return a
    if t >= 1.0:
        return b

    return RGB(
        a.r + (b.r - a.r) * t,
        a.g + (b.g - a.g) * t,
        a.b + (b.b - a.b) * t,
    )


def create_buffer(width: int, height: int) -> ScreenBuffer:
    chars = np.full((height, width), " ", dtype="<U1")
    styles = np.full((height, width), "", dtype=object)
    return ScreenBuffer(width, height, chars, styles)


def buffer_diff(screen: Screen) -> list[tuple[int, int, ScreenCell]]:
    old = screen.old_buffer
    new = screen.new_buffer

    mask = (old.chars != new.chars) | (old.styles != new.styles)
    ys, xs = np.nonzero(mask)

    diffs = [(y, x, (new.chars[y, x], new.styles[y, x])) for y, x in zip(ys, xs)]  # type: ignore

    # Update buffers
    screen.old_buffer = ScreenBuffer(
        new.width, new.height, new.chars.copy(), new.styles.copy()
    )
    screen.new_buffer = create_buffer(screen.width, screen.height)

    return diffs  # type: ignore


def flush_diffs(term: Terminal, diffs: list[tuple[int, int, ScreenCell]]) -> None:
    output = [
        term.move_xy(int(x), int(y)) + style + char + term.normal
        for y, x, (char, style) in diffs
    ]
    sys.stdout.write("".join(output))
    sys.stdout.flush()


def create_fps_limiter(
    fps: float,
    poll_interval: float = 0.001,
    spin_reserve: float = 0.002,
) -> Callable[[], float]:
    """
    High-precision, drift-correcting frame limiter.
    Keeps perfect alignment with wall time to avoid visible jitter.
    """
    target = 1.0 / float(fps)
    next_frame = time.perf_counter() + target

    def wait_for_next_frame() -> float:
        nonlocal next_frame
        target_time = next_frame
        now = time.perf_counter()

        # --- Sleep until close to target ---
        while True:
            remaining = target_time - now - spin_reserve
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))
            now = time.perf_counter()

        # --- Spin for last couple ms for precision ---
        while time.perf_counter() < target_time:
            pass

        end = time.perf_counter()

        # --- Compute actual frame time ---
        dt = end - (next_frame - target)

        # --- Schedule next frame based on *absolute time*, not drifted increments ---
        next_frame = target_time + target

        # If we’re very late, resync instead of stacking drift
        if end > next_frame:
            next_frame = end + target

        return dt

    return wait_for_next_frame


def update_fps_counter(fps: FPSCounter, dt: float) -> None:
    if dt <= 0.0:
        return
    inst = 1.0 / dt
    if fps.ema <= 0.0:
        fps.ema = inst
    else:
        fps.ema = fps.ema * (1.0 - fps.alpha) + inst * fps.alpha


def _make_style(term: Terminal, fg: RGB, bg: RGB | None, bold: bool) -> str:
    """
    Build a blessed style string from RGB fg/bg and bold flag.
    If bg is None, fall back to BACKGROUND_COLOR.
    """
    if not term.does_styling:
        return term.normal

    fg_rgb = _rgb_to_rgb_int(fg)
    bg_use = bg if bg is not None else BACKGROUND_COLOR
    bg_rgb = _rgb_to_rgb_int(bg_use)

    fg_str = term.color_rgb(*fg_rgb)
    bg_str = term.on_color_rgb(*bg_rgb)
    bold_str = term.bold if bold else ""

    return f"{term.normal}{bold_str}{fg_str}{bg_str}"


def _rgb_to_rgb_int(color: RGB) -> tuple[int, int, int]:
    arr = np.array((color.r, color.g, color.b), dtype=np.float64)
    scaled = np.clip(np.round(arr * 255.0), 0, 255).astype(np.int32)
    return int(scaled[0]), int(scaled[1]), int(scaled[2])


def print_at(
    term: Terminal,
    screen: Screen,
    x: int,
    y: int,
    text: str | RichText | list[str | RichText],
) -> None:
    """
    Draw RichText (or list[RichText]) into the new_buffer at (x,y).
    Uses numpy slices for segment writes while preserving per-character placement.
    Falls back safely at buffer edges and handles Unicode by treating characters as '<U1'.
    """
    buf: ScreenBuffer = screen.new_buffer

    # Normalize to list[RichText]
    if isinstance(text, str):
        segments = [RichText(text, RGB.WHITE)]
    elif isinstance(text, RichText):
        segments = [text]
    elif isinstance(text, list):
        segments: list[RichText] = []
        for seg in text:
            if isinstance(seg, str):
                seg = RichText(seg, RGB.WHITE)

            segments.append(seg)

    if not (0 <= y < buf.height):
        return

    px = x
    for seg in segments:
        style = _make_style(term, seg.text_color, seg.bg_color, seg.bold)
        # safe per-codepoint array (handles unicode characters)
        chars_arr = np.array(list(seg.text), dtype="<U1")
        n = chars_arr.shape[0]

        # nothing to do if already past the right edge
        if px >= buf.width:
            px += n
            continue

        x_end = min(px + n, buf.width)
        slice_len = x_end - px
        if slice_len > 0:
            buf.chars[y, px:x_end] = chars_arr[:slice_len]
            buf.styles[y, px:x_end] = style
        px += n


def fill_screen_background(term: Terminal, screen: Screen, color: RGB) -> None:
    bg_style = term.on_color_rgb(*_rgb_to_rgb_int(color))

    screen.new_buffer.chars[:, :] = " "
    screen.new_buffer.styles[:, :] = bg_style
