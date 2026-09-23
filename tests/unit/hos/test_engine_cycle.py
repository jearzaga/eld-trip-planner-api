from hos.engine import plan_timeline
from hos.models import DutyStatus, Leg, StopType, TripInput

CYCLE_FULL_AT_START_TRIP = TripInput(legs=(Leg(60, 60), Leg(180, 180)), cycle_used_min=4200)
CYCLE_HITS_70_MID_TRIP = TripInput(legs=(Leg(120, 120), Leg(1080, 1080)), cycle_used_min=3900)


# SC-4 · R-04, A-05: cycle used = 70 h at start -> plan begins with a 34-hr restart
def test_cycle_full_at_start_begins_with_a_34_hour_restart():
    timeline = plan_timeline(CYCLE_FULL_AT_START_TRIP)
    first_segment = timeline.segments[0]
    assert (first_segment.status, first_segment.note, first_segment.start_min) == (
        DutyStatus.OFF,
        "34-hour restart",
        0,
    )
    assert first_segment.duration_min == 34 * 60


# SC-3 · R-04: 34-hr restart inserted mid-trip once on-duty hours in the cycle reach 70
def test_34_hour_restart_inserted_mid_trip_when_cycle_hits_70():
    timeline = plan_timeline(CYCLE_HITS_70_MID_TRIP)
    restart_segment = next(s for s in timeline.segments if s.note == "34-hour restart")
    assert restart_segment.status == DutyStatus.OFF
    assert restart_segment.duration_min == 34 * 60

    driving_before_restart_min = sum(
        s.duration_min
        for s in timeline.segments
        if s.status == DutyStatus.D and s.end_min <= restart_segment.start_min
    )
    leg_1_driving_min = 120
    leg_2_driving_before_restart_min = 105
    assert driving_before_restart_min == leg_1_driving_min + leg_2_driving_before_restart_min


def test_restart_is_registered_as_a_stop():
    timeline = plan_timeline(CYCLE_HITS_70_MID_TRIP)
    (restart_stop,) = [stop for stop in timeline.stops if stop.type == StopType.RESTART_34]
    assert restart_stop.duration_min == 34 * 60
