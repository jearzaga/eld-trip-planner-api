from dataclasses import dataclass

RICHMOND = {"label": "Richmond, VA", "lat": 37.5407, "lng": -77.4360}
FREDERICKSBURG = {"label": "Fredericksburg, VA", "lat": 38.3032, "lng": -77.4605}
PHILADELPHIA = {"label": "Philadelphia, PA", "lat": 39.9526, "lng": -75.1652}
BALTIMORE = {"label": "Baltimore, MD", "lat": 39.2904, "lng": -76.6122}
KANSAS_CITY = {"label": "Kansas City, MO", "lat": 39.0997, "lng": -94.5786}
CHARLOTTE = {"label": "Charlotte, NC", "lat": 35.2271, "lng": -80.8431}
LOS_ANGELES = {"label": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437}
HONOLULU = {"label": "Honolulu, HI", "lat": 21.3069, "lng": -157.8583}
ANCHORAGE = {"label": "Anchorage, AK", "lat": 61.2181, "lng": -149.9003}

START_TIME = "2026-09-24T06:00"
HOME_TIMEZONE = "America/New_York"


@dataclass(frozen=True)
class Scenario:
    spec_id: str
    request: dict
    expected: dict


def trip_request(current, pickup, dropoff, cycle_used_hrs):
    return {
        "current": current,
        "pickup": pickup,
        "dropoff": dropoff,
        "cycle_used_hrs": cycle_used_hrs,
        "start_time": START_TIME,
        "home_timezone": HOME_TIMEZONE,
    }


SHORT_DAY_TRIP = Scenario(
    "SC-1",
    trip_request(RICHMOND, FREDERICKSBURG, PHILADELPHIA, 0),
    {
        "log_days": 1,
        "totals": [{"OFF": 17.5, "SB": 0.0, "D": 4.0, "ON": 2.5}],
        "stop_types": ["pickup", "dropoff"],
    },
)

TWO_DAY_WORKED_EXAMPLE_TRIP = Scenario(
    "SC-2",
    trip_request(RICHMOND, BALTIMORE, KANSAS_CITY, 20),
    {
        "log_days": 2,
        "totals": [
            {"OFF": 6.5, "SB": 5.25, "D": 11.0, "ON": 1.25},
            {"OFF": 8.5, "SB": 4.75, "D": 9.0, "ON": 1.75},
        ],
        "stop_types": ["pickup", "break_30", "rest_10", "fuel", "dropoff"],
    },
)

CYCLE_LIMITED_TRIP = Scenario(
    "SC-3",
    trip_request(RICHMOND, BALTIMORE, KANSAS_CITY, 65),
    {"log_days": 4, "restart_34": 1},
)

CYCLE_FULL_TRIP = Scenario(
    "SC-4",
    trip_request(RICHMOND, FREDERICKSBURG, PHILADELPHIA, 70),
    {
        "log_days": 2,
        "day_1_totals": {"OFF": 24.0, "SB": 0.0, "D": 0.0, "ON": 0.0},
        "first_stop": "restart_34",
    },
)

CROSS_COUNTRY_TRIP = Scenario(
    "SC-5",
    trip_request(RICHMOND, CHARLOTTE, LOS_ANGELES, 10),
    {"log_days": 5, "fuel": 2, "rest_10": 4, "break_30": 2},
)

UNROUTABLE_TRIP = Scenario(
    "SC-6",
    trip_request(RICHMOND, HONOLULU, ANCHORAGE, 0),
    {"status": 422, "error_code": "ROUTE_NOT_FOUND"},
)

PICKUP_AT_CURRENT_LOCATION_TRIP = Scenario(
    "SC-7",
    trip_request(RICHMOND, RICHMOND, PHILADELPHIA, 0),
    {"log_days": 1, "pickup_arrive_at": "2026-09-24T06:15:00-04:00"},
)

ROUTABLE_SCENARIOS = [
    SHORT_DAY_TRIP,
    TWO_DAY_WORKED_EXAMPLE_TRIP,
    CYCLE_LIMITED_TRIP,
    CYCLE_FULL_TRIP,
    CROSS_COUNTRY_TRIP,
    PICKUP_AT_CURRENT_LOCATION_TRIP,
]
