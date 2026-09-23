from hos.engine import _State, plan_timeline
from hos.models import DutyStatus, Leg, TripInput

FREQUENT_FUEL_STOPS_TRIP = TripInput(legs=(Leg(100_000, 6_000), Leg(60, 60)), cycle_used_min=0)


# R-02: off-duty time inside the window does not extend it
def test_off_duty_time_does_not_extend_the_14_hour_window():
    s = _State()
    s.on(15, "Pre-trip inspection")
    s.off(120, DutyStatus.OFF, "Waiting")
    assert s.minutes_since_shift_start() == 135


# R-02: on-duty (not driving) work is allowed after the 14th hour
def test_on_duty_work_is_allowed_after_the_14th_hour():
    s = _State(shift_active=True, shift_start=0, t=900)
    s.on(30, "Paperwork")
    assert s.segments[-1].status == DutyStatus.ON
    assert s.minutes_since_shift_start() == 930


# R-02 (guide p.6: on-duty at 06:00 -> no driving after 20:00, i.e. 14h later)
def test_driving_stops_at_14_hours_even_when_11_hour_budget_remains():
    timeline = plan_timeline(FREQUENT_FUEL_STOPS_TRIP)
    reset_segment = next(s for s in timeline.segments if s.note == "10-hour reset")
    assert reset_segment.start_min == 840

    driven_before_reset_min = sum(
        s.duration_min
        for s in timeline.segments
        if s.status == DutyStatus.D and s.end_min <= reset_segment.start_min
    )
    assert driven_before_reset_min < 660
