from hos.engine import plan_timeline
from hos.models import Leg, StopType, TripInput

TWO_DAY_WORKED_EXAMPLE_TRIP = TripInput(
    legs=(Leg(120, 120), Leg(1080, 1080)), cycle_used_min=20 * 60
)
FREQUENT_FUEL_STOPS_TRIP = TripInput(legs=(Leg(100_000, 6_000), Leg(60, 60)), cycle_used_min=0)
CYCLE_FULL_AT_START_TRIP = TripInput(legs=(Leg(60, 60), Leg(180, 180)), cycle_used_min=4200)
CYCLE_HITS_70_MID_TRIP = TripInput(legs=(Leg(120, 120), Leg(1080, 1080)), cycle_used_min=3900)


# SC-2 · AC-14 · business rules §7
def test_two_day_worked_example_stops_name_the_rule_that_caused_them():
    timeline = plan_timeline(TWO_DAY_WORKED_EXAMPLE_TRIP)
    assert [(stop.type, stop.reason) for stop in timeline.stops] == [
        (StopType.PICKUP, "1 hour on duty to load"),
        (StopType.BREAK_30, "8 hours of driving since the last break"),
        (StopType.REST_10, "11-hour driving limit reached"),
        (StopType.FUEL, "Fuel needed every 1,000 miles"),
        (StopType.DROPOFF, "1 hour on duty to unload"),
    ]


# AC-14 · R-02
def test_rest_forced_by_the_14_hour_window_names_the_window():
    timeline = plan_timeline(FREQUENT_FUEL_STOPS_TRIP)
    first_rest = next(stop for stop in timeline.stops if stop.type == StopType.REST_10)
    assert first_rest.reason == "14-hour duty window closed"


# SC-4 · AC-14 · A-05
def test_restart_at_trip_start_names_the_full_cycle():
    timeline = plan_timeline(CYCLE_FULL_AT_START_TRIP)
    assert timeline.stops[0].reason == "Cycle already at 70 hours at trip start"


# SC-3 · AC-14 · R-04
def test_restart_mid_trip_names_the_70_hour_limit():
    timeline = plan_timeline(CYCLE_HITS_70_MID_TRIP)
    restart = next(stop for stop in timeline.stops if stop.type == StopType.RESTART_34)
    assert restart.reason == "70-hour / 8-day limit reached"
