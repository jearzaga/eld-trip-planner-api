from datetime import UTC, datetime

from hos.log_builder import Remark, build_daily_logs
from hos.models import DutyStatus, Segment, Timeline


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-09
def test_remark_emitted_for_each_status_change_with_location_or_note():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 15, mile_marker=0.0, location="Richmond, VA", note="Pre-trip"),
        Segment(DutyStatus.D, 15, 135, mile_marker=0.0),
        Segment(
            DutyStatus.ON, 135, 195, mile_marker=120.0, location="Baltimore, MD", note="Pickup"
        ),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert daily_log.remarks == (
        Remark(at_min=360, location="Richmond, VA", note="Pre-trip"),
        Remark(at_min=495, location="Baltimore, MD", note="Pickup"),
    )


# R-09
def test_no_remark_for_status_change_without_location_or_note():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 15, mile_marker=0.0),
        Segment(DutyStatus.D, 15, 135, mile_marker=0.0),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert daily_log.remarks == ()


# R-09
def test_no_duplicate_remark_for_the_continuation_piece_after_a_midnight_split():
    timeline = _timeline(
        Segment(DutyStatus.D, 0, 1020, mile_marker=0.0),  # 06:00 -> 23:00 day 1
        Segment(
            DutyStatus.SB, 1020, 1620, mile_marker=0.0, location="Cherry Hill, NJ", note="Rest"
        ),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    day_one, day_two = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert len(day_one.remarks) == 1
    assert day_one.remarks[0].location == "Cherry Hill, NJ"
    assert day_two.remarks == ()
