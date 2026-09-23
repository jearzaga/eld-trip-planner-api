from datetime import UTC, datetime

from hos.log_builder import LogMeta, build_daily_logs
from hos.models import DutyStatus, Segment, Timeline


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-11 · A-13
def test_header_from_to_and_mileage_from_the_days_segments():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 15, mile_marker=0.0, location="Richmond, VA"),
        Segment(DutyStatus.D, 15, 135, mile_marker=0.0),
        Segment(DutyStatus.ON, 135, 195, mile_marker=120.0, location="Baltimore, MD"),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert daily_log.header.from_location == "Richmond, VA"
    assert daily_log.header.to_location == "Baltimore, MD"
    assert daily_log.header.miles_driving_today == 120.0
    assert daily_log.header.total_mileage_today == 120.0  # A-13


# R-11 · A-15
def test_header_carries_log_meta_fields():
    timeline = _timeline(Segment(DutyStatus.D, 0, 60, mile_marker=0.0))
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    meta = LogMeta(driver_name="Jane Roe", truck_tractor_no="999")
    (daily_log,) = build_daily_logs(
        timeline, start_utc=start_utc, home_tz="America/New_York", meta=meta
    )

    assert daily_log.header.driver_name == "Jane Roe"
    assert daily_log.header.truck_tractor_no == "999"


# R-11: a driving segment split at midnight is prorated by minutes between the two days
def test_header_mileage_prorated_when_driving_segment_splits_at_midnight():
    timeline = _timeline(
        Segment(DutyStatus.D, 0, 1020, mile_marker=0.0),  # 06:00 -> 23:00 day 1, 0 mi
        Segment(DutyStatus.D, 1020, 1140, mile_marker=0.0),  # 23:00 day1 -> 01:00 day2, 120 mi
        Segment(DutyStatus.ON, 1140, 1200, mile_marker=120.0),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    day_one, day_two = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert day_one.header.miles_driving_today == 60.0  # 60 of the 120 min before midnight
    assert day_two.header.miles_driving_today == 60.0
