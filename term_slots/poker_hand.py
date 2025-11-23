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

POKER_HAND_COIN_VALUE: dict[PokerHand, int] = {
    PokerHand.FLUSH_FIVE: 170,
    PokerHand.FLUSH_HOUSE: 165,
    PokerHand.FIVE_OF_A_KIND: 150,
    PokerHand.ROYAL_FLUSH: 140,
    PokerHand.STRAIGHT_FLUSH: 120,
    PokerHand.FOUR_OF_A_KIND: 100,
    PokerHand.FULL_HOUSE: 80,
    PokerHand.FLUSH: 55,
    PokerHand.STRAIGHT: 50,
    PokerHand.THREE_OF_A_KIND: 30,
    PokerHand.TWO_PAIR: 20,
    PokerHand.PAIR: 10,
    PokerHand.HIGH_CARD: 5,
}


def eval_poker_hand(cards: list[PlayingCard]) -> tuple[PokerHand, list[PlayingCard]]:
    suit_count: Counter[Suit] = _get_suit_count(cards)
    rank_count: Counter[Rank] = _get_rank_count(cards)

    flush_cards: list[PlayingCard] = _get_flush_cards(cards, suit_count)
    is_flush: bool = len(flush_cards) > 0

    if is_flush and _is_n_of_a_kind(5, rank_count):
        return (PokerHand.FLUSH_FIVE, flush_cards)

    if is_flush and _is_full_house(rank_count):
        return (PokerHand.FLUSH_HOUSE, flush_cards)

    if _is_n_of_a_kind(5, rank_count):
        return (PokerHand.FIVE_OF_A_KIND, _get_n_of_a_kind_cards(5, cards, rank_count))

    if _is_royal_flush(rank_count, suit_count):
        return (PokerHand.ROYAL_FLUSH, flush_cards)

    if _is_straight(rank_count) and is_flush:
        return (PokerHand.STRAIGHT_FLUSH, flush_cards)

    if 4 in rank_count.values():
        return (PokerHand.FOUR_OF_A_KIND, _get_n_of_a_kind_cards(4, cards, rank_count))

    if _is_full_house(rank_count):
        return (PokerHand.FULL_HOUSE, _get_full_house_cards(cards, rank_count))

    if _is_flush(suit_count):
        return (PokerHand.FLUSH, flush_cards)

    if _is_straight(rank_count):
        return (PokerHand.STRAIGHT, _get_straight_cards(cards, rank_count))

    if _is_n_of_a_kind(3, rank_count):
        return (PokerHand.THREE_OF_A_KIND, _get_n_of_a_kind_cards(3, cards, rank_count))

    if list(rank_count.values()).count(2) == 2:
        return (PokerHand.TWO_PAIR, _get_two_pair_cards(cards, rank_count))

    if _is_n_of_a_kind(2, rank_count):
        return (PokerHand.PAIR, _get_n_of_a_kind_cards(2, cards, rank_count))

    highest_rank_card: PlayingCard = max(cards, key=lambda card: card.rank)
    return (PokerHand.HIGH_CARD, [highest_rank_card])


def _get_suit_count(cards: list[PlayingCard]) -> Counter[Suit]:
    suits: list[Suit] = [c.suit for c in cards]
    suit_count: Counter[Suit] = Counter(suits)
    return suit_count


def _get_rank_count(cards: list[PlayingCard]) -> Counter[Rank]:
    ranks: list[Rank] = [c.rank for c in cards]
    rank_count: Counter[Rank] = Counter(ranks)
    return rank_count


def _get_two_pair_cards(cards: list[PlayingCard], rank_count: Counter[Rank]) -> list[PlayingCard]:
    # find all ranks with at least 2 cards, sorted descending
    pair_ranks = sorted((r for r, cnt in rank_count.items() if cnt >= 2), reverse=True)
    if len(pair_ranks) < 2:
        return []

    # pick top two pairs
    first_pair = [c for c in cards if c.rank == pair_ranks[0]][:2]
    second_pair = [c for c in cards if c.rank == pair_ranks[1]][:2]

    # kicker = highest remaining card
    remaining = [c for c in cards if c.rank not in pair_ranks[:2]]
    if remaining:
        kicker = max(remaining, key=lambda c: c.rank.value)
        return first_pair + second_pair + [kicker]

    return first_pair + second_pair


def _is_straight(rank_count: Counter[Rank]) -> bool:
    sorted_ranks: list[Rank] = sorted(set(rank_count))
    for i in range(len(sorted_ranks) - 4):
        if sorted_ranks[i + 4] - sorted_ranks[i] == 4:
            return True
    # special case: Ace-low straight
    if set([Rank.ACE, Rank.NUM_2, Rank.NUM_3, Rank.NUM_4, Rank.NUM_5]).issubset(rank_count):
        return True
    return False


def _get_straight_cards(cards: list[PlayingCard], rank_count: Counter[Rank]) -> list[PlayingCard]:
    sorted_ranks = sorted(set(rank_count), reverse=True)
    straight_ranks = []

    # search for straight (high-to-low)
    for i in range(len(sorted_ranks) - 4):
        if sorted_ranks[i] - sorted_ranks[i + 4] == 4:
            straight_ranks = sorted_ranks[i : i + 5]
            break
    else:
        # special case: Ace-low straight
        if set([Rank.ACE, Rank.NUM_2, Rank.NUM_3, Rank.NUM_4, Rank.NUM_5]).issubset(rank_count):
            straight_ranks = [Rank.ACE, Rank.NUM_2, Rank.NUM_3, Rank.NUM_4, Rank.NUM_5]

    if not straight_ranks:
        return []

    # pick one card per rank (if duplicates exist)
    straight_cards: list[PlayingCard] = [
        next(card for card in cards if card.rank == rank) for rank in straight_ranks
    ]
    return sorted(straight_cards, key=lambda c: c.rank.value, reverse=True)


def _is_full_house(rank_count: Counter[Rank]) -> bool:
    return sorted(rank_count.values())[-2:] == [2, 3]


def _get_full_house_cards(cards: list[PlayingCard], rank_count: Counter[Rank]) -> list[PlayingCard]:
    # get highest three-of-a-kind
    three_cards = _get_n_of_a_kind_cards(3, cards, rank_count)
    if not three_cards:
        return []

    # remove the three-of-a-kind rank for picking a pair
    remaining_rank_count = rank_count.copy()
    remaining_rank_count.pop(three_cards[0].rank)

    pair_cards = _get_n_of_a_kind_cards(2, cards, remaining_rank_count)
    if not pair_cards:
        return []

    # combine for full house
    return three_cards + pair_cards


def _is_flush(suit_count: Counter[Suit]) -> bool:
    return any(v >= 5 for v in suit_count.values())


def _get_flush_cards(cards: list[PlayingCard], suit_count: Counter[Suit]) -> list[PlayingCard]:
    # find a suit with at least 5 cards
    flush_suit = next((suit for suit, count in suit_count.items() if count >= 5), None)
    if flush_suit is None:
        return []
    # return top 5 cards of that suit
    flush_cards: list[PlayingCard] = [card for card in cards if card.suit == flush_suit]
    return sorted(flush_cards, key=lambda card: card.rank.value, reverse=True)[:5]


def _is_n_of_a_kind(n: int, rank_count: Counter[Rank]) -> bool:
    return n in rank_count.values()


def _get_n_of_a_kind_cards(
    n: int,
    cards: list[PlayingCard],
    rank_count: Counter[Rank],
) -> list[PlayingCard]:
    # find ranks with at least n cards, sorted descending
    ranks: list[Rank] = sorted(
        (rank for rank, count in rank_count.items() if count >= n), reverse=True
    )
    if not ranks:
        return []
    # pick highest rank
    top_rank = ranks[0]
    # return exactly n cards of that rank, sorted by rank descending
    kind_cards: list[PlayingCard] = [card for card in cards if card.rank == top_rank][:n]
    return kind_cards


def _is_royal_flush(rank_count: Counter[Rank], suit_count: Counter[Suit]) -> bool:
    return _is_flush(suit_count) and _is_straight(rank_count) and min(rank_count) == Rank.NUM_10
