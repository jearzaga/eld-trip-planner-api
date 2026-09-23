from datetime import UTC, datetime, timedelta

import pytest

from geo.cache import CachedGeoProvider
from geo.provider import Place, ProviderUnavailable, RouteLeg

RICHMOND = (37.5407, -77.4360)
BALTIMORE = (39.2904, -76.6122)


class InMemoryCacheRepository:
    def __init__(self):
        self.store = {}

    def get(self, collection, key, key_field="key"):
        doc = self.store.get((collection, key_field, key))
        if doc is None:
            return None
        if doc["expires_at"] <= datetime.now(UTC):
            return None
        return {k: v for k, v in doc.items() if k not in {key_field, "expires_at"}}

    def put(self, collection, key, payload, ttl, key_field="key"):
        self.store[(collection, key_field, key)] = {
            key_field: key,
            **payload,
            "expires_at": datetime.now(UTC) + ttl,
        }


class SpyGeoProvider:
    def __init__(self, route_result=None, geocode_result=None, reverse_result=None, raises=None):
        self.route_calls = 0
        self.geocode_calls = 0
        self.reverse_calls = 0
        self._route_result = route_result
        self._geocode_result = geocode_result
        self._reverse_result = reverse_result
        self._raises = raises

    def route(self, points):
        self.route_calls += 1
        if self._raises:
            raise self._raises
        return self._route_result

    def geocode(self, query):
        self.geocode_calls += 1
        if self._raises:
            raise self._raises
        return self._geocode_result

    def reverse(self, point):
        self.reverse_calls += 1
        if self._raises:
            raise self._raises
        return self._reverse_result


def test_route_cache_miss_then_hit_calls_inner_once():
    leg = RouteLeg(
        distance_mi=128.9, duration_h=2.34, geometry=[(-77.436, 37.5407), (-76.6122, 39.2904)]
    )
    inner = SpyGeoProvider(route_result=[leg])
    provider = CachedGeoProvider(inner, InMemoryCacheRepository())

    first = provider.route([RICHMOND, BALTIMORE])
    second = provider.route([RICHMOND, BALTIMORE])

    assert inner.route_calls == 1
    assert first == [leg]
    assert second == [leg]


def test_route_cache_key_rounds_points_to_five_decimal_places():
    leg = RouteLeg(distance_mi=1.0, duration_h=0.1, geometry=[(0.0, 0.0), (1.0, 1.0)])
    inner = SpyGeoProvider(route_result=[leg])
    provider = CachedGeoProvider(inner, InMemoryCacheRepository())

    provider.route([(37.540698, -77.436001), (39.2904, -76.6122)])
    provider.route([(37.540703, -77.436), (39.2904, -76.6122)])

    assert inner.route_calls == 1


def test_route_leg_round_trips_through_cache_with_tuple_geometry():
    leg = RouteLeg(
        distance_mi=128.9, duration_h=2.34, geometry=[(-77.436, 37.5407), (-76.6122, 39.2904)]
    )
    inner = SpyGeoProvider(route_result=[leg])
    repository = InMemoryCacheRepository()
    provider = CachedGeoProvider(inner, repository)

    provider.route([RICHMOND, BALTIMORE])
    cached = provider.route([RICHMOND, BALTIMORE])

    assert cached == [leg]
    assert all(isinstance(point, tuple) for point in cached[0].geometry)


def test_route_error_from_inner_propagates_and_is_not_cached():
    inner = SpyGeoProvider(raises=ProviderUnavailable("down"))
    repository = InMemoryCacheRepository()
    provider = CachedGeoProvider(inner, repository)

    with pytest.raises(ProviderUnavailable):
        provider.route([RICHMOND, BALTIMORE])
    with pytest.raises(ProviderUnavailable):
        provider.route([RICHMOND, BALTIMORE])

    assert inner.route_calls == 2
    assert repository.store == {}


def test_geocode_cache_miss_then_hit_calls_inner_once():
    places = [Place(label="Richmond, VA", lat=37.5407, lng=-77.436)]
    inner = SpyGeoProvider(geocode_result=places)
    provider = CachedGeoProvider(inner, InMemoryCacheRepository())

    first = provider.geocode("Richmond, VA")
    second = provider.geocode(" richmond, VA ")

    assert inner.geocode_calls == 1
    assert first == places
    assert second == places


def test_geocode_error_from_inner_propagates_and_is_not_cached():
    inner = SpyGeoProvider(raises=ProviderUnavailable("down"))
    repository = InMemoryCacheRepository()
    provider = CachedGeoProvider(inner, repository)

    with pytest.raises(ProviderUnavailable):
        provider.geocode("Richmond, VA")

    assert repository.store == {}


def test_reverse_cache_miss_then_hit_calls_inner_once_and_rounds_to_four_decimal_places():
    inner = SpyGeoProvider(reverse_result="Richmond, VA")
    provider = CachedGeoProvider(inner, InMemoryCacheRepository())

    first = provider.reverse((37.540712, -77.436099))
    second = provider.reverse((37.540698, -77.436088))

    assert inner.reverse_calls == 1
    assert first == "Richmond, VA"
    assert second == "Richmond, VA"


def test_reverse_error_from_inner_propagates_and_is_not_cached():
    inner = SpyGeoProvider(raises=ProviderUnavailable("down"))
    repository = InMemoryCacheRepository()
    provider = CachedGeoProvider(inner, repository)

    with pytest.raises(ProviderUnavailable):
        provider.reverse(RICHMOND)

    assert repository.store == {}


def test_expired_cache_entry_is_treated_as_a_miss():
    leg = RouteLeg(distance_mi=1.0, duration_h=0.1, geometry=[(0.0, 0.0), (1.0, 1.0)])
    inner = SpyGeoProvider(route_result=[leg])
    repository = InMemoryCacheRepository()
    provider = CachedGeoProvider(inner, repository)

    provider.route([RICHMOND, BALTIMORE])
    for doc in repository.store.values():
        doc["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    provider.route([RICHMOND, BALTIMORE])

    assert inner.route_calls == 2
