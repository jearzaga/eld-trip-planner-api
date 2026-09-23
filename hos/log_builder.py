from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from hos.models import DutyStatus, Segment, Timeline
from hos.rules import RESTART_MIN

Totals = dict[str, float]

ON_DUTY_STATUSES = (DutyStatus.D, DutyStatus.ON)
RESTING_STATUSES = (DutyStatus.OFF, DutyStatus.SB)


@dataclass(frozen=True)
class LogMeta:
    driver_name: str = "John Doe"
    co_driver_name: str = ""
    carrier_name: str = "John Doe's Transportation"
    main_office_address: str = "Washington, D.C."
    home_terminal_address: str = "Richmond, VA"
    truck_tractor_no: str = "123"
    trailer_no: str = "456"
    shipping_doc_no: str = "BOL-10001"
    shipper_commodity: str = "ACME Co. — paper products"


@dataclass(frozen=True)
class DaySegment:
    status: DutyStatus
    start_min: int
    end_min: int
    note: str | None = None
    location: str | None = None

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min


@dataclass(frozen=True)
class Remark:
    at_min: int
    location: str | None
    note: str | None


@dataclass(frozen=True)
class Header:
    date: str
    from_location: str
    to_location: str
    miles_driving_today: float
    total_mileage_today: float
    driver_name: str
    co_driver_name: str
    carrier_name: str
    main_office_address: str
    home_terminal_address: str
    truck_tractor_no: str
    trailer_no: str
    shipping_doc_no: str
    shipper_commodity: str


@dataclass(frozen=True)
class Recap:
    on_duty_today: float
    a_last_7: float
    b_available_tomorrow: float
    c_last_5: float
    restart_34_taken: bool


@dataclass(frozen=True)
class DailyLog:
    day_number: int
    date: str
    header: Header
    segments: tuple[DaySegment, ...]
    totals: Totals
    remarks: tuple[Remark, ...]
    recap: Recap


@dataclass
class _Piece:
    status: DutyStatus
    start_dt: datetime
    end_dt: datetime
    mile_start: float
    mile_end: float
    note: str | None
    location: str | None
    is_continuation: bool


def _local_midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _raw_pieces(timeline: Timeline, start_utc: datetime, tz: ZoneInfo) -> list[_Piece]:
    segments = timeline.segments
    pieces: list[_Piece] = []

    def local(minute: int) -> datetime:
        return (start_utc + timedelta(minutes=minute)).astimezone(tz)

    trip_start_local = local(0)
    day_start = _local_midnight(trip_start_local)
    if day_start < trip_start_local:
        pieces.append(
            _Piece(
                status=DutyStatus.OFF,
                start_dt=day_start,
                end_dt=trip_start_local,
                mile_start=segments[0].mile_marker if segments else 0.0,
                mile_end=segments[0].mile_marker if segments else 0.0,
                note=None,
                location=None,
                is_continuation=False,
            )
        )

    for index, segment in enumerate(segments):
        has_next = index + 1 < len(segments)
        mile_end = segments[index + 1].mile_marker if has_next else segment.mile_marker
        pieces.append(
            _Piece(
                status=segment.status,
                start_dt=local(segment.start_min),
                end_dt=local(segment.end_min),
                mile_start=segment.mile_marker,
                mile_end=mile_end,
                note=segment.note,
                location=segment.location,
                is_continuation=False,
            )
        )

    trip_end_local = local(segments[-1].end_min) if segments else trip_start_local
    end_day_start = _local_midnight(trip_end_local)
    if trip_end_local > end_day_start:
        day_after_end = end_day_start + timedelta(days=1)
        last_mile = segments[-1].mile_marker if segments else 0.0
        pieces.append(
            _Piece(
                status=DutyStatus.OFF,
                start_dt=trip_end_local,
                end_dt=day_after_end,
                mile_start=last_mile,
                mile_end=last_mile,
                note=None,
                location=None,
                is_continuation=False,
            )
        )

    return pieces


def _split_at_midnights(piece: _Piece) -> list[_Piece]:
    if piece.start_dt == piece.end_dt:
        return []

    total_duration = (piece.end_dt - piece.start_dt).total_seconds() / 60
    total_mile_delta = piece.mile_end - piece.mile_start

    split: list[_Piece] = []
    cursor = piece.start_dt
    mile_cursor = piece.mile_start
    first = True
    while cursor < piece.end_dt:
        next_midnight = _local_midnight(cursor) + timedelta(days=1)
        boundary = min(next_midnight, piece.end_dt)
        duration = (boundary - cursor).total_seconds() / 60
        mile_delta = total_mile_delta * (duration / total_duration) if total_duration else 0.0
        split.append(
            _Piece(
                status=piece.status,
                start_dt=cursor,
                end_dt=boundary,
                mile_start=mile_cursor,
                mile_end=mile_cursor + mile_delta,
                note=piece.note if first else None,
                location=piece.location if first else None,
                is_continuation=not first,
            )
        )
        mile_cursor += mile_delta
        cursor = boundary
        first = False

    return split


def _restart_ends_min(segments: tuple[Segment, ...]) -> list[int]:
    ends: list[int] = []
    run_start: int | None = None
    run_end: int | None = None
    for segment in segments:
        if segment.status in RESTING_STATUSES:
            if run_start is None:
                run_start = segment.start_min
            run_end = segment.end_min
        else:
            if run_start is not None and run_end - run_start >= RESTART_MIN:
                ends.append(run_end)
            run_start = None
            run_end = None
    if run_start is not None and run_end - run_start >= RESTART_MIN:
        ends.append(run_end)
    return ends


def _recap_for_day(
    *,
    segments: tuple[Segment, ...],
    restart_ends: list[int],
    cycle_used_min: int,
    on_duty_today_min: int,
    day_start_min: float,
    day_end_min: float,
) -> Recap:
    prior_restarts = [end for end in restart_ends if end <= day_end_min]
    effective_start = max(prior_restarts) if prior_restarts else 0
    baseline_hours = 0.0 if prior_restarts else cycle_used_min / 60

    on_duty_min = 0.0
    for segment in segments:
        if segment.status not in ON_DUTY_STATUSES:
            continue
        overlap_start = max(segment.start_min, effective_start)
        overlap_end = min(segment.end_min, day_end_min)
        if overlap_end > overlap_start:
            on_duty_min += overlap_end - overlap_start

    a_last_7 = round(baseline_hours + on_duty_min / 60, 2)
    b_available_tomorrow = round(max(0.0, 70 - a_last_7), 2)
    restart_today = any(day_start_min <= end < day_end_min for end in restart_ends)

    return Recap(
        on_duty_today=round(on_duty_today_min / 60, 2),
        a_last_7=a_last_7,
        b_available_tomorrow=b_available_tomorrow,
        c_last_5=a_last_7,  # A-14: no rolling window, so C matches A
        restart_34_taken=restart_today,
    )


def build_daily_logs(
    timeline: Timeline,
    *,
    start_utc: datetime,
    home_tz: str,
    cycle_used_min: int = 0,
    meta: LogMeta | None = None,
) -> list[DailyLog]:
    meta = meta or LogMeta()
    tz = ZoneInfo(home_tz)

    pieces = [
        split_piece
        for raw_piece in _raw_pieces(timeline, start_utc, tz)
        for split_piece in _split_at_midnights(raw_piece)
    ]

    days = sorted({piece.start_dt.date() for piece in pieces})
    restart_ends = _restart_ends_min(timeline.segments)

    daily_logs: list[DailyLog] = []
    for day_number, day_date in enumerate(days, start=1):
        day_start_local = datetime(day_date.year, day_date.month, day_date.day, tzinfo=tz)
        day_end_local = day_start_local + timedelta(days=1)
        day_start_min = (day_start_local - start_utc).total_seconds() / 60
        day_end_min = (day_end_local - start_utc).total_seconds() / 60

        day_pieces = [p for p in pieces if p.start_dt.date() == day_date]

        day_segments = tuple(
            DaySegment(
                status=p.status,
                start_min=round((p.start_dt - day_start_local).total_seconds() / 60),
                end_min=round((p.end_dt - day_start_local).total_seconds() / 60),
                note=p.note,
                location=p.location,
            )
            for p in day_pieces
        )

        totals: Totals = {status.value: 0.0 for status in DutyStatus}
        for segment in day_segments:
            totals[segment.status.value] = round(
                totals[segment.status.value] + segment.duration_min / 60, 2
            )

        remarks = tuple(
            Remark(at_min=segment.start_min, location=piece.location, note=piece.note)
            for piece, segment in zip(day_pieces, day_segments, strict=True)
            if not piece.is_continuation and (piece.location or piece.note)
        )

        located_pieces = [p for p in day_pieces if p.location]
        from_location = located_pieces[0].location if located_pieces else ""
        to_location = located_pieces[-1].location if located_pieces else ""
        miles_driving_today = round(
            sum(p.mile_end - p.mile_start for p in day_pieces if p.status == DutyStatus.D), 2
        )

        on_duty_today_min = sum(
            s.duration_min for s in day_segments if s.status in ON_DUTY_STATUSES
        )
        recap = _recap_for_day(
            segments=timeline.segments,
            restart_ends=restart_ends,
            cycle_used_min=cycle_used_min,
            on_duty_today_min=on_duty_today_min,
            day_start_min=day_start_min,
            day_end_min=day_end_min,
        )

        header = Header(
            date=day_date.isoformat(),
            from_location=from_location,
            to_location=to_location,
            miles_driving_today=miles_driving_today,
            total_mileage_today=miles_driving_today,  # A-13
            driver_name=meta.driver_name,
            co_driver_name=meta.co_driver_name,
            carrier_name=meta.carrier_name,
            main_office_address=meta.main_office_address,
            home_terminal_address=meta.home_terminal_address,
            truck_tractor_no=meta.truck_tractor_no,
            trailer_no=meta.trailer_no,
            shipping_doc_no=meta.shipping_doc_no,
            shipper_commodity=meta.shipper_commodity,
        )

        daily_logs.append(
            DailyLog(
                day_number=day_number,
                date=day_date.isoformat(),
                header=header,
                segments=day_segments,
                totals=totals,
                remarks=remarks,
                recap=recap,
            )
        )

    return daily_logs
