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
    HAND_SELECT_CARD = auto()
    HAND_DESELECT_CARD = auto()


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
        first_column_is_selected: bool = ctx.slots.selected_column_index == 0
        last_column_is_selected: bool = (
            ctx.slots.selected_column_index == len(ctx.slots.columns) - 1
        )

        if input == Input.CONFIRM:
            return Action.SLOTS_PICK_CARD

        elif input == Input.LEFT and not first_column_is_selected:
            return Action.SLOTS_MOVE_SELECTION_LEFT

        elif input == Input.RIGHT and not last_column_is_selected:
            return Action.SLOTS_MOVE_SELECTION_RIGHT

    if ctx.game_state == GameState.SELECTING_HAND_CARDS:
        cursor_is_on_first_card: bool = ctx.hand.cursor_pos == 0
        cursor_is_on_last_card: bool = ctx.hand.cursor_pos == len(ctx.hand.cards) - 1
        card_at_cursor_is_selected: bool = ctx.hand.cursor_pos in ctx.hand.selected_card_indexes

        if input == Input.SWAP:
            return Action.FOCUS_SLOTS

        if input == Input.LEFT and not cursor_is_on_first_card:
            return Action.HAND_MOVE_SELECTION_LEFT

        elif input == Input.RIGHT and not cursor_is_on_last_card:
            return Action.HAND_MOVE_SELECTION_RIGHT

        elif input == Input.UP and not card_at_cursor_is_selected:
            return Action.HAND_SELECT_CARD

        elif input == Input.DOWN and card_at_cursor_is_selected:
            return Action.HAND_DESELECT_CARD

    return None
