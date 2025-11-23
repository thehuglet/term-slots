from enum import Enum, auto

from blessed.keyboard import Keystroke

from term_slots import config
from term_slots.context import Context
from term_slots.game_state import GameState
from term_slots.playing_card import RANK_COIN_VALUE, PlayingCard, Rank
from term_slots.poker_hand import POKER_HAND_COIN_VALUE, eval_poker_hand
from term_slots.slots import Column, calc_column_spin_duration_sec, calc_spin_cost


class Input(Enum):
    QUIT = auto()
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    CONFIRM = auto()
    SWAP = auto()
    TOGGLE_BURN_MODE = auto()
    SORT_HAND_BY_RANK = auto()
    SORT_HAND_BY_SUIT = auto()


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
    ENTER_BURN_MODE = auto()
    EXIT_BURN_MODE = auto()
    BURN_CARD = auto()
    BURN_CARD_FORCED = auto()
    PLAY_HAND = auto()
    SORT_HAND_BY_RANK = auto()
    SORT_HAND_BY_SUIT = auto()


KEYMAP: dict[str, Input] = {
    "KEY_UP": Input.UP,
    "KEY_LEFT": Input.LEFT,
    "KEY_DOWN": Input.DOWN,
    "KEY_RIGHT": Input.RIGHT,
    "KEY_ENTER": Input.CONFIRM,
    "KEY_TAB": Input.SWAP,
    "b": Input.TOGGLE_BURN_MODE,
    "q": Input.QUIT,
    "x": Input.SORT_HAND_BY_RANK,
    "c": Input.SORT_HAND_BY_SUIT,
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
        spin_cost: int = calc_spin_cost(ctx.slots.spin_count)

        if input == Input.CONFIRM and ctx.coins > spin_cost:
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

        if input == Input.LEFT and not first_column_is_selected:
            return Action.SLOTS_MOVE_SELECTION_LEFT

        if input == Input.RIGHT and not last_column_is_selected:
            return Action.SLOTS_MOVE_SELECTION_RIGHT

    elif ctx.game_state in (
        GameState.SELECTING_HAND_CARDS,
        GameState.BURN_MODE,
        GameState.FORCED_BURN_MODE,
    ):
        cursor_is_on_first_card: bool = ctx.hand.cursor_pos == 0
        cursor_is_on_last_card: bool = ctx.hand.cursor_pos == len(ctx.hand.cards) - 1
        card_at_cursor_is_selected: bool = ctx.hand.cursor_pos in ctx.hand.selected_card_indexes

        if input == Input.SWAP and ctx.game_state != GameState.FORCED_BURN_MODE:
            return Action.FOCUS_SLOTS

        if input == Input.LEFT and not cursor_is_on_first_card:
            return Action.HAND_MOVE_SELECTION_LEFT

        if input == Input.RIGHT and not cursor_is_on_last_card:
            return Action.HAND_MOVE_SELECTION_RIGHT

        if input == Input.TOGGLE_BURN_MODE and ctx.game_state == GameState.BURN_MODE:
            return Action.EXIT_BURN_MODE

        if input == Input.SORT_HAND_BY_RANK:
            return Action.SORT_HAND_BY_RANK

        if input == Input.SORT_HAND_BY_SUIT:
            return Action.SORT_HAND_BY_SUIT

        if input == Input.CONFIRM:
            any_card_selected: bool = len(ctx.hand.selected_card_indexes) > 0

            if ctx.game_state == GameState.SELECTING_HAND_CARDS and any_card_selected:
                return Action.PLAY_HAND

            if ctx.game_state == GameState.BURN_MODE:
                return Action.BURN_CARD

            if ctx.game_state == GameState.FORCED_BURN_MODE:
                return Action.BURN_CARD_FORCED

        if ctx.game_state == GameState.SELECTING_HAND_CARDS:
            if input == Input.TOGGLE_BURN_MODE and ctx.hand.cards:
                return Action.ENTER_BURN_MODE

            if input == Input.UP and not card_at_cursor_is_selected:
                return Action.HAND_SELECT_CARD

            if input == Input.DOWN and card_at_cursor_is_selected:
                return Action.HAND_DESELECT_CARD

    return None


def resolve_action(ctx: Context, action: Action, config: config.Config):
    """This mutates `ctx` directly"""

    match action:
        case Action.QUIT_GAME:
            exit()

        case Action.SPIN_SLOTS:
            spin_cost: int = calc_spin_cost(ctx.slots.spin_count)
            ctx.coins -= spin_cost
            ctx.slots.spin_count += 1

            for col_index, selected_col in enumerate(ctx.slots.columns):
                spin_duration: float = calc_column_spin_duration_sec(col_index, config)
                selected_col.spin_duration = spin_duration
                selected_col.spin_time_remaining = spin_duration

            ctx.game_state = GameState.SPINNING_SLOTS

        case Action.SLOTS_MOVE_SELECTION_LEFT:
            ctx.slots.selected_column_index -= 1

        case Action.SLOTS_MOVE_SELECTION_RIGHT:
            ctx.slots.selected_column_index += 1

        case Action.SLOTS_PICK_CARD:
            empty_card_slot_available: bool = len(ctx.hand.cards) < ctx.hand.hand_size

            selected_col: Column = ctx.slots.columns[ctx.slots.selected_column_index]
            selected_card_index: int = int(selected_col.cursor) % len(selected_col.cards)
            selected_card: PlayingCard = selected_col.cards[selected_card_index]

            if empty_card_slot_available:
                # Add card to hand
                ctx.hand.cards.append(selected_card)
                ctx.game_state = GameState.READY_TO_SPIN_SLOTS
            else:
                # Cant add card, force burning
                ctx.forced_burn_replacement_card = selected_card
                ctx.game_state = GameState.FORCED_BURN_MODE

        case Action.FOCUS_SLOTS:
            ctx.hand.current_poker_hand = None
            ctx.hand.selected_card_indexes = set()
            ctx.game_state = GameState.READY_TO_SPIN_SLOTS

        case Action.FOCUS_HAND:
            ctx.game_state = GameState.SELECTING_HAND_CARDS

        case Action.HAND_MOVE_SELECTION_LEFT:
            ctx.hand.cursor_pos -= 1

        case Action.HAND_MOVE_SELECTION_RIGHT:
            ctx.hand.cursor_pos += 1

        case Action.HAND_SELECT_CARD:
            if len(ctx.hand.selected_card_indexes) < 5:
                ctx.hand.selected_card_indexes.add(ctx.hand.cursor_pos)
                ctx.hand.current_poker_hand, _ = eval_poker_hand(
                    [ctx.hand.cards[card_index] for card_index in ctx.hand.selected_card_indexes]
                )

        case Action.HAND_DESELECT_CARD:
            ctx.hand.selected_card_indexes.remove(ctx.hand.cursor_pos)
            if ctx.hand.selected_card_indexes:
                ctx.hand.current_poker_hand, _ = eval_poker_hand(
                    [ctx.hand.cards[card_index] for card_index in ctx.hand.selected_card_indexes]
                )
            else:
                ctx.hand.current_poker_hand = None

        case Action.ENTER_BURN_MODE:
            ctx.game_state = GameState.BURN_MODE

        case Action.EXIT_BURN_MODE:
            ctx.game_state = GameState.SELECTING_HAND_CARDS

        case Action.BURN_CARD_FORCED:
            index_to_replace: int = ctx.hand.cursor_pos
            ctx.hand.cards[index_to_replace] = ctx.forced_burn_replacement_card
            ctx.game_state = GameState.READY_TO_SPIN_SLOTS

        case Action.BURN_CARD:
            index_to_burn: int = ctx.hand.cursor_pos
            ctx.hand.selected_card_indexes = set()
            ctx.hand.current_poker_hand = None
            _ = ctx.hand.cards.pop(index_to_burn)

            new_card_count: int = len(ctx.hand.cards)

            if new_card_count == 0:
                ctx.game_state = GameState.READY_TO_SPIN_SLOTS
            else:
                # Clamp cursor to not exceed the max card index
                ctx.hand.cursor_pos = min(new_card_count - 1, ctx.hand.cursor_pos)
                ctx.game_state = GameState.SELECTING_HAND_CARDS

        case Action.PLAY_HAND:
            played_hand: list[PlayingCard] = [
                card
                for card_index, card in enumerate(ctx.hand.cards)
                if card_index in ctx.hand.selected_card_indexes
            ]

            # Additional check to prevent a potential race condition
            if result := eval_poker_hand(played_hand):
                poker_hand, scoring_cards = result

                remaining_cards: list[PlayingCard] = [
                    card
                    for card_index, card in enumerate(ctx.hand.cards)
                    if card_index not in ctx.hand.selected_card_indexes
                ]

                ctx.hand.cards = remaining_cards

                coin_payout: int = 0
                coin_payout += POKER_HAND_COIN_VALUE[poker_hand]

                for card in scoring_cards:
                    rank: Rank = card.rank
                    coin_payout += RANK_COIN_VALUE[rank]

                ctx.coins += coin_payout

                ctx.score += coin_payout

                ctx.hand.selected_card_indexes = set()
                ctx.hand.current_poker_hand = None
                # Clamp cursor to not exceed the max card index
                new_card_count = len(ctx.hand.cards)
                ctx.hand.cursor_pos = min(new_card_count - 1, ctx.hand.cursor_pos)

                if new_card_count == 0:
                    ctx.game_state = GameState.READY_TO_SPIN_SLOTS

        case Action.SORT_HAND_BY_RANK:
            ctx.hand.cards.sort(key=lambda card: card.rank.value, reverse=True)

        case Action.SORT_HAND_BY_SUIT:
            ctx.hand.cards.sort(key=lambda card: card.suit.value)
