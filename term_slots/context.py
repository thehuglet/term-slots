from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from term_slots.ezterm import FPSCounter, RichText
    from term_slots.game_state import GameState
    from term_slots.hand import Hand
    from term_slots.playing_card import PlayingCard
    from term_slots.slots import Slots


@dataclass
class Context:
    game_time: float
    game_state: GameState
    coins: int
    score: int
    slots: Slots
    hand: Hand
    forced_burn_replacement_card: PlayingCard
    fps_counter: FPSCounter
    debug_text: str | RichText = ""
