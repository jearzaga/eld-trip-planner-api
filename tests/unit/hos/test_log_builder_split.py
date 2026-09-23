from datetime import UTC, datetime

from hos.log_builder import build_daily_logs
from hos.models import DutyStatus, Segment, Timeline


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-08 · R-10: rest crossing midnight splits across two sheets, each still totals 24h
def test_rest_crossing_midnight_splits_across_two_sheets():
    timeline = _timeline(
        Segment(DutyStatus.D, 0, 1020, mile_marker=0.0),  # 06:00 -> 23:00 day 1
        Segment(DutyStatus.SB, 1020, 1620, mile_marker=0.0),  # 10-hr reset, crosses midnight
        Segment(DutyStatus.D, 1620, 1680, mile_marker=0.0),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    day_one, day_two = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert day_one.segments[-1].status == DutyStatus.SB
    assert day_one.segments[-1].end_min == 1440
    assert day_two.segments[0].status == DutyStatus.SB
    assert day_two.segments[0].start_min == 0

    assert sum(day_one.totals.values()) == 24.0
    assert sum(day_two.totals.values()) == 24.0


# R-08: a 34-hr restart spans three midnights, so it splits across three sheets
def test_long_rest_spanning_multiple_midnights_splits_across_three_sheets():
    timeline = _timeline(
        Segment(DutyStatus.D, 0, 1020, mile_marker=0.0),  # 06:00 -> 23:00 day 1
        Segment(DutyStatus.OFF, 1020, 3060, mile_marker=0.0),  # 34h restart, spans two midnights
        Segment(DutyStatus.D, 3060, 3120, mile_marker=0.0),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    daily_logs = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert len(daily_logs) == 3
    for daily_log in daily_logs:
        assert sum(daily_log.totals.values()) == 24.0
