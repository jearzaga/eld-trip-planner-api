import json

import pytest

from tests.fixtures.scenarios import ROUTABLE_SCENARIOS, UNROUTABLE_TRIP
from trips.management.commands.dump_scenarios import FIXTURES_DIR, build_fixtures

REGENERATE_COMMAND = "uv run python manage.py dump_scenarios"


def test_committed_scenario_fixtures_match_a_fresh_generation():
    fresh_fixtures = build_fixtures()

    for filename, content in fresh_fixtures.items():
        committed_path = FIXTURES_DIR / filename
        assert committed_path.read_text() == content, (
            f"{filename} is stale. Regenerate fixtures with: {REGENERATE_COMMAND}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize("scenario", ROUTABLE_SCENARIOS, ids=lambda scenario: scenario.spec_id)
def test_routable_scenario_response_matches_its_committed_fixture(api_client, scenario):
    response = api_client.post("/api/trips/", scenario.request, format="json")
    assert response.status_code == 201, response.content

    body = response.json()
    filename = f"{scenario.spec_id.lower().replace('-', '')}.json"
    expected = json.loads((FIXTURES_DIR / filename).read_text())
    expected["id"] = body["id"]

    assert body == expected


@pytest.mark.django_db
def test_unroutable_scenario_response_matches_its_committed_fixture(api_client):
    response = api_client.post("/api/trips/", UNROUTABLE_TRIP.request, format="json")
    assert response.status_code == 422

    expected = json.loads((FIXTURES_DIR / "sc6.json").read_text())
    assert response.json() == expected
