from hypothesis import given, settings
from hypothesis import strategies as st

from hos.engine import plan_timeline
from hos.models import DutyStatus, Leg, TripInput
from hos.rules import (
    CYCLE_LIMIT_MIN,
    DRIVING_BEFORE_BREAK_MIN,
    FUEL_INTERVAL_MI,
    MAX_DRIVING_MIN,
    QUARTER_HOUR_MIN,
    SHIFT_WINDOW_MIN,
)


@st.composite
def _random_leg(draw):
    speed_mph = draw(st.floats(min_value=40, max_value=65, allow_nan=False))
    distance_mi = draw(st.floats(min_value=0, max_value=3000, allow_nan=False))
    return Leg(distance_mi, distance_mi / speed_mph * 60)


@st.composite
def _random_trip(draw):
    cycle_used_min = draw(st.integers(min_value=0, max_value=280)) * 15  # 0-70h, step 0.25h
    return TripInput(
        legs=(draw(_random_leg()), draw(_random_leg())),
        cycle_used_min=cycle_used_min,
        include_inspections=draw(st.booleans()),
    )


def _peak_counters_during_each_driving_segment(segments):
    drive_in_shift = 0
    shift_start = 0
    drive_since_break = 0
    cycle_used = 0
    non_driving_streak = 0
    off_streak = 0
    last_fuel_mile_marker = 0.0
    peaks = []
    for index, segment in enumerate(segments):
        if segment.status == DutyStatus.D:
            drive_in_shift += segment.duration_min
            drive_since_break += segment.duration_min
            cycle_used += segment.duration_min
            non_driving_streak = 0
            off_streak = 0
            end_mile_marker = segments[index + 1].mile_marker
            peaks.append(
                {
                    "drive_in_shift": drive_in_shift,
                    "minutes_since_shift_start": segment.end_min - shift_start,
                    "drive_since_break": drive_since_break,
                    "cycle_used": cycle_used,
                    "miles_since_fuel": end_mile_marker - last_fuel_mile_marker,
                }
            )
        else:
            non_driving_streak += segment.duration_min
            if non_driving_streak >= 30:  # R-03
                drive_since_break = 0
            if segment.status == DutyStatus.ON:
                cycle_used += segment.duration_min
                off_streak = 0
                if segment.note == "Fuel":
                    last_fuel_mile_marker = segment.mile_marker
            else:
                off_streak += segment.duration_min
                if off_streak >= 600:  # R-05
                    shift_start = segment.end_min
                    drive_in_shift = 0
                if off_streak >= 2040:  # R-04
                    cycle_used = 0
    return peaks


# architecture 02 §4.1: never driving beyond any HOS limit
@given(_random_trip())
@settings(max_examples=100, deadline=None)
def test_engine_never_drives_past_any_hos_limit(trip):
    timeline = plan_timeline(trip)
    for peak in _peak_counters_during_each_driving_segment(timeline.segments):
        assert peak["drive_in_shift"] <= MAX_DRIVING_MIN
        assert peak["minutes_since_shift_start"] <= SHIFT_WINDOW_MIN
        assert peak["drive_since_break"] <= DRIVING_BEFORE_BREAK_MIN
        assert peak["cycle_used"] <= CYCLE_LIMIT_MIN
        assert peak["miles_since_fuel"] <= FUEL_INTERVAL_MI + 1e-6


# architecture 02 §4.1: contiguous segments starting at 0, every boundary on a 15-min tick
@given(_random_trip())
@settings(max_examples=100, deadline=None)
def test_segments_are_contiguous_and_quarter_hour_aligned(trip):
    timeline = plan_timeline(trip)
    segments = timeline.segments
    assert segments[0].start_min == 0
    for segment in segments:
        assert segment.start_min % QUARTER_HOUR_MIN == 0
        assert segment.end_min % QUARTER_HOUR_MIN == 0
        assert segment.end_min > segment.start_min
    for earlier, later in zip(segments, segments[1:]):  # noqa: B905
        assert earlier.end_min == later.start_min


# architecture 02 §4.1: stops are in time order, each boundary on a 15-min tick
@given(_random_trip())
@settings(max_examples=100, deadline=None)
def test_stops_are_time_ordered_and_quarter_hour_aligned(trip):
    timeline = plan_timeline(trip)
    stops = timeline.stops
    assert [stop.start_min for stop in stops] == sorted(stop.start_min for stop in stops)
    for stop in stops:
        assert stop.start_min % QUARTER_HOUR_MIN == 0
        assert stop.end_min % QUARTER_HOUR_MIN == 0
