from dataclasses import dataclass
from typing import TYPE_CHECKING

from blessed import Terminal

from horny_app.playing_card import PlayingCard

if TYPE_CHECKING:
    from horny_app.ezterm import FPSCounter, RichText, Screen
    from horny_app.game_state import GameState
    from horny_app.slots import Slots


@dataclass
class Context:
    term: Terminal
    screen: Screen
    slots: Slots
    cards_in_hand: list[PlayingCard]
    game_state: GameState
    fps_counter: FPSCounter
    debug_text: str | RichText = ""
