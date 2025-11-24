def smoothstep(t: float) -> float:
    return t * t * (3 - 2 * t)


def ease_in(t: float) -> float:
    return t * t
