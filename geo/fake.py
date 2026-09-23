import json
from functools import cache
from itertools import pairwise
from pathlib import Path

from geo.provider import LatLng, Place, RouteLeg, RouteNotFound
from geo.route_math import haversine_mi

FAKE_SPEED_MPH = 55
REVERSE_NEARBY_RADIUS_MI = 15
MAX_GEOCODE_RESULTS = 5
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _round_point(point: LatLng) -> tuple[float, float]:
    return (round(point[0], 4), round(point[1], 4))


@cache
def _load_scenarios() -> dict[tuple[tuple[float, float], ...], dict]:
    scenarios = {}
    for path in sorted((FIXTURES_DIR / "scenarios").glob("sc*.json")):
        fixture = json.loads(path.read_text())
        key = tuple(_round_point(p) for p in fixture["points"])
        scenarios[key] = fixture
    return scenarios


@cache
def _load_places() -> list[Place]:
    raw = json.loads((FIXTURES_DIR / "places.json").read_text())
    return [Place(label=p["label"], lat=p["lat"], lng=p["lng"]) for p in raw]


def _straight_line_leg(a: LatLng, b: LatLng) -> RouteLeg:
    miles = haversine_mi(a, b)
    return RouteLeg(
        distance_mi=miles,
        duration_h=miles / FAKE_SPEED_MPH,
        geometry=[(a[1], a[0]), (b[1], b[0])],
    )


def _fixture_leg(leg: dict, a: LatLng, b: LatLng) -> RouteLeg:
    return RouteLeg(
        distance_mi=leg["distance_mi"],
        duration_h=leg["duration_h"],
        geometry=[(a[1], a[0]), (b[1], b[0])],
    )


class FakeGeoProvider:
    def route(self, points: list[LatLng]) -> list[RouteLeg]:
        if len(points) == 3:
            fixture = _load_scenarios().get(tuple(_round_point(p) for p in points))
            if fixture is not None:
                if fixture.get("route_not_found"):
                    raise RouteNotFound(fixture["spec_id"])
                return [
                    _fixture_leg(leg, a, b)
                    for leg, (a, b) in zip(fixture["legs"], pairwise(points), strict=True)
                ]
        return [_straight_line_leg(a, b) for a, b in pairwise(points)]

    def geocode(self, query: str) -> list[Place]:
        if len(query) < 3:
            return []
        needle = query.lower()
        matches = [place for place in _load_places() if needle in place.label.lower()]
        return matches[:MAX_GEOCODE_RESULTS]

    def reverse(self, point: LatLng) -> str:
        nearest = min(_load_places(), key=lambda place: haversine_mi(point, (place.lat, place.lng)))
        distance_mi = haversine_mi(point, (nearest.lat, nearest.lng))
        if distance_mi <= REVERSE_NEARBY_RADIUS_MI:
            return nearest.label
        return f"near {nearest.label}"
