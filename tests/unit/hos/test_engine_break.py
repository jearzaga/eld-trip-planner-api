from hos.engine import _State, plan_timeline
from hos.models import DutyStatus, Leg, TripInput

EIGHT_HOUR_TRIGGERS_BREAK_TRIP = TripInput(legs=(Leg(600, 600), Leg(60, 60)), cycle_used_min=0)


# R-03
def test_break_required_after_8_hours_of_driving():
    timeline = plan_timeline(EIGHT_HOUR_TRIGGERS_BREAK_TRIP)
    break_segment = next(s for s in timeline.segments if s.note == "30-minute break")
    assert (break_segment.status, break_segment.start_min, break_segment.end_min) == (
        DutyStatus.OFF,
        495,
        525,
    )


def test_break_segment_is_also_registered_as_a_stop():
    timeline = plan_timeline(EIGHT_HOUR_TRIGGERS_BREAK_TRIP)
    (break_stop,) = [stop for stop in timeline.stops if stop.type.value == "break_30"]
    assert (break_stop.start_min, break_stop.end_min) == (495, 525)


# R-03: consecutive non-driving periods combine (15 ON + 15 OFF counts)
def test_combined_15_plus_15_non_driving_counts_as_a_qualifying_break():
    s = _State(drive_since_break=450)
    s.on(15, "Fuel")
    assert s.drive_since_break == 450
    s.off(15, DutyStatus.OFF, "Waiting")
    assert s.drive_since_break == 0


def test_two_separate_15_minute_stretches_split_by_driving_do_not_combine():
    s = _State(drive_since_break=450)
    s.on(15, "Fuel")
    s.drive(15, Leg(15, 15))
    s.off(15, DutyStatus.OFF, "Waiting")
    assert s.drive_since_break == 465
