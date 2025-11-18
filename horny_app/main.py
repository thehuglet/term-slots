import math
import random
from abc import ABC
from copy import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from typing import Callable, cast

from blessed import Terminal

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
    lerp_rgb,
    update_fps_counter,
)
from horny_app.ezterm import print_at as verbose_print_at
from horny_app.playing_cards import (
    FULL_DECK,
    RANK_STR,
    SUIT_STR,
    PlayingCard,
    Rank,
    Suit,
    card_rich_text,
)
from horny_app.slots import Column, Slots, calc_spin_speed, wrap_cursor

type PrintAtCallable = Callable[[int, int, str | RichText | list[str | RichText]], None]


class ProgramStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


@dataclass
class Context:
    term: Terminal
    screen: Screen
    slots: Slots
    time_running: float = 0.0
    debug_text: str | RichText = ""


def tick(
    ctx: Context,
    delta_time: float,
    print_at: PrintAtCallable,
    fps_counter: FPSCounter,
) -> ProgramStatus:
    key = ctx.term.inkey(0.0)

    slots_spinning = ctx.slots.columns[-1].spin_time_remaining > 0.0
    slots_can_move_left: bool = (
        not slots_spinning and ctx.slots.selected_column_index > 0
    )
    slots_can_move_right: bool = (
        not slots_spinning
        and ctx.slots.selected_column_index < len(ctx.slots.columns) - 1
    )

    if key.lower() == "q":
        return ProgramStatus.EXIT

    elif key == "s":
        for n, column in enumerate(ctx.slots.columns):
            column.spin_duration = 3.0 + n * 1.0
            column.spin_time_remaining = column.spin_duration

    elif key.name == "KEY_LEFT" and slots_can_move_left:
        ctx.slots.selected_column_index -= 1

    elif key.name == "KEY_RIGHT" and slots_can_move_right:
        ctx.slots.selected_column_index += 1

    fill_screen_background(ctx.term, ctx.screen, BACKGROUND_COLOR)

    for n, column in enumerate(ctx.slots.columns):
        # --- Column spinning logic ---
        if column.spin_time_remaining > 0.0:
            duration = column.spin_duration
            time_remaining = column.spin_time_remaining

            spin_speed = calc_spin_speed(duration, time_remaining, snap_threshold=0.15)
            column.cursor -= spin_speed * delta_time

            column.spin_time_remaining = max(0.0, time_remaining - delta_time)

            # This is done to account for snapping
            if spin_speed == 0.0:
                column.spin_time_remaining = 0.0

        # --- Slot column rendering ---
        column_spacing = 5
        column_x = 5 + n * column_spacing
        column_y = 5
        column_is_selected = ctx.slots.selected_column_index == n

        neighbor_count = 3
        for row_offset in range(-neighbor_count, neighbor_count + 1):
            is_cursor_row = row_offset == 0

            card_index = wrap_cursor(int(column.cursor + row_offset), column.cards)
            rich_text = card_rich_text(column.cards[card_index])

            if column_is_selected and not slots_spinning:
                rich_text.bg_color = lerp_rgb(rich_text.bg_color, RGB.GOLD, 0.5)
                # Arrows
                print_at(
                    column_x,
                    column_y + neighbor_count + 1,
                    RichText(" ▴ ", RGB.GOLD * 0.4),
                )
                print_at(
                    column_x,
                    column_y - neighbor_count - 1,
                    RichText(" ▾ ", RGB.GOLD * 0.4),
                )

            if not is_cursor_row:
                # Fade away dimming of neighbors
                alpha_mult = abs(1.0 / row_offset * 0.3)
                rich_text.bg_color *= alpha_mult
                rich_text.text_color *= alpha_mult

            if column.spin_time_remaining:
                rich_text.bg_color *= random.uniform(0.85, 1.0)
                rich_text.text_color = lerp_rgb(
                    rich_text.bg_color,
                    rich_text.text_color,
                    random.uniform(0.0, 1.0),
                )

            print_at(column_x, column_y + row_offset, rich_text)

    update_fps_counter(fps_counter, delta_time)
    fps_text = f"{fps_counter.ema:5.1f} FPS"
    color = RGB.WHITE
    x = max(0, ctx.screen.width - len(fps_text) - 1)
    print_at(x, 0, RichText(fps_text, color))

    ctx.time_running += delta_time
    flush_diffs(ctx.term, buffer_diff(ctx.screen))
    return ProgramStatus.RUNNING


def main():
    foo = [PlayingCard(Suit.SPADE, Rank.R_A) for _ in range(52)]
    term = Terminal()
    screen = Screen(term.width, term.height)
    ctx = Context(
        term,
        screen,
        Slots(
            columns=[
                Column(0, foo),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
            ]
        ),
    )

    for column in ctx.slots.columns:
        random.shuffle(column.cards)

    print_at = partial(verbose_print_at, term, screen)

    fps_limiter = create_fps_limiter(144)
    fps_counter = FPSCounter()

    with (
        term.cbreak(),
        term.hidden_cursor(),
        term.fullscreen(),
    ):
        delta_time: float = 0.0

        while True:
            tick_outcome: ProgramStatus = tick(
                ctx,
                delta_time,
                print_at,
                fps_counter,
            )
            if tick_outcome == ProgramStatus.EXIT:
                break

            delta_time = fps_limiter()
