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
from term_slots.poker_hand import POKER_HAND_NAMES
from term_slots.slots import (
    Column,
    Slots,
    calc_spin_cost,
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
        spin_finished: bool = spin_slots_and_check_finished(ctx, dt, config.slots_max_spin_speed)

        if spin_finished:
            ctx.game_state = GameState.SLOTS_POST_SPIN_COLUMN_PICKING

    update_fps_counter(ctx.fps_counter, dt / config.game_speed)

    # --- Rendering ---
    draw_calls: list[DrawCall] = []

    # Hack to fix shitty terminal behavior for bg filling at the start
    for row in range(100):
        draw_calls.append(DrawCall(0, row, RichText("-" * 300, bg_color=RGB.BLACK)))
        if dt > 0.0:
            draw_calls.append(DrawCall(0, row, RichText(" " * 300, bg_color=RGB.BLACK)))

    fill_screen_background(screen.new_buffer, BACKGROUND_COLOR)

    # Slots rendering
    draw_calls.extend(render_slots(13, 6, ctx, ctx.game_time))

    # Current hand display rendering
    if poker_hand := ctx.hand.current_poker_hand:
        draw_calls.append(
            DrawCall(
                5,
                23,
                RichText(POKER_HAND_NAMES[poker_hand]),
            )
        )

    # Score display rendering
    draw_calls.append(DrawCall(5, 14, RichText(f"Score: {ctx.score}", RGB.LIGHT_BLUE)))

    # Coins display rendering
    coins_text_color: RGB = lerp_rgb(RGB.GOLD, RGB.ORANGE, 0.4)
    draw_calls.append(DrawCall(5, 15, RichText(f"Coins: {ctx.coins}", coins_text_color)))

    # Spin cost display rendering
    spin_cost: int = calc_spin_cost(ctx.slots.spin_count)
    draw_calls.append(DrawCall(5, 12, RichText(f"Spin cost: {spin_cost}")))

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
        coins=500,
        score=0,
        slots=Slots(
            spin_count=0,
            columns=[
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
                # Column(0, FULL_DECK.copy()),
            ],
        ),
        hand=Hand(
            hand_size=10,
            cards=[
                # PlayingCard(Suit.HEART, Rank.ACE),
                # PlayingCard(Suit.HEART, Rank.ACE),
                # PlayingCard(Suit.SPADE, Rank.ACE),
                # PlayingCard(Suit.SPADE, Rank.ACE),
                # PlayingCard(Suit.SPADE, Rank.ACE),
                # PlayingCard(Suit.SPADE, Rank.ACE),
                # PlayingCard(Suit.DIAMOND, Rank.NUM_5),
                # PlayingCard(Suit.SPADE, Rank.NUM_5),
                # PlayingCard(Suit.SPADE, Rank.NUM_5),
                # PlayingCard(Suit.SPADE, Rank.NUM_3),
                # PlayingCard(Suit.SPADE, Rank.NUM_2),
                # PlayingCard(Suit.SPADE, Rank.QUEEN),
            ],
            cursor_pos=0,
            selected_card_indexes=set(),
            current_poker_hand=None,
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
        dt: float = 0.0

        while True:
            dt *= config.game_speed
            tick(dt, ctx, term, screen, config)
            dt = fps_limiter()
