from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from math import ceil, isclose
from zoneinfo import ZoneInfo

from geo.provider import GeoProvider, get_provider
from geo.route_math import point_at_fraction
from geo.timezone import timezone_at
from hos.engine import plan_timeline
from hos.log_builder import LogMeta, build_daily_logs
from hos.models import DutyStatus, Leg, StopType, TripInput

TIME_FORMAT = "%Y-%m-%dT%H:%M"
ON_DUTY_STATUSES = (DutyStatus.D, DutyStatus.ON)


def _place(entry: dict) -> dict:
    return {"label": entry["label"], "lat": entry["lat"], "lng": entry["lng"]}


def _resolve_home_timezone(request: dict) -> str:
    home_timezone = request.get("home_timezone")
    if home_timezone:
        return home_timezone
    current = request["current"]
    return timezone_at((current["lat"], current["lng"]))  # A-11


def _next_quarter_hour(local_now: datetime) -> datetime:
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = (local_now - day_start).total_seconds() / 60
    quarter = ceil(minutes_since_midnight / 15) * 15
    return day_start + timedelta(minutes=quarter)


def _resolve_start_local(request: dict, tz: ZoneInfo, now: datetime | None) -> datetime:
    raw = request.get("start_time")
    if raw:
        return datetime.strptime(raw, TIME_FORMAT).replace(tzinfo=tz)
    now = now or datetime.now(UTC)  # A-11
    return _next_quarter_hour(now.astimezone(tz))


def _resolve_log_meta(request: dict) -> LogMeta:
    defaults = asdict(LogMeta())
    provided = request.get("log_meta") or {}
    merged = {
        **defaults,
        **{key: value for key, value in provided.items() if key in defaults and value is not None},
    }
    return LogMeta(**merged)


def _resolve_include_inspections(request: dict) -> bool:
    value = request.get("include_inspections")
    return True if value is None else value


def plan_trip(
    request: dict, provider: GeoProvider | None = None, now: datetime | None = None
) -> dict:
    provider = provider or get_provider()

    current, pickup, dropoff = request["current"], request["pickup"], request["dropoff"]
    cycle_used_hrs = float(request["cycle_used_hrs"])
    home_timezone = _resolve_home_timezone(request)
    tz = ZoneInfo(home_timezone)
    start_local = _resolve_start_local(request, tz, now)
    start_utc = start_local.astimezone(UTC)
    include_inspections = _resolve_include_inspections(request)
    meta = _resolve_log_meta(request)

    leg0, leg1 = provider.route(
        [
            (current["lat"], current["lng"]),
            (pickup["lat"], pickup["lng"]),
            (dropoff["lat"], dropoff["lng"]),
        ]
    )
    total_distance_mi = leg0.distance_mi + leg1.distance_mi

    cycle_used_min = round(cycle_used_hrs * 60)
    trip_legs = (
        Leg(leg0.distance_mi, leg0.duration_h * 60),
        Leg(leg1.distance_mi, leg1.duration_h * 60),
    )
    timeline = plan_timeline(
        TripInput(
            legs=trip_legs, cycle_used_min=cycle_used_min, include_inspections=include_inspections
        )
    )

    reverse_cache: dict[tuple[float, float], str] = {}

    def locate(mile: float) -> tuple[str, float, float]:
        if isclose(mile, 0.0, abs_tol=1e-6):
            return current["label"], current["lat"], current["lng"]
        if isclose(mile, leg0.distance_mi, abs_tol=1e-6):
            return pickup["label"], pickup["lat"], pickup["lng"]
        if isclose(mile, total_distance_mi, abs_tol=1e-6):
            return dropoff["label"], dropoff["lat"], dropoff["lng"]
        leg, leg_start = (leg0, 0.0) if mile <= leg0.distance_mi else (leg1, leg0.distance_mi)
        fraction = (mile - leg_start) / leg.distance_mi if leg.distance_mi else 0.0
        lat, lng = point_at_fraction(leg.geometry, fraction)
        key = (round(lat, 6), round(lng, 6))
        if key not in reverse_cache:
            reverse_cache[key] = provider.reverse((lat, lng))
        return reverse_cache[key], lat, lng

    timeline = replace(
        timeline,
        segments=tuple(
            replace(segment, location=locate(segment.mile_marker)[0])
            for segment in timeline.segments
        ),
    )

    def local_dt(minute: int) -> datetime:
        return (start_utc + timedelta(minutes=minute)).astimezone(tz)

    stops = []
    for seq, stop in enumerate(timeline.stops, start=1):
        if stop.type is StopType.PICKUP:
            label, lat, lng = pickup["label"], pickup["lat"], pickup["lng"]
        elif stop.type is StopType.DROPOFF:
            label, lat, lng = dropoff["label"], dropoff["lat"], dropoff["lng"]
        else:
            label, lat, lng = locate(stop.mile_marker)
        stops.append(
            {
                "seq": seq,
                "type": stop.type.value,
                "label": label,
                "lat": lat,
                "lng": lng,
                "mile_marker": round(stop.mile_marker, 1),
                "arrive_at": local_dt(stop.start_min).isoformat(),
                "depart_at": local_dt(stop.end_min).isoformat(),
                "duration_min": stop.duration_min,
                "status": stop.status.value,
                "reason": stop.reason,
            }
        )

    engine_logs = build_daily_logs(
        timeline,
        start_utc=start_utc,
        home_tz=home_timezone,
        cycle_used_min=cycle_used_min,
        meta=meta,
    )
    daily_logs = [
        {
            "day_number": log.day_number,
            "date": log.date,
            "header": {
                "from": log.header.from_location,
                "to": log.header.to_location,
                "miles_driving_today": round(log.header.miles_driving_today, 1),
                "total_mileage_today": round(log.header.total_mileage_today, 1),
                "driver_name": log.header.driver_name,
                "co_driver_name": log.header.co_driver_name,
                "carrier_name": log.header.carrier_name,
                "main_office_address": log.header.main_office_address,
                "home_terminal_address": log.header.home_terminal_address,
                "truck_tractor_no": log.header.truck_tractor_no,
                "trailer_no": log.header.trailer_no,
                "shipping_doc_no": log.header.shipping_doc_no,
                "shipper_commodity": log.header.shipper_commodity,
            },
            "segments": [
                {
                    "status": segment.status.value,
                    "start_min": segment.start_min,
                    "end_min": segment.end_min,
                    "note": segment.note,
                    "location": segment.location,
                }
                for segment in log.segments
            ],
            "totals": dict(log.totals),
            "remarks": [
                {"at_min": remark.at_min, "location": remark.location, "note": remark.note}
                for remark in log.remarks
            ],
            "recap": {
                "on_duty_today": log.recap.on_duty_today,
                "a_last_7": log.recap.a_last_7,
                "b_available_tomorrow": log.recap.b_available_tomorrow,
                "c_last_5": log.recap.c_last_5,
                "restart_34_taken": log.recap.restart_34_taken,
            },
        }
        for log in engine_logs
    ]

    total_driving_min = sum(s.duration_min for s in timeline.segments if s.status == DutyStatus.D)
    total_on_duty_min = sum(
        s.duration_min for s in timeline.segments if s.status in ON_DUTY_STATUSES
    )
    dropoff_stop = next(stop for stop in stops if stop["type"] == "dropoff")

    return {
        "inputs": {
            "current": _place(current),
            "pickup": _place(pickup),
            "dropoff": _place(dropoff),
            "cycle_used_hrs": cycle_used_hrs,
            "start_time": start_local.strftime(TIME_FORMAT),
            "home_timezone": home_timezone,
            "include_inspections": include_inspections,
            "log_meta": asdict(meta),
        },
        "summary": {
            "total_miles": round(total_distance_mi, 1),
            "total_driving_hrs": round(total_driving_min / 60, 2),
            "total_on_duty_hrs": round(total_on_duty_min / 60, 2),
            "start_at": start_local.isoformat(),
            "arrive_at": dropoff_stop["arrive_at"],
            "end_at": local_dt(timeline.segments[-1].end_min).isoformat(),
            "log_days": len(daily_logs),
            "stop_count": len(stops),
            "cycle_used_end_hrs": daily_logs[-1]["recap"]["a_last_7"],
            "home_timezone": home_timezone,
        },
        "route": {
            "geometry": {
                "type": "LineString",
                "coordinates": [list(point) for point in leg0.geometry]
                + [list(point) for point in leg1.geometry[1:]],
            },
            "legs": [
                {
                    "from": "current",
                    "to": "pickup",
                    "distance_mi": round(leg0.distance_mi, 1),
                    "duration_hrs": round(leg0.duration_h, 2),
                },
                {
                    "from": "pickup",
                    "to": "dropoff",
                    "distance_mi": round(leg1.distance_mi, 1),
                    "duration_hrs": round(leg1.duration_h, 2),
                },
            ],
        },
        "stops": stops,
        "daily_logs": daily_logs,
    }
