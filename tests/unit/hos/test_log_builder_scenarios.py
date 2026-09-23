from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from hos.engine import plan_timeline
from hos.log_builder import build_daily_logs
from hos.models import Leg, TripInput

HOME_TIMEZONE = "America/New_York"
SIX_AM_HOME_TIME = datetime(2026, 9, 24, 6, 0, tzinfo=ZoneInfo(HOME_TIMEZONE))


def trip(first_leg: tuple[float, float], second_leg: tuple[float, float], cycle_hrs: float):
    legs = tuple(Leg(miles, hours * 60) for miles, hours in (first_leg, second_leg))
    return TripInput(legs=legs, cycle_used_min=round(cycle_hrs * 60))


def plan_daily_logs(trip_input: TripInput):
    return build_daily_logs(
        plan_timeline(trip_input),
        start_utc=SIX_AM_HOME_TIME,
        home_tz=HOME_TIMEZONE,
        cycle_used_min=trip_input.cycle_used_min,
    )


# SC-1 · SC-2 · SC-3 · SC-4 · SC-5 · R-08 · R-10
@pytest.mark.parametrize(
    ("spec_id", "trip_input", "expected_sheets"),
    [
        ("SC-1", trip((60, 1), (180, 3), 0), 1),
        ("SC-2", trip((120, 2), (1080, 18), 20), 2),
        ("SC-3", trip((120, 2), (1080, 18), 65), 4),
        ("SC-4", trip((60, 1), (180, 3), 70), 2),
        ("SC-5", trip((300, 5), (2500, 42), 10), 5),
    ],
)
def test_planned_trip_produces_expected_sheets_each_totalling_24_hours(
    spec_id, trip_input, expected_sheets
):
    daily_logs = plan_daily_logs(trip_input)
    assert len(daily_logs) == expected_sheets, spec_id
    assert [round(sum(log.totals.values()), 2) for log in daily_logs] == [24.0] * expected_sheets


# SC-1
def test_short_day_trip_log_totals():
    (daily_log,) = plan_daily_logs(trip((60, 1), (180, 3), 0))
    assert daily_log.totals == {"OFF": 17.5, "SB": 0.0, "D": 4.0, "ON": 2.5}


# SC-2 · AC-33
def test_two_day_trip_logs_match_business_rules_worked_example():
    daily_logs = plan_daily_logs(trip((120, 2), (1080, 18), 20))
    assert [log.totals for log in daily_logs] == [
        {"OFF": 6.5, "SB": 5.25, "D": 11.0, "ON": 1.25},
        {"OFF": 8.5, "SB": 4.75, "D": 9.0, "ON": 1.75},
    ]
    assert [log.header.miles_driving_today for log in daily_logs] == [660.0, 540.0]
    assert [(log.recap.a_last_7, log.recap.b_available_tomorrow) for log in daily_logs] == [
        (32.25, 37.75),
        (43.0, 27.0),
    ]
