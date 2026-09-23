import json
from pathlib import Path

from django.core.management.base import BaseCommand

from geo.fake import FakeGeoProvider
from geo.provider import RouteNotFound
from tests.fixtures.scenarios import (
    CROSS_COUNTRY_TRIP,
    CYCLE_FULL_TRIP,
    CYCLE_LIMITED_TRIP,
    PICKUP_AT_CURRENT_LOCATION_TRIP,
    SHORT_DAY_TRIP,
    TWO_DAY_WORKED_EXAMPLE_TRIP,
    UNROUTABLE_TRIP,
)
from trips.exceptions import api_exception_handler
from trips.services import plan_trip

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "responses"

SCENARIOS_IN_SPEC_ORDER = [
    SHORT_DAY_TRIP,
    TWO_DAY_WORKED_EXAMPLE_TRIP,
    CYCLE_LIMITED_TRIP,
    CYCLE_FULL_TRIP,
    CROSS_COUNTRY_TRIP,
    UNROUTABLE_TRIP,
    PICKUP_AT_CURRENT_LOCATION_TRIP,
]


def _fixed_trip_id(spec_id: str) -> str:
    sequence_number = int(spec_id.removeprefix("SC-"))
    return str(sequence_number).rjust(24, "0")


def _fixture_filename(spec_id: str) -> str:
    return f"{spec_id.lower().replace('-', '')}.json"


def _fixture_body(scenario) -> dict:
    if scenario.spec_id == UNROUTABLE_TRIP.spec_id:
        try:
            plan_trip(scenario.request, FakeGeoProvider())
        except RouteNotFound as exc:
            return api_exception_handler(exc, {}).data
        raise AssertionError(f"{scenario.spec_id} was expected to raise RouteNotFound")
    plan = plan_trip(scenario.request, FakeGeoProvider())
    return {"id": _fixed_trip_id(scenario.spec_id), **plan}


def build_fixtures() -> dict[str, str]:
    return {
        _fixture_filename(scenario.spec_id): json.dumps(
            _fixture_body(scenario), indent=2, ensure_ascii=False
        )
        + "\n"
        for scenario in SCENARIOS_IN_SPEC_ORDER
    }


class Command(BaseCommand):
    help = "Regenerate tests/fixtures/responses/sc1..sc7.json from tests/fixtures/scenarios.py."

    def handle(self, *args, **options):
        fixtures = build_fixtures()
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        for filename, content in fixtures.items():
            (FIXTURES_DIR / filename).write_text(content)
        self.stdout.write(
            self.style.SUCCESS(f"Wrote {len(fixtures)} scenario fixtures to {FIXTURES_DIR}")
        )
