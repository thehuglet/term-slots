import random
from dataclasses import dataclass, field

from term_slots.context import Context
from term_slots.ezterm import RGB, DrawInstruction, RichText, lerp_rgb
from term_slots.game_state import GameState
from term_slots.playing_card import PlayingCard, card_rich_text

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


def start_slots_spin(
    ctx: Context,
    duration_sec: float,
    duration_stagger_sec_min: float,
    duration_stagger_ratio: float,
    duration_stagger_diminishing_ratio: float,
):
    r = duration_stagger_diminishing_ratio

    for n, column in enumerate(ctx.slots.columns):
        if n == 0:
            staggered_duration = 0
        else:
            staggered_duration = 0
            # initial increment is duration_sec * duration_stagger_ratio
            increment = duration_sec * duration_stagger_ratio
            for i in range(n):
                # clamp the increment to min stagger
                current_increment = max(increment * (r**i), duration_stagger_sec_min)
                staggered_duration += current_increment

        total_duration = duration_sec + staggered_duration
        column.spin_duration = total_duration
        column.spin_time_remaining = total_duration


def tick_slots_spin(ctx: Context, dt: float, max_spin_speed: float) -> bool:
    """Return `True` once the spinning finishes or if it never starts."""

    for n, column in enumerate(ctx.slots.columns):
        if not column.spin_time_remaining:
            continue

        column.spin_speed = calc_spin_speed(
            column.spin_duration,
            column.spin_time_remaining,
            snap_threshold=0.15,
            max_spin_speed=max_spin_speed,
        )

        column.cursor -= column.spin_speed * dt
        column.spin_time_remaining = max(0.0, column.spin_time_remaining - dt)

        if column.spin_speed == 0.0:
            column.spin_time_remaining = 0.0

        is_last_column: bool = n == len(ctx.slots.columns) - 1
        if is_last_column and column.spin_speed == 0:
            # Last column stopped == Entire slots stopped
            return True

    if not ctx.slots.columns:
        # No columns -> Case where it never starts
        return True

    return False


def render_slots(ctx: Context, x: int, y: int) -> list[DrawInstruction]:
    draw_instructions: list[DrawInstruction] = []

    spacing = 5
    # y = 6
    any_column_spinning: bool = ctx.game_state == GameState.SPINNING_SLOTS

    for n, column in enumerate(ctx.slots.columns):
        is_selected: bool = ctx.slots.selected_column_index == n

        col_x = x + n * spacing
        instructions: list[DrawInstruction] = render_column(
            col_x, y, column, is_selected, any_column_spinning, ctx.game_state
        )
        draw_instructions.extend(instructions)

    return draw_instructions


def render_column(
    x: int,
    y: int,
    column: Column,
    is_selected: bool,
    any_column_spinning: bool,
    game_state: GameState,
) -> list[DrawInstruction]:
    draw_instructions: list[DrawInstruction] = []

    for row_offset in range(-SLOT_COLUMN_NEIGHBOR_COUNT, SLOT_COLUMN_NEIGHBOR_COUNT + 1):
        is_cursor_row = row_offset == 0

        card_index = wrap_cursor(int(column.cursor + row_offset), column.cards)
        rich_text = card_rich_text(column.cards[card_index])

        if is_selected and game_state == GameState.SLOTS_POST_SPIN_COLUMN_PICKING:
            rich_text.bg_color = lerp_rgb(rich_text.bg_color, RGB.GOLD, 0.5)
            # Arrows
            draw_instructions.append(
                DrawInstruction(
                    x,
                    y + SLOT_COLUMN_NEIGHBOR_COUNT + 1,
                    RichText(" ▴ ", RGB.GOLD * 0.4),
                )
            )
            draw_instructions.append(
                DrawInstruction(
                    x,
                    y - SLOT_COLUMN_NEIGHBOR_COUNT - 1,
                    RichText(" ▾ ", RGB.GOLD * 0.4),
                )
            )

        if not is_cursor_row:
            # Fade away dimming of neighbors
            alpha = abs(1.0 / row_offset * 0.3)
            rich_text.bg_color *= alpha
            rich_text.text_color *= alpha

        # draw_instructions.append(DrawInstruction(x, 2, f"{column.spin_duration:2.1f}"))

        if column.spin_time_remaining:
            seeded_random = random.Random(card_index)
            # alpha = seeded_random.uniform(0.85, 1.0)
            rich_text.bg_color *= seeded_random.uniform(0.85, 1.0)
            rich_text.text_color = lerp_rgb(
                rich_text.bg_color,
                rich_text.text_color,
                seeded_random.uniform(0.0, 1.0),
            )

        slots_focussed_game_states: list[GameState] = [
            GameState.READY_TO_SPIN_SLOTS,
            GameState.SPINNING_SLOTS,
            GameState.SLOTS_POST_SPIN_COLUMN_PICKING,
        ]
        if game_state not in slots_focussed_game_states:
            rich_text.bg_color *= 0.8
            rich_text.text_color *= 0.8

        draw_instructions.append(DrawInstruction(x, y + row_offset, rich_text))

    return draw_instructions


def calc_spin_speed(
    duration: float, time_remaining: float, snap_threshold: float, max_spin_speed: float
) -> float:
    exponent = 6

    time_normalized = time_remaining / duration
    time_normalized = max(0.0, min(1.0, time_normalized))

    if time_normalized <= snap_threshold:
        return 0.0

    return max_spin_speed * (1 - (1 - time_normalized) ** exponent)


def wrap_cursor(cursor: int, cards: list[PlayingCard]):
    return cursor % len(cards)
