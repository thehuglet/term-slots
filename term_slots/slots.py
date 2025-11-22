import math
import random
from dataclasses import dataclass, field

from term_slots.config import Config
from term_slots.context import Context
from term_slots.ezterm import RGB, DrawCall, RichText, lerp_rgb, mul_alpha
from term_slots.game_state import GameState
from term_slots.playing_card import PlayingCard, render_card_small

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
    spin_speed: float = 0.0


def calc_column_spin_duration_sec(col_index: int, cfg: Config) -> float:
    duration: float = cfg.slots_spin_duration_sec
    stagger_ratio: float = cfg.slots_spin_duration_stagger_ratio
    min_stagger_duration: float = cfg.slots_spin_duration_stagger_sec_min
    geometric_weight: float = cfg.slots_spin_geometric_weight

    base: float = duration * stagger_ratio

    if col_index == 0:
        return duration

    geometric_increments: list[float] = [
        max(base * (stagger_ratio**i), min_stagger_duration) for i in range(col_index)
    ]

    linear_increments: list[float] = [max(base, min_stagger_duration) for _ in range(col_index)]

    stagger: float = sum(
        linear_increments[i] * (1.0 - geometric_weight) + geometric_increments[i] * geometric_weight
        for i in range(col_index)
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


def render_slots(x: int, y: int, ctx: Context, game_time: float) -> list[DrawCall]:
    draw_calls: list[DrawCall] = []
    all_focussed_game_states: list[GameState] = [
        GameState.READY_TO_SPIN_SLOTS,
        GameState.SPINNING_SLOTS,
        GameState.SLOTS_POST_SPIN_COLUMN_PICKING,
    ]

    x_spacing = 5
    slots_are_focused: bool = ctx.game_state in all_focussed_game_states

    for col_index, col in enumerate(ctx.slots.columns):
        is_game_state_picking: bool = ctx.game_state == GameState.SLOTS_POST_SPIN_COLUMN_PICKING
        col_is_selected: bool = ctx.slots.selected_column_index == col_index

        col_x: int = x + col_index * x_spacing
        col_y: int = y
        draw_calls.extend(
            render_column(
                col_x,
                col_y,
                col,  # pyright: ignore
                game_time,
                slots_are_focused,
                column_is_selected=is_game_state_picking and col_is_selected,
            )
        )

        # Center center row indicators
        is_first_column: bool = col_index == 0
        is_last_column: bool = col_index == len(ctx.slots.columns) - 1

        column_indicator_color: RGB = lerp_rgb(RGB.GOLD, RGB.WHITE, 0.5) * 0.4
        row_indicator_color: RGB = lerp_rgb(RGB.GOLD, RGB.WHITE, 0.5)

        # Dim row indicator arrows when not focussed
        if not slots_are_focused:
            row_indicator_color *= 0.2

        if is_first_column:
            draw_calls.append(DrawCall(col_x - 2, col_y, RichText("▸", row_indicator_color)))
        if is_last_column:
            draw_calls.append(DrawCall(col_x + 4, col_y, RichText("◂", row_indicator_color)))

        # Column selection arrows
        if is_game_state_picking and col_is_selected:
            arrow_x: int = col_x + 1
            top_arrow_y: int = col_y + SLOT_COLUMN_NEIGHBOR_COUNT + 1
            bot_arrow_y: int = col_y - SLOT_COLUMN_NEIGHBOR_COUNT - 1

            # Column indicator arrows
            draw_calls.append(DrawCall(arrow_x, top_arrow_y, RichText("▴", column_indicator_color)))
            draw_calls.append(DrawCall(arrow_x, bot_arrow_y, RichText("▾", column_indicator_color)))

    return draw_calls


def render_column(
    x: int,
    y: int,
    column: Column,
    game_time: float,
    slots_are_focused: bool,
    column_is_selected: bool,
) -> list[DrawCall]:
    def get_card_index(row_offset: int, column: Column) -> int:
        """Retrieves the wrapped card index from the column."""
        index: int = int(column.cursor + row_offset)
        wrapped_index: int = index % len(column.cards)
        return wrapped_index

    draw_calls: list[DrawCall] = []

    for row_offset in range(
        -SLOT_COLUMN_NEIGHBOR_COUNT,
        SLOT_COLUMN_NEIGHBOR_COUNT + 1,
    ):
        is_center_row: bool = row_offset == 0

        card_x: int = x
        card_y: int = y + row_offset
        card_index: int = get_card_index(row_offset, column)
        card: PlayingCard = column.cards[card_index]

        card_draw_call: DrawCall = render_card_small(card_x, card_y, card)
        rt: RichText = card_draw_call.rich_text

        # Base card background alpha
        if rt.bg_color:
            rt.bg_color *= 0.8

        # Column center row highlight during picking phase
        if column_is_selected and rt.bg_color:
            # Column Highlight
            rt.bg_color = lerp_rgb(rt.bg_color, RGB.GOLD, 0.3)

            # Sinewave center row highlight
            if is_center_row:
                amplitude: float = 1.0
                frequency: float = 6.5
                t: float = 0.5 + 0.5 * amplitude * math.sin(frequency * game_time)

                rt.bg_color = lerp_rgb(rt.bg_color, RGB.WHITE, t)
                rt.text_color = lerp_rgb(rt.text_color, RGB.WHITE, t * 0.8)

        # Multiplying by random alpha while spinning
        col_is_spinning: bool = column.spin_time_remaining > 0.0
        if col_is_spinning and rt.bg_color:
            seeded_random = random.Random(card_index)
            rt.bg_color *= seeded_random.uniform(0.85, 1.0)
            rt.text_color = lerp_rgb(
                rt.bg_color,
                rt.text_color,
                seeded_random.uniform(0.0, 1.0),
            )

        # Alpha dimming of neighbors using a gaussian curve
        sigma: float = 1.3
        alpha: float = math.exp(-(row_offset**2) / (2 * sigma**2))

        if not slots_are_focused:
            # This trick lowers the brightness and contrast when unfocussed
            alpha = alpha * 0.1 + 0.05

        rt = mul_alpha(rt, alpha)

        card_draw_call.rich_text = rt
        draw_calls.append(card_draw_call)

    return draw_calls


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
