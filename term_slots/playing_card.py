from dataclasses import dataclass
from enum import IntEnum

from term_slots.ezterm import RGB, RichText


class Suit(IntEnum):
    SPADE = 0
    HEART = 1
    DIAMOND = 2
    CLUB = 3


class Rank(IntEnum):
    N_2 = 2
    N_3 = 3
    N_4 = 4
    N_5 = 5
    N_6 = 6
    N_7 = 7
    N_8 = 8
    N_9 = 9
    N_10 = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@dataclass
class PlayingCard:
    suit: Suit
    rank: Rank


SUIT_COLOR: dict[Suit, RGB] = {
    Suit.SPADE: RGB.BLACK,
    Suit.CLUB: RGB.BLACK,
    Suit.HEART: RGB.RED * 0.7,
    Suit.DIAMOND: RGB.RED * 0.7,
}

SUIT_STR: dict[Suit, str] = {
    Suit.SPADE: "♠",
    Suit.HEART: "♥",
    Suit.DIAMOND: "♦",
    Suit.CLUB: "♣",
}

RANK_STR: dict[Rank, str] = {
    Rank.N_2: "2",
    Rank.N_3: "3",
    Rank.N_4: "4",
    Rank.N_5: "5",
    Rank.N_6: "6",
    Rank.N_7: "7",
    Rank.N_8: "8",
    Rank.N_9: "9",
    Rank.N_10: "10",
    Rank.JACK: "J",
    Rank.QUEEN: "Q",
    Rank.KING: "K",
    Rank.ACE: "A",
}

FULL_DECK: list[PlayingCard] = [PlayingCard(suit, rank) for suit in Suit for rank in Rank]


def card_rich_text(card: PlayingCard) -> RichText:
    suit_str = SUIT_STR[card.suit]
    suit_color = SUIT_COLOR[card.suit]
    rank_str = RANK_STR[card.rank]

    text = suit_str + rank_str.rjust(2)

    return RichText(
        text=text,
        text_color=suit_color,
        bg_color=RGB.WHITE * 0.8,
        bold=True,
    )


def card_rich_text_big(card: PlayingCard) -> list[RichText]:
    suit_str = SUIT_STR[card.suit]
    suit_color = SUIT_COLOR[card.suit]
    rank_str = RANK_STR[card.rank]
    bg_color = RGB.WHITE * 0.8

    # Choose pattern based on rank
    if card.rank == Rank.ACE:
        pattern = [
            "<< ",
            " S ",
            " >>",
        ]
    elif card.rank == Rank.N_2:
        pattern = [
            "<<S",
            "   ",
            "S>>",
        ]
    else:
        pattern = [
            "<<S",
            " S ",
            "S>>",
        ]

    output: list[RichText] = []

    for pattern_row in pattern:
        text_row = pattern_row

        text_row = text_row.replace("<<", rank_str.ljust(2))
        text_row = text_row.replace(">>", rank_str.rjust(2))
        text_row = text_row.replace("S", suit_str)

        output.append(RichText(text_row, suit_color, bg_color))

    return output
