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


def get_provider(name: str | None = None) -> GeoProvider:
    name = name or settings.GEO_PROVIDER
    if name == "fake":
        from geo.fake import FakeGeoProvider

        return FakeGeoProvider()
    raise ValueError(f"Unknown GEO_PROVIDER: {name!r}")
