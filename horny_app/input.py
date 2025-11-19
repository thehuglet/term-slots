from dataclasses import dataclass
from enum import Enum, auto

from blessed.keyboard import Keystroke

from horny_app.context import Context, GameState


class Input(Enum):
    QUIT = auto()
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    CONFIRM = auto()


class Action(Enum):
    QUIT_GAME = auto()
    SPIN_SLOTS = auto()


@dataclass
class ValidatedInputAction:
    input_action: Input
    is_valid: bool


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
        if input == Input.CONFIRM:
            return Action.SPIN_SLOTS

    return None

    # if input_action == Input.QUIT:
    #     # Always valid
    #     return ValidatedInputAction(input_action, True)

    # if ctx.game_state == GameState.POST_SPIN_COLUMN_PICKING:
    #     first_column_selected = ctx.slots.selected_column_index == 0
    #     last_column_selected = ctx.slots.selected_column_index == len(ctx.slots.columns) - 1

    #     if input_action == Input.LEFT and not first_column_selected:
    #         return ValidatedInputAction(input_action, True)
    #     if input_action == Input.RIGHT and not last_column_selected:
    #         return ValidatedInputAction(input_action, True)

    # return ValidatedInputAction(input_action, False)
