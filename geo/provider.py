from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

LatLng = tuple[float, float]
LngLat = tuple[float, float]


@dataclass(frozen=True)
class RouteLeg:
    distance_mi: float
    duration_h: float
    geometry: list[LngLat]  # GeoJSON LineString coordinates


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lng: float


class RouteNotFound(Exception):
    pass


class ProviderUnavailable(Exception):
    pass


class GeoProvider(Protocol):
    def route(self, points: list[LatLng]) -> list[RouteLeg]: ...

    def geocode(self, query: str) -> list[Place]: ...

    def reverse(self, point: LatLng) -> str: ...


class LiveGeoProvider:
    def __init__(self, router, geocoder):
        self.router = router
        self.geocoder = geocoder

    def route(self, points: list[LatLng]) -> list[RouteLeg]:
        return self.router.route(points)

    def geocode(self, query: str) -> list[Place]:
        return self.geocoder.geocode(query)

    def reverse(self, point: LatLng) -> str:
        return self.geocoder.reverse(point)


def get_provider(name: str | None = None) -> GeoProvider:
    name = name or settings.GEO_PROVIDER
    if name == "fake":
        from geo.fake import FakeGeoProvider

        return FakeGeoProvider()
    if name == "live":
        from django.db import connection

        from geo.cache import CachedGeoProvider, MongoCacheRepository
        from geo.ors import OrsRouter
        from geo.photon import PhotonGeocoder

        return CachedGeoProvider(
            LiveGeoProvider(OrsRouter(settings.ORS_API_KEY), PhotonGeocoder(settings.PHOTON_URL)),
            MongoCacheRepository(connection.database),
        )
    raise ValueError(f"Unknown GEO_PROVIDER: {name!r}")
