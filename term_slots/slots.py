import math
import random
from dataclasses import dataclass, field

from term_slots.config import Config
from term_slots.context import Context
from term_slots.ezterm import RGB, DrawCall, RichText, lerp_rgb
from term_slots.game_state import GameState
from term_slots.playing_card import PlayingCard, card_rich_text, render_card_small

SLOT_COLUMN_NEIGHBOR_COUNT = 3


@dataclass
class Slots:
    selected_column_index: int = 0
    columns: list[Column] = field(default_factory=list)


@dataclass
class Column:
    # Cursor is a float for easier incrementation
    # will have to be converted into an int to use as index
    cursor: float
    cards: list[PlayingCard] = field(default_factory=list)
    spin_duration: float = 0.0
    spin_time_remaining: float = 0.0
    # finish_flash_timer: float = 0.0
    spin_speed: float = 0.0
    spin_speed


# def start_slots_spin(
#     ctx: Context,
#     duration_sec: float,
#     duration_stagger_sec_min: float,
#     duration_stagger_ratio: float,
#     duration_stagger_diminishing_ratio: float,
# ):
#     base_increment = duration_sec * duration_stagger_ratio
#     r = duration_stagger_diminishing_ratio

#     for n, column in enumerate(ctx.slots.columns):
#         if n == 0:
#             stagger = 0
#         else:
#             # total extra time = sum of all previous per-column increments, clamped to min
#             stagger = sum(max(base_increment * (r**i), duration_stagger_sec_min) for i in range(n))

#         total_duration = duration_sec + stagger
#         column.spin_duration = total_duration
#         column.spin_time_remaining = total_duration


def calc_column_spin_duration_sec(col_index: int, config: Config) -> float:
    duration: float = config.slots_spin_duration_sec
    stagger_ratio: float = config.slots_spin_duration_stagger_ratio
    min_stagger_time: float = config.slots_spin_duration_stagger_sec_min

    base_increment: float = duration * stagger_ratio

    if col_index == 0:
        stagger = 0
    else:
        # total extra time = sum of all previous per-column increments, clamped to min
        stagger = sum(
            max(base_increment * (stagger_ratio**i), min_stagger_time) for i in range(col_index)
        )

    return duration + stagger


def spin_slots_and_check_finished(ctx: Context, dt: float, max_spin_speed: float) -> bool:
    """Mutates `ctx.slots`.

    Returns `True` once the spinning finishes or if it never starts.
    """

    if not ctx.slots.columns:
        # No columns -> Case where it never starts
        return True

    col_finished: int = 0
    for col in ctx.slots.columns:
        col.spin_time_remaining = max(0.0, col.spin_time_remaining - dt)
        col.spin_speed = calc_spin_speed(
            col.spin_duration,
            col.spin_time_remaining,
            snap_threshold=0.15,
            max_spin_speed=max_spin_speed,
        )

        col.cursor -= col.spin_speed * dt

        # `ctx.spin_speed` will always be equal to 0.0
        # when `ctx.spin_time_remaining` is equal to 0.0
        spin_stopped: bool = col.spin_speed == 0.0
        if spin_stopped:
            col.spin_time_remaining = 0.0
            col_finished += 1

    if col_finished == len(ctx.slots.columns):
        return True

    return False


# def render_slots_old(ctx: Context, x: int, y: int) -> list[DrawCall]:
#     draw_instructions: list[DrawCall] = []

#     spacing = 5
#     # y = 6
#     any_column_spinning: bool = ctx.game_state == GameState.SPINNING_SLOTS

#     for n, column in enumerate(ctx.slots.columns):
#         is_selected: bool = ctx.slots.selected_column_index == n

#         col_x = x + n * spacing
#         instructions: list[DrawCall] = render_column_old(
#             col_x, y, column, is_selected, any_column_spinning, ctx.game_state
#         )  # pyright: ignore
#         draw_instructions.extend(instructions)

#     return draw_instructions


def render_slots(x: int, y: int, ctx: Context) -> list[DrawCall]:
    draw_calls: list[DrawCall] = []

    x_spacing = 5
    slots_focussed: bool = # TODO: finish this
    # any_col_is_spinning: bool = ctx.game_state == GameState.SPINNING_SLOTS

    for col_index, col in enumerate(ctx.slots.columns):
        # is_selected: bool = ctx.slots.selected_column_index == col_index

        col_x: int = x + col_index * x_spacing
        col_y: int = y
        draw_calls.extend(
            render_column(
                col_x,
                col_y,
                col,  # pyright: ignore
                is_focussed=True,
            )
        )

    return draw_calls


def render_column(x: int, y: int, column: Column, is_focussed: bool) -> list[DrawCall]:
    def card_index(row_offset: int, column: Column) -> int:
        """Retrieves the wrapped card index from the column."""
        index: int = int(column.cursor + row_offset)
        wrapped_index: int = index % len(column.cards)
        return wrapped_index

    draw_calls: list[DrawCall] = []

    for row_offset in range(
        -SLOT_COLUMN_NEIGHBOR_COUNT,
        SLOT_COLUMN_NEIGHBOR_COUNT + 1,
    ):
        card_x: int = x
        card_y: int = y + row_offset
        card: PlayingCard = column.cards[card_index(row_offset, column)]

        card_draw_call: DrawCall = render_card_small(card_x, card_y, card)

        # Alpha dimming of neighbors using a gaussian curve
        sigma: float = 1.5
        alpha: float = math.exp(-(row_offset**2) / (2 * sigma**2))

        if card_draw_call.text.bg_color:
            card_draw_call.text.bg_color *= alpha
        card_draw_call.text.text_color *= alpha

        # Unfocussed dimming
        if not is_focussed:
            draw_calls

        draw_calls.append(card_draw_call)
        # is_main_row: bool = row_offset == 0

    return draw_calls


# def render_column_old(
#     x: int,
#     y: int,
#     column: Column,
#     is_selected: bool,
#     any_column_spinning: bool,
#     game_state: GameState,
# ) -> list[DrawCall]:
#     draw_instructions: list[DrawCall] = []

#     for row_offset in range(-SLOT_COLUMN_NEIGHBOR_COUNT, SLOT_COLUMN_NEIGHBOR_COUNT + 1):
#         is_cursor_row = row_offset == 0

#         card_index = wrap_cursor(int(column.cursor + row_offset), column.cards)
#         rich_text = card_rich_text(column.cards[card_index])

#         if is_selected and game_state == GameState.SLOTS_POST_SPIN_COLUMN_PICKING:
#             rich_text.bg_color = lerp_rgb(rich_text.bg_color, RGB.GOLD, 0.5)
#             # Arrows
#             draw_instructions.append(
#                 DrawCall(
#                     x,
#                     y + SLOT_COLUMN_NEIGHBOR_COUNT + 1,
#                     RichText(" ▴ ", RGB.GOLD * 0.4),
#                 )
#             )
#             draw_instructions.append(
#                 DrawCall(
#                     x,
#                     y - SLOT_COLUMN_NEIGHBOR_COUNT - 1,
#                     RichText(" ▾ ", RGB.GOLD * 0.4),
#                 )
#             )

#         if is_cursor_row:
#             alpha = 0.9
#             rich_text.bg_color *= alpha
#             rich_text.text_color *= alpha
#         else:
#             # Fade away dimming of neighbors
#             alpha = abs(1.0 / row_offset * 0.3)
#             rich_text.bg_color *= alpha
#             rich_text.text_color *= alpha

#         # draw_instructions.append(DrawInstruction(x, 2, f"{column.spin_duration:2.1f}"))

#         if column.spin_time_remaining:
#             seeded_random = random.Random(card_index)
#             # alpha = seeded_random.uniform(0.85, 1.0)
#             rich_text.bg_color *= seeded_random.uniform(0.85, 1.0)
#             rich_text.text_color = lerp_rgb(
#                 rich_text.bg_color,
#                 rich_text.text_color,
#                 seeded_random.uniform(0.0, 1.0),
#             )

#         slots_focussed_game_states: list[GameState] = [
#             GameState.READY_TO_SPIN_SLOTS,
#             GameState.SPINNING_SLOTS,
#             GameState.SLOTS_POST_SPIN_COLUMN_PICKING,
#         ]
#         if game_state not in slots_focussed_game_states:
#             unfocussed_alpha_modifier = 0.5 * (abs(row_offset) + 1) * 0.4
#             # unfocussed_alpha_modifier = 0.3
#             rich_text.bg_color *= unfocussed_alpha_modifier
#             rich_text.text_color *= unfocussed_alpha_modifier

#         draw_instructions.append(DrawCall(x, y + row_offset, rich_text))

#     return draw_instructions


def calc_spin_speed(
    duration: float, time_remaining: float, snap_threshold: float, max_spin_speed: float
) -> float:
    exponent = 6

    # clamp normalized time
    time_normalized = max(0.0, min(1.0, time_remaining / duration))

    # guaranteed zero at end or snap early
    if time_normalized <= 0.0 or time_normalized <= snap_threshold:
        return 0.0

    # easing curve
    return max_spin_speed * (1 - (1 - time_normalized) ** exponent)
