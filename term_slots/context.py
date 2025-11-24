from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from term_slots.ezterm import FPSCounter, RichText, Screen
    from term_slots.game_state import GameState
    from term_slots.hand import Hand
    from term_slots.playing_card import PlayingCard
    from term_slots.popup_text import TextPopup
    from term_slots.slots import Slots


@dataclass
class Context:
    screen: Screen
    game_time: float
    game_state: GameState
    coins: int
    score: int
    slots: Slots
    hand: Hand
    forced_burn_replacement_card: PlayingCard
    all_text_popups: list[TextPopup]
    fps_counter: FPSCounter
    debug_text: str | RichText = ""


def elapsed_fraction(game_time: float, start_timestamp: float, duration: float) -> float:
    """
    Returns a value in [0, 1] representing how far through the effect we are.
    >1 means the effect is finished.
    """
    if duration <= 0.0:
        return 1.0  # instantly expired
    t = (game_time - start_timestamp) / duration
    return max(0.0, min(1.0, t))
