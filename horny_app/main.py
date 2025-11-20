import random
from enum import Enum, auto

from blessed import Terminal

from horny_app.context import Context
from horny_app.ezterm import (
    BACKGROUND_COLOR,
    RGB,
    DrawInstruction,
    FPSCounter,
    PrintAtCallable,
    RichText,
    Screen,
    buffer_diff,
    create_fps_limiter,
    fill_screen_background,
    flush_diffs,
    lerp_rgb,
    print_at,
    render_fps_counter,
    update_fps_counter,
)
from horny_app.game_state import GameState
from horny_app.input import Action, map_input, resolve_input
from horny_app.playing_card import (
    FULL_DECK,
    PlayingCard,
    Rank,
    Suit,
    card_rich_text,
)
from horny_app.slots import (
    Column,
    Slots,
    calc_spin_speed,
    render_slots,
    start_slots_spin,
    tick_slots_spin,
    wrap_cursor,
)


class ProgramStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


def tick(
    ctx: Context,
    delta_time: float,
    print_at: PrintAtCallable,
) -> ProgramStatus:
    # --- Input handling ---
    key = ctx.term.inkey(0.0)

    slots_spinning = ctx.slots.columns[-1].spin_time_remaining > 0.0
    slots_can_move_left: bool = not slots_spinning and ctx.slots.selected_column_index > 0
    slots_can_move_right: bool = (
        not slots_spinning and ctx.slots.selected_column_index < len(ctx.slots.columns) - 1
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

    # --- Game logic ---
    # Slots
    for n, column in enumerate(ctx.slots.columns):
        if not column.spin_time_remaining:
            continue

        spin_speed = calc_spin_speed(
            column.spin_duration,
            column.spin_time_remaining,
            snap_threshold=0.15,
        )
        column.cursor -= spin_speed * delta_time
        column.spin_time_remaining = max(0.0, column.spin_time_remaining - delta_time)

        if spin_speed == 0.0:
            column.spin_time_remaining = 0.0

    fill_screen_background(ctx.term, ctx.screen, BACKGROUND_COLOR)

    for n, column in enumerate(ctx.slots.columns):
        # --- Slot column rendering ---
        spacing = 5
        column_x = 5 + n * spacing
        column_y = 5
        x = 5 + n * spacing
        is_selected = ctx.slots.selected_column_index == n
        # render_column(x, 5, column, is_selected)

        neighbor_count = 3
        for row_offset in range(-neighbor_count, neighbor_count + 1):
            is_cursor_row = row_offset == 0

            card_index = wrap_cursor(int(column.cursor + row_offset), column.cards)
            rich_text = card_rich_text(column.cards[card_index])

            if is_selected and not slots_spinning:
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

    update_fps_counter(ctx.fps_counter, delta_time)

    # FPS Display
    fps_text = f"{ctx.fps_counter.ema:5.1f} FPS"
    x = max(0, ctx.screen.width - len(fps_text) - 1)
    print_at(x, 0, RichText(fps_text, RGB.WHITE))

    flush_diffs(ctx.term, buffer_diff(ctx.screen))
    return ProgramStatus.RUNNING


def main():
    foo = [PlayingCard(Suit.SPADE, Rank.R_A) for _ in range(52)]
    term = Terminal()
    screen = Screen(term.width, term.height)
    ctx = Context(
        term=term,
        screen=screen,
        game_state=GameState.READY_TO_SPIN_SLOTS,
        slots=Slots(
            columns=[
                Column(0, foo),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
            ]
        ),
        cards_in_hand=[],
        fps_counter=FPSCounter(),
    )

    for column in ctx.slots.columns:
        random.shuffle(column.cards)

    # print_at = partial(verbose_print_at, term, screen)
    fps_limiter = create_fps_limiter(144)

    with (
        term.cbreak(),
        term.hidden_cursor(),
        term.fullscreen(),
    ):
        dt: float = 0.01666

        while True:
            if input := map_input(term.inkey(0.0)):
                action = resolve_input(ctx, input)

                if action == Action.QUIT_GAME:
                    exit()

                elif action == Action.SPIN_SLOTS:
                    start_slots_spin(ctx)
                    ctx.game_state = GameState.SPINNING_SLOTS

                elif action == Action.SLOTS_MOVE_SELECTION_LEFT:
                    ctx.slots.selected_column_index -= 1

                elif action == Action.SLOTS_MOVE_SELECTION_RIGHT:
                    ctx.slots.selected_column_index += 1

                elif action == Action.SLOTS_PICK_CARD:
                    selected_column: Column = ctx.slots.columns[ctx.slots.selected_column_index]
                    selected_card_index: int = wrap_cursor(
                        int(selected_column.cursor), selected_column.cards
                    )

                    ctx.cards_in_hand.append(selected_column.cards[selected_card_index])
                    ctx.game_state = GameState.READY_TO_SPIN_SLOTS

            # --- Logic tick ---
            if ctx.game_state == GameState.SPINNING_SLOTS:
                spin_finished = tick_slots_spin(ctx, dt)

                if spin_finished:
                    ctx.game_state = GameState.POST_SPIN_COLUMN_PICKING

            update_fps_counter(ctx.fps_counter, dt)

            # --- Rendering ---
            draw_instructions: list[DrawInstruction] = []

            draw_instructions.extend(render_slots(ctx))

            fps_text = f"{ctx.fps_counter.ema:5.1f} FPS"
            x = ctx.screen.width - len(fps_text) - 1
            draw_instructions.append(
                DrawInstruction(
                    x,
                    0,
                    RichText(
                        fps_text,
                        lerp_rgb(RGB.GREEN, RGB.WHITE, 0.6),
                    ),
                )
            )

            draw_instructions.append(
                DrawInstruction(
                    0,
                    23,
                    RichText(
                        str(ctx.game_state.name),
                        lerp_rgb(RGB.RED, RGB.WHITE, 0.6),
                    ),
                )
            )

            # temp hand rendering
            for n, card in enumerate(ctx.cards_in_hand):
                rich_text = card_rich_text(card)
                rich_text.bg_color *= 1.0 - 0.1 * n
                rich_text.text_color *= 1.0 - 0.1 * n

                print_at(term, screen, 40, 5 + n, rich_text)

            for instruction in draw_instructions:
                print_at(term, screen, instruction.x, instruction.y, instruction.rich_text)
            flush_diffs(ctx.term, buffer_diff(ctx.screen))

            # Special debug line
            print_at(term, screen, 35, 23, ctx.debug_text)

            dt = fps_limiter()
