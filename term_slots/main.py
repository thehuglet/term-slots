import random

from blessed import Terminal

from term_slots.config import Config
from term_slots.context import Context
from term_slots.ezterm import (
    BACKGROUND_COLOR,
    RGB,
    DrawInstruction,
    FPSCounter,
    RichText,
    Screen,
    buffer_diff,
    create_fps_limiter,
    fill_screen_background,
    flush_diffs,
    lerp_rgb,
    print_at,
    update_fps_counter,
)
from term_slots.game_state import GameState
from term_slots.hand import Hand
from term_slots.input import Action, map_input, resolve_input
from term_slots.playing_card import (
    FULL_DECK,
    PlayingCard,
    Rank,
    Suit,
    card_rich_text_big,
)
from term_slots.slots import (
    Column,
    Slots,
    render_slots,
    start_slots_spin,
    tick_slots_spin,
    wrap_cursor,
)


def main():
    aces_of_spades_deck = [PlayingCard(Suit.SPADE, Rank.ACE) for _ in range(52)]
    term = Terminal()
    screen = Screen(term.width, term.height)

    config = Config()

    ctx = Context(
        term=term,
        screen=screen,
        game_state=GameState.READY_TO_SPIN_SLOTS,
        slots=Slots(
            columns=[
                Column(0, aces_of_spades_deck),
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
        hand=Hand(
            cards=[],
            cursor_pos=0,
            selected_card_indexes=[],
        ),
        fps_counter=FPSCounter(),
    )

    for column in ctx.slots.columns:
        random.shuffle(column.cards)

    fps_limiter = create_fps_limiter(144)

    with (
        term.cbreak(),
        term.hidden_cursor(),
        term.fullscreen(),
    ):
        dt: float = 0.01666

        while True:
            dt *= config.game_speed

            if input := map_input(term.inkey(0.0)):
                action: Action | None = resolve_input(ctx, input)

                if action == Action.QUIT_GAME:
                    exit()

                elif action == Action.SPIN_SLOTS:
                    start_slots_spin(
                        ctx,
                        config.slots_spin_duration_sec,
                        config.slots_spin_duration_stagger_sec_min,
                        config.slots_spin_duration_stagger_ratio,
                        config.slots_spin_duration_stagger_diminishing_ratio,
                    )
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

                    ctx.hand.cards.append(selected_column.cards[selected_card_index])
                    ctx.game_state = GameState.READY_TO_SPIN_SLOTS

                elif action == Action.FOCUS_SLOTS:
                    ctx.game_state = GameState.READY_TO_SPIN_SLOTS

                elif action == Action.FOCUS_HAND:
                    ctx.game_state = GameState.SELECTING_HAND_CARDS

            # --- Logic tick ---
            if ctx.game_state == GameState.SPINNING_SLOTS:
                spin_finished = tick_slots_spin(ctx, dt, config.slots_max_spin_speed)

                if spin_finished:
                    ctx.game_state = GameState.SLOTS_POST_SPIN_COLUMN_PICKING

            update_fps_counter(ctx.fps_counter, dt / config.game_speed)

            # --- Rendering ---
            draw_instructions: list[DrawInstruction] = []

            draw_instructions.extend(render_slots(ctx, 5, 6))

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
                    0,
                    RichText(
                        str(ctx.game_state.name),
                        lerp_rgb(RGB.RED, RGB.WHITE, 0.6),
                    ),
                )
            )

            fill_screen_background(ctx.term, ctx.screen, BACKGROUND_COLOR)

            # temp hand rendering
            for n, card in enumerate(ctx.hand.cards):
                x = 5
                y = 22

                alpha_multiplier = 0.4

                if ctx.game_state == GameState.SELECTING_HAND_CARDS:
                    alpha_multiplier = 0.8

                rich_text_batch = card_rich_text_big(card)

                for y_offset, rich_text in enumerate(rich_text_batch):
                    rich_text.bg_color *= alpha_multiplier
                    rich_text.text_color *= alpha_multiplier

                    draw_instructions.append(
                        DrawInstruction(
                            x + n * 4,
                            y + y_offset,
                            rich_text,
                        )
                    )

            for instruction in draw_instructions:
                print_at(term, screen, instruction.x, instruction.y, instruction.rich_text)
            flush_diffs(ctx.term, buffer_diff(ctx.screen))

            # Special debug line
            print_at(term, screen, 35, 23, ctx.debug_text)

            dt = fps_limiter()
