import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_returns_ok():
    res = APIClient().get("/api/health/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
