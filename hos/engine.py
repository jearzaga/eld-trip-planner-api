from dataclasses import dataclass, field

from hos.models import DutyStatus, Leg, Segment, Stop, StopType, Timeline, TripInput
from hos.rules import (
    BREAK_MIN,
    CYCLE_LIMIT_MIN,
    DRIVING_BEFORE_BREAK_MIN,
    DROPOFF_MIN,
    FUEL_INTERVAL_MI,
    FUEL_MIN,
    INSPECTION_MIN,
    MAX_DRIVING_MIN,
    PICKUP_MIN,
    RESET_MIN,
    RESTART_MIN,
    SHIFT_WINDOW_MIN,
)
from hos.time_utils import ceil_q, floor_q


def _minutes_for(miles: float, mph: float) -> float:
    return miles / mph * 60 if mph else 0.0


@dataclass
class _State:
    cycle_used: int = 0
    t: int = 0
    shift_start: int = 0
    shift_active: bool = False
    drive_in_shift: int = 0
    drive_since_break: int = 0
    miles_since_fuel: float = 0.0
    total_miles: float = 0.0
    non_driving_streak: int = 0
    off_streak: int = 0
    segments: list[Segment] = field(default_factory=list)
    stops: list[Stop] = field(default_factory=list)

    def minutes_since_shift_start(self) -> int:
        return self.t - self.shift_start

    def start_shift_if_needed(self) -> None:
        if not self.shift_active:
            self.shift_active = True
            self.shift_start = self.t

    def drive(self, minutes: int, leg: Leg) -> int:
        self.start_shift_if_needed()
        self.segments.append(Segment(DutyStatus.D, self.t, self.t + minutes, self.total_miles))
        miles = minutes / 60 * leg.mph
        self.t += minutes
        self.total_miles += miles
        self.miles_since_fuel += miles
        self.drive_in_shift += minutes  # R-01
        self.drive_since_break += minutes  # R-03
        self.cycle_used += minutes  # R-04
        self.non_driving_streak = 0
        self.off_streak = 0
        return minutes

    def on(self, minutes: int, note: str, stop_type: StopType | None = None) -> None:
        self.start_shift_if_needed()  # R-02
        start = self.t
        end = start + minutes
        self.segments.append(Segment(DutyStatus.ON, start, end, self.total_miles, note))
        if stop_type is not None:
            self.stops.append(Stop(stop_type, DutyStatus.ON, start, end, self.total_miles))
        self.t += minutes
        self.cycle_used += minutes  # R-04
        self.non_driving_streak += minutes
        if self.non_driving_streak >= BREAK_MIN:  # R-03
            self.drive_since_break = 0
        self.off_streak = 0

    def off(
        self, minutes: int, status: DutyStatus, note: str, stop_type: StopType | None = None
    ) -> None:
        start = self.t
        self.segments.append(Segment(status, start, start + minutes, self.total_miles, note))
        if stop_type is not None:
            self.stops.append(Stop(stop_type, status, start, start + minutes, self.total_miles))
        self.t += minutes
        self.non_driving_streak += minutes
        if self.non_driving_streak >= BREAK_MIN:  # R-03
            self.drive_since_break = 0
        self.off_streak += minutes
        if self.off_streak >= RESET_MIN:  # R-05
            self.shift_active = False
            self.drive_in_shift = 0
        if self.off_streak >= RESTART_MIN:  # R-04
            self.cycle_used = 0

    def fuel_stop(self) -> None:
        self.on(FUEL_MIN, "Fuel", StopType.FUEL)  # R-06
        self.miles_since_fuel = 0.0

    def break_30(self) -> None:
        self.off(BREAK_MIN, DutyStatus.OFF, "30-minute break", StopType.BREAK_30)  # R-03, A-07

    def reset_10(self) -> None:
        self.off(RESET_MIN, DutyStatus.SB, "10-hour reset", StopType.REST_10)  # R-05, A-07

    def restart_34(self) -> None:
        self.off(RESTART_MIN, DutyStatus.OFF, "34-hour restart", StopType.RESTART_34)  # R-04, A-07

    def resolve(self, hit: set[str]) -> None:  # A-12
        if "fuel" in hit:
            self.fuel_stop()
            hit = hit - {"break"}  # a fuel stop is already >= 30 min non-driving (R-03)
        if "70" in hit:
            self.restart_34()
        elif "11" in hit or "14" in hit:
            self.reset_10()
        elif "break" in hit:
            self.break_30()

    @property
    def timeline(self) -> Timeline:
        return Timeline(segments=tuple(self.segments), stops=tuple(self.stops))


def _drive_leg(s: _State, leg: Leg) -> None:
    remaining = ceil_q(leg.duration_min)  # A-08
    while remaining > 0:
        s.start_shift_if_needed()
        fuel_miles_left = max(0.0, FUEL_INTERVAL_MI - s.miles_since_fuel)
        minutes_to_fuel = _minutes_for(fuel_miles_left, leg.mph) if leg.mph else remaining
        limits = {
            "leg": remaining,
            "fuel": floor_q(minutes_to_fuel),  # R-06, A-09
            "break": DRIVING_BEFORE_BREAK_MIN - s.drive_since_break,  # R-03
            "11": MAX_DRIVING_MIN - s.drive_in_shift,  # R-01
            "14": SHIFT_WINDOW_MIN - s.minutes_since_shift_start(),  # R-02
            "70": CYCLE_LIMIT_MIN - s.cycle_used,  # R-04
        }
        chunk = max(0, min(limits.values()))
        if chunk:
            remaining -= s.drive(chunk, leg)
        hit = {key for key, value in limits.items() if value <= chunk}
        if "leg" in hit and remaining == 0:
            return
        s.resolve(hit)


def plan_timeline(trip: TripInput) -> Timeline:
    s = _State(cycle_used=trip.cycle_used_min)
    if s.cycle_used >= CYCLE_LIMIT_MIN:  # A-05
        s.restart_34()
    if trip.include_inspections:
        s.on(INSPECTION_MIN, "Pre-trip inspection")  # A-06
    _drive_leg(s, trip.legs[0])
    s.on(PICKUP_MIN, "Pickup", StopType.PICKUP)  # R-07
    _drive_leg(s, trip.legs[1])
    s.on(DROPOFF_MIN, "Dropoff", StopType.DROPOFF)  # R-07
    if trip.include_inspections:
        s.on(INSPECTION_MIN, "Post-trip inspection")  # A-06
    return s.timeline
