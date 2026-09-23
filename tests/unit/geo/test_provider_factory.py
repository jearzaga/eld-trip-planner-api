import pytest

from geo.fake import FakeGeoProvider
from geo.provider import get_provider

RICHMOND = (37.5407, -77.4360)
BALTIMORE = (39.2904, -76.6122)
KANSAS_CITY = (39.0997, -94.5786)


def test_fake_provider_selected_by_name():
    assert isinstance(get_provider("fake"), FakeGeoProvider)


def test_default_provider_comes_from_geo_provider_setting(settings):
    settings.GEO_PROVIDER = "fake"
    assert isinstance(get_provider(), FakeGeoProvider)


def test_unknown_provider_rejected():
    with pytest.raises(ValueError, match="nope"):
        get_provider("nope")


def test_fake_route_returns_one_straight_line_leg_per_hop():
    legs = FakeGeoProvider().route([RICHMOND, BALTIMORE, KANSAS_CITY])

    assert len(legs) == 2
    assert legs[0].geometry == [(-77.4360, 37.5407), (-76.6122, 39.2904)]  # GeoJSON order: lng, lat
    assert legs[1].geometry == [(-76.6122, 39.2904), (-94.5786, 39.0997)]


def test_fake_route_uses_great_circle_miles_at_55_mph():
    leg = FakeGeoProvider().route([RICHMOND, BALTIMORE])[0]

    assert leg.distance_mi == pytest.approx(128.9, abs=0.5)
    assert leg.duration_h == pytest.approx(leg.distance_mi / 55)


def test_fake_route_zero_length_leg_when_points_match():
    leg = FakeGeoProvider().route([RICHMOND, RICHMOND])[0]

    assert leg.distance_mi == 0
    assert leg.duration_h == 0
