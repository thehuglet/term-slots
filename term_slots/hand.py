from dataclasses import dataclass

from term_slots.playing_card import PlayingCard


@dataclass
class Hand:
    cards: list[PlayingCard]
    cursor_pos: int
    selected_card_indexes: list[int]
