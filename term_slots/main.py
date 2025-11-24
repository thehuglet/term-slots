import random
from typing import Never

from blessed import Terminal
from blessed.keyboard import Keystroke

from term_slots.config import Config
from term_slots.context import Context, elapsed_fraction
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
from term_slots.hand import Hand, get_selected_cards_in_hand, render_hand
from term_slots.input import get_action, map_input, resolve_action
from term_slots.playing_card import (
    FULL_DECK,
    PlayingCard,
    Rank,
    Suit,
)
from term_slots.poker_hand import POKER_HAND_NAMES, eval_poker_hand
from term_slots.popup_text import render_all_text_popups
from term_slots.slots import (
    Column,
    Slots,
    calc_spin_cost,
    render_slots,
    spin_slots_and_check_finished,
)


def tick(dt: float, ctx: Context, term: Terminal, config: Config) -> None:
    if (term.width, term.height) != (ctx.screen.width, ctx.screen.height):
        ctx.screen = Screen(term.width, term.height)
        fill_screen_background(ctx.screen.new_buffer, BACKGROUND_COLOR)

    # --- Inputs ---
    key_event: Keystroke = term.inkey(timeout=0.0)

    # Mouse hover memory
    if key_event.name and key_event.name == "MOUSE_MOTION":
        ctx.last_mouse_pos = key_event.mouse_xy

    if input := map_input(key_event):
        if action := get_action(ctx, input):
            resolve_action(ctx, action, config)

    # --- Game logic ---
    ctx.game_time += dt

    if ctx.game_state == GameState.SPINNING_SLOTS:
        spin_finished: bool = spin_slots_and_check_finished(ctx, dt, config.slots_max_spin_speed)

        if spin_finished:
            ctx.game_state = GameState.SLOTS_POST_SPIN_COLUMN_PICKING

    # Cleanup all finished popups
    ctx.all_text_popups = [
        p
        for p in ctx.all_text_popups
        if elapsed_fraction(ctx.game_time, p.start_timestamp, p.duration_sec) < 1.0
    ]

    update_fps_counter(ctx.fps_counter, dt / config.game_speed)

    # --- Rendering ---
    draw_calls: list[DrawCall] = []

    # Slots rendering
    draw_calls.extend(render_slots(13, 6, ctx, ctx.game_time))

    # Current hand display rendering
    selected_cards: list[PlayingCard] = [
        c.card for c in get_selected_cards_in_hand(ctx.hand.cards_in_hand)
    ]
    if selected_cards:
        poker_hand, _ = eval_poker_hand(selected_cards)

        draw_calls.append(
            DrawCall(
                5,
                17,
                RichText(POKER_HAND_NAMES[poker_hand]),
            )
        )

    # Spin cost display rendering
    spin_cost: int = calc_spin_cost(ctx.slots.spin_count)
    draw_calls.append(DrawCall(5, 12, RichText(f"Spin cost: {spin_cost}", RGB.WHITE)))

    # Score display rendering
    draw_calls.append(DrawCall(5, 13, RichText(f"Score: {ctx.score}", RGB.LIGHT_BLUE)))

    # Coins display rendering
    coins_text_color: RGB = lerp_rgb(RGB.GOLD, RGB.ORANGE, 0.4)
    draw_calls.append(DrawCall(5, 14, RichText(f"Coins: {ctx.coins}", coins_text_color)))

    # FPS display rendering
    fps_text = f"{ctx.fps_counter.ema:5.1f} FPS"
    x = ctx.screen.width - len(fps_text) - 1
    draw_calls.append(
        DrawCall(
            x,
            1,
            RichText(
                fps_text,
                lerp_rgb(RGB.GREEN, RGB.WHITE, 0.6),
            ),
        )
    )

    # Hand rendering
    hand_is_focused: bool = ctx.game_state in (
        GameState.SELECTING_HAND_CARDS,
        GameState.BURN_MODE,
        GameState.FORCED_BURN_MODE,
        GameState.SCORING_PLAYED_HAND,
    )
    burn_mode_active: bool = ctx.game_state in (
        GameState.BURN_MODE,
        GameState.FORCED_BURN_MODE,
    )
    draw_calls.extend(
        render_hand(
            13,
            20,
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
                5, 20, ctx.forced_burn_replacement_card, ctx.game_time
            )
        )

    # Misc debug line rendering
    if isinstance(ctx.debug_text, str):
        ctx.debug_text = RichText(ctx.debug_text, RGB.WHITE * 0.5)
    draw_calls.append(DrawCall(35, 0, ctx.debug_text))

    # Text popup rendering
    draw_calls.extend(render_all_text_popups(ctx.all_text_popups, ctx.game_time))

    # Debug game state display rendering
    game_state_text = str(ctx.game_state.name)
    x = ctx.screen.width - len(game_state_text) - 1
    draw_calls.append(
        DrawCall(
            x,
            0,
            RichText(game_state_text, lerp_rgb(RGB.RED, RGB.WHITE, 0.6)),
        )
    )

    # REALTIME MOUSE POSITION EXPERIMENT
    # draw_calls.append(
    #     DrawCall(ctx.last_mouse_pos[0], ctx.last_mouse_pos[1], RichText(" ", bg_color=RGB.WHITE))
    # )

    for draw_call in draw_calls:
        print_at(term, ctx.screen, draw_call.x, draw_call.y, draw_call.rich_text)
    flush_diffs(term, buffer_diff(ctx.screen))


def main() -> Never:
    # aces_of_spades_deck = [PlayingCard(Suit.SPADE, Rank.ACE) for _ in range(52)]
    term = Terminal()
    config = Config()
    ctx = Context(
        last_mouse_pos=(0, 0),
        screen=Screen(term.width, term.height),
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
            ],
        ),
        hand=Hand(
            hand_size=10,
            cards_in_hand=[],
            cursor_pos=0,
        ),
        all_text_popups=[],
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
        term.mouse_enabled(report_motion=True),
    ):
        dt: float = 0.0

        fill_screen_background(ctx.screen.new_buffer, BACKGROUND_COLOR)

        while True:
            dt *= config.game_speed
            tick(dt, ctx, term, config)
            dt = fps_limiter()
