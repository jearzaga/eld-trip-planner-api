import pytest

from tests.fixtures.scenarios import SHORT_DAY_TRIP


@pytest.mark.django_db
def test_get_trip_after_create_returns_the_identical_body(api_client):
    created = api_client.post("/api/trips/", SHORT_DAY_TRIP.request, format="json")
    assert created.status_code == 201, created.content
    trip_id = created.json()["id"]

    response = api_client.get(f"/api/trips/{trip_id}/")

    assert response.status_code == 200
    assert response.json() == created.json()


@pytest.mark.django_db
def test_get_trip_with_unknown_object_id_returns_404_shape(api_client):
    response = api_client.get("/api/trips/000000000000000000000001/")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["fields"] == {}


@pytest.mark.django_db
def test_get_trip_with_malformed_id_returns_404_shape(api_client):
    response = api_client.get("/api/trips/not-an-id/")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["fields"] == {}
