import geo.timezone as timezone_module
from geo.timezone import timezone_at

RICHMOND_VA = (37.5407, -77.4360)
LOS_ANGELES_CA = (34.0522, -118.2437)
KANSAS_CITY_MO = (39.0997, -94.5786)
HONOLULU_HI = (21.3069, -157.8583)


def test_richmond_virginia_resolves_to_eastern_time():
    assert timezone_at(RICHMOND_VA) == "America/New_York"


def test_los_angeles_resolves_to_pacific_time():
    assert timezone_at(LOS_ANGELES_CA) == "America/Los_Angeles"


def test_kansas_city_resolves_to_central_time():
    assert timezone_at(KANSAS_CITY_MO) == "America/Chicago"


def test_honolulu_resolves_to_hawaii_time():
    assert timezone_at(HONOLULU_HI) == "Pacific/Honolulu"


def test_unresolved_coordinates_fall_back_to_utc(monkeypatch):
    class _NoneFinder:
        def timezone_at(self, *, lat, lng):
            return None

    monkeypatch.setattr(timezone_module, "_get_finder", lambda: _NoneFinder())

    assert timezone_at((0.0, 0.0)) == "UTC"
