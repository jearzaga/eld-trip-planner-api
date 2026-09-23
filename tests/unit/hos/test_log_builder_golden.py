import pytest

JOHN_DOE_SEGMENTS = [
    ("OFF", 0, 360, None, None),
    ("ON", 360, 450, "Richmond, VA", "Reported, loaded, pre-trip"),
    ("D", 450, 540, None, None),
    ("ON", 540, 570, "Fredericksburg, VA", "Fueled"),
    ("D", 570, 720, None, None),
    ("OFF", 720, 780, "Baltimore, MD", "Lunch"),
    ("D", 780, 900, None, None),
    ("ON", 900, 930, "Philadelphia, PA", "Delivery"),
    ("D", 930, 960, None, None),
    ("SB", 960, 1065, "Cherry Hill, NJ", "Sleeper berth"),
    ("D", 1065, 1140, None, None),
    ("ON", 1140, 1260, "Newark, NJ", "Post-trip, paperwork"),
    ("OFF", 1260, 1440, None, None),
]


@pytest.mark.skip(reason="enable in A3-04")
def test_ac34_john_doe_golden():
    from hos.log_builder import build_daily_logs

    (day,) = build_daily_logs(JOHN_DOE_SEGMENTS)
    assert day.totals == {"OFF": 10.0, "SB": 1.75, "D": 7.75, "ON": 4.5}
    assert len(day.remarks) == 6
