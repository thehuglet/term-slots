from dataclasses import dataclass
from enum import IntEnum

from horny_app.ezterm import RGB, RichText


class Suit(IntEnum):
    SPADE = 0
    HEART = 1
    DIAMOND = 2
    CLUB = 3


class Rank(IntEnum):
    R_A = 1
    R_2 = 2
    R_3 = 3
    R_4 = 4
    R_5 = 5
    R_6 = 6
    R_7 = 7
    R_8 = 8
    R_9 = 9
    R_10 = 10
    R_J = 11
    R_Q = 12
    R_K = 13


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
    Rank.R_A: "A",
    Rank.R_2: "2",
    Rank.R_3: "3",
    Rank.R_4: "4",
    Rank.R_5: "5",
    Rank.R_6: "6",
    Rank.R_7: "7",
    Rank.R_8: "8",
    Rank.R_9: "9",
    Rank.R_10: "10",
    Rank.R_J: "J",
    Rank.R_Q: "Q",
    Rank.R_K: "K",
}

FULL_DECK: list[PlayingCard] = [PlayingCard(suit, rank) for suit in Suit for rank in Rank]


def card_rich_text(card: PlayingCard) -> RichText:
    suit_str = SUIT_STR[card.suit]
    suit_color = SUIT_COLOR[card.suit]
    rank_str = RANK_STR[card.rank]

    text = suit_str + rank_str.rjust(2)
    # Debug for only showing the bg
    # text = "   "

    return RichText(
        text=text,
        text_color=suit_color,
        bg_color=RGB.WHITE * 0.8,
        bold=True,
    )
