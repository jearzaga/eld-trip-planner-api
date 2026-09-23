from datetime import UTC, datetime

from hos.log_builder import build_daily_logs
from hos.models import DutyStatus, Segment, Timeline


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-08 · SC-2 (business rules §8)
def test_totals_match_worked_example_day_one():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 15, mile_marker=0.0, note="Pre-trip inspection"),
        Segment(DutyStatus.D, 15, 135, mile_marker=0.0),
        Segment(DutyStatus.ON, 135, 195, mile_marker=120.0, note="Pickup"),
        Segment(DutyStatus.D, 195, 675, mile_marker=120.0),
        Segment(DutyStatus.OFF, 675, 705, mile_marker=600.0, note="30-min break"),
        Segment(DutyStatus.D, 705, 765, mile_marker=600.0),
        Segment(DutyStatus.SB, 765, 1365, mile_marker=660.0, note="10-hr reset"),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (day_one, _day_two) = build_daily_logs(
        timeline, start_utc=start_utc, home_tz="America/New_York"
    )

    assert day_one.totals == {"OFF": 6.5, "SB": 5.25, "D": 11.0, "ON": 1.25}
    assert sum(day_one.totals.values()) == 24.0


def test_totals_contain_all_four_duty_statuses_even_when_unused():
    timeline = _timeline(Segment(DutyStatus.D, 0, 60, mile_marker=0.0))
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert set(daily_log.totals) == {"OFF", "SB", "D", "ON"}
    assert daily_log.totals["SB"] == 0.0
