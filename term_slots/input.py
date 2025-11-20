from enum import Enum, auto

from blessed.keyboard import Keystroke

from term_slots.context import Context
from term_slots.game_state import GameState


class Input(Enum):
    QUIT = auto()
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    CONFIRM = auto()
    SWAP = auto()


class Action(Enum):
    QUIT_GAME = auto()
    SPIN_SLOTS = auto()
    SLOTS_MOVE_SELECTION_LEFT = auto()
    SLOTS_MOVE_SELECTION_RIGHT = auto()
    SLOTS_PICK_CARD = auto()
    FOCUS_SLOTS = auto()
    FOCUS_HAND = auto()
    HAND_MOVE_SELECTION_LEFT = auto()
    HAND_MOVE_SELECTION_RIGHT = auto()


KEYMAP: dict[str, Input] = {
    "q": Input.QUIT,
    "w": Input.UP,
    "a": Input.LEFT,
    "s": Input.DOWN,
    "d": Input.RIGHT,
    "KEY_UP": Input.UP,
    "KEY_LEFT": Input.LEFT,
    "KEY_DOWN": Input.DOWN,
    "KEY_RIGHT": Input.RIGHT,
    "KEY_ENTER": Input.CONFIRM,
    "KEY_TAB": Input.SWAP,
}


def map_input(keystroke: Keystroke) -> Input | None:
    if action := KEYMAP.get(str(keystroke)):
        return action
    if keystroke.name is not None:
        return KEYMAP.get(keystroke.name)
    return None


def resolve_input(ctx: Context, input: Input) -> Action | None:
    if input == Input.QUIT:
        return Action.QUIT_GAME

    if ctx.game_state == GameState.READY_TO_SPIN_SLOTS:
        any_cards_in_hand: bool = len(ctx.hand.cards) > 0

        if input == Input.CONFIRM:
            return Action.SPIN_SLOTS

        if input == Input.SWAP and any_cards_in_hand:
            return Action.FOCUS_HAND

    elif ctx.game_state == GameState.SLOTS_POST_SPIN_COLUMN_PICKING:
        is_first_column_selected: bool = ctx.slots.selected_column_index == 0
        is_last_column_selected: bool = (
            ctx.slots.selected_column_index == len(ctx.slots.columns) - 1
        )

        if input == Input.CONFIRM:
            return Action.SLOTS_PICK_CARD

        elif input == Input.LEFT and not is_first_column_selected:
            return Action.SLOTS_MOVE_SELECTION_LEFT

        elif input == Input.RIGHT and not is_last_column_selected:
            return Action.SLOTS_MOVE_SELECTION_RIGHT

    if ctx.game_state == GameState.SELECTING_HAND_CARDS:
        is_cursor_on_first_card: bool = ctx.hand.cursor_pos == 0
        is_cursor_on_last_card: bool = ctx.hand.cursor_pos == len(ctx.hand.cards) - 1

        if input == Input.SWAP:
            return Action.FOCUS_SLOTS

        if input == Input.LEFT and is_cursor_on_first_card:
            return Action.HAND_MOVE_SELECTION_LEFT

        elif input == Input.RIGHT and is_cursor_on_last_card:
            return Action.HAND_MOVE_SELECTION_RIGHT

    return None
