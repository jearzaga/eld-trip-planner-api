from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from hos.log_builder import build_daily_logs
from hos.models import DutyStatus, Segment, Timeline


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-08: log times use the home-terminal time zone, not the trip's start-location time zone
def test_log_shows_home_terminal_time_even_when_trip_starts_in_another_zone():
    start_local_pacific = datetime(2026, 9, 24, 6, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    start_utc = start_local_pacific.astimezone(UTC)  # 06:00 PT == 09:00 ET

    timeline = _timeline(Segment(DutyStatus.D, 0, 60, mile_marker=0.0))
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    first_non_off = next(s for s in daily_log.segments if s.status != DutyStatus.OFF)
    assert first_non_off.start_min == 540  # 09:00 ET
