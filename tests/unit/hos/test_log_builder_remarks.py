from dataclasses import replace
from datetime import UTC, datetime
from itertools import pairwise

from hos.engine import plan_timeline
from hos.log_builder import Remark, build_daily_logs
from hos.models import DutyStatus, Leg, Segment, Timeline, TripInput


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
        Remark(at_min=555, location="Baltimore, MD", note="Off duty"),
    )


# R-09
def test_only_the_final_off_duty_remark_for_segments_without_location_or_note():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 15, mile_marker=0.0),
        Segment(DutyStatus.D, 15, 135, mile_marker=0.0),
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    (daily_log,) = build_daily_logs(timeline, start_utc=start_utc, home_tz="America/New_York")

    assert daily_log.remarks == (Remark(at_min=495, location=None, note="Off duty"),)


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
    assert [remark.note for remark in day_two.remarks] == ["Off duty"]


def _two_day_trip_logs_with_locations():
    trip_input = TripInput(legs=(Leg(120, 120), Leg(1080, 1080)), cycle_used_min=20 * 60)
    planned = plan_timeline(trip_input)
    located = Timeline(
        segments=tuple(
            replace(segment, location=f"Mile {round(segment.mile_marker)}, VA")
            for segment in planned.segments
        ),
        stops=planned.stops,
    )
    start_utc = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
    return build_daily_logs(located, start_utc=start_utc, home_tz="America/New_York")


# R-09 · AC-25
def test_every_duty_status_change_has_a_remark_with_location_and_reason():
    for daily_log in _two_day_trip_logs_with_locations():
        remarks_by_minute = {remark.at_min: remark for remark in daily_log.remarks}
        for previous, current in pairwise(daily_log.segments):
            if previous.status == current.status:
                continue
            remark = remarks_by_minute.get(current.start_min)
            assert remark is not None, (daily_log.day_number, current)
            assert remark.location and remark.note, (daily_log.day_number, remark)


# R-09 · AC-25
def test_final_change_to_off_duty_has_a_remark_at_the_last_location():
    last_day = _two_day_trip_logs_with_locations()[-1]
    final_segment = last_day.segments[-1]
    assert final_segment.status == DutyStatus.OFF
    assert last_day.remarks[-1] == Remark(
        at_min=final_segment.start_min, location=last_day.remarks[-2].location, note="Off duty"
    )
