from enum import Enum, auto


class GameState(Enum):
    READY_TO_SPIN_SLOTS = auto()
    SPINNING_SLOTS = auto()
    SLOTS_POST_SPIN_COLUMN_PICKING = auto()
    SELECTING_HAND_CARDS = auto()
    BURN_MODE = auto()
    FORCED_BURN_MODE = auto()
