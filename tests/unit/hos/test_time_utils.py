import pytest

from hos.time_utils import ceil_q, floor_q


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0, 0), (1, 15), (15, 15), (16, 30), (119.5, 120), (120, 120)],
)
def test_ceil_rounds_up_to_quarter_hour(minutes, expected):
    assert ceil_q(minutes) == expected


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0, 0), (14.9, 0), (15, 15), (1000, 990), (999.99, 990)],
)
def test_floor_rounds_down_to_quarter_hour(minutes, expected):
    assert floor_q(minutes) == expected


def test_rounding_returns_integers():
    assert isinstance(ceil_q(7.5), int) and isinstance(floor_q(7.5), int)
