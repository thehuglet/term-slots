from collections import Counter
from enum import IntEnum, auto

from term_slots.playing_card import PlayingCard, Rank, Suit


class PokerHand(IntEnum):
    HIGH_CARD = auto()
    PAIR = auto()
    TWO_PAIR = auto()
    THREE_OF_A_KIND = auto()
    STRAIGHT = auto()
    FLUSH = auto()
    FULL_HOUSE = auto()
    FOUR_OF_A_KIND = auto()
    STRAIGHT_FLUSH = auto()
    ROYAL_FLUSH = auto()
    FIVE_OF_A_KIND = auto()
    FLUSH_HOUSE = auto()
    FLUSH_FIVE = auto()


POKER_HAND_NAMES: dict[PokerHand, str] = {
    PokerHand.FLUSH_FIVE: "Flush Five",
    PokerHand.FLUSH_HOUSE: "Flush House",
    PokerHand.FIVE_OF_A_KIND: "Five of a Kind",
    PokerHand.ROYAL_FLUSH: "Royal Flush",
    PokerHand.STRAIGHT_FLUSH: "Straight Flush",
    PokerHand.FOUR_OF_A_KIND: "Four of a Kind",
    PokerHand.FULL_HOUSE: "Full House",
    PokerHand.FLUSH: "Flush",
    PokerHand.STRAIGHT: "Straight",
    PokerHand.THREE_OF_A_KIND: "Three of a Kind",
    PokerHand.TWO_PAIR: "Two Pair",
    PokerHand.PAIR: "Pair",
    PokerHand.HIGH_CARD: "High Card",
}


def _get_suit_count(cards: list[PlayingCard]) -> Counter[Suit]:
    suits: list[Suit] = [c.suit for c in cards]
    suit_count: Counter[Suit] = Counter(suits)
    return suit_count


def _get_rank_count(cards: list[PlayingCard]) -> Counter[Rank]:
    ranks: list[Rank] = [c.rank for c in cards]
    rank_count: Counter[Rank] = Counter(ranks)
    return rank_count


def _is_straight(rank_count: Counter[Rank]) -> bool:
    sorted_ranks: list[Rank] = sorted(set(rank_count))
    for i in range(len(sorted_ranks) - 4):
        if sorted_ranks[i + 4] - sorted_ranks[i] == 4:
            return True
    # special case: Ace-low straight
    if set([Rank.ACE, Rank.NUM_2, Rank.NUM_3, Rank.NUM_4, Rank.NUM_5]).issubset(rank_count):
        return True
    return False


def _is_full_house(rank_count: Counter[Rank]) -> bool:
    return sorted(rank_count.values())[-2:] == [2, 3]


def _is_flush(suit_count: Counter[Suit]) -> bool:
    return any(v >= 5 for v in suit_count.values())


def _is_royal_flush(rank_count: Counter[Rank], suit_count: Counter[Suit]) -> bool:
    return _is_flush(suit_count) and _is_straight(rank_count) and min(rank_count) == Rank.NUM_10


def eval_poker_hand(cards: list[PlayingCard]) -> PokerHand:
    suit_count: Counter[Suit] = _get_suit_count(cards)
    rank_count: Counter[Rank] = _get_rank_count(cards)

    if 5 in rank_count.values() and _is_flush(suit_count):
        return PokerHand.FLUSH_FIVE

    if _is_full_house(rank_count) and _is_flush(suit_count):
        return PokerHand.FLUSH_HOUSE

    if 5 in rank_count.values():
        return PokerHand.FIVE_OF_A_KIND

    if _is_royal_flush(rank_count, suit_count):
        return PokerHand.ROYAL_FLUSH

    if _is_straight(rank_count) and _is_flush(suit_count):
        return PokerHand.STRAIGHT_FLUSH

    if 4 in rank_count.values():
        return PokerHand.FOUR_OF_A_KIND

    if _is_full_house(rank_count):
        return PokerHand.FULL_HOUSE

    if _is_flush(suit_count):
        return PokerHand.FLUSH

    if _is_straight(rank_count):
        return PokerHand.STRAIGHT

    if 3 in rank_count.values():
        return PokerHand.THREE_OF_A_KIND

    if list(rank_count.values()).count(2) == 2:
        return PokerHand.TWO_PAIR

    if 2 in rank_count.values():
        return PokerHand.PAIR

    return PokerHand.HIGH_CARD
