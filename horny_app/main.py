from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from typing import Callable

from blessed.terminal import Terminal

from horny_app.ezterm import (
    BACKGROUND_COLOR,
    RGB,
    FPSCounter,
    RichText,
    Screen,
    buffer_diff,
    create_fps_limiter,
    fill_screen_background,
    flush_diffs,
    update_fps_counter,
)
from horny_app.ezterm import print_at as verbose_print_at

type PrintAtCallable = Callable[[int, int, str | RichText | list[str | RichText]], None]


class ProgramStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


@dataclass
class Context:
    debug_text: str | RichText = ""


def tick(
    ctx: Context,
    screen: Screen,
    term: Terminal,
    delta_time: float,
    print_at: PrintAtCallable,
    fps_counter: FPSCounter,
) -> ProgramStatus:
    inp = term.inkey(0.0)

    if inp == "q":
        return ProgramStatus.EXIT

    if inp.name == "MOUSE_LEFT":
        ctx.debug_text = f"{inp.name}, {inp.mouse_xy}"

    print_at(0, 0, ctx.debug_text)
    # print_at(0, 1, f"button {inp.name} at (y={inp.y}, x={inp.x})")

    update_fps_counter(fps_counter, delta_time)
    fps_text = f"{fps_counter.ema:5.1f} FPS"
    color = RGB.WHITE
    x = max(0, screen.width - len(fps_text) - 1)
    print_at(x, 0, RichText(fps_text, color, bold=True))

    flush_diffs(term, buffer_diff(screen))
    return ProgramStatus.RUNNING


def main():
    ctx = Context()
    term = Terminal()
    screen = Screen(term.width, term.height)
    print_at = partial(verbose_print_at, term, screen)

    fps_limiter = create_fps_limiter(144)
    fps_counter = FPSCounter()
    fill_screen_background(term, screen, BACKGROUND_COLOR)

    with (
        term.cbreak(),
        term.hidden_cursor(),
        term.fullscreen(),
        term.mouse_enabled(),
    ):
        delta_time: float = 0.0

        while True:
            tick_outcome: ProgramStatus = tick(
                ctx,
                screen,
                term,
                delta_time,
                print_at,
                fps_counter,
            )
            if tick_outcome == ProgramStatus.EXIT:
                break

            delta_time = fps_limiter()
