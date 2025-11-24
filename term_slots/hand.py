import math
from dataclasses import dataclass

from term_slots.config import Config
from term_slots.ezterm import RGB, DrawCall, RichText, lerp_rgb, mul_alpha
from term_slots.playing_card import PLAYING_CARD_WIDTH, PlayingCard, render_card_big

BURN_HIGHLIGHT_COLOR: RGB = lerp_rgb(RGB.ORANGE, RGB.RED, 0.7)


@dataclass
class Hand:
    hand_size: int
    cards_in_hand: list[CardInHand]
    cursor_pos: int


@dataclass
class CardInHand:
    card: PlayingCard
    is_selected: bool


def get_selected_cards_in_hand(cards_in_hand: list[CardInHand]) -> list[CardInHand]:
    return [card_in_hand for card_in_hand in cards_in_hand if card_in_hand.is_selected]


def get_not_selected_cards_in_hand(cards_in_hand: list[CardInHand]) -> list[CardInHand]:
    return [card_in_hand for card_in_hand in cards_in_hand if not card_in_hand.is_selected]


def render_hand(
    x: int,
    y: int,
    hand: Hand,
    config: Config,
    game_time: float,
    hand_is_focused: bool,
    burn_mode_active: bool,
) -> list[DrawCall]:
    draw_calls: list[DrawCall] = []
    card_x_spacing: int = PLAYING_CARD_WIDTH + config.hand_card_x_spacing

    # Card counter
    card_count: int = len(hand.cards_in_hand)
    draw_calls.append(
        DrawCall(
            x + hand.hand_size * card_x_spacing,
            y + 4,
            RichText(f"{card_count}/{hand.hand_size}".rjust(5)),
        )
    )

    for card_index, card_in_hand in enumerate(hand.cards_in_hand):
        card: PlayingCard = card_in_hand.card
        cursor_on_card: bool = hand.cursor_pos == card_index

        card_x: int = x + card_index * card_x_spacing
        card_y: int = y

        amplitude: float = 1.0
        frequency: float = 5.0
        burn_sinewave: float = 0.5 + 0.5 * amplitude * math.sin(frequency * game_time)

        # Cursor arrow indicator
        if cursor_on_card and hand_is_focused:
            arrow_x: int = card_x + 1
            arrow_y: int = card_y + 3
            text_color: RGB = (
                lerp_rgb(RGB.WHITE * 0.7, BURN_HIGHLIGHT_COLOR, burn_sinewave)
                if burn_mode_active
                else lerp_rgb(RGB.GOLD, RGB.WHITE, 0.5) * 0.8
            )
            draw_calls.append(DrawCall(arrow_x, arrow_y, RichText("▴", text_color)))

        # Selected card Y offset
        if card_in_hand.is_selected and not burn_mode_active:
            card_y -= 1

        card_draw_calls: list[DrawCall] = render_card_big(card_x, card_y, card)

        for draw_call_index, draw_call in enumerate(card_draw_calls):
            rt: RichText = draw_call.rich_text

            # Base card alpha
            if rt.bg_color:
                rt.bg_color *= 0.6
            rt.text_color *= 0.8

            # Selected card alpha boost
            if card_in_hand.is_selected and not burn_mode_active:
                if rt.bg_color:
                    rt.bg_color *= 1.5
                rt.text_color *= 1.5

            # Lower alpha when hand is not focused
            if not hand_is_focused:
                rt = mul_alpha(draw_call.rich_text, 0.5)

            # Cursor on hand burn mode highlight
            if cursor_on_card and burn_mode_active and rt.bg_color:
                rt.bg_color = lerp_rgb(rt.bg_color, BURN_HIGHLIGHT_COLOR, burn_sinewave * 0.7)
                rt.text_color = lerp_rgb(rt.text_color, BURN_HIGHLIGHT_COLOR, burn_sinewave * 0.3)

            # Cursor on hand bg highlight
            if cursor_on_card and hand_is_focused and not burn_mode_active and rt.bg_color:
                rt.bg_color = lerp_rgb(RGB.WHITE, RGB.GOLD, 0.5)

            card_draw_calls[draw_call_index].rich_text = rt

        draw_calls.extend(card_draw_calls)

    return draw_calls
