from dataclasses import dataclass
from enum import StrEnum


class DutyStatus(StrEnum):
    OFF = "OFF"
    SB = "SB"
    D = "D"
    ON = "ON"


class StopType(StrEnum):
    PICKUP = "pickup"
    FUEL = "fuel"
    BREAK_30 = "break_30"
    REST_10 = "rest_10"
    RESTART_34 = "restart_34"
    DROPOFF = "dropoff"


@dataclass(frozen=True)
class Leg:
    distance_mi: float
    duration_min: float

    @property
    def mph(self) -> float:
        return self.distance_mi / self.duration_min * 60 if self.duration_min else 0


@dataclass(frozen=True)
class TripInput:
    legs: tuple[Leg, Leg]
    cycle_used_min: int
    include_inspections: bool = True


@dataclass(frozen=True)
class Segment:
    status: DutyStatus
    start_min: int
    end_min: int
    mile_marker: float
    note: str | None = None
    location: str | None = None

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min


@dataclass(frozen=True)
class Stop:
    type: StopType
    status: DutyStatus
    start_min: int
    end_min: int
    mile_marker: float
    reason: str

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min


@dataclass(frozen=True)
class Timeline:
    segments: tuple[Segment, ...]
    stops: tuple[Stop, ...]
