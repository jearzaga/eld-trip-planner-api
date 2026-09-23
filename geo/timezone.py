from timezonefinder import TimezoneFinder

from geo.provider import LatLng

_finder: TimezoneFinder | None = None


def _get_finder() -> TimezoneFinder:
    global _finder
    if _finder is None:
        _finder = TimezoneFinder()
    return _finder


def timezone_at(point: LatLng) -> str:
    lat, lng = point
    return _get_finder().timezone_at(lat=lat, lng=lng) or "UTC"
