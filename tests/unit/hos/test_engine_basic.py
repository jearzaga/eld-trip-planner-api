from hos.engine import plan_timeline
from hos.models import DutyStatus, Leg, StopType, TripInput

SHORT_DAY_TRIP = TripInput(legs=(Leg(60, 60), Leg(180, 180)), cycle_used_min=0)


def as_tuples(timeline):
    return [(s.status, s.start_min, s.end_min) for s in timeline.segments]


# SC-1
def test_short_trip_runs_pretrip_leg_pickup_leg_dropoff_posttrip_in_order():
    timeline = plan_timeline(SHORT_DAY_TRIP)
    assert as_tuples(timeline) == [
        (DutyStatus.ON, 0, 15),
        (DutyStatus.D, 15, 75),
        (DutyStatus.ON, 75, 135),
        (DutyStatus.D, 135, 315),
        (DutyStatus.ON, 315, 375),
        (DutyStatus.ON, 375, 390),
    ]


def test_segments_start_at_zero_and_are_contiguous():
    timeline = plan_timeline(SHORT_DAY_TRIP)
    segments = timeline.segments
    assert segments[0].start_min == 0
    for earlier, later in zip(segments, segments[1:]):  # noqa: B905
        assert earlier.end_min == later.start_min


def test_pickup_and_dropoff_are_the_only_stops_for_a_short_trip():
    timeline = plan_timeline(SHORT_DAY_TRIP)
    assert [stop.type for stop in timeline.stops] == [StopType.PICKUP, StopType.DROPOFF]
