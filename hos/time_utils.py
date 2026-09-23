import math

from hos.rules import QUARTER_HOUR_MIN


def ceil_q(minutes: float) -> int:
    return math.ceil(minutes / QUARTER_HOUR_MIN) * QUARTER_HOUR_MIN


def floor_q(minutes: float) -> int:
    return math.floor(minutes / QUARTER_HOUR_MIN) * QUARTER_HOUR_MIN
