import json
from pathlib import Path

from trips.serializers import (
    ErrorResponseSerializer,
    GeocodeResultSerializer,
    TripResponseSerializer,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "trip_response_example.json"


def load_example():
    return json.loads(FIXTURE_PATH.read_text())


def test_trip_response_serializer_matches_example_fixture_exactly():
    example = load_example()
    assert TripResponseSerializer(example).data == example


def test_route_leg_from_to_keys_are_literal():
    example = load_example()
    leg = TripResponseSerializer(example).data["route"]["legs"][0]
    assert leg["from"] == "current"
    assert leg["to"] == "pickup"


def test_daily_log_header_from_to_keys_are_literal():
    example = load_example()
    header = TripResponseSerializer(example).data["daily_logs"][0]["header"]
    assert header["from"] == "Richmond, VA"
    assert header["to"] == "Philadelphia, PA"


def test_geocode_result_serializer_matches_shape():
    place = {"label": "Richmond, VA", "lat": 37.5407, "lng": -77.436}
    assert GeocodeResultSerializer(place).data == place


def test_error_response_serializer_matches_shape():
    error = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request.",
            "fields": {"cycle_used_hrs": ["Must be between 0 and 70."]},
        }
    }
    assert ErrorResponseSerializer(error).data == error


def test_error_response_serializer_allows_empty_fields():
    error = {
        "error": {
            "code": "ROUTE_NOT_FOUND",
            "message": "No route found.",
            "fields": {},
        }
    }
    assert ErrorResponseSerializer(error).data == error
