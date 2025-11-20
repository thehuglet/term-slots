from enum import Enum, auto


class GameState(Enum):
    READY_TO_SPIN_SLOTS = auto()
    SPINNING_SLOTS = auto()
    POST_SPIN_COLUMN_PICKING = auto()
