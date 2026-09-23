from datetime import UTC, datetime

from hos.models import DutyStatus, Segment, Timeline


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-10
def test_pads_off_duty_before_trip_start_to_local_midnight():
    from hos.log_builder import build_daily_logs

    timeline = _timeline(Segment(DutyStatus.D, 0, 60, mile_marker=0.0))
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    first = daily_log.segments[0]
    assert first.status == DutyStatus.OFF
    assert first.start_min == 0
    assert first.end_min == 360


# R-10
def test_pads_off_duty_after_trip_end_to_local_midnight():
    from hos.log_builder import build_daily_logs

    timeline = _timeline(Segment(DutyStatus.D, 0, 60, mile_marker=0.0))
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    last = daily_log.segments[-1]
    assert last.status == DutyStatus.OFF
    assert last.start_min == 420
    assert last.end_min == 1440


# R-08 · A-11
def test_no_padding_when_trip_starts_and_ends_exactly_on_local_midnight():
    from hos.log_builder import build_daily_logs

    timeline = _timeline(Segment(DutyStatus.D, 0, 1440, mile_marker=0.0))
    start_utc = datetime(2026, 9, 24, 4, 0, tzinfo=UTC)  # 00:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert daily_log.segments[0].status == DutyStatus.D
    assert daily_log.segments[0].start_min == 0
    assert daily_log.segments[-1].end_min == 1440
