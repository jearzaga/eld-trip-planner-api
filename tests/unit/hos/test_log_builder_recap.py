from datetime import UTC, datetime

from hos.log_builder import build_daily_logs
from hos.models import DutyStatus, Segment, Timeline

START_UTC = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 06:00 America/New_York
HOME_TZ = "America/New_York"


def _timeline(*segments):
    return Timeline(segments=tuple(segments), stops=())


# R-12 · A-04 · A-14 · SC-2 (business rules §8 worked example)
def test_recap_matches_worked_example_across_two_days():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 15, mile_marker=0.0),
        Segment(DutyStatus.D, 15, 135, mile_marker=0.0),
        Segment(DutyStatus.ON, 135, 195, mile_marker=120.0),
        Segment(DutyStatus.D, 195, 675, mile_marker=120.0),
        Segment(DutyStatus.OFF, 675, 705, mile_marker=600.0),
        Segment(DutyStatus.D, 705, 765, mile_marker=600.0),
        Segment(DutyStatus.SB, 765, 1365, mile_marker=660.0),
        Segment(DutyStatus.D, 1365, 1695, mile_marker=660.0),
        Segment(DutyStatus.ON, 1695, 1725, mile_marker=990.0),
        Segment(DutyStatus.D, 1725, 1935, mile_marker=990.0),
        Segment(DutyStatus.ON, 1935, 1995, mile_marker=1200.0),
        Segment(DutyStatus.ON, 1995, 2010, mile_marker=1200.0),
    )
    day_one, day_two = build_daily_logs(
        timeline, start_utc=START_UTC, home_tz=HOME_TZ, cycle_used_min=20 * 60
    )

    assert day_one.recap.on_duty_today == 12.25
    assert day_one.recap.a_last_7 == 32.25
    assert day_one.recap.b_available_tomorrow == 37.75
    assert day_one.recap.restart_34_taken is False

    assert day_two.recap.on_duty_today == 10.75
    assert day_two.recap.a_last_7 == 43.00
    assert day_two.recap.b_available_tomorrow == 27.00
    assert day_two.recap.restart_34_taken is False


# R-12 · A-14: no rolling window, so C always matches A
def test_recap_c_last_5_matches_a_last_7():
    timeline = _timeline(Segment(DutyStatus.ON, 0, 60, mile_marker=0.0))
    (daily_log,) = build_daily_logs(
        timeline, start_utc=START_UTC, home_tz=HOME_TZ, cycle_used_min=10 * 60
    )

    assert daily_log.recap.c_last_5 == daily_log.recap.a_last_7


# R-04 · R-12: after a 34-hr restart completes, A/C reset and count only on-duty since the restart
def test_recap_resets_after_a_34_hour_restart():
    timeline = _timeline(
        Segment(DutyStatus.ON, 0, 60, mile_marker=0.0),  # 1h on-duty before the restart
        Segment(DutyStatus.OFF, 60, 2100, mile_marker=0.0),  # 34-hr restart (2040 min)
        Segment(DutyStatus.ON, 2100, 2160, mile_marker=0.0),  # 1h on-duty after the restart
    )
    daily_logs = build_daily_logs(
        timeline, start_utc=START_UTC, home_tz=HOME_TZ, cycle_used_min=65 * 60
    )
    restart_day = next(log for log in daily_logs if log.recap.restart_34_taken)

    assert sum(1 for log in daily_logs if log.recap.restart_34_taken) == 1
    assert restart_day.recap.a_last_7 < 10.0
    assert daily_logs[-1].recap.a_last_7 == 1.0
    assert daily_logs[-1].recap.b_available_tomorrow == 69.0
