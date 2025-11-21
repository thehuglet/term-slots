from enum import Enum, auto

from blessed.keyboard import Keystroke

from term_slots import config
from term_slots.context import Context
from term_slots.game_state import GameState
from term_slots.slots import Column, calc_column_spin_duration_sec


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


def get_action(ctx: Context, input: Input) -> Action | None:
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


def resolve_action(ctx: Context, action: Action, config: config.Config):
    """This mutates `ctx` directly"""

    match action:
        case Action.QUIT_GAME:
            exit()

        case Action.SPIN_SLOTS:
            for col_index, selected_col in enumerate(ctx.slots.columns):
                spin_duration = calc_column_spin_duration_sec(col_index, config)
                selected_col.spin_duration = spin_duration
                selected_col.spin_time_remaining = spin_duration

            ctx.game_state = GameState.SPINNING_SLOTS

        case Action.SLOTS_MOVE_SELECTION_LEFT:
            ctx.slots.selected_column_index -= 1

        case Action.SLOTS_MOVE_SELECTION_RIGHT:
            ctx.slots.selected_column_index += 1

        case Action.SLOTS_PICK_CARD:
            selected_col: Column = ctx.slots.columns[ctx.slots.selected_column_index]
            selected_card_index: int = int(selected_col.cursor) % len(selected_col.cards)

            ctx.hand.cards.append(selected_col.cards[selected_card_index])
            ctx.game_state = GameState.READY_TO_SPIN_SLOTS

        case Action.FOCUS_SLOTS:
            ctx.game_state = GameState.READY_TO_SPIN_SLOTS

        case Action.FOCUS_HAND:
            ctx.game_state = GameState.SELECTING_HAND_CARDS

        case Action.HAND_MOVE_SELECTION_LEFT:
            ctx.hand.cursor_pos -= 1

        case Action.HAND_MOVE_SELECTION_RIGHT:
            ctx.hand.cursor_pos += 1

        case Action.HAND_SELECT_CARD:
            ctx.hand.selected_card_indexes.add(ctx.hand.cursor_pos)

        case Action.HAND_DESELECT_CARD:
            ctx.hand.selected_card_indexes.remove(ctx.hand.cursor_pos)
