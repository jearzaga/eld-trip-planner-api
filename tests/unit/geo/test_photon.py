import json
from pathlib import Path

import httpx
import pytest
import respx

from geo.photon import PhotonGeocoder
from geo.provider import ProviderUnavailable

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "http"

BASE_URL = "https://photon.komoot.io"
GEOCODE_URL = f"{BASE_URL}/api/"
REVERSE_URL = f"{BASE_URL}/reverse"

RICHMOND = (37.5407, -77.4360)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def geocoder() -> PhotonGeocoder:
    return PhotonGeocoder()


@respx.mock(assert_all_mocked=True)
def test_geocode_keeps_only_us_results_deduplicates_and_caps_at_five(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_geocode_richmond.json"))
    )

    places = geocoder().geocode("Richmond")

    assert [place.label for place in places] == [
        "Richmond, VA",
        "Richmond, IN",
        "Richmond Heights, MO",
        "Richmond, CA",
        "Richmond, KY",
    ]


@respx.mock(assert_all_mocked=True)
def test_geocode_place_carries_lat_lng_from_geojson_lng_lat_coordinates(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_geocode_richmond.json"))
    )

    places = geocoder().geocode("Richmond")

    assert (places[0].lat, places[0].lng) == (37.5407, -77.4360)


@respx.mock(assert_all_mocked=True)
def test_geocode_sends_query_limit_and_language(respx_mock):
    mocked = respx_mock.get(GEOCODE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_geocode_richmond.json"))
    )

    geocoder().geocode("Richmond")

    request = mocked.calls.last.request
    assert request.url.params["q"] == "Richmond"
    assert request.url.params["limit"] == "10"
    assert request.url.params["lang"] == "en"


@respx.mock(assert_all_mocked=True)
def test_geocode_skips_features_with_unusable_geometry(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_geocode_missing_geometry.json"))
    )

    places = geocoder().geocode("Richmond")

    assert [place.label for place in places] == ["Richmond, IN"]


@respx.mock(assert_all_mocked=True)
def test_geocode_no_results_returns_empty_list(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json={"features": []}))

    assert geocoder().geocode("Nowhere") == []


@respx.mock(assert_all_mocked=True)
def test_reverse_returns_city_state_from_first_feature(respx_mock):
    respx_mock.get(REVERSE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_reverse_richmond.json"))
    )

    assert geocoder().reverse(RICHMOND) == "Richmond, VA"


@respx.mock(assert_all_mocked=True)
def test_reverse_falls_back_to_town_when_city_is_missing(respx_mock):
    respx_mock.get(REVERSE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_reverse_no_city_field.json"))
    )

    assert geocoder().reverse((38.5307, -78.4680)) == "Luray, VA"


@respx.mock(assert_all_mocked=True)
def test_reverse_non_us_feature_returns_near_best_label(respx_mock):
    respx_mock.get(REVERSE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_reverse_non_us.json"))
    )

    assert geocoder().reverse((42.3149, -83.0458)) == "near Windsor"


@respx.mock(assert_all_mocked=True)
def test_reverse_no_features_returns_coordinate_label_for_wilderness(respx_mock):
    respx_mock.get(REVERSE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_reverse_no_features.json"))
    )

    assert geocoder().reverse((44.2, -110.5)) == "44.20, -110.50"


@respx.mock(assert_all_mocked=True)
def test_reverse_sends_lat_lon_and_language(respx_mock):
    mocked = respx_mock.get(REVERSE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("photon_reverse_richmond.json"))
    )

    geocoder().reverse(RICHMOND)

    request = mocked.calls.last.request
    assert request.url.params["lat"] == "37.5407"
    assert request.url.params["lon"] == "-77.436"
    assert request.url.params["lang"] == "en"


@pytest.mark.parametrize("status_code", [500, 502, 503])
@respx.mock(assert_all_mocked=True)
def test_geocode_server_error_raises_provider_unavailable(status_code, respx_mock):
    respx_mock.get(GEOCODE_URL).mock(return_value=httpx.Response(status_code, text="error"))

    with pytest.raises(ProviderUnavailable):
        geocoder().geocode("Richmond")


@respx.mock(assert_all_mocked=True)
def test_geocode_timeout_raises_provider_unavailable(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(ProviderUnavailable):
        geocoder().geocode("Richmond")


@respx.mock(assert_all_mocked=True)
def test_geocode_connection_error_raises_provider_unavailable(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(ProviderUnavailable):
        geocoder().geocode("Richmond")


@respx.mock(assert_all_mocked=True)
def test_geocode_malformed_body_raises_provider_unavailable(respx_mock):
    respx_mock.get(GEOCODE_URL).mock(
        return_value=httpx.Response(
            200, content=b"not json", headers={"content-type": "text/plain"}
        )
    )

    with pytest.raises(ProviderUnavailable):
        geocoder().geocode("Richmond")


@respx.mock(assert_all_mocked=True)
def test_reverse_timeout_raises_provider_unavailable(respx_mock):
    respx_mock.get(REVERSE_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(ProviderUnavailable):
        geocoder().reverse(RICHMOND)


@respx.mock(assert_all_mocked=True)
def test_reverse_connection_error_raises_provider_unavailable(respx_mock):
    respx_mock.get(REVERSE_URL).mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(ProviderUnavailable):
        geocoder().reverse(RICHMOND)


@respx.mock(assert_all_mocked=True)
def test_reverse_server_error_raises_provider_unavailable(respx_mock):
    respx_mock.get(REVERSE_URL).mock(return_value=httpx.Response(500, text="error"))

    with pytest.raises(ProviderUnavailable):
        geocoder().reverse(RICHMOND)


@respx.mock(assert_all_mocked=True)
def test_reverse_malformed_body_raises_provider_unavailable(respx_mock):
    respx_mock.get(REVERSE_URL).mock(
        return_value=httpx.Response(
            200, content=b"not json", headers={"content-type": "text/plain"}
        )
    )

    with pytest.raises(ProviderUnavailable):
        geocoder().reverse(RICHMOND)
