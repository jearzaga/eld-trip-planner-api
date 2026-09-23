from hos.engine import plan_timeline
from hos.models import Leg, StopType, TripInput

# SC-5
CROSS_COUNTRY_TRIP = TripInput(legs=(Leg(300, 300), Leg(2500, 2520)), cycle_used_min=600)


def test_every_stop_carries_a_mile_marker_in_time_order():
    timeline = plan_timeline(CROSS_COUNTRY_TRIP)
    assert [stop.start_min for stop in timeline.stops] == sorted(
        stop.start_min for stop in timeline.stops
    )
    mile_markers = [stop.mile_marker for stop in timeline.stops]
    assert mile_markers == sorted(mile_markers)
    assert all(marker >= 0 for marker in mile_markers)


# SC-5: 2 fuel, 4 x 10-hr reset, 2 x 30-min break
def test_cross_country_trip_matches_sc5_stop_counts():
    timeline = plan_timeline(CROSS_COUNTRY_TRIP)
    stop_types = [stop.type for stop in timeline.stops]
    assert stop_types.count(StopType.FUEL) == 2
    assert stop_types.count(StopType.REST_10) == 4
    assert stop_types.count(StopType.BREAK_30) == 2
    assert stop_types[0] == StopType.PICKUP
    assert stop_types[-1] == StopType.DROPOFF


def test_fuel_stops_stay_under_1000_miles_since_the_previous_fuel_stop():
    timeline = plan_timeline(CROSS_COUNTRY_TRIP)
    fuel_stops = [stop for stop in timeline.stops if stop.type == StopType.FUEL]
    since_last = fuel_stops[0].mile_marker
    assert since_last < 1000
    for earlier, later in zip(fuel_stops, fuel_stops[1:]):  # noqa: B905
        assert later.mile_marker - earlier.mile_marker < 1000


def test_pickup_and_dropoff_mile_markers_match_leg_boundaries():
    timeline = plan_timeline(CROSS_COUNTRY_TRIP)
    pickup = next(stop for stop in timeline.stops if stop.type == StopType.PICKUP)
    dropoff = next(stop for stop in timeline.stops if stop.type == StopType.DROPOFF)
    assert pickup.mile_marker == 300
    assert dropoff.mile_marker == 2800
