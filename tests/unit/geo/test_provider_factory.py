import pytest

from geo.fake import FakeGeoProvider
from geo.provider import GeoProvider, Place, ProviderUnavailable, RouteNotFound, get_provider


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
