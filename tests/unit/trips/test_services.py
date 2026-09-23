import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from geo.fake import FakeGeoProvider
from geo.provider import RouteNotFound
from tests.fixtures.scenarios import (
    CYCLE_FULL_TRIP,
    LOS_ANGELES,
    PHILADELPHIA,
    PICKUP_AT_CURRENT_LOCATION_TRIP,
    SHORT_DAY_TRIP,
    TWO_DAY_WORKED_EXAMPLE_TRIP,
    UNROUTABLE_TRIP,
)
from trips.services import plan_trip

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


class _SpyGeoProvider(FakeGeoProvider):
    def __init__(self):
        self.reverse_calls: list[tuple[float, float]] = []

    def reverse(self, point):
        self.reverse_calls.append(point)
        return super().reverse(point)


# SC-1
def test_golden_short_day_trip_matches_contract_example():
    expected = json.loads((FIXTURES_DIR / "trip_response_example.json").read_text())
    expected.pop("id")

    trip_plan = plan_trip(SHORT_DAY_TRIP.request, FakeGeoProvider())

    assert trip_plan == expected


# SC-2 · AC-33
def test_two_day_worked_example_matches_business_rules():
    trip_plan = plan_trip(TWO_DAY_WORKED_EXAMPLE_TRIP.request, FakeGeoProvider())
    expected = TWO_DAY_WORKED_EXAMPLE_TRIP.expected

    assert [log["totals"] for log in trip_plan["daily_logs"]] == expected["totals"]
    assert [stop["type"] for stop in trip_plan["stops"]] == expected["stop_types"]

    summary = trip_plan["summary"]
    assert summary["total_miles"] == 1200.0
    assert summary["total_driving_hrs"] == 20.0
    assert summary["total_on_duty_hrs"] == 23.0
    assert summary["cycle_used_end_hrs"] == 43.0
    assert summary["arrive_at"] == "2026-09-25T14:15:00-04:00"
    assert summary["end_at"] == "2026-09-25T15:30:00-04:00"

    assert trip_plan["daily_logs"][0]["header"]["from"] == "Richmond, VA"

    non_terminal_labels = [
        stop["label"] for stop in trip_plan["stops"] if stop["type"] not in ("pickup", "dropoff")
    ]
    assert non_terminal_labels and all(non_terminal_labels)


# SC-4
def test_cycle_full_trip_starts_with_restart_and_reports_cycle_used_since_restart():
    trip_plan = plan_trip(CYCLE_FULL_TRIP.request, FakeGeoProvider())
    expected = CYCLE_FULL_TRIP.expected

    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    assert trip_plan["daily_logs"][0]["totals"] == expected["day_1_totals"]
    assert trip_plan["stops"][0]["type"] == expected["first_stop"]
    assert trip_plan["summary"]["cycle_used_end_hrs"] == 6.5


# SC-6
def test_unroutable_trip_raises_route_not_found():
    with pytest.raises(RouteNotFound):
        plan_trip(UNROUTABLE_TRIP.request, FakeGeoProvider())


# SC-7
def test_pickup_at_current_location_arrives_right_after_pre_trip():
    trip_plan = plan_trip(PICKUP_AT_CURRENT_LOCATION_TRIP.request, FakeGeoProvider())
    expected = PICKUP_AT_CURRENT_LOCATION_TRIP.expected

    pickup_stop = trip_plan["stops"][0]
    assert pickup_stop["type"] == "pickup"
    assert pickup_stop["mile_marker"] == 0.0
    assert pickup_stop["arrive_at"] == expected["pickup_arrive_at"]


# A-11
def test_home_timezone_defaults_from_current_location_when_missing():
    request = {
        "current": LOS_ANGELES,
        "pickup": LOS_ANGELES,
        "dropoff": PHILADELPHIA,
        "cycle_used_hrs": 0,
        "start_time": "2026-09-24T06:00",
    }

    trip_plan = plan_trip(request, FakeGeoProvider())

    assert trip_plan["inputs"]["home_timezone"] == "America/Los_Angeles"
    assert trip_plan["summary"]["start_at"] == "2026-09-24T06:00:00-07:00"


# A-11
def test_start_time_defaults_to_next_quarter_hour_at_or_after_now():
    request = {**SHORT_DAY_TRIP.request, "home_timezone": "America/New_York"}
    request.pop("start_time")
    now = datetime(2026, 9, 24, 13, 32, tzinfo=UTC)  # 09:32 America/New_York

    trip_plan = plan_trip(request, FakeGeoProvider(), now=now)

    assert trip_plan["inputs"]["start_time"] == "2026-09-24T09:45"
    assert trip_plan["summary"]["start_at"] == "2026-09-24T09:45:00-04:00"


# A-11
def test_start_time_default_keeps_now_when_already_on_a_quarter_hour():
    request = {**SHORT_DAY_TRIP.request, "home_timezone": "America/New_York"}
    request.pop("start_time")
    now = datetime(2026, 9, 24, 13, 30, tzinfo=UTC)  # 09:30 America/New_York, exact quarter hour

    trip_plan = plan_trip(request, FakeGeoProvider(), now=now)

    assert trip_plan["inputs"]["start_time"] == "2026-09-24T09:30"


def test_missing_log_meta_uses_log_meta_defaults():
    request = dict(SHORT_DAY_TRIP.request)
    assert "log_meta" not in request

    trip_plan = plan_trip(request, FakeGeoProvider())

    assert trip_plan["inputs"]["log_meta"]["driver_name"] == "John Doe"
    assert trip_plan["inputs"]["log_meta"]["carrier_name"] == "John Doe's Transportation"


def test_partial_log_meta_merges_with_defaults():
    request = {
        **SHORT_DAY_TRIP.request,
        "log_meta": {"driver_name": "Jane Roe", "trailer_no": "789"},
    }

    trip_plan = plan_trip(request, FakeGeoProvider())

    log_meta = trip_plan["inputs"]["log_meta"]
    assert log_meta["driver_name"] == "Jane Roe"
    assert log_meta["trailer_no"] == "789"
    assert log_meta["carrier_name"] == "John Doe's Transportation"
    assert trip_plan["daily_logs"][0]["header"]["driver_name"] == "Jane Roe"


# A-06
def test_include_inspections_false_omits_inspection_segments():
    request = {**SHORT_DAY_TRIP.request, "include_inspections": False}

    trip_plan = plan_trip(request, FakeGeoProvider())

    notes = [
        segment["note"]
        for log in trip_plan["daily_logs"]
        for segment in log["segments"]
        if segment["note"]
    ]
    assert "Pre-trip inspection" not in notes
    assert "Post-trip inspection" not in notes
    assert trip_plan["inputs"]["include_inspections"] is False


def test_reverse_geocoding_happens_once_per_distinct_point():
    spy = _SpyGeoProvider()

    plan_trip(TWO_DAY_WORKED_EXAMPLE_TRIP.request, spy)

    assert spy.reverse_calls
    assert len(spy.reverse_calls) == len(set(spy.reverse_calls))
