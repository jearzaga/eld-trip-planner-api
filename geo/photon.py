import httpx

from geo.provider import LatLng, Place, ProviderUnavailable

MAX_GEOCODE_RESULTS = 5

US_STATES = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}


class PhotonGeocoder:
    def __init__(self, base_url: str = "https://photon.komoot.io", timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    def geocode(self, query: str) -> list[Place]:
        features = self._get(f"{self.base_url}/api/", {"q": query, "limit": 10, "lang": "en"})

        places: list[Place] = []
        seen_labels: set[str] = set()
        for feature in features:
            properties = feature.get("properties", {})
            if properties.get("countrycode") != "US":
                continue
            label = _us_label(properties)
            if label is None or label in seen_labels:
                continue
            try:
                lng, lat = feature["geometry"]["coordinates"]
            except (KeyError, ValueError, TypeError):
                continue
            seen_labels.add(label)
            places.append(Place(label=label, lat=lat, lng=lng))
            if len(places) == MAX_GEOCODE_RESULTS:
                break
        return places

    def reverse(self, point: LatLng) -> str:
        lat, lng = point
        features = self._get(f"{self.base_url}/reverse", {"lat": lat, "lon": lng, "lang": "en"})

        if not features:
            return f"{lat:.2f}, {lng:.2f}"

        properties = features[0].get("properties", {})
        if properties.get("countrycode") == "US":
            label = _us_label(properties, name_fallbacks=("town", "village", "name"))
            if label is not None:
                return label

        best = (
            properties.get("city")
            or properties.get("town")
            or properties.get("village")
            or properties.get("name")
            or properties.get("country")
        )
        return f"near {best}" if best else f"{lat:.2f}, {lng:.2f}"

    def _get(self, url: str, params: dict) -> list[dict]:
        try:
            response = httpx.get(url, params=params, timeout=self.timeout)
        except httpx.RequestError as exc:
            raise ProviderUnavailable(str(exc)) from exc

        if response.status_code != 200:
            raise ProviderUnavailable(f"Photon returned HTTP {response.status_code}")

        try:
            return response.json()["features"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderUnavailable("malformed Photon response") from exc


def _us_label(properties: dict, name_fallbacks: tuple[str, ...] = ()) -> str | None:
    city = properties.get("city")
    if not city:
        for key in name_fallbacks:
            if properties.get(key):
                city = properties[key]
                break
        else:
            city = properties.get("name")
    state_abbr = US_STATES.get(properties.get("state", ""))
    if not city or not state_abbr:
        return None
    return f"{city}, {state_abbr}"
