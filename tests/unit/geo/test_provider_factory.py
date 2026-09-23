import pytest

from geo.cache import CachedGeoProvider
from geo.fake import FakeGeoProvider
from geo.ors import OrsRouter
from geo.photon import PhotonGeocoder
from geo.provider import (
    GeoProvider,
    LiveGeoProvider,
    Place,
    ProviderUnavailable,
    RouteNotFound,
    get_provider,
)


def test_fake_provider_selected_by_name():
    assert isinstance(get_provider("fake"), FakeGeoProvider)


def test_default_provider_comes_from_geo_provider_setting(settings):
    settings.GEO_PROVIDER = "fake"
    assert isinstance(get_provider(), FakeGeoProvider)


def test_unknown_provider_rejected():
    with pytest.raises(ValueError, match="nope"):
        get_provider("nope")


def test_geo_provider_protocol_covers_routing_and_geocoding():
    assert {"route", "geocode", "reverse"} <= GeoProvider.__protocol_attrs__


def test_route_not_found_and_provider_unavailable_are_distinct_errors():
    assert not issubclass(RouteNotFound, ProviderUnavailable)
    assert not issubclass(ProviderUnavailable, RouteNotFound)


def test_place_carries_label_and_coordinates():
    place = Place(label="Richmond, VA", lat=37.5407, lng=-77.4360)

    assert (place.label, place.lat, place.lng) == ("Richmond, VA", 37.5407, -77.4360)


@pytest.mark.django_db
def test_live_provider_routes_with_ors_and_geocodes_with_photon_behind_the_cache(settings):
    settings.ORS_API_KEY = "test-key"
    settings.PHOTON_URL = "https://photon.test"

    provider = get_provider("live")

    assert isinstance(provider, CachedGeoProvider)
    live = provider._inner
    assert isinstance(live.router, OrsRouter) and live.router.api_key == "test-key"
    assert isinstance(live.geocoder, PhotonGeocoder)
    assert live.geocoder.base_url == "https://photon.test"


def test_live_provider_delegates_route_to_router_and_lookups_to_geocoder():
    class Router:
        def route(self, points):
            return ["leg"]

    class Geocoder:
        def geocode(self, query):
            return [query]

        def reverse(self, point):
            return "Richmond, VA"

    live = LiveGeoProvider(Router(), Geocoder())

    assert live.route([(37.5407, -77.4360), (39.2904, -76.6122)]) == ["leg"]
    assert live.geocode("Rich") == ["Rich"]
    assert live.reverse((37.5407, -77.4360)) == "Richmond, VA"
