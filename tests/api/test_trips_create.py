import pytest

from geo.fake import FakeGeoProvider
from geo.provider import ProviderUnavailable
from tests.fixtures.scenarios import SHORT_DAY_TRIP, UNROUTABLE_TRIP
from trips.models import Trip
from trips.services import plan_trip


@pytest.mark.django_db
def test_create_trip_returns_201_with_persisted_service_output(api_client):
    response = api_client.post("/api/trips/", SHORT_DAY_TRIP.request, format="json")

    assert response.status_code == 201, response.content
    body = response.json()

    expected = plan_trip(SHORT_DAY_TRIP.request, FakeGeoProvider())
    expected["id"] = body["id"]
    assert body == expected

    assert Trip.objects.get(pk=body["id"]).to_response() == body


@pytest.mark.django_db
def test_create_trip_with_invalid_body_returns_400_validation_shape(api_client):
    invalid_request = {**SHORT_DAY_TRIP.request, "cycle_used_hrs": 200}

    response = api_client.post("/api/trips/", invalid_request, format="json")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "cycle_used_hrs" in body["error"]["fields"]


@pytest.mark.django_db
def test_create_trip_for_unroutable_locations_returns_422(api_client):
    response = api_client.post("/api/trips/", UNROUTABLE_TRIP.request, format="json")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ROUTE_NOT_FOUND"


@pytest.mark.django_db
def test_create_trip_returns_502_when_provider_unavailable(api_client, monkeypatch):
    def raise_unavailable(name=None):
        raise ProviderUnavailable("upstream exploded")

    monkeypatch.setattr("trips.services.get_provider", raise_unavailable)

    response = api_client.post("/api/trips/", SHORT_DAY_TRIP.request, format="json")

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "upstream exploded" not in body["error"]["message"]
