from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection

from geo.cache import GEOCODE_CACHE_COLLECTION, ROUTE_CACHE_COLLECTION, MongoCacheRepository


@pytest.fixture
def database():
    return connection.database


@pytest.mark.django_db
def test_put_then_get_round_trips_payload(database):
    repository = MongoCacheRepository(database)

    repository.put("geocode_cache", "geocode:richmond, va", {"payload": ["a"]}, timedelta(days=1))

    assert repository.get("geocode_cache", "geocode:richmond, va") == {"payload": ["a"]}


@pytest.mark.django_db
def test_put_upserts_on_matching_key(database):
    repository = MongoCacheRepository(database)

    repository.put("geocode_cache", "geocode:richmond, va", {"payload": ["old"]}, timedelta(days=1))
    repository.put("geocode_cache", "geocode:richmond, va", {"payload": ["new"]}, timedelta(days=1))

    assert repository.get("geocode_cache", "geocode:richmond, va") == {"payload": ["new"]}
    assert database["geocode_cache"].count_documents({"key": "geocode:richmond, va"}) == 1


@pytest.mark.django_db
def test_get_ignores_document_with_expired_ttl(database):
    repository = MongoCacheRepository(database)
    database["geocode_cache"].insert_one(
        {
            "key": "geocode:stale",
            "payload": ["x"],
            "expires_at": datetime.now(UTC) - timedelta(seconds=1),
        }
    )

    assert repository.get("geocode_cache", "geocode:stale") is None


@pytest.mark.django_db
def test_get_missing_key_returns_none(database):
    repository = MongoCacheRepository(database)

    assert repository.get("geocode_cache", "geocode:nowhere") is None


@pytest.mark.django_db
def test_route_cache_uses_coords_hash_key_field(database):
    repository = MongoCacheRepository(database)

    repository.put(
        "route_cache",
        "abc123",
        {"geometry": [[0, 0]], "legs": []},
        timedelta(days=1),
        key_field="coords_hash",
    )

    assert repository.get("route_cache", "abc123", key_field="coords_hash") == {
        "geometry": [[0, 0]],
        "legs": [],
    }
    stored = database["route_cache"].find_one({"coords_hash": "abc123"})
    assert stored["coords_hash"] == "abc123"


@pytest.mark.django_db
def test_ensure_indexes_creates_expected_indexes(database):
    call_command("ensure_indexes", stdout=StringIO())

    route_indexes = database[ROUTE_CACHE_COLLECTION].index_information()
    geocode_indexes = database[GEOCODE_CACHE_COLLECTION].index_information()

    coords_hash_index = next(i for i in route_indexes.values() if i["key"] == [("coords_hash", 1)])
    assert coords_hash_index["unique"] is True

    route_ttl_index = next(i for i in route_indexes.values() if i["key"] == [("expires_at", 1)])
    assert route_ttl_index["expireAfterSeconds"] == 0

    key_index = next(i for i in geocode_indexes.values() if i["key"] == [("key", 1)])
    assert key_index["unique"] is True

    geocode_ttl_index = next(i for i in geocode_indexes.values() if i["key"] == [("expires_at", 1)])
    assert geocode_ttl_index["expireAfterSeconds"] == 0


@pytest.mark.django_db
def test_ensure_indexes_is_idempotent(database):
    call_command("ensure_indexes", stdout=StringIO())
    call_command("ensure_indexes", stdout=StringIO())

    route_indexes = database[ROUTE_CACHE_COLLECTION].index_information()
    assert sum(1 for i in route_indexes.values() if i["key"] == [("coords_hash", 1)]) == 1


@pytest.mark.django_db
def test_ensure_indexes_prints_a_summary(database):
    out = StringIO()

    call_command("ensure_indexes", stdout=out)

    assert "route_cache" in out.getvalue()
    assert "geocode_cache" in out.getvalue()
