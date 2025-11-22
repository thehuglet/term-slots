import math

from term_slots.ezterm import RGB, DrawCall, RichText, lerp_rgb
from term_slots.playing_card import PlayingCard, render_card_big


def render_forced_burn_replacement_card(
    x: int,
    y: int,
    card: PlayingCard,
    game_time: float,
) -> list[DrawCall]:
    draw_calls: list[DrawCall] = []

    card_draw_calls: list[DrawCall] = render_card_big(x, y, card)

    for draw_call in card_draw_calls:
        rt: RichText = draw_call.rich_text

        # Green sinewave highlight
        if rt.bg_color:
            amplitude: float = 1.0
            frequency: float = 5.0
            phase_offset: float = 0.3

            t: float = 0.5 + 0.5 * amplitude * math.sin(frequency * game_time + phase_offset)

            rt.bg_color = lerp_rgb(rt.bg_color, RGB.GREEN, t * 0.7)
            rt.text_color = lerp_rgb(rt.text_color, RGB.GREEN, t * 0.4)

        draw_call.rich_text = rt

    draw_calls.extend(card_draw_calls)
    return draw_calls
