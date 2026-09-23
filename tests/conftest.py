import pytest
from rest_framework.test import APIClient

from tests.fixtures.scenarios import SCENARIOS


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def scenario():
    return SCENARIOS.__getitem__
