from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_MI = 3958.8


def haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * asin(sqrt(h))
