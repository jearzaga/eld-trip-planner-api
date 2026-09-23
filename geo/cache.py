import hashlib
import json
from datetime import UTC, datetime, timedelta

from geo.provider import GeoProvider, LatLng, LngLat, Place, RouteLeg

ROUTE_CACHE_TTL = timedelta(days=30)
GEOCODE_CACHE_TTL = timedelta(days=30)

ROUTE_CACHE_COLLECTION = "route_cache"
GEOCODE_CACHE_COLLECTION = "geocode_cache"


def _coords_hash(points: list[LatLng]) -> str:
    rounded = [[round(lat, 5), round(lng, 5)] for lat, lng in points]
    return hashlib.sha256(json.dumps(rounded).encode()).hexdigest()


def _geocode_key(query: str) -> str:
    return "geocode:" + query.strip().lower()


def _reverse_key(point: LatLng) -> str:
    lat, lng = point
    return f"reverse:{round(lat, 4)},{round(lng, 4)}"


def _serialize_leg(leg: RouteLeg) -> dict:
    return {
        "distance_mi": leg.distance_mi,
        "duration_h": leg.duration_h,
        "geometry": [[lng, lat] for lng, lat in leg.geometry],
    }


def _deserialize_leg(data: dict) -> RouteLeg:
    return RouteLeg(
        distance_mi=data["distance_mi"],
        duration_h=data["duration_h"],
        geometry=[(lng, lat) for lng, lat in data["geometry"]],
    )


class CachedGeoProvider:
    def __init__(self, inner: GeoProvider, repository):
        self._inner = inner
        self._repository = repository

    def route(self, points: list[LatLng]) -> list[RouteLeg]:
        key = _coords_hash(points)
        cached = self._repository.get(ROUTE_CACHE_COLLECTION, key, key_field="coords_hash")
        if cached is not None:
            return [_deserialize_leg(leg) for leg in cached["legs"]]

        legs = self._inner.route(points)
        geometry: list[LngLat] = [point for leg in legs for point in leg.geometry]
        payload = {
            "geometry": [[lng, lat] for lng, lat in geometry],
            "legs": [_serialize_leg(leg) for leg in legs],
        }
        self._repository.put(
            ROUTE_CACHE_COLLECTION, key, payload, ROUTE_CACHE_TTL, key_field="coords_hash"
        )
        return legs

    def geocode(self, query: str) -> list[Place]:
        key = _geocode_key(query)
        cached = self._repository.get(GEOCODE_CACHE_COLLECTION, key)
        if cached is not None:
            return [Place(**place) for place in cached["payload"]]

        places = self._inner.geocode(query)
        payload = {"payload": [{"label": p.label, "lat": p.lat, "lng": p.lng} for p in places]}
        self._repository.put(GEOCODE_CACHE_COLLECTION, key, payload, GEOCODE_CACHE_TTL)
        return places

    def reverse(self, point: LatLng) -> str:
        key = _reverse_key(point)
        cached = self._repository.get(GEOCODE_CACHE_COLLECTION, key)
        if cached is not None:
            return cached["payload"]

        label = self._inner.reverse(point)
        self._repository.put(GEOCODE_CACHE_COLLECTION, key, {"payload": label}, GEOCODE_CACHE_TTL)
        return label


class MongoCacheRepository:
    def __init__(self, database):
        self._database = database

    def get(self, collection: str, key, key_field: str = "key"):
        doc = self._database[collection].find_one({key_field: key})
        if doc is None:
            return None
        if _as_utc(doc["expires_at"]) <= datetime.now(UTC):
            return None
        return {k: v for k, v in doc.items() if k not in {"_id", key_field, "expires_at"}}

    def put(self, collection: str, key, payload: dict, ttl: timedelta, key_field: str = "key"):
        document = {key_field: key, **payload, "expires_at": datetime.now(UTC) + ttl}
        self._database[collection].update_one({key_field: key}, {"$set": document}, upsert=True)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)
