import random

from blessed import Terminal

from horny_app.config import Config
from horny_app.context import Context
from horny_app.ezterm import (
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
from horny_app.game_state import GameState
from horny_app.input import Action, map_input, resolve_input
from horny_app.playing_card import (
    FULL_DECK,
    PlayingCard,
    Rank,
    Suit,
    card_rich_text,
    card_rich_text_big,
)
from horny_app.slots import (
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
            dt *= config.game_speed

            if input := map_input(term.inkey(0.0)):
                action = resolve_input(ctx, input)

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

                    ctx.cards_in_hand.append(selected_column.cards[selected_card_index])
                    ctx.game_state = GameState.READY_TO_SPIN_SLOTS

            # --- Logic tick ---
            if ctx.game_state == GameState.SPINNING_SLOTS:
                spin_finished = tick_slots_spin(ctx, dt, config.slots_max_spin_speed)

                if spin_finished:
                    ctx.game_state = GameState.POST_SPIN_COLUMN_PICKING

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
            for n, card in enumerate(ctx.cards_in_hand):
                x = 5
                y = 22

                # if n % 2 == 0:
                #     alpha_multiplier = 0.8
                # else:
                #     alpha_multiplier = 0.6
                alpha_multiplier = 0.8

                if n == 2:
                    alpha_multiplier = 1.0
                    y -= 1

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
