from dataclasses import dataclass
from enum import Enum, auto

from blessed import Terminal

from horny_app.ezterm import FPSCounter, RichText, Screen
from horny_app.slots import Slots


class GameState(Enum):
    READY_TO_SPIN_SLOTS = auto()
    SPINNING_SLOTS = auto()
    POST_SPIN_COLUMN_PICKING = auto()


@dataclass
class Context:
    term: Terminal
    screen: Screen
    slots: Slots
    game_state: GameState
    fps_counter: FPSCounter
    debug_text: str | RichText = ""
