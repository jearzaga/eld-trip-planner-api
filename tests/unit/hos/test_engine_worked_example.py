from hos.engine import plan_timeline
from hos.models import DutyStatus, Leg, StopType, TripInput

# SC-2 · business rules §8: start 06:00, cycle used 20 h.
# Leg 1: 120 mi / 2 h. Leg 2: 1,080 mi / 18 h (avg 60 mph).
TWO_DAY_WORKED_EXAMPLE_TRIP = TripInput(
    legs=(Leg(120, 120), Leg(1080, 1080)), cycle_used_min=20 * 60
)

# (status, start_min, end_min, note) — minutes from trip start (t=0 == 06:00)
EXPECTED_SEGMENTS = [
    (DutyStatus.ON, 0, 15, "Pre-trip inspection"),
    (DutyStatus.D, 15, 135, None),
    (DutyStatus.ON, 135, 195, "Pickup"),
    (DutyStatus.D, 195, 675, None),
    (DutyStatus.OFF, 675, 705, "30-minute break"),
    (DutyStatus.D, 705, 765, None),
    (DutyStatus.SB, 765, 1365, "10-hour reset"),
    (DutyStatus.D, 1365, 1695, None),
    (DutyStatus.ON, 1695, 1725, "Fuel"),
    (DutyStatus.D, 1725, 1935, None),
    (DutyStatus.ON, 1935, 1995, "Dropoff"),
    (DutyStatus.ON, 1995, 2010, "Post-trip inspection"),
]


# SC-2 · AC-33 — golden: exact segments must match business rules §8
def test_two_day_worked_example_segments():
    timeline = plan_timeline(TWO_DAY_WORKED_EXAMPLE_TRIP)
    actual = [(s.status, s.start_min, s.end_min, s.note) for s in timeline.segments]
    assert actual == EXPECTED_SEGMENTS


def test_two_day_worked_example_stop_order_and_timing():
    timeline = plan_timeline(TWO_DAY_WORKED_EXAMPLE_TRIP)
    assert [(stop.type, stop.start_min, stop.end_min) for stop in timeline.stops] == [
        (StopType.PICKUP, 135, 195),
        (StopType.BREAK_30, 675, 705),
        (StopType.REST_10, 765, 1365),
        (StopType.FUEL, 1695, 1725),
        (StopType.DROPOFF, 1935, 1995),
    ]


def test_two_day_worked_example_total_miles_driven():
    timeline = plan_timeline(TWO_DAY_WORKED_EXAMPLE_TRIP)
    dropoff = next(stop for stop in timeline.stops if stop.type == StopType.DROPOFF)
    assert dropoff.mile_marker == 120 + 1080
