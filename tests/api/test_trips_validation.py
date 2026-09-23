import pytest

from trips.serializers import TripRequestSerializer

VALID_REQUEST = {
    "current": {"label": "Richmond, VA", "lat": 37.5407, "lng": -77.4360},
    "pickup": {"label": "Fredericksburg, VA", "lat": 38.3032, "lng": -77.4605},
    "dropoff": {"label": "Philadelphia, PA", "lat": 39.9526, "lng": -75.1652},
    "cycle_used_hrs": 20,
    "start_time": "2026-09-24T06:00",
    "home_timezone": "America/New_York",
    "include_inspections": True,
    "log_meta": {"driver_name": "John Doe", "co_driver_name": ""},
}


def make_request(**overrides):
    return {**VALID_REQUEST, **overrides}


@pytest.mark.parametrize("field", ["current", "pickup", "dropoff", "cycle_used_hrs"])
def test_missing_required_field_is_rejected(field):
    data = {k: v for k, v in VALID_REQUEST.items() if k != field}
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert field in serializer.errors


@pytest.mark.parametrize("lat", [-90.1, 90.1])
def test_out_of_range_latitude_is_rejected(lat):
    data = make_request(current={**VALID_REQUEST["current"], "lat": lat})
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "lat" in serializer.errors["current"]


@pytest.mark.parametrize("lng", [-180.1, 180.1])
def test_out_of_range_longitude_is_rejected(lng):
    data = make_request(current={**VALID_REQUEST["current"], "lng": lng})
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "lng" in serializer.errors["current"]


def test_blank_label_is_rejected():
    data = make_request(pickup={**VALID_REQUEST["pickup"], "label": ""})
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "label" in serializer.errors["pickup"]


@pytest.mark.parametrize("cycle_used_hrs", [0, 70, 20.25, 69.75])
def test_cycle_used_hrs_within_range_and_on_step_is_accepted(cycle_used_hrs):
    data = make_request(cycle_used_hrs=cycle_used_hrs)
    serializer = TripRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["cycle_used_hrs"] == float(cycle_used_hrs)
    assert isinstance(serializer.validated_data["cycle_used_hrs"], float)


def test_cycle_used_hrs_above_seventy_is_rejected():
    data = make_request(cycle_used_hrs=70.25)
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "cycle_used_hrs" in serializer.errors


def test_cycle_used_hrs_below_zero_is_rejected():
    data = make_request(cycle_used_hrs=-0.25)
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "cycle_used_hrs" in serializer.errors


def test_cycle_used_hrs_off_quarter_hour_step_is_rejected():
    data = make_request(cycle_used_hrs=20.1)
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "cycle_used_hrs" in serializer.errors


@pytest.mark.parametrize(
    "start_time",
    ["2026-09-24 06:00", "09/24/2026T06:00", "2026-09-24T06", "not-a-time"],
)
def test_start_time_bad_format_is_rejected(start_time):
    data = make_request(start_time=start_time)
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "start_time" in serializer.errors


def test_start_time_off_quarter_hour_minute_is_rejected():
    data = make_request(start_time="2026-09-24T06:07")
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "start_time" in serializer.errors


def test_start_time_valid_string_is_kept_as_string():
    serializer = TripRequestSerializer(data=make_request(start_time="2026-09-24T06:15"))
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["start_time"] == "2026-09-24T06:15"
    assert isinstance(serializer.validated_data["start_time"], str)


def test_start_time_is_optional_and_nullable():
    data = {k: v for k, v in VALID_REQUEST.items() if k != "start_time"}
    serializer = TripRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert "start_time" not in serializer.validated_data

    serializer = TripRequestSerializer(data={**data, "start_time": None})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["start_time"] is None


def test_unknown_timezone_is_rejected():
    data = make_request(home_timezone="Mars/Olympus_Mons")
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "home_timezone" in serializer.errors


def test_home_timezone_is_optional_and_nullable():
    data = {k: v for k, v in VALID_REQUEST.items() if k != "home_timezone"}
    serializer = TripRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert "home_timezone" not in serializer.validated_data

    serializer = TripRequestSerializer(data={**data, "home_timezone": None})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["home_timezone"] is None


def test_known_timezone_is_accepted():
    serializer = TripRequestSerializer(data=make_request(home_timezone="America/Chicago"))
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["home_timezone"] == "America/Chicago"


def test_log_meta_co_driver_name_blank_is_allowed():
    data = make_request(log_meta={"co_driver_name": ""})
    serializer = TripRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["log_meta"]["co_driver_name"] == ""


def test_log_meta_driver_name_blank_is_rejected():
    data = make_request(log_meta={"driver_name": ""})
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "driver_name" in serializer.errors["log_meta"]


def test_log_meta_field_over_max_length_is_rejected():
    data = make_request(log_meta={"driver_name": "x" * 201})
    serializer = TripRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "driver_name" in serializer.errors["log_meta"]


def test_minimal_valid_request_validated_data_has_only_required_keys():
    minimal = {
        "current": VALID_REQUEST["current"],
        "pickup": VALID_REQUEST["pickup"],
        "dropoff": VALID_REQUEST["dropoff"],
        "cycle_used_hrs": 0,
    }
    serializer = TripRequestSerializer(data=minimal)
    assert serializer.is_valid(), serializer.errors
    assert set(serializer.validated_data.keys()) == {
        "current",
        "pickup",
        "dropoff",
        "cycle_used_hrs",
    }


def test_unknown_top_level_keys_are_ignored():
    data = make_request(unexpected_field="surprise")
    serializer = TripRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert "unexpected_field" not in serializer.validated_data
