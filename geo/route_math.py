from bisect import bisect_right
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt

from geo.provider import LatLng, LngLat

EARTH_RADIUS_MI = 3958.8


def haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * asin(sqrt(h))


def _as_latlng(vertex: LngLat) -> LatLng:
    lng, lat = vertex
    return (lat, lng)


def cumulative_miles(geometry: list[LngLat]) -> list[float]:
    running = [0.0]
    for previous, current in pairwise(geometry):
        running.append(running[-1] + haversine_mi(_as_latlng(previous), _as_latlng(current)))
    return running


def _interpolate(a: LngLat, b: LngLat, t: float) -> LatLng:
    return (a[1] + (b[1] - a[1]) * t, a[0] + (b[0] - a[0]) * t)


def point_at_mile(geometry: list[LngLat], mile: float) -> LatLng:
    running = cumulative_miles(geometry)
    total = running[-1]
    if mile <= 0:
        return _as_latlng(geometry[0])
    if mile >= total:
        return _as_latlng(geometry[-1])
    i = min(bisect_right(running, mile) - 1, len(geometry) - 2)
    segment_start, segment_end = running[i], running[i + 1]
    t = (mile - segment_start) / (segment_end - segment_start)
    return _interpolate(geometry[i], geometry[i + 1], t)


def point_at_fraction(geometry: list[LngLat], fraction: float) -> LatLng:
    running = cumulative_miles(geometry)
    total = running[-1]
    fraction = min(max(fraction, 0.0), 1.0)
    return point_at_mile(geometry, fraction * total)
