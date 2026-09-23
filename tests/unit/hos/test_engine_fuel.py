from hos.engine import _State, plan_timeline
from hos.models import DutyStatus, Leg, StopType, TripInput

FUEL_ROUNDS_DOWN_TRIP = TripInput(legs=(Leg(3000, 1200), Leg(60, 60)), cycle_used_min=0)


# R-06, A-09: fuel timing rounds down, so the stop happens at or before 1,000 mi, never after
def test_fuel_stop_happens_before_1000_miles_rounded_down_to_the_quarter_hour():
    timeline = plan_timeline(FUEL_ROUNDS_DOWN_TRIP)
    fuel_segment = next(s for s in timeline.segments if s.note == "Fuel")
    assert (fuel_segment.status, fuel_segment.start_min, fuel_segment.duration_min) == (
        DutyStatus.ON,
        405,
        30,
    )
    assert fuel_segment.mile_marker == 975
    assert fuel_segment.mile_marker < 1000


def test_fuel_stop_is_also_registered_as_a_stop_with_the_same_mile_marker():
    timeline = plan_timeline(FUEL_ROUNDS_DOWN_TRIP)
    first_fuel_stop = next(stop for stop in timeline.stops if stop.type == StopType.FUEL)
    assert first_fuel_stop.mile_marker == 975
    assert first_fuel_stop.duration_min == 30


# A leg longer than 1,000 mi needs more than one fuel stop, each under 1,000 mi since the last
def test_a_leg_over_1000_miles_takes_multiple_fuel_stops():
    timeline = plan_timeline(FUEL_ROUNDS_DOWN_TRIP)
    fuel_stops = [stop for stop in timeline.stops if stop.type == StopType.FUEL]
    assert len(fuel_stops) >= 2

    since_last_fuel = fuel_stops[0].mile_marker
    assert since_last_fuel < 1000
    for earlier, later in zip(fuel_stops, fuel_stops[1:]):  # noqa: B905
        since_last_fuel = later.mile_marker - earlier.mile_marker
        assert since_last_fuel < 1000


# R-03: a fuel stop is >= 30 min non-driving, so it also counts as a qualifying break
def test_fuel_stop_counts_as_a_qualifying_break():
    s = _State(drive_since_break=200)
    s.fuel_stop()
    assert s.drive_since_break == 0
    assert s.miles_since_fuel == 0
