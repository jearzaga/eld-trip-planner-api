from hos.engine import plan_timeline
from hos.models import DutyStatus, Leg, TripInput

ELEVEN_HOUR_LIMIT_TRIP = TripInput(legs=(Leg(660, 660), Leg(60, 60)), cycle_used_min=0)


# R-01
def test_driving_stops_at_11_hours_in_a_shift():
    timeline = plan_timeline(ELEVEN_HOUR_LIMIT_TRIP)
    driving_segments = [s for s in timeline.segments if s.status == DutyStatus.D]
    total_before_reset_min = sum(s.duration_min for s in driving_segments if s.start_min < 700)
    assert total_before_reset_min == 660


# R-05, A-07
def test_10_hour_reset_follows_the_11_hour_limit_and_is_logged_as_sleeper_berth():
    timeline = plan_timeline(ELEVEN_HOUR_LIMIT_TRIP)
    reset_segment = next(s for s in timeline.segments if s.note == "10-hour reset")
    assert reset_segment.status == DutyStatus.SB
    assert reset_segment.duration_min == 600


# R-05: 10-hr reset starts a fresh shift (R-01, R-02 counters clear)
def test_driving_resumes_after_the_reset_with_a_fresh_11_hour_budget():
    timeline = plan_timeline(ELEVEN_HOUR_LIMIT_TRIP)
    reset_segment = next(s for s in timeline.segments if s.note == "10-hour reset")
    driving_after_reset = [
        s
        for s in timeline.segments
        if s.status == DutyStatus.D and s.start_min >= reset_segment.end_min
    ]
    assert sum(s.duration_min for s in driving_after_reset) == 60
