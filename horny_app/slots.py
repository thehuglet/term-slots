import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from horny_app.context import Context

from horny_app.context import GameState
from horny_app.ezterm import RGB, DrawInstruction, PrintAtCallable, RichText, lerp_rgb
from horny_app.playing_card import PlayingCard, card_rich_text

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
    finish_flash_timer: float = 0.0


def tick_slots(ctx: Context, dt: float):
    for n, column in enumerate(ctx.slots.columns):
        if not column.spin_time_remaining:
            continue

        spin_speed = calc_spin_speed(
            column.spin_duration,
            column.spin_time_remaining,
            snap_threshold=0.15,
        )
        column.cursor -= spin_speed * dt
        column.spin_time_remaining = max(0.0, column.spin_time_remaining - dt)

        if spin_speed == 0.0:
            column.spin_time_remaining = 0.0


def render_slots(ctx: Context) -> list[DrawInstruction]:
    draw_instructions: list[DrawInstruction] = []

    spacing = 5
    y = 5
    any_column_spinning: bool = ctx.game_state == GameState.SPINNING_SLOTS

    for n, column in enumerate(ctx.slots.columns):
        x = 5 + n * spacing
        is_selected: bool = ctx.slots.selected_column_index == n

        instructions: list[DrawInstruction] = render_column(
            x, y, column, any_column_spinning, is_selected
        )
        draw_instructions.extend(instructions)

    return draw_instructions


def render_column(
    x: int,
    y: int,
    column: Column,
    is_selected: bool,
    any_column_spinning: bool,
) -> list[DrawInstruction]:
    draw_instructions: list[DrawInstruction] = []

    for row_offset in range(-SLOT_COLUMN_NEIGHBOR_COUNT, SLOT_COLUMN_NEIGHBOR_COUNT + 1):
        is_cursor_row = row_offset == 0

        card_index = wrap_cursor(int(column.cursor + row_offset), column.cards)
        rich_text = card_rich_text(column.cards[card_index])

        if is_selected and not any_column_spinning:
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

        draw_instructions.append(DrawInstruction(x, y + row_offset, rich_text))

    return draw_instructions


def calc_spin_speed(
    duration: float,
    time_remaining: float,
    snap_threshold: float,
) -> float:
    max_speed = 60.0
    exponent = 6

    time_normalized = time_remaining / duration
    time_normalized = max(0.0, min(1.0, time_normalized))

    if time_normalized <= snap_threshold:
        return 0.0

    return max_speed * (1 - (1 - time_normalized) ** exponent)


def wrap_cursor(cursor: int, cards: list[PlayingCard]):
    return cursor % len(cards)
