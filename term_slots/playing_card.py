from dataclasses import dataclass
from enum import IntEnum

from term_slots.ezterm import RGB, DrawCall, RichText

DEFAULT_CARD_BG_COLOR: RGB = RGB.WHITE


class Suit(IntEnum):
    SPADE = 0
    HEART = 1
    DIAMOND = 2
    CLUB = 3


class Rank(IntEnum):
    NUM_2 = 2
    NUM_3 = 3
    NUM_4 = 4
    NUM_5 = 5
    NUM_6 = 6
    NUM_7 = 7
    NUM_8 = 8
    NUM_9 = 9
    NUM_10 = 10
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
    Rank.NUM_2: "2",
    Rank.NUM_3: "3",
    Rank.NUM_4: "4",
    Rank.NUM_5: "5",
    Rank.NUM_6: "6",
    Rank.NUM_7: "7",
    Rank.NUM_8: "8",
    Rank.NUM_9: "9",
    Rank.NUM_10: "10",
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
        bg_color=RGB.WHITE * 0.9,
        bold=True,
    )


def card_rich_text_big(card: PlayingCard) -> list[RichText]:
    suit_str = SUIT_STR[card.suit]
    suit_color = SUIT_COLOR[card.suit]
    rank_str = RANK_STR[card.rank]
    bg_color = RGB.WHITE * 0.9

    # Choose pattern based on rank
    if card.rank == Rank.ACE:
        pattern = [
            "<< ",
            " S ",
            " >>",
        ]
    elif card.rank == Rank.NUM_2:
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

        output.append(RichText(text_row, suit_color, bg_color, bold=True))

    return output


def render_card_small(x: int, y: int, card: PlayingCard) -> DrawCall:
    suit_str: str = SUIT_STR[card.suit]
    suit_color: RGB = SUIT_COLOR[card.suit]
    rank_str: str = RANK_STR[card.rank]

    # Pad rank with rjust(2) so "10" aligns correctly, making card width 3 chars
    text: str = suit_str + rank_str.rjust(2)

    return DrawCall(x, y, RichText(text, suit_color, DEFAULT_CARD_BG_COLOR, bold=True))
