from collections import Counter
from datetime import datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest

from tests.fixtures.scenarios import ROUTABLE


def _plan(api_client, scenario, sc_id):
    res = api_client.post("/api/trips/", scenario(sc_id).request, format="json")
    assert res.status_code == 201, res.content
    return res.json()


def _stop_types(body):
    return [s["type"] for s in body["stops"]]


def _timeline(body):
    return [
        seg["status"]
        for day in body["daily_logs"]
        for seg in day["segments"]
        for _ in range(seg["start_min"], seg["end_min"])
    ]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc1_short_day(api_client, scenario):
    body = _plan(api_client, scenario, "SC-1")
    expected = scenario("SC-1").expected
    assert len(body["daily_logs"]) == expected["log_days"]
    assert [d["totals"] for d in body["daily_logs"]] == expected["totals"]
    assert _stop_types(body) == expected["stop_types"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc2_ac33_matches_worked_example(api_client, scenario):
    body = _plan(api_client, scenario, "SC-2")
    expected = scenario("SC-2").expected
    assert len(body["daily_logs"]) == expected["log_days"]
    assert [d["totals"] for d in body["daily_logs"]] == expected["totals"]
    assert _stop_types(body) == expected["stop_types"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc3_ac31_high_cycle_takes_34h_restart(api_client, scenario):
    body = _plan(api_client, scenario, "SC-3")
    expected = scenario("SC-3").expected
    assert len(body["daily_logs"]) == expected["log_days"]
    assert Counter(_stop_types(body))["restart_34"] == expected["restart_34"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc4_ac31_full_cycle_starts_with_restart(api_client, scenario):
    body = _plan(api_client, scenario, "SC-4")
    expected = scenario("SC-4").expected
    assert len(body["daily_logs"]) == expected["log_days"]
    assert body["daily_logs"][0]["totals"] == expected["day_1_totals"]
    assert _stop_types(body)[0] == expected["first_stop"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc5_ac32_cross_country(api_client, scenario):
    body = _plan(api_client, scenario, "SC-5")
    expected = scenario("SC-5").expected
    counts = Counter(_stop_types(body))
    assert len(body["daily_logs"]) == expected["log_days"]
    assert counts["fuel"] == expected["fuel"]
    assert counts["rest_10"] == expected["rest_10"]
    assert counts["break_30"] == expected["break_30"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc6_unroutable_returns_422(api_client, scenario):
    expected = scenario("SC-6").expected
    res = api_client.post("/api/trips/", scenario("SC-6").request, format="json")
    assert res.status_code == expected["status"]
    assert res.json()["error"]["code"] == expected["error_code"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_sc7_pickup_at_current_location(api_client, scenario):
    body = _plan(api_client, scenario, "SC-7")
    expected = scenario("SC-7").expected
    assert len(body["daily_logs"]) == expected["log_days"]
    pickup = body["stops"][0]
    assert pickup["type"] == "pickup"
    assert pickup["mile_marker"] == 0.0
    assert pickup["arrive_at"] == expected["pickup_arrive_at"]


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
@pytest.mark.parametrize("sc_id", ROUTABLE)
def test_ac30_plan_never_violates_hos(api_client, scenario, sc_id):
    body = _plan(api_client, scenario, sc_id)
    cycle = scenario(sc_id).request["cycle_used_hrs"] * 60
    off = non_driving = in_shift = since_break = 0
    shift_start = None
    for t, status in enumerate(_timeline(body)):
        if status == "D":
            if non_driving >= 30:
                since_break = 0
            non_driving = 0
        else:
            non_driving += 1
        if status in ("OFF", "SB"):
            off += 1
            continue
        if off >= 34 * 60:
            cycle = 0
        if off >= 10 * 60:
            shift_start, in_shift = None, 0
        off = 0
        if shift_start is None:
            shift_start = t
        cycle += 1
        if status == "D":
            in_shift += 1
            since_break += 1
            assert in_shift <= 11 * 60, f"R-01 at minute {t}"
            assert t - shift_start < 14 * 60, f"R-02 at minute {t}"
            assert since_break <= 8 * 60, f"R-03 at minute {t}"
            assert cycle <= 70 * 60, f"R-04 at minute {t}"
    fuel_markers = [s["mile_marker"] for s in body["stops"] if s["type"] == "fuel"]
    markers = [0.0, *fuel_markers, body["summary"]["total_miles"]]
    assert all(b - a <= 1000 for a, b in pairwise(markers)), "R-06"
    for stop in body["stops"]:
        if stop["type"] in ("pickup", "dropoff"):
            assert stop["duration_min"] == 60, "R-07"


@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
@pytest.mark.parametrize("sc_id", ROUTABLE)
def test_ac35_quarter_hours_in_home_timezone(api_client, scenario, sc_id):
    body = _plan(api_client, scenario, sc_id)
    home = ZoneInfo(scenario(sc_id).request["home_timezone"])
    for day in body["daily_logs"]:
        segments = day["segments"]
        assert segments[0]["start_min"] == 0
        assert segments[-1]["end_min"] == 1440
        for a, b in pairwise(segments):
            assert a["end_min"] == b["start_min"]
        assert all(s["start_min"] % 15 == 0 and s["end_min"] % 15 == 0 for s in segments)
        assert sum(day["totals"].values()) == 24.0
    stamps = [body["summary"]["start_at"], body["summary"]["end_at"]]
    stamps += [s[k] for s in body["stops"] for k in ("arrive_at", "depart_at")]
    for stamp in stamps:
        dt = datetime.fromisoformat(stamp)
        assert dt.utcoffset() == dt.astimezone(home).utcoffset(), stamp
