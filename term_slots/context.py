from dataclasses import dataclass
from typing import TYPE_CHECKING

from blessed import Terminal

if TYPE_CHECKING:
    from term_slots.ezterm import FPSCounter, RichText, Screen
    from term_slots.game_state import GameState
    from term_slots.hand import Hand
    from term_slots.slots import Slots


@dataclass
class Context:
    term: Terminal
    screen: Screen
    slots: Slots
    hand: Hand
    game_state: GameState
    fps_counter: FPSCounter
    debug_text: str | RichText = ""
