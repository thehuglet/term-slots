from dataclasses import dataclass


@dataclass
class Config:
    game_speed: float = 20.0
    slots_max_spin_speed: float = 60.0
    slots_spin_duration_sec: float = 3.0
    slots_spin_duration_stagger_sec_min: float = 0.5
    slots_spin_duration_stagger_ratio: float = 0.35
    slots_spin_duration_stagger_diminishing_ratio: float = 0.8
    slots_after_spin_delay_sec: float = 0.8
