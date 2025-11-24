import sys
import time
from dataclasses import dataclass, field
from typing import Callable, ClassVar

import numpy as np
from blessed import Terminal

# A cell is (character, style)
ScreenCell = tuple[str, str]


@dataclass
class RGBA:
    r: float
    g: float
    b: float
    a: float = 1.0

    WHITE: ClassVar[RGBA]
    BLACK: ClassVar[RGBA]
    CRIMSON_RED: ClassVar[RGBA]
    RED: ClassVar[RGBA]
    GREEN: ClassVar[RGBA]
    LIME: ClassVar[RGBA]
    BLUE: ClassVar[RGBA]
    ORANGE: ClassVar[RGBA]
    LIGHT_BLUE: ClassVar[RGBA]
    GOLD: ClassVar[RGBA]
    CYAN: ClassVar[RGBA]

    def __mul__(self, other: float | RGBA):
        if isinstance(other, RGBA):
            return RGBA(
                min(1.0, self.r * other.r),
                min(1.0, self.g * other.g),
                min(1.0, self.b * other.b),
                min(1.0, self.a * other.a),
            )

        return RGBA(
            min(1.0, self.r * other),
            min(1.0, self.g * other),
            min(1.0, self.b * other),
            min(1.0, self.a * other),
        )


# Color constants
RGBA.WHITE = RGBA(1.0, 1.0, 1.0)
RGBA.BLACK = RGBA(0.0, 0.0, 0.0)
RGBA.RED = RGBA(1.0, 0.0, 0.0)
RGBA.CRIMSON_RED = RGBA(0.86, 0.08, 0.24)
RGBA.GREEN = RGBA(0.0, 1.0, 0.0)
RGBA.LIME = RGBA(0.56, 0.93, 0.56)
RGBA.BLUE = RGBA(0.0, 0.0, 1.0)
RGBA.ORANGE = RGBA(1.0, 0.5, 0.0)
RGBA.LIGHT_BLUE = RGBA(0.65, 0.85, 0.9)
RGBA.GOLD = RGBA(1.0, 0.85, 0.0)
RGBA.CYAN = RGBA(0.0, 1.0, 1.0)


@dataclass
class RichText:
    text: str
    text_color: RGBA = field(default_factory=lambda: RGBA.WHITE)
    bg_color: RGBA | None = None
    bold: bool = False


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
class ScreenBuffer:
    width: int
    height: int
    chars: np.ndarray  # shape (height, width), dtype='<U1'
    styles: (
        np.ndarray
    )  # shape (height, width), dtype=object, each element: (fg: RGB, bg: RGB, bold: bool)


@dataclass
class DrawCall:
    x: int
    y: int
    rich_text: RichText


@dataclass
class FPSCounter:
    ema: float = 0.0
    alpha: float = 0.08


def mul_darken(rich_text: RichText, value: float) -> RichText:
    """Multiplies the alpha of `text_color` and `bg_color` if applicable."""

    new_text_color: RGBA = lerp_rgb(RGBA.BLACK, rich_text.text_color, value)
    new_bg_color: RGBA | None = rich_text.bg_color

    if new_bg_color:
        new_bg_color = lerp_rgb(RGBA.BLACK, new_bg_color, value)

    return RichText(rich_text.text, new_text_color, new_bg_color, rich_text.bold)


def lerp_rgb(a: RGBA, b: RGBA, t: float) -> RGBA:
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

    return RGBA(
        a.r + (b.r - a.r) * t,
        a.g + (b.g - a.g) * t,
        a.b + (b.b - a.b) * t,
    )


def create_buffer(width: int, height: int) -> ScreenBuffer:
    chars = np.full((height, width), " ", dtype="<U1")
    # store default style: white text on background color, not bold
    default_style = np.empty((height, width), dtype=object)
    for y in range(height):
        for x in range(width):
            default_style[y, x] = (None, RGBA.BLACK, False)
    return ScreenBuffer(width, height, chars, default_style)


def buffer_diff(screen: Screen) -> list[tuple[int, int, ScreenCell]]:
    old = screen.old_buffer
    new = screen.new_buffer

    # per-char difference
    mask_chars = old.chars != new.chars

    # explicit per-cell style comparison (fg, bg, bold)
    def style_neq(a, b):
        return a[0] != b[0] or a[1] != b[1] or a[2] != b[2]

    # use numpy.frompyfunc to vectorize the python comparator
    style_cmp = np.frompyfunc(style_neq, 2, 1)
    mask_styles = style_cmp(old.styles, new.styles).astype(bool)

    mask = mask_chars | mask_styles
    ys, xs = np.nonzero(mask)

    diffs = [(int(y), int(x), (new.chars[y, x], new.styles[y, x])) for y, x in zip(ys, xs)]

    # Update buffers
    screen.old_buffer = ScreenBuffer(new.width, new.height, new.chars.copy(), new.styles.copy())
    screen.new_buffer = create_buffer(screen.width, screen.height)

    return diffs  # pyright: ignore


def flush_diffs(term: Terminal, diffs: list[tuple[int, int, ScreenCell]]) -> None:
    output = []
    for y, x, (char, style) in diffs:
        if isinstance(style, tuple):
            fg, bg, bold = style
            style_str = _make_style(term, fg, bg, bold)
        else:
            style_str = style  # fallback in case

        output.append(term.move_xy(int(x), int(y)) + style_str + char + term.normal)

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


def update_fps_counter(fps_counter: FPSCounter, dt: float) -> None:
    if dt <= 0.0:
        return
    inst = 1.0 / dt
    if fps_counter.ema <= 0.0:
        fps_counter.ema = inst
    else:
        fps_counter.ema = fps_counter.ema * (1.0 - fps_counter.alpha) + inst * fps_counter.alpha


def _make_style(term: Terminal, fg: RGBA | None, bg: RGBA | None, bold: bool) -> str:
    if not term.does_styling:
        return term.normal

    # minimal fix: fallback to WHITE/BLACK if None
    fg_rgb = _rgb_to_rgb_int(fg if fg is not None else RGBA.WHITE)
    bg_rgb = _rgb_to_rgb_int(bg if bg is not None else RGBA.BLACK)

    fg_str = term.color_rgb(*fg_rgb)
    bg_str = term.on_color_rgb(*bg_rgb)
    bold_str = term.bold if bold else ""
    return f"{term.normal}{bold_str}{fg_str}{bg_str}"


def _rgb_to_rgb_int(color: RGBA) -> tuple[int, int, int]:
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
    Respects the existing buffer background per character if seg.bg_color is None.
    """
    buf: ScreenBuffer = screen.new_buffer

    # normalize to list of RichText
    if isinstance(text, str):
        segments = [RichText(text, RGBA.WHITE)]
    elif isinstance(text, RichText):
        segments = [text]
    else:
        segments = [seg if isinstance(seg, RichText) else RichText(seg, RGBA.WHITE) for seg in text]

    if not (0 <= y < buf.height):
        return

    px = x
    for seg in segments:
        chars = list(seg.text)
        for i, char in enumerate(chars):
            cx = px + i
            if cx >= buf.width:
                break

            existing_fg, existing_bg, existing_bold = buf.styles[y, cx]

            # --- Handle background ---
            if seg.bg_color is None:
                # keep existing background
                bg = existing_bg
            else:
                # fully opaque? just replace
                if seg.bg_color.a >= 1.0:
                    bg = seg.bg_color
                else:
                    # semi-transparent → blend over existing
                    bg = _blend_rgba(seg.bg_color, existing_bg)

            # --- Handle character transparency ---
            if char == " ":
                # keep the old character
                fg = existing_fg
                char_to_draw = buf.chars[y, cx]  # the old character stays
                bold = existing_bold
            else:
                fg = seg.text_color
                char_to_draw = char
                bold = seg.bold

            buf.chars[y, cx] = char_to_draw
            buf.styles[y, cx] = (fg, bg, bold)

        px += len(chars)


def fill_screen_background(new_buffer: ScreenBuffer, color: RGBA) -> None:
    new_buffer.chars[:, :] = " "
    style_tuple = (RGBA.WHITE, color, False)
    for y in range(new_buffer.height):
        for x in range(new_buffer.width):
            new_buffer.styles[y, x] = style_tuple


def render_fps_counter(x: int, y: int, fps_counter: FPSCounter) -> list[DrawCall]:
    draw_instructions: list[DrawCall] = []

    fps_text = f"{fps_counter.ema:5.1f} FPS"
    # x = max(0, ctx.screen.width - len(fps_text) - 1)
    # print_at(x, y, RichText(fps_text, RGB.WHITE))
    draw_instructions.append(DrawCall(x, y, RichText(fps_text, RGBA.WHITE)))

    return draw_instructions


def _blend_rgba(top: RGBA, bottom: RGBA) -> RGBA:
    """Source-over alpha blending"""
    # clamp alpha
    ta = max(0.0, min(1.0, top.a))
    ba = max(0.0, min(1.0, bottom.a))

    out_a = ta + ba * (1.0 - ta)  # resulting alpha

    if out_a <= 0.0:
        # fully transparent result
        return RGBA(0.0, 0.0, 0.0, 0.0)

    # blend each channel
    out_r = (top.r * ta + bottom.r * ba * (1.0 - ta)) / out_a
    out_g = (top.g * ta + bottom.g * ba * (1.0 - ta)) / out_a
    out_b = (top.b * ta + bottom.b * ba * (1.0 - ta)) / out_a

    return RGBA(out_r, out_g, out_b, out_a)
