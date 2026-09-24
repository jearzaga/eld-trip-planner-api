import copy
import json
from pathlib import Path

import pytest

from trips.models import Trip

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "trip_response_example.json"


def _load_example() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.mark.django_db
def test_round_trip_preserves_the_short_day_trip_response_exactly():
    plan = _load_example()
    del plan["id"]

    trip = Trip.from_plan(plan)
    trip.save()

    reloaded = Trip.objects.get(pk=trip.pk)
    response = reloaded.to_response()

    expected = copy.deepcopy(plan)
    expected["id"] = str(trip.pk)
    assert response == expected
    assert str(reloaded) == f"Trip {reloaded.pk} Fredericksburg, VA -> Philadelphia, PA"


def _second_scenario() -> dict:
    plan = _load_example()
    del plan["id"]

    plan["inputs"]["home_timezone"] = "America/Los_Angeles"
    plan["inputs"]["start_time"] = "2026-09-24T06:00"
    plan["summary"]["home_timezone"] = "America/Los_Angeles"
    plan["summary"]["start_at"] = "2026-09-24T06:00:00-07:00"
    plan["summary"]["arrive_at"] = "2026-09-24T11:15:00-07:00"
    plan["summary"]["end_at"] = "2026-09-24T12:30:00-07:00"
    plan["summary"]["cycle_used_end_hrs"] = 40.5

    plan["stops"] = [
        {
            "seq": 1,
            "type": "rest_10",
            "label": "near Redding, CA",
            "lat": 40.5865,
            "lng": -122.3917,
            "mile_marker": 60.0,
            "arrive_at": "2026-09-24T07:15:00-07:00",
            "depart_at": "2026-09-24T17:15:00-07:00",
            "duration_min": 600,
            "status": "SB",
            "reason": "11-hour driving limit reached",
        },
        {
            "seq": 2,
            "type": "restart_34",
            "label": "near Sacramento, CA",
            "lat": 38.5816,
            "lng": -121.4944,
            "mile_marker": 120.0,
            "arrive_at": "2026-09-25T08:00:00-07:00",
            "depart_at": "2026-09-26T18:00:00-07:00",
            "duration_min": 2040,
            "status": "SB",
            "reason": "70-hour / 8-day limit reached",
        },
        {
            "seq": 3,
            "type": "dropoff",
            "label": "Portland, OR",
            "lat": 45.5152,
            "lng": -122.6784,
            "mile_marker": 240.0,
            "arrive_at": "2026-09-26T22:15:00-07:00",
            "depart_at": "2026-09-26T23:15:00-07:00",
            "duration_min": 60,
            "status": "ON",
            "reason": "1 hour on duty to unload",
        },
    ]
    plan["summary"]["stop_count"] = 3

    second_day = copy.deepcopy(plan["daily_logs"][0])
    second_day["day_number"] = 2
    second_day["date"] = "2026-09-25"
    second_day["header"]["from"] = "near Sacramento, CA"
    second_day["header"]["to"] = "near Sacramento, CA"
    second_day["header"]["miles_driving_today"] = 0.0
    second_day["header"]["total_mileage_today"] = 0.0
    second_day["segments"] = [
        {"status": "SB", "start_min": 0, "end_min": 1440, "note": None, "location": None}
    ]
    second_day["remarks"] = []
    second_day["totals"] = {"OFF": 0.0, "SB": 24.0, "D": 0.0, "ON": 0.0}
    second_day["recap"] = {
        "on_duty_today": 0.0,
        "a_last_7": 6.5,
        "b_available_tomorrow": 63.5,
        "c_last_5": 6.5,
        "restart_34_taken": True,
    }
    plan["daily_logs"].append(second_day)
    plan["summary"]["log_days"] = 2

    return plan


@pytest.mark.django_db
def test_round_trip_preserves_restart_and_second_day_with_a_non_eastern_timezone():
    plan = _second_scenario()

    trip = Trip.from_plan(plan)
    trip.save()

    reloaded = Trip.objects.get(pk=trip.pk)
    response = reloaded.to_response()

    expected = copy.deepcopy(plan)
    expected["id"] = str(trip.pk)
    assert response == expected


@pytest.mark.django_db
def test_trip_saved_before_stop_reasons_existed_reads_a_null_reason():
    plan = _load_example()
    del plan["id"]
    for stop in plan["stops"]:
        del stop["reason"]

    trip = Trip.from_plan(plan)
    trip.save()

    stops = Trip.objects.get(pk=trip.pk).to_response()["stops"]
    assert [stop["reason"] for stop in stops] == [None, None]
