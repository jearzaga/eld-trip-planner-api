from django.http import Http404
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotFound,
    ParseError,
    UnsupportedMediaType,
    ValidationError,
)

from geo.provider import ProviderUnavailable, RouteNotFound
from trips.exceptions import api_exception_handler


def test_nested_validation_errors_flatten_to_dot_joined_paths():
    exc = ValidationError(
        {
            "current": {"lat": ["Ensure this value is less than or equal to 90."]},
            "cycle_used_hrs": ["A valid number is required."],
        }
    )

    response = api_exception_handler(exc, {})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    assert response.data["error"]["message"] == "Invalid request."
    assert response.data["error"]["fields"] == {
        "current.lat": ["Ensure this value is less than or equal to 90."],
        "cycle_used_hrs": ["A valid number is required."],
    }


def test_validation_errors_in_lists_use_numeric_indices():
    exc = ValidationError({"stops": [{}, {"label": ["This field is required."]}]})

    response = api_exception_handler(exc, {})

    assert response.data["error"]["fields"] == {"stops.1.label": ["This field is required."]}


def test_validation_error_leaf_not_wrapped_in_a_list_is_still_flattened():
    exc = ValidationError({"q": "Search query must be at least 3 characters."})

    response = api_exception_handler(exc, {})

    assert response.data["error"]["fields"] == {
        "q": ["Search query must be at least 3 characters."]
    }


def test_top_level_list_validation_errors_go_under_non_field_errors():
    exc = ValidationError(["Pickup must be reachable from current location."])

    response = api_exception_handler(exc, {})

    assert response.data["error"]["fields"] == {
        "non_field_errors": ["Pickup must be reachable from current location."]
    }


def test_parse_error_maps_to_validation_error_with_no_fields():
    exc = ParseError("JSON parse error - Expecting value: line 1 column 1 (char 0)")

    response = api_exception_handler(exc, {})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    assert response.data["error"]["fields"] == {}


def test_django_http404_maps_to_not_found():
    response = api_exception_handler(Http404(), {})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"
    assert response.data["error"]["fields"] == {}


def test_drf_not_found_maps_to_not_found():
    response = api_exception_handler(NotFound(), {})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"


def test_route_not_found_maps_to_422():
    response = api_exception_handler(RouteNotFound("SC-6"), {})

    assert response.status_code == 422
    assert response.data["error"]["code"] == "ROUTE_NOT_FOUND"
    assert response.data["error"]["message"] == "No truck route connects these locations."
    assert response.data["error"]["fields"] == {}


def test_provider_unavailable_maps_to_502_without_leaking_upstream_text():
    response = api_exception_handler(ProviderUnavailable("connection refused to ors.example"), {})

    assert response.status_code == 502
    assert response.data["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "connection refused" not in response.data["error"]["message"]
    assert "ors.example" not in response.data["error"]["message"]


def test_method_not_allowed_uses_its_status_and_upper_cased_default_code():
    response = api_exception_handler(MethodNotAllowed("DELETE"), {})

    assert response.status_code == 405
    assert response.data["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_unsupported_media_type_uses_its_status_and_upper_cased_default_code():
    response = api_exception_handler(UnsupportedMediaType("text/plain"), {})

    assert response.status_code == 415
    assert response.data["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_unknown_exception_returns_none_to_let_django_handle_it():
    assert api_exception_handler(KeyError("boom"), {}) is None


def test_method_not_allowed_on_health_endpoint_uses_standard_error_shape(api_client):
    res = api_client.delete("/api/health/")

    assert res.status_code == 405
    body = res.json()
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert body["error"]["fields"] == {}
