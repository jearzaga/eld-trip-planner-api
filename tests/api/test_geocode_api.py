from geo.provider import ProviderUnavailable


def test_geocode_returns_matches_with_richmond_first(api_client):
    res = api_client.get("/api/geocode/", {"q": "Rich"})

    assert res.status_code == 200
    body = res.json()
    assert body[0] == {"label": "Richmond, VA", "lat": 37.5407, "lng": -77.436}


def test_geocode_returns_empty_list_when_nothing_matches(api_client):
    res = api_client.get("/api/geocode/", {"q": "Zzzzz"})

    assert res.status_code == 200
    assert res.json() == []


def test_geocode_rejects_query_shorter_than_three_characters(api_client):
    res = api_client.get("/api/geocode/", {"q": "Ri"})

    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "q" in body["error"]["fields"]


def test_geocode_rejects_missing_query(api_client):
    res = api_client.get("/api/geocode/")

    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "q" in body["error"]["fields"]


def test_geocode_returns_502_when_provider_unavailable(api_client, monkeypatch):
    def raise_unavailable(name=None):
        raise ProviderUnavailable("upstream exploded")

    monkeypatch.setattr("trips.views.get_provider", raise_unavailable)

    res = api_client.get("/api/geocode/", {"q": "Rich"})

    assert res.status_code == 502
    body = res.json()
    assert body["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "upstream exploded" not in body["error"]["message"]
