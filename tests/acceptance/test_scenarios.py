from collections import Counter
from datetime import datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest

from tests.fixtures.scenarios import (
    CROSS_COUNTRY_TRIP,
    CYCLE_FULL_TRIP,
    CYCLE_LIMITED_TRIP,
    PICKUP_AT_CURRENT_LOCATION_TRIP,
    ROUTABLE_SCENARIOS,
    SHORT_DAY_TRIP,
    TWO_DAY_WORKED_EXAMPLE_TRIP,
    UNROUTABLE_TRIP,
)


def plan_trip(api_client, scenario):
    response = api_client.post("/api/trips/", scenario.request, format="json")
    assert response.status_code == 201, response.content
    return response.json()


def stop_types_in_order(trip_plan):
    return [stop["type"] for stop in trip_plan["stops"]]


def daily_totals(trip_plan):
    return [daily_log["totals"] for daily_log in trip_plan["daily_logs"]]


def duty_status_per_minute(trip_plan):
    return [
        segment["status"]
        for daily_log in trip_plan["daily_logs"]
        for segment in daily_log["segments"]
        for _ in range(segment["start_min"], segment["end_min"])
    ]


# SC-1
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_short_day_trip_fits_on_one_log_sheet(api_client):
    trip_plan = plan_trip(api_client, SHORT_DAY_TRIP)
    expected = SHORT_DAY_TRIP.expected
    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    assert daily_totals(trip_plan) == expected["totals"]
    assert stop_types_in_order(trip_plan) == expected["stop_types"]


# SC-2 · AC-33
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_two_day_trip_matches_business_rules_worked_example(api_client):
    trip_plan = plan_trip(api_client, TWO_DAY_WORKED_EXAMPLE_TRIP)
    expected = TWO_DAY_WORKED_EXAMPLE_TRIP.expected
    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    assert daily_totals(trip_plan) == expected["totals"]
    assert stop_types_in_order(trip_plan) == expected["stop_types"]


# SC-3 · AC-31
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_trip_reaching_the_70_hour_cycle_takes_a_34_hour_restart(api_client):
    trip_plan = plan_trip(api_client, CYCLE_LIMITED_TRIP)
    expected = CYCLE_LIMITED_TRIP.expected
    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    assert Counter(stop_types_in_order(trip_plan))["restart_34"] == expected["restart_34"]


# SC-4 · AC-31
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_trip_with_a_full_cycle_starts_with_a_34_hour_restart(api_client):
    trip_plan = plan_trip(api_client, CYCLE_FULL_TRIP)
    expected = CYCLE_FULL_TRIP.expected
    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    assert trip_plan["daily_logs"][0]["totals"] == expected["day_1_totals"]
    assert stop_types_in_order(trip_plan)[0] == expected["first_stop"]


# SC-5 · AC-32
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_cross_country_trip_adds_fuel_rest_and_break_stops(api_client):
    trip_plan = plan_trip(api_client, CROSS_COUNTRY_TRIP)
    expected = CROSS_COUNTRY_TRIP.expected
    stop_counts = Counter(stop_types_in_order(trip_plan))
    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    assert stop_counts["fuel"] == expected["fuel"]
    assert stop_counts["rest_10"] == expected["rest_10"]
    assert stop_counts["break_30"] == expected["break_30"]


# SC-6
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_unroutable_trip_returns_422_route_not_found(api_client):
    expected = UNROUTABLE_TRIP.expected
    response = api_client.post("/api/trips/", UNROUTABLE_TRIP.request, format="json")
    assert response.status_code == expected["status"]
    assert response.json()["error"]["code"] == expected["error_code"]


# SC-7
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_pickup_at_current_location_happens_right_after_pre_trip(api_client):
    trip_plan = plan_trip(api_client, PICKUP_AT_CURRENT_LOCATION_TRIP)
    expected = PICKUP_AT_CURRENT_LOCATION_TRIP.expected
    assert len(trip_plan["daily_logs"]) == expected["log_days"]
    pickup = trip_plan["stops"][0]
    assert pickup["type"] == "pickup"
    assert pickup["mile_marker"] == 0.0
    assert pickup["arrive_at"] == expected["pickup_arrive_at"]


# AC-30
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
@pytest.mark.parametrize("scenario", ROUTABLE_SCENARIOS, ids=lambda scenario: scenario.spec_id)
def test_planned_trip_never_violates_hours_of_service_rules(api_client, scenario):
    trip_plan = plan_trip(api_client, scenario)
    cycle_on_duty_min = scenario.request["cycle_used_hrs"] * 60
    off_duty_streak_min = non_driving_streak_min = shift_driving_min = driving_since_break_min = 0
    shift_start_minute = None
    for minute, status in enumerate(duty_status_per_minute(trip_plan)):
        if status == "D":
            if non_driving_streak_min >= 30:
                driving_since_break_min = 0
            non_driving_streak_min = 0
        else:
            non_driving_streak_min += 1
        if status in ("OFF", "SB"):
            off_duty_streak_min += 1
            continue
        if off_duty_streak_min >= 34 * 60:
            cycle_on_duty_min = 0
        if off_duty_streak_min >= 10 * 60:
            shift_start_minute, shift_driving_min = None, 0
        off_duty_streak_min = 0
        if shift_start_minute is None:
            shift_start_minute = minute
        cycle_on_duty_min += 1
        if status == "D":
            shift_driving_min += 1
            driving_since_break_min += 1
            assert shift_driving_min <= 11 * 60, f"R-01 at minute {minute}"
            assert minute - shift_start_minute < 14 * 60, f"R-02 at minute {minute}"
            assert driving_since_break_min <= 8 * 60, f"R-03 at minute {minute}"
            assert cycle_on_duty_min <= 70 * 60, f"R-04 at minute {minute}"
    fuel_mile_markers = [
        stop["mile_marker"] for stop in trip_plan["stops"] if stop["type"] == "fuel"
    ]
    refuel_points = [0.0, *fuel_mile_markers, trip_plan["summary"]["total_miles"]]
    assert all(
        next_point - previous_point <= 1000
        for previous_point, next_point in pairwise(refuel_points)
    ), "R-06"
    for stop in trip_plan["stops"]:
        if stop["type"] in ("pickup", "dropoff"):
            assert stop["duration_min"] == 60, "R-07"


# AC-35
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
@pytest.mark.parametrize("scenario", ROUTABLE_SCENARIOS, ids=lambda scenario: scenario.spec_id)
def test_logs_use_quarter_hours_in_the_home_timezone(api_client, scenario):
    trip_plan = plan_trip(api_client, scenario)
    home_timezone = ZoneInfo(scenario.request["home_timezone"])
    for daily_log in trip_plan["daily_logs"]:
        segments = daily_log["segments"]
        assert segments[0]["start_min"] == 0
        assert segments[-1]["end_min"] == 1440
        for previous_segment, next_segment in pairwise(segments):
            assert previous_segment["end_min"] == next_segment["start_min"]
        assert all(
            segment["start_min"] % 15 == 0 and segment["end_min"] % 15 == 0 for segment in segments
        )
        assert sum(daily_log["totals"].values()) == 24.0
    timestamps = [trip_plan["summary"]["start_at"], trip_plan["summary"]["end_at"]]
    timestamps += [stop[key] for stop in trip_plan["stops"] for key in ("arrive_at", "depart_at")]
    for timestamp in timestamps:
        parsed = datetime.fromisoformat(timestamp)
        assert parsed.utcoffset() == parsed.astimezone(home_timezone).utcoffset(), timestamp
