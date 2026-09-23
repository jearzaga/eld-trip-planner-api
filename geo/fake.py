from itertools import pairwise

from geo.provider import LatLng, RouteLeg
from geo.route_math import haversine_mi

FAKE_SPEED_MPH = 55


class FakeGeoProvider:
    """Straight-line routes for unknown coordinates; scenario fixtures (SC-1…SC-7) arrive in A4."""

    def route(self, points: list[LatLng]) -> list[RouteLeg]:
        legs = []
        for a, b in pairwise(points):
            miles = haversine_mi(a, b)
            legs.append(
                RouteLeg(
                    distance_mi=miles,
                    duration_h=miles / FAKE_SPEED_MPH,
                    geometry=[(a[1], a[0]), (b[1], b[0])],
                )
            )
        return legs
