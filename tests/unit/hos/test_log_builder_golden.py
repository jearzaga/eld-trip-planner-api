from datetime import UTC, datetime

from hos.log_builder import build_daily_logs
from hos.models import DutyStatus, Segment, Timeline

JOHN_DOE_SEGMENTS = (
    Segment(
        DutyStatus.ON,
        0,
        90,
        mile_marker=0.0,
        location="Richmond, VA",
        note="Reported, loaded, pre-trip",
    ),
    Segment(DutyStatus.D, 90, 180, mile_marker=0.0),
    Segment(
        DutyStatus.ON, 180, 210, mile_marker=90.0, location="Fredericksburg, VA", note="Fueled"
    ),
    Segment(DutyStatus.D, 210, 360, mile_marker=90.0),
    Segment(DutyStatus.OFF, 360, 420, mile_marker=200.0, location="Baltimore, MD", note="Lunch"),
    Segment(DutyStatus.D, 420, 540, mile_marker=200.0),
    Segment(
        DutyStatus.ON,
        540,
        570,
        mile_marker=300.0,
        location="Philadelphia, PA",
        note="Delivery",
    ),
    Segment(DutyStatus.D, 570, 600, mile_marker=300.0),
    Segment(
        DutyStatus.SB,
        600,
        705,
        mile_marker=320.0,
        location="Cherry Hill, NJ",
        note="Sleeper berth",
    ),
    Segment(DutyStatus.D, 705, 780, mile_marker=320.0),
    Segment(
        DutyStatus.ON,
        780,
        900,
        mile_marker=350.0,
        location="Newark, NJ",
        note="Post-trip, paperwork",
    ),
)


# AC-34
def test_john_doe_example_log_matches_totals_and_remarks():
    timeline = Timeline(segments=JOHN_DOE_SEGMENTS, stops=())
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York

    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert daily_log.totals == {"OFF": 10.0, "SB": 1.75, "D": 7.75, "ON": 4.5}
    assert len(daily_log.remarks) == 6
