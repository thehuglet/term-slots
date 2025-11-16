from dataclasses import dataclass, field

from horny_app.playing_cards import PlayingCard


@dataclass
class Column:
    # Cursor is a float for easier management with spinning logic,
    # retrieving the card at the cursor should be done with round()
    cursor: float
    cards: list[PlayingCard] = field(default_factory=list)
    spin_duration: float = 0.0
    spin_time_remaining: float = 0.0
    finish_flash_timer: float = 0.0


@dataclass
class Slots:
    columns: list[Column] = field(default_factory=list)


def calc_spin_speed(
    duration: float,
    time_remaining: float,
    snap_threshold: float,
) -> float:
    max_speed = 60.0
    exponent = 6

    time_normalized = time_remaining / duration
    time_normalized = max(0.0, min(1.0, time_normalized))

    if time_normalized <= snap_threshold:
        return 0.0

    return max_speed * (1 - (1 - time_normalized) ** exponent)


def wrap_cursor(cursor: int, cards: list[PlayingCard]):
    return cursor % len(cards)
