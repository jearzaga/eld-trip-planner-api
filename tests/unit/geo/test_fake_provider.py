import pytest

from geo.fake import FakeGeoProvider
from geo.provider import RouteNotFound

RICHMOND = (37.5407, -77.4360)
FREDERICKSBURG = (38.3032, -77.4605)
PHILADELPHIA = (39.9526, -75.1652)
BALTIMORE = (39.2904, -76.6122)
KANSAS_CITY = (39.0997, -94.5786)
CHARLOTTE = (35.2271, -80.8431)
LOS_ANGELES = (34.0522, -118.2437)
HONOLULU = (21.3069, -157.8583)
ANCHORAGE = (61.2181, -149.9003)


def test_fake_route_returns_one_straight_line_leg_per_hop():
    legs = FakeGeoProvider().route([RICHMOND, BALTIMORE])

    assert len(legs) == 1
    assert legs[0].geometry == [(-77.4360, 37.5407), (-76.6122, 39.2904)]  # GeoJSON order: lng, lat


def test_fake_route_uses_great_circle_miles_at_55_mph_for_unknown_points():
    leg = FakeGeoProvider().route([RICHMOND, BALTIMORE])[0]

    assert leg.distance_mi == pytest.approx(128.9, abs=0.5)
    assert leg.duration_h == pytest.approx(leg.distance_mi / 55)


def test_fake_route_zero_length_leg_when_unknown_points_match():
    leg = FakeGeoProvider().route([RICHMOND, RICHMOND])[0]

    assert leg.distance_mi == 0
    assert leg.duration_h == 0


def test_fake_route_falls_back_to_straight_line_for_any_number_of_unknown_points():
    legs = FakeGeoProvider().route([RICHMOND, FREDERICKSBURG, BALTIMORE, KANSAS_CITY])

    assert len(legs) == 3
    for leg in legs:
        assert leg.duration_h == pytest.approx(leg.distance_mi / 55)


# SC-1
def test_short_day_scenario_returns_fixture_legs():
    legs = FakeGeoProvider().route([RICHMOND, FREDERICKSBURG, PHILADELPHIA])

    assert [(leg.distance_mi, leg.duration_h) for leg in legs] == [(60, 1), (180, 3)]


# SC-2
def test_two_day_worked_example_scenario_returns_fixture_legs():
    legs = FakeGeoProvider().route([RICHMOND, BALTIMORE, KANSAS_CITY])

    assert [(leg.distance_mi, leg.duration_h) for leg in legs] == [(120, 2), (1080, 18)]


# SC-3, shares points/legs with SC-2
def test_cycle_limited_scenario_shares_two_day_worked_example_fixture():
    legs = FakeGeoProvider().route([RICHMOND, BALTIMORE, KANSAS_CITY])

    assert [(leg.distance_mi, leg.duration_h) for leg in legs] == [(120, 2), (1080, 18)]


# SC-4, shares points/legs with SC-1
def test_cycle_full_scenario_shares_short_day_fixture():
    legs = FakeGeoProvider().route([RICHMOND, FREDERICKSBURG, PHILADELPHIA])

    assert [(leg.distance_mi, leg.duration_h) for leg in legs] == [(60, 1), (180, 3)]


# SC-5
def test_cross_country_scenario_returns_fixture_legs():
    legs = FakeGeoProvider().route([RICHMOND, CHARLOTTE, LOS_ANGELES])

    assert [(leg.distance_mi, leg.duration_h) for leg in legs] == [(300, 5), (2500, 42)]


# SC-6
def test_unroutable_scenario_raises_route_not_found():
    with pytest.raises(RouteNotFound):
        FakeGeoProvider().route([RICHMOND, HONOLULU, ANCHORAGE])


# SC-7
def test_pickup_at_current_location_scenario_has_zero_length_first_leg():
    legs = FakeGeoProvider().route([RICHMOND, RICHMOND, PHILADELPHIA])

    assert [(leg.distance_mi, leg.duration_h) for leg in legs] == [(0, 0), (180, 3)]
    assert legs[0].geometry == [(-77.4360, 37.5407), (-77.4360, 37.5407)]


def test_geocode_matches_prefix_of_place_name():
    results = FakeGeoProvider().geocode("Rich")

    assert results[0].label == "Richmond, VA"
    assert (results[0].lat, results[0].lng) == (37.5407, -77.4360)


def test_geocode_returns_no_results_for_unknown_query():
    assert FakeGeoProvider().geocode("Zzyzxville") == []


def test_geocode_returns_no_results_for_short_query():
    assert FakeGeoProvider().geocode("ri") == []


def test_geocode_caps_results_at_five():
    assert len(FakeGeoProvider().geocode("ville")) <= 5


def test_reverse_returns_exact_city_label_within_fifteen_miles():
    assert FakeGeoProvider().reverse(RICHMOND) == "Richmond, VA"


def test_reverse_returns_near_label_outside_fifteen_miles():
    far_from_any_known_place = (37.8407, -77.4360)

    label = FakeGeoProvider().reverse(far_from_any_known_place)

    assert label.startswith("near ")
    assert "Richmond, VA" in label
