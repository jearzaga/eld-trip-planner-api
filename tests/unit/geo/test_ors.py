import json
from pathlib import Path

import httpx
import pytest
import respx

from geo.ors import OrsRouter
from geo.provider import ProviderUnavailable, RouteNotFound

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "http"

BASE_URL = "https://api.openrouteservice.org"
DIRECTIONS_URL = f"{BASE_URL}/v2/directions/driving-hgv/geojson"

RICHMOND = (37.5407, -77.4360)
BALTIMORE = (39.2904, -76.6122)
KANSAS_CITY = (39.0997, -94.5786)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def router() -> OrsRouter:
    return OrsRouter(api_key="test-ors-key")


@respx.mock(assert_all_mocked=True)
def test_route_returns_one_leg_per_segment_in_miles_and_hours(respx_mock):
    fixture = load_fixture("ors_route_two_legs.json")
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(200, json=fixture))

    legs = router().route([RICHMOND, BALTIMORE, KANSAS_CITY])

    segments = fixture["features"][0]["properties"]["segments"]
    assert len(legs) == 2
    assert legs[0].distance_mi == pytest.approx(segments[0]["distance"] / 1609.344)
    assert legs[0].duration_h == pytest.approx(segments[0]["duration"] / 3600)
    assert legs[1].distance_mi == pytest.approx(segments[1]["distance"] / 1609.344)
    assert legs[1].duration_h == pytest.approx(segments[1]["duration"] / 3600)


@respx.mock(assert_all_mocked=True)
def test_route_splits_geometry_per_leg_using_way_points_inclusive(respx_mock):
    fixture = load_fixture("ors_route_two_legs.json")
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(200, json=fixture))

    legs = router().route([RICHMOND, BALTIMORE, KANSAS_CITY])

    assert legs[0].geometry == [
        (-77.4360, 37.5407),
        (-77.2000, 37.8000),
        (-76.9000, 38.6000),
        (-76.6122, 39.2904),
    ]
    assert legs[1].geometry[0] == (-76.6122, 39.2904)
    assert legs[1].geometry[-1] == (-94.5786, 39.0997)


@respx.mock(assert_all_mocked=True)
def test_route_sends_coordinates_in_lng_lat_order_with_auth_header(respx_mock):
    fixture = load_fixture("ors_route_two_legs.json")
    mocked = respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(200, json=fixture))

    router().route([RICHMOND, BALTIMORE, KANSAS_CITY])

    request = mocked.calls.last.request
    assert request.headers["authorization"] == "test-ors-key"
    body = json.loads(request.content)
    assert body["coordinates"] == [
        [-77.4360, 37.5407],
        [-76.6122, 39.2904],
        [-94.5786, 39.0997],
    ]


@respx.mock(assert_all_mocked=True)
def test_zero_length_leg_when_ors_still_returns_a_segment_for_identical_points(respx_mock):
    fixture = load_fixture("ors_route_duplicate_point_with_segment.json")
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(200, json=fixture))

    legs = router().route([RICHMOND, BALTIMORE, BALTIMORE])

    assert len(legs) == 2
    assert legs[1].distance_mi == 0
    assert legs[1].duration_h == 0
    assert legs[1].geometry == [(-76.6122, 39.2904), (-76.6122, 39.2904)]


@respx.mock(assert_all_mocked=True)
def test_zero_length_leg_is_synthesized_when_ors_omits_the_segment_for_duplicate_points(respx_mock):
    fixture = load_fixture("ors_route_missing_segment_for_duplicate.json")
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(200, json=fixture))

    legs = router().route([RICHMOND, BALTIMORE, BALTIMORE])

    assert len(legs) == 2
    assert legs[0].distance_mi > 0
    assert legs[1].distance_mi == 0
    assert legs[1].duration_h == 0
    assert legs[1].geometry == [(-76.6122, 39.2904), (-76.6122, 39.2904)]


@respx.mock(assert_all_mocked=True)
def test_http_404_raises_route_not_found(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )

    with pytest.raises(RouteNotFound):
        router().route([RICHMOND, BALTIMORE])


@pytest.mark.parametrize(
    "fixture_name",
    ["ors_error_no_route_2009.json", "ors_error_unroutable_point_2010.json"],
)
@respx.mock(assert_all_mocked=True)
def test_http_400_with_no_route_error_code_raises_route_not_found(fixture_name, respx_mock):
    body = load_fixture(fixture_name)
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(400, json=body))

    with pytest.raises(RouteNotFound):
        router().route([RICHMOND, BALTIMORE])


@respx.mock(assert_all_mocked=True)
def test_http_400_with_other_error_code_raises_provider_unavailable(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(
        return_value=httpx.Response(
            400, json={"error": {"code": 6010, "message": "unknown parameter"}}
        )
    )

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])


@respx.mock(assert_all_mocked=True)
def test_http_400_with_malformed_error_body_raises_provider_unavailable(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(
        return_value=httpx.Response(
            400, content=b"not json", headers={"content-type": "text/plain"}
        )
    )

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])


@pytest.mark.parametrize("status_code", [401, 403, 429, 500, 503])
@respx.mock(assert_all_mocked=True)
def test_bad_key_rate_limit_and_server_errors_raise_provider_unavailable(status_code, respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(status_code, text="error"))

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])


@respx.mock(assert_all_mocked=True)
def test_timeout_raises_provider_unavailable(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])


@respx.mock(assert_all_mocked=True)
def test_connection_error_raises_provider_unavailable(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])


@respx.mock(assert_all_mocked=True)
def test_malformed_success_body_raises_provider_unavailable(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(return_value=httpx.Response(200, json={"features": []}))

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])


@respx.mock(assert_all_mocked=True)
def test_non_json_success_body_raises_provider_unavailable(respx_mock):
    respx_mock.post(DIRECTIONS_URL).mock(
        return_value=httpx.Response(
            200, content=b"not json", headers={"content-type": "text/plain"}
        )
    )

    with pytest.raises(ProviderUnavailable):
        router().route([RICHMOND, BALTIMORE])
