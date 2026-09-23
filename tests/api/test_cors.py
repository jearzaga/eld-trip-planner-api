from rest_framework.test import APIClient

PREVIEW_REGEX = r"^https://eld-trip-planner-web-.*\.vercel\.app$"


def preflight(origin: str):
    return APIClient().options(
        "/api/trips/",
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )


def test_local_vite_origin_allowed(settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]

    res = preflight("http://localhost:5173")

    assert res["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "POST" in res["Access-Control-Allow-Methods"]


def test_other_origin_not_allowed(settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
    settings.CORS_ALLOWED_ORIGIN_REGEXES = []

    res = preflight("https://evil.example.com")

    assert "Access-Control-Allow-Origin" not in res


def test_vercel_preview_origin_allowed_by_regex(settings):
    settings.CORS_ALLOWED_ORIGINS = []
    settings.CORS_ALLOWED_ORIGIN_REGEXES = [PREVIEW_REGEX]
    origin = "https://eld-trip-planner-web-git-feat-x-john.vercel.app"

    res = preflight(origin)

    assert res["Access-Control-Allow-Origin"] == origin


def test_cors_origins_read_from_env():
    from config.settings import env_list

    assert env_list("UNSET_VAR_FOR_TEST", "http://a.test, https://b.test,") == [
        "http://a.test",
        "https://b.test",
    ]
