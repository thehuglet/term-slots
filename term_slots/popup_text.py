from dataclasses import dataclass

from term_slots.context import elapsed_fraction
from term_slots.curves import ease_in
from term_slots.ezterm import DrawCall, RichText, mul_alpha


@dataclass
class TextPopup:
    x: int
    y: int
    text: RichText
    duration_sec: float
    start_timestamp: float


def render_all_text_popups(all_text_popups: list[TextPopup], game_time: float) -> list[DrawCall]:
    draw_calls: list[DrawCall] = []

    for popup in all_text_popups:
        t: float = elapsed_fraction(game_time, popup.start_timestamp, popup.duration_sec)

        if t >= 1.0:
            continue

        rich_text: RichText = popup.text

        rich_text = mul_alpha(rich_text, _calc_popup_alpha(t))

        draw_calls.append(
            DrawCall(
                popup.x,
                popup.y,
                rich_text,
            )
        )

    return draw_calls


def _calc_popup_alpha(t: float) -> float:
    ramp_frac: float = 0.05

    if t < ramp_frac:
        local_t = t / ramp_frac
        return 0.5 + 0.5 * local_t

    # Decay phase
    decay_t = (t - ramp_frac) / (1 - ramp_frac)

    return 1.0 - ease_in(decay_t)
