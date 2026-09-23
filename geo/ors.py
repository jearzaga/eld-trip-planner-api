import httpx

from geo.provider import LatLng, ProviderUnavailable, RouteLeg, RouteNotFound

METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600
ROUTE_NOT_FOUND_ERROR_CODES = {2009, 2010}


class OrsRouter:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openrouteservice.org",
        timeout: float = 20.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def route(self, points: list[LatLng]) -> list[RouteLeg]:
        try:
            response = httpx.post(
                f"{self.base_url}/v2/directions/driving-hgv/geojson",
                headers={"Authorization": self.api_key},
                json={"coordinates": [[lng, lat] for lat, lng in points]},
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise ProviderUnavailable(str(exc)) from exc

        if response.status_code == 404:
            raise RouteNotFound(response.text)
        if response.status_code == 400:
            if _error_code(response) in ROUTE_NOT_FOUND_ERROR_CODES:
                raise RouteNotFound(response.text)
            raise ProviderUnavailable(response.text)
        if response.status_code != 200:
            raise ProviderUnavailable(f"ORS returned HTTP {response.status_code}")

        try:
            return _legs_from_response(response.json(), points)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderUnavailable("malformed ORS response") from exc


def _error_code(response: httpx.Response) -> int | None:
    try:
        return response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return None


def _legs_from_response(data: dict, points: list[LatLng]) -> list[RouteLeg]:
    feature = data["features"][0]
    segments = feature["properties"]["segments"]
    way_points = feature["properties"]["way_points"]
    coordinates = feature["geometry"]["coordinates"]

    expected_legs = len(points) - 1
    missing_segments = expected_legs - len(segments)

    legs = []
    segment_index = 0
    for i in range(expected_legs):
        if missing_segments > 0 and points[i] == points[i + 1]:
            lng, lat = points[i][1], points[i][0]
            legs.append(
                RouteLeg(distance_mi=0.0, duration_h=0.0, geometry=[(lng, lat), (lng, lat)])
            )
            missing_segments -= 1
            continue

        segment = segments[segment_index]
        start, end = way_points[segment_index], way_points[segment_index + 1]
        geometry = [tuple(point) for point in coordinates[start : end + 1]]
        if len(geometry) < 2:
            geometry = geometry * 2
        legs.append(
            RouteLeg(
                distance_mi=segment["distance"] / METERS_PER_MILE,
                duration_h=segment["duration"] / SECONDS_PER_HOUR,
                geometry=geometry,
            )
        )
        segment_index += 1

    return legs
