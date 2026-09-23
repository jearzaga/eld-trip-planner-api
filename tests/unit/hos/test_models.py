import dataclasses

import pytest

from hos.models import DutyStatus, Leg, Segment, Stop, StopType, Timeline, TripInput
from hos.rules import CYCLE_LIMIT_MIN, MAX_DRIVING_MIN, SHIFT_WINDOW_MIN


def test_duty_status_values_match_log_grid_rows():
    assert [status.value for status in DutyStatus] == ["OFF", "SB", "D", "ON"]


def test_stop_type_values_match_api_contract():
    assert {stop_type.value for stop_type in StopType} == {
        "pickup",
        "fuel",
        "break_30",
        "rest_10",
        "restart_34",
        "dropoff",
    }


def test_leg_speed_is_distance_over_duration():
    assert Leg(distance_mi=120, duration_min=120).mph == 60


def test_zero_mile_leg_has_zero_speed():
    assert Leg(distance_mi=0, duration_min=0).mph == 0


def test_segment_duration_and_immutability():
    driving = Segment(DutyStatus.D, start_min=15, end_min=135, mile_marker=0)
    assert driving.duration_min == 120
    assert driving.note is None and driving.location is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        driving.end_min = 150


def test_timeline_and_trip_input_defaults():
    trip = TripInput(legs=(Leg(60, 60), Leg(180, 180)), cycle_used_min=0)
    assert trip.include_inspections is True
    pickup = Stop(StopType.PICKUP, DutyStatus.ON, start_min=75, end_min=135, mile_marker=60)
    assert Timeline(segments=(), stops=(pickup,)).stops[0].duration_min == 60


# R-01 · R-02 · R-04
def test_rule_limits_are_in_minutes():
    assert (MAX_DRIVING_MIN, SHIFT_WINDOW_MIN, CYCLE_LIMIT_MIN) == (660, 840, 4200)
