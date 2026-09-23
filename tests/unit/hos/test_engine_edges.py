from hos.engine import plan_timeline
from hos.models import DutyStatus, Leg, StopType, TripInput

PICKUP_AT_CURRENT_LOCATION_TRIP = TripInput(legs=(Leg(0, 0), Leg(180, 180)), cycle_used_min=0)
INSPECTIONS_OFF_TRIP = TripInput(
    legs=(Leg(60, 60), Leg(180, 180)), cycle_used_min=0, include_inspections=False
)


# SC-7: current location = pickup -> leg 1 has 0 miles; no driving, pickup immediately
def test_zero_mile_leg_drives_nothing():
    timeline = plan_timeline(PICKUP_AT_CURRENT_LOCATION_TRIP)
    assert not any(s.status == DutyStatus.D and s.mile_marker == 0 for s in timeline.segments[:2])
    pickup_stop = next(stop for stop in timeline.stops if stop.type == StopType.PICKUP)
    assert pickup_stop.mile_marker == 0
    assert pickup_stop.start_min == 15


def test_pickup_follows_pretrip_inspection_directly_when_leg_1_is_zero_miles():
    timeline = plan_timeline(PICKUP_AT_CURRENT_LOCATION_TRIP)
    pretrip, pickup = timeline.segments[0], timeline.segments[1]
    assert pretrip.note == "Pre-trip inspection"
    assert pickup.note == "Pickup"
    assert pretrip.end_min == pickup.start_min


# inspections toggled off (A-06): no pre-trip / post-trip segments at all
def test_inspections_off_skips_pretrip_and_posttrip_segments():
    timeline = plan_timeline(INSPECTIONS_OFF_TRIP)
    assert all("inspection" not in (s.note or "").lower() for s in timeline.segments)
    assert timeline.segments[0].status == DutyStatus.D
    assert timeline.segments[0].start_min == 0
