import math
from copy import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from random import shuffle, uniform
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
    update_fps_counter,
)
from horny_app.ezterm import print_at as verbose_print_at
from horny_app.playing_cards import (
    FULL_DECK,
    RANK_STR,
    SUIT_STR,
    PlayingCard,
    card_rich_text,
)
from horny_app.slots import Column, Slots, calc_spin_speed, wrap_cursor

type PrintAtCallable = Callable[[int, int, str | RichText | list[str | RichText]], None]


class ProgramStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


# @dataclass
# class SlotColumn:
#     cursor: int
#     elements: list[PlayingCard] = field(default_factory=list)
#     # cursor_progress: float = 0.0
#     spin_time_remaining: float = 0.0

# def move_cursor_continuous(self, delta_cursor: float):
#     self.cursor_progress += delta_cursor
#     self.cursor = int(self.cursor_progress) % len(self.elements)

# def get_element_wrapped_around(self, index: int) -> str:
#     return self.elements[index % len(self.elements)]


@dataclass
class Context:
    term: Terminal
    screen: Screen
    slots: Slots
    time_running: float = 0.0
    # slots: list[SlotColumn] = field(default_factory=list)
    debug_text: str | RichText = ""
    # spin_time_remaining: float = 0.0


def tick(
    ctx: Context,
    delta_time: float,
    print_at: PrintAtCallable,
    fps_counter: FPSCounter,
) -> ProgramStatus:
    inp = ctx.term.inkey(0.0)

    if inp == "q":
        return ProgramStatus.EXIT
    elif inp == "s":
        for n, column in enumerate(ctx.slots.columns):
            column.spin_duration = 3.0 + n * 1.0
            column.spin_time_remaining = column.spin_duration

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
                column.finish_flash_timer = 1.0

        flash_multiplier = 1.0
        if column.finish_flash_timer > 0.0:
            flash_multiplier += column.finish_flash_timer * 0.2

            column.finish_flash_timer = max(
                0.0, column.finish_flash_timer - delta_time * 25
            )

        # --- Slot column rendering ---
        card_at_cursor = column.cards[
            wrap_cursor(math.floor(column.cursor), column.cards)
        ]
        rich_text = card_rich_text(card_at_cursor)

        if column.spin_time_remaining > 0.0:
            assert isinstance(rich_text.bg, RGB)
            rich_text.bg *= uniform(0.7, 1.0)
            rich_text.color *= flash_multiplier
            rich_text.bg *= uniform(0.7, 1.0)
            rich_text.color *= flash_multiplier

        x = 5 + n * 5
        print_at(x, 5, rich_text)

        neighbor_count = 3
        for neighbor in range(-neighbor_count, neighbor_count + 1):
            if neighbor == 0:
                # Skip middle cursor row
                continue

            card = column.cards[
                wrap_cursor(int(column.cursor + neighbor), column.cards)
            ]
            rich_text = card_rich_text(card)
            alpha_mult = abs(1.0 / neighbor * 0.3)

            if column.spin_time_remaining > 0.0:
                alpha_mult *= uniform(0.7, 1.0)

            assert isinstance(rich_text.bg, RGB)
            rich_text.bg *= alpha_mult
            rich_text.bg *= flash_multiplier
            rich_text.color *= alpha_mult
            rich_text.color *= flash_multiplier

            print_at(x, 5 + neighbor, rich_text)

    # ctx.spin_time_remaining = spin_duration
    # print_at(0, 0, str(len(FULL_DECK)))
    # if ctx.spin_time_remaining > 0.0:
    #     ctx.spin_time_remaining = max(0.0, ctx.spin_time_remaining - delta_time)

    # for n, slot_column in enumerate(ctx.slots):
    #     slot_width = 1
    #     spacer_width = 2
    #     x_offset = n * (slot_width + spacer_width)

    #     base_stagger = 10.0  # max delay for leftmost column
    #     max_speed = 12.0
    #     snap_time_remaining = 3.5
    #     max_variation = 0.15

    #     speed = 0
    #     if ctx.spin_time_remaining > 0.0:
    #         n_columns = len(ctx.slots)

    #         for i, slot_column in enumerate(ctx.slots):
    #             # stagger: leftmost starts first, rightmost starts later
    #             stagger_amount = base_stagger * (
    #                 (n_columns - 1 - i) / max(1, n_columns - 1)
    #             )
    #             stagger_amount += uniform(-max_variation, max_variation)
    #             stagger_amount = max(0.0, stagger_amount)

    #             # effective time since this column started spinning
    #             column_elapsed = max(
    #                 0.0, spin_duration - (ctx.spin_time_remaining - stagger_amount)
    #             )
    #             column_elapsed = min(column_elapsed, spin_duration)

    #             # snap instantly if almost done
    #             if column_elapsed >= spin_duration - snap_time_remaining:
    #                 speed = 0.0
    #             else:
    #                 t = column_elapsed / spin_duration
    #                 speed_factor = math.sqrt(1 - t)  # easing: fast start, slow finish
    #                 speed = max_speed * speed_factor

    #             if speed > 0:
    #                 slot_column.move_cursor_continuous(speed * delta_time)

    #         # decrement overall spin timer
    #         ctx.spin_time_remaining = max(0.0, ctx.spin_time_remaining - delta_time)

    #     # text = slot_column.get_element_wrapped_around(slot_column.cursor)
    #     # print_at(
    #     #     5 + x_offset,
    #     #     5,
    #     #     RichText(text.center(slot_width), RGB(1.0, 0.0, 0.0), bg=RGB.WHITE),
    #     # )
    #     text = slot_column.get_element_wrapped_around(slot_column.cursor)
    #     x_centered = (
    #         5 + x_offset + (slot_width - len(text)) // 2
    #     )  # offset for centering
    #     print_at(
    #         x_centered,
    #         5,
    #         RichText(
    #             text,
    #             copy(RGB.RED) * 0.9,
    #             bg=RGB.WHITE * 0.9,
    #             bold=True,
    #         ),
    #     )

    #     preview_row_count = 3

    #     def calc_alpha(row: int) -> float:
    #         return 1.0 / (0.5 + 2.0 ** abs(row))

    #     for preview_row in range(1, preview_row_count + 1):
    #         for row in [-preview_row, preview_row]:
    #             text = slot_column.get_element_wrapped_around(slot_column.cursor - row)
    #             x_centered = (
    #                 5 + x_offset + (slot_width - len(text)) // 2
    #             )  # offset for centering

    #             rand_alpha_mult = 1.0
    #             if speed > 0:
    #                 print_at(0, 17, str(speed))
    #                 rand_alpha_mult = uniform(0.8, 1.0)

    #             print_at(
    #                 x_centered,
    #                 5 + row,
    #                 RichText(
    #                     text,
    #                     RGB.RED * calc_alpha(row),
    #                     bg=RGB.WHITE * calc_alpha(row) * rand_alpha_mult,
    #                 ),
    #             )

    update_fps_counter(fps_counter, delta_time)
    fps_text = f"{fps_counter.ema:5.1f} FPS"
    color = RGB.WHITE
    x = max(0, ctx.screen.width - len(fps_text) - 1)
    print_at(x, 0, RichText(fps_text, color))

    ctx.time_running += delta_time
    flush_diffs(ctx.term, buffer_diff(ctx.screen))
    return ProgramStatus.RUNNING


def main():
    # slot_definition: list[str] = ["♥A", "♥3"]

    # ctx = Context(
    #     slots=[SlotColumn(0, slot_definition.copy()) for _ in range(4)],
    # )

    # for slot_data in ctx.slots:
    #     shuffle(slot_data.elements)

    term = Terminal()
    screen = Screen(term.width, term.height)
    ctx = Context(
        term,
        screen,
        Slots(
            columns=[
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
            ]
        ),
    )

    for column in ctx.slots.columns:
        shuffle(column.cards)

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
