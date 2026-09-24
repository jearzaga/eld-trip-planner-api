from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from django.db import models
from django_mongodb_backend.fields import EmbeddedModelArrayField, EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel

LOG_META_FIELDS = (
    "driver_name",
    "co_driver_name",
    "carrier_name",
    "main_office_address",
    "home_terminal_address",
    "truck_tractor_no",
    "trailer_no",
    "shipping_doc_no",
    "shipper_commodity",
)


def _to_utc(value: str, tz: str | None = None) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(tz))
    return parsed.astimezone(UTC)


def _iso(dt: datetime, tz: str) -> str:
    return dt.astimezone(ZoneInfo(tz)).isoformat()


def _wall_clock(dt: datetime, tz: str) -> str:
    return dt.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%dT%H:%M")


class Location(EmbeddedModel):
    label = models.CharField(max_length=255)
    lat = models.FloatField()
    lng = models.FloatField()

    def to_dict(self) -> dict:
        return {"label": self.label, "lat": self.lat, "lng": self.lng}


class LogMeta(EmbeddedModel):
    driver_name = models.CharField(max_length=255, blank=True)
    co_driver_name = models.CharField(max_length=255, blank=True)
    carrier_name = models.CharField(max_length=255, blank=True)
    main_office_address = models.CharField(max_length=255, blank=True)
    home_terminal_address = models.CharField(max_length=255, blank=True)
    truck_tractor_no = models.CharField(max_length=255, blank=True)
    trailer_no = models.CharField(max_length=255, blank=True)
    shipping_doc_no = models.CharField(max_length=255, blank=True)
    shipper_commodity = models.CharField(max_length=255, blank=True)

    def to_dict(self) -> dict:
        return {field: getattr(self, field) for field in LOG_META_FIELDS}


class DutySegment(EmbeddedModel):
    status = models.CharField(max_length=8)
    start_min = models.IntegerField()
    end_min = models.IntegerField()
    note = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    location = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "start_min": self.start_min,
            "end_min": self.end_min,
            "note": self.note,
            "location": self.location,
        }


class Remark(EmbeddedModel):
    at_min = models.IntegerField()
    location = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    note = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    def to_dict(self) -> dict:
        return {"at_min": self.at_min, "location": self.location, "note": self.note}


class StopRecord(EmbeddedModel):
    seq = models.IntegerField()
    type = models.CharField(max_length=32)
    label = models.CharField(max_length=255)
    lat = models.FloatField()
    lng = models.FloatField()
    mile_marker = models.FloatField()
    arrive_at = models.DateTimeField()
    depart_at = models.DateTimeField()
    status = models.CharField(max_length=8)
    reason = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    def to_dict(self, tz: str) -> dict:
        duration_min = round((self.depart_at - self.arrive_at).total_seconds() / 60)
        return {
            "seq": self.seq,
            "type": self.type,
            "label": self.label,
            "lat": self.lat,
            "lng": self.lng,
            "mile_marker": self.mile_marker,
            "arrive_at": _iso(self.arrive_at, tz),
            "depart_at": _iso(self.depart_at, tz),
            "duration_min": duration_min,
            "status": self.status,
            "reason": self.reason,
        }


class DailyLog(EmbeddedModel):
    day_number = models.IntegerField()
    date = models.CharField(max_length=10)
    from_location = models.CharField(max_length=255)
    to_location = models.CharField(max_length=255)
    miles_driving_today = models.FloatField()
    total_mileage_today = models.FloatField()
    log_meta = EmbeddedModelField(LogMeta)
    off_hrs = models.FloatField()
    sb_hrs = models.FloatField()
    d_hrs = models.FloatField()
    on_hrs = models.FloatField()
    segments = EmbeddedModelArrayField(DutySegment)
    remarks = EmbeddedModelArrayField(Remark)
    recap_on_duty_today = models.FloatField()
    recap_a_last_7 = models.FloatField()
    recap_b_available = models.FloatField()
    recap_c_last_5 = models.FloatField()
    restart_34_taken = models.BooleanField()

    def to_dict(self) -> dict:
        return {
            "day_number": self.day_number,
            "date": self.date,
            "header": {
                "from": self.from_location,
                "to": self.to_location,
                "miles_driving_today": self.miles_driving_today,
                "total_mileage_today": self.total_mileage_today,
                **self.log_meta.to_dict(),
            },
            "segments": [segment.to_dict() for segment in self.segments],
            "totals": {
                "OFF": self.off_hrs,
                "SB": self.sb_hrs,
                "D": self.d_hrs,
                "ON": self.on_hrs,
            },
            "remarks": [remark.to_dict() for remark in self.remarks],
            "recap": {
                "on_duty_today": self.recap_on_duty_today,
                "a_last_7": self.recap_a_last_7,
                "b_available_tomorrow": self.recap_b_available,
                "c_last_5": self.recap_c_last_5,
                "restart_34_taken": self.restart_34_taken,
            },
        }


class Trip(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    current = EmbeddedModelField(Location)
    pickup = EmbeddedModelField(Location)
    dropoff = EmbeddedModelField(Location)
    cycle_used_hrs = models.FloatField()
    start_at = models.DateTimeField()
    home_timezone = models.CharField(max_length=64)
    include_inspections = models.BooleanField()
    log_meta = EmbeddedModelField(LogMeta)
    total_miles = models.FloatField()
    total_driving_hrs = models.FloatField()
    total_on_duty_hrs = models.FloatField()
    arrive_at = models.DateTimeField()
    end_at = models.DateTimeField()
    log_days = models.IntegerField()
    cycle_used_end_hrs = models.FloatField()
    route_geometry = models.JSONField()
    route_legs = models.JSONField()
    stops = EmbeddedModelArrayField(StopRecord)
    daily_logs = EmbeddedModelArrayField(DailyLog)

    class Meta:
        db_table = "trips"

    def __str__(self) -> str:
        return f"Trip {self.pk} {self.pickup.label} -> {self.dropoff.label}"

    @classmethod
    def from_plan(cls, plan: dict) -> "Trip":
        inputs = plan["inputs"]
        summary = plan["summary"]
        route = plan["route"]
        tz = inputs["home_timezone"]

        def location(data: dict) -> Location:
            return Location(label=data["label"], lat=data["lat"], lng=data["lng"])

        def stop(data: dict) -> StopRecord:
            return StopRecord(
                seq=data["seq"],
                type=data["type"],
                label=data["label"],
                lat=data["lat"],
                lng=data["lng"],
                mile_marker=data["mile_marker"],
                arrive_at=_to_utc(data["arrive_at"]),
                depart_at=_to_utc(data["depart_at"]),
                status=data["status"],
                reason=data.get("reason"),
            )

        def daily_log(data: dict) -> DailyLog:
            header = data["header"]
            totals = data["totals"]
            recap = data["recap"]
            return DailyLog(
                day_number=data["day_number"],
                date=data["date"],
                from_location=header["from"],
                to_location=header["to"],
                miles_driving_today=header["miles_driving_today"],
                total_mileage_today=header["total_mileage_today"],
                log_meta=LogMeta(**{field: header[field] for field in LOG_META_FIELDS}),
                off_hrs=totals["OFF"],
                sb_hrs=totals["SB"],
                d_hrs=totals["D"],
                on_hrs=totals["ON"],
                segments=[
                    DutySegment(
                        status=segment["status"],
                        start_min=segment["start_min"],
                        end_min=segment["end_min"],
                        note=segment["note"],
                        location=segment["location"],
                    )
                    for segment in data["segments"]
                ],
                remarks=[
                    Remark(
                        at_min=remark["at_min"],
                        location=remark["location"],
                        note=remark["note"],
                    )
                    for remark in data["remarks"]
                ],
                recap_on_duty_today=recap["on_duty_today"],
                recap_a_last_7=recap["a_last_7"],
                recap_b_available=recap["b_available_tomorrow"],
                recap_c_last_5=recap["c_last_5"],
                restart_34_taken=recap["restart_34_taken"],
            )

        return cls(
            current=location(inputs["current"]),
            pickup=location(inputs["pickup"]),
            dropoff=location(inputs["dropoff"]),
            cycle_used_hrs=inputs["cycle_used_hrs"],
            start_at=_to_utc(inputs["start_time"], tz),
            home_timezone=tz,
            include_inspections=inputs["include_inspections"],
            log_meta=LogMeta(**{field: inputs["log_meta"][field] for field in LOG_META_FIELDS}),
            total_miles=summary["total_miles"],
            total_driving_hrs=summary["total_driving_hrs"],
            total_on_duty_hrs=summary["total_on_duty_hrs"],
            arrive_at=_to_utc(summary["arrive_at"]),
            end_at=_to_utc(summary["end_at"]),
            log_days=summary["log_days"],
            cycle_used_end_hrs=summary["cycle_used_end_hrs"],
            route_geometry=route["geometry"],
            route_legs=route["legs"],
            stops=[stop(item) for item in plan["stops"]],
            daily_logs=[daily_log(item) for item in plan["daily_logs"]],
        )

    def to_response(self) -> dict:
        tz = self.home_timezone
        return {
            "id": str(self.pk),
            "inputs": {
                "current": self.current.to_dict(),
                "pickup": self.pickup.to_dict(),
                "dropoff": self.dropoff.to_dict(),
                "cycle_used_hrs": self.cycle_used_hrs,
                "start_time": _wall_clock(self.start_at, tz),
                "home_timezone": tz,
                "include_inspections": self.include_inspections,
                "log_meta": self.log_meta.to_dict(),
            },
            "summary": {
                "total_miles": self.total_miles,
                "total_driving_hrs": self.total_driving_hrs,
                "total_on_duty_hrs": self.total_on_duty_hrs,
                "start_at": _iso(self.start_at, tz),
                "arrive_at": _iso(self.arrive_at, tz),
                "end_at": _iso(self.end_at, tz),
                "log_days": self.log_days,
                "stop_count": len(self.stops),
                "cycle_used_end_hrs": self.cycle_used_end_hrs,
                "home_timezone": tz,
            },
            "route": {
                "geometry": self.route_geometry,
                "legs": self.route_legs,
            },
            "stops": [item.to_dict(tz) for item in self.stops],
            "daily_logs": [item.to_dict() for item in self.daily_logs],
        }
