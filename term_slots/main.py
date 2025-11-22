import random
from typing import Never

from blessed import Terminal

from term_slots.config import Config
from term_slots.context import Context
from term_slots.ezterm import (
    BACKGROUND_COLOR,
    RGB,
    DrawCall,
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
from term_slots.forced_burn import render_forced_burn_replacement_card
from term_slots.game_state import GameState
from term_slots.hand import Hand, render_hand
from term_slots.input import get_action, map_input, resolve_action
from term_slots.playing_card import (
    FULL_DECK,
    PlayingCard,
    Rank,
    Suit,
)
from term_slots.slots import (
    Column,
    Slots,
    render_slots,
    spin_slots_and_check_finished,
)


def tick(dt: float, ctx: Context, term: Terminal, screen: Screen, config: Config):
    # --- Inputs ---
    if input := map_input(term.inkey(timeout=0.0)):
        if action := get_action(ctx, input):
            resolve_action(ctx, action, config)

    # --- Game logic ---
    ctx.game_time += dt

    if ctx.game_state == GameState.SPINNING_SLOTS:
        spin_finished = spin_slots_and_check_finished(ctx, dt, config.slots_max_spin_speed)

        if spin_finished:
            ctx.game_state = GameState.SLOTS_POST_SPIN_COLUMN_PICKING

    update_fps_counter(ctx.fps_counter, dt / config.game_speed)

    # --- Rendering ---
    fill_screen_background(screen.new_buffer, BACKGROUND_COLOR)
    draw_calls: list[DrawCall] = []

    # Slots rendering
    draw_calls.extend(render_slots(13, 6, ctx, ctx.game_time))

    # Hand rendering
    hand_is_focused: bool = ctx.game_state in (
        GameState.SELECTING_HAND_CARDS,
        GameState.BURN_MODE,
        GameState.FORCED_BURN_MODE,
    )
    burn_mode_active: bool = ctx.game_state in (
        GameState.BURN_MODE,
        GameState.FORCED_BURN_MODE,
    )
    draw_calls.extend(
        render_hand(
            13,
            26,
            ctx.hand,
            config,
            ctx.game_time,
            hand_is_focused,
            burn_mode_active,
        )
    )

    # Forced burn mode replacement card rendering
    if ctx.game_state == GameState.FORCED_BURN_MODE:
        draw_calls.extend(
            render_forced_burn_replacement_card(
                5, 26, ctx.forced_burn_replacement_card, ctx.game_time
            )
        )

    # Misc debug line rendering
    if isinstance(ctx.debug_text, str):
        ctx.debug_text = RichText(ctx.debug_text, RGB.WHITE * 0.5)
    draw_calls.append(DrawCall(35, 0, ctx.debug_text))

    # Debug game state display rendering
    draw_calls.append(
        DrawCall(
            0,
            0,
            RichText(str(ctx.game_state.name), lerp_rgb(RGB.RED, RGB.WHITE, 0.6)),
        )
    )

    for draw_call in draw_calls:
        print_at(term, screen, draw_call.x, draw_call.y, draw_call.rich_text)
    flush_diffs(term, buffer_diff(screen))


def main() -> Never:
    # aces_of_spades_deck = [PlayingCard(Suit.SPADE, Rank.ACE) for _ in range(52)]
    term = Terminal()
    screen = Screen(term.width, term.height)
    config = Config()
    ctx = Context(
        game_time=0.0,
        game_state=GameState.READY_TO_SPIN_SLOTS,
        slots=Slots(
            columns=[
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
            ]
        ),
        hand=Hand(
            hand_size=10,
            cards=[
                PlayingCard(Suit.HEART, Rank.NUM_2),
                PlayingCard(Suit.DIAMOND, Rank.NUM_10),
                PlayingCard(Suit.SPADE, Rank.KING),
                PlayingCard(Suit.CLUB, Rank.ACE),
                PlayingCard(Suit.CLUB, Rank.ACE),
                PlayingCard(Suit.CLUB, Rank.ACE),
                PlayingCard(Suit.CLUB, Rank.ACE),
                PlayingCard(Suit.CLUB, Rank.ACE),
                PlayingCard(Suit.CLUB, Rank.ACE),
                PlayingCard(Suit.CLUB, Rank.ACE),
            ],
            cursor_pos=0,
            selected_card_indexes=set(),
        ),
        forced_burn_replacement_card=PlayingCard(Suit.SPADE, Rank.ACE),
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
            tick(dt, ctx, term, screen, config)
            dt = fps_limiter()

            # dt *= config.game_speed

            # # --- Logic tick ---
            # if ctx.game_state == GameState.SPINNING_SLOTS:
            #     spin_finished = spin_slots_and_check_finished(ctx, dt, config.slots_max_spin_speed)

            #     if spin_finished:
            #         ctx.game_state = GameState.SLOTS_POST_SPIN_COLUMN_PICKING

            # # update_fps_counter(ctx.fps_counter, dt / config.game_speed)

            # # --- Rendering ---
            # draw_instructions: list[DrawCall] = []

            # # draw_instructions.extend(render_slots_old(ctx, 5, 6))

            # fps_text = f"{ctx.fps_counter.ema:5.1f} FPS"
            # x = ctx.screen.width - len(fps_text) - 1
            # draw_instructions.append(
            #     DrawCall(
            #         x,
            #         0,
            #         RichText(
            #             fps_text,
            #             lerp_rgb(RGB.GREEN, RGB.WHITE, 0.6),
            #         ),
            #     )
            # )

            # draw_instructions.append(
            #     DrawCall(
            #         0,
            #         0,
            #         RichText(
            #             str(ctx.game_state.name),
            #             lerp_rgb(RGB.RED, RGB.WHITE, 0.6),
            #         ),
            #     )
            # )

            # fill_screen_background(ctx.term, ctx.screen, BACKGROUND_COLOR)

            # # ctx.debug_text = f"{ctx.hand.cursor_pos}"

            # # temp hand rendering
            # x = 5
            # y = 22
            # max_card_count = 10

            # # Draw hand background
            # for row in range(7):
            #     draw_instructions.append(
            #         DrawCall(
            #             x - 2,
            #             y - 2 + row,
            #             RichText(" " * 43, bg_color=lerp_rgb(RGB.GREEN, RGB.WHITE, 0.4) * 0.1),
            #         )
            #     )

            # # Card slot rendering
            # for n in range(max_card_count):
            #     card_slot_x = x + n * 4

            #     for row in range(3):
            #         draw_instructions.append(
            #             DrawCall(
            #                 card_slot_x,
            #                 y + row,
            #                 RichText("   ", bg_color=lerp_rgb(RGB.GREEN, RGB.WHITE, 0.4) * 0.25),
            #             )
            #         )

            # # Actual card rendering
            # for n, card in enumerate(ctx.hand.cards):
            #     if ctx.game_state == GameState.SELECTING_HAND_CARDS:
            #         alpha_multiplier = 0.8

            #     else:
            #         alpha_multiplier = 0.4

            #     rich_text_batch = card_rich_text_big(card)

            #     for y_offset, rich_text in enumerate(rich_text_batch):
            #         assert rich_text.bg_color
            #         rich_text.bg_color *= alpha_multiplier
            #         rich_text.text_color *= alpha_multiplier

            #         selected_y_offset: int = 0
            #         if n in ctx.hand.selected_card_indexes:
            #             selected_y_offset += 1

            #         draw_instructions.append(
            #             DrawCall(
            #                 x + n * 4,
            #                 y + y_offset - selected_y_offset,
            #                 rich_text,
            #             )
            #         )

            #         if (
            #             ctx.game_state == GameState.SELECTING_HAND_CARDS
            #             and ctx.hand.cursor_pos == n
            #         ):
            #             rich_text.bg_color = lerp_rgb(rich_text.bg_color, RGB.GOLD, 0.45)

            #             draw_instructions.append(
            #                 DrawCall(
            #                     x + n * 4,
            #                     y + 3,
            #                     RichText(" ▴ ", lerp_rgb(RGB.WHITE, RGB.GOLD, 0.45)),
            #                 )
            #             )

            # card_count = len(ctx.hand.cards)
            # draw_instructions.append(
            #     DrawCall(x + 35, y + 4, f"{card_count}/{max_card_count}".rjust(5))
            # )

            # for instruction in draw_instructions:
            #     print_at(term, screen, instruction.x, instruction.y, instruction.rich_text)

            # # Special debug line
            # print_at(
            #     term,
            #     screen,
            #     35,
            #     0,
            #     RichText(ctx.debug_text),
            # )

            # flush_diffs(ctx.term, buffer_diff(ctx.screen))
