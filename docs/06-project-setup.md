# 06 — Project Setup (Python virtual environment · Django · DRF · MongoDB)

Step-by-step setup of `eld-trip-planner-api` from an empty repo to a green health-check test. Run every command from the
repo root unless stated otherwise. Commands are shown for **macOS/Linux**; Windows (PowerShell) differences are noted.

**Target versions**

| Tool | Version | Why |
|---|---|---|
| Python | 3.12 | Supported by Django 5.2 and all libraries below |
| Django | **5.2 LTS** (`~=5.2.0`) | Supported until April 2028; matches the `django-mongodb-backend` 5.2.x series |
| django-mongodb-backend | **`>=5.2.1,<5.3`** | 5.2.1 added connection strings in `HOST`, and the version must match Django's |
| MongoDB | **Atlas M0 (free tier)** in every environment | No local MongoDB or Docker; dev, tests, E2E, CI and Render all connect to Atlas |

> Newer Django releases exist (6.x) with matching `django-mongodb-backend` 6.x. We stay on the **5.2 LTS** line for
> stability during the assessment. Whichever line you pick, **the backend's major.minor must match Django's**.

---

## 1. Prerequisites

```bash
python3.12 --version     # Windows: py -3.12 --version
git --version
```

You also need a **MongoDB Atlas** account (free M0 cluster, see §6).

Missing Python 3.12? Use `uv python install 3.12` (see §2A), or install it from python.org or pyenv.

---

## 2. Virtual environment: pick ONE option

A virtual environment (`.venv/`) keeps this project's packages separate from the rest of your system. **Never** install
the project's packages globally.

### Option A: `uv` (recommended; the rest of the docs use it)

`uv` creates and manages `.venv/` for you, pins exact versions in `uv.lock`, and is very fast.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv python install 3.12                                   # only if 3.12 isn't installed
uv init --app --python 3.12 .                            # creates pyproject.toml, .python-version
rm -f main.py hello.py                                   # remove uv's sample file(s)
```

Run any command inside the venv by prefixing `uv run` (e.g. `uv run python manage.py runserver`), or activate it:

```bash
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
deactivate                          # to leave
```

### Option B: classic `venv` + `pip`

```bash
python3.12 -m venv .venv            # Windows: py -3.12 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

With option B, drop the `uv run` prefix from every command in these docs and use the `pip` lines shown below.
Update the Commands section of `CLAUDE.md` to match.

> **Windows PowerShell** may block activation scripts. Run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

> **VS Code:** Command Palette → *Python: Select Interpreter* → pick `./.venv`.

---

## 3. Install dependencies

### 3.1 Runtime

| Package | Purpose |
|---|---|
| `django~=5.2.0` | Web framework |
| `djangorestframework` | REST API views, serializers, validation |
| `django-mongodb-backend>=5.2.1,<5.3` | Official MongoDB database backend for Django (installs PyMongo) |
| `django-cors-headers` | Allow the Vercel frontend to call the API |
| `drf-spectacular` | Generates the OpenAPI schema (the contract shared with the web repo) |
| `httpx` | HTTP client for OpenRouteService and Photon |
| `timezonefinder` | Offline lookup of the time zone for a lat/lng (home-terminal time) |
| `python-dotenv` | Loads `.env` in local development |
| `gunicorn` | Production WSGI server on Render |

```bash
# Option A (uv)
uv add "django~=5.2.0" djangorestframework "django-mongodb-backend>=5.2.1,<5.3" \
       django-cors-headers drf-spectacular httpx timezonefinder python-dotenv gunicorn

# Option B (pip)
pip install "django~=5.2.0" djangorestframework "django-mongodb-backend>=5.2.1,<5.3" \
            django-cors-headers drf-spectacular httpx timezonefinder python-dotenv gunicorn
```

### 3.2 Development / testing

| Package | Purpose |
|---|---|
| `pytest`, `pytest-django` | Test runner + Django integration |
| `pytest-cov` | Coverage gates (`hos/` ≥ 95 %) |
| `hypothesis` | Property-based tests for HOS invariants |
| `respx` | Mocks `httpx` calls to ORS/Photon |
| `ruff` | Lint + format |

```bash
# Option A (uv)
uv add --dev pytest pytest-django pytest-cov hypothesis respx ruff

# Option B (pip)
pip install pytest pytest-django pytest-cov hypothesis respx ruff
```

### 3.3 Lock files for Render

Render installs from `requirements.txt`:

```bash
# Option A (uv): export from the lock file (repeat after every dependency change)
uv export --no-dev --no-hashes -o requirements.txt

# Option B (pip): keep runtime and dev deps separate
pip freeze > requirements.txt          # then move test-only packages into requirements-devı.txt
```

---

## 4. Create the Django project and apps

```bash
uv run django-admin startproject config .        # "." = put manage.py in the repo root
uv run python manage.py startapp trips
mkdir -p hos geo tests/unit/hos tests/unit/geo tests/api tests/acceptance tests/contract tests/fixtures/responses
touch hos/__init__.py geo/__init__.py tests/__init__.py
rm trips/admin.py trips/tests.py                 # no admin in scope; tests live in tests/
```

Resulting layout:

```
eld-trip-planner-api/
├─ manage.py
├─ config/        settings.py · urls.py · wsgi.py · asgi.py
├─ trips/         apps.py · models.py · views.py · migrations/
├─ hos/           (pure Python — no Django imports)
├─ geo/
└─ tests/
```

### 4.1 Required fix for `django-mongodb-backend` 5.2.x: `trips/apps.py`

`startapp` writes `default_auto_field = 'django.db.models.BigAutoField'`. MongoDB uses `ObjectId` primary keys, so on
5.2.x you **must remove that line**. The project-wide `DEFAULT_AUTO_FIELD` (below) then applies.

```python
# trips/apps.py
from django.apps import AppConfig


class TripsConfig(AppConfig):
    name = "trips"
```

---

## 5. Configure settings

### 5.1 `.env.example` (commit this) and `.env` (don't commit)

```dotenv
# .env.example
DJANGO_SECRET_KEY=dev-only-change-me
DJANGO_DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
# MongoDB Atlas (free M0) SRV URI, required. Format:
# mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&appName=eld-trip-planner
MONGODB_URI=
MONGODB_DB=eld_dev
GEO_PROVIDER=fake
ORS_API_KEY=
PHOTON_URL=https://photon.komoot.io
CORS_ALLOWED_ORIGINS=http://localhost:5173
CORS_ALLOWED_ORIGIN_REGEXES=
```

```bash
cp .env.example .env     # then paste your Atlas URI into MONGODB_URI (§6)
```

### 5.2 `config/settings.py` (replace the generated file)

```python
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is not set. Add it to .env (see .env.example).")
    return value


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# No admin/auth/sessions: the app has no login (out of scope)
INSTALLED_APPS = [
    "django_mongodb_backend",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "trips",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must come before CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# --- MongoDB Atlas (django-mongodb-backend >= 5.2.1 accepts a connection string in HOST) ---
# There is no local MongoDB: every environment (dev, tests, E2E, CI, Render) uses an Atlas SRV URI.
DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": env_required("MONGODB_URI"),
        "NAME": os.environ.get("MONGODB_DB", "eld"),
    }
}
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]  # required for embedded models

# --- DRF: JSON only, no auth ---
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # "EXCEPTION_HANDLER": "trips.exceptions.api_exception_handler",  # standard error shape (A5-08)
}
SPECTACULAR_SETTINGS = {
    "TITLE": "ELD Trip Planner API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- CORS (Vercel prod + previews) ---
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOWED_ORIGIN_REGEXES = env_list("CORS_ALLOWED_ORIGIN_REGEXES")

# --- Time: store UTC; convert to home-terminal time only in the log builder ---
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

# --- App settings ---
GEO_PROVIDER = os.environ.get("GEO_PROVIDER", "fake")  # fake | live
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")
PHOTON_URL = os.environ.get("PHOTON_URL", "https://photon.komoot.io")

# --- Production hardening (Render terminates TLS in front of the app) ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

> `MONGODB_URI` has **no default**: settings raise `ImproperlyConfigured` if it's missing, so nothing silently falls
> back to `localhost`. This also applies to `pytest` (pytest-django loads settings), so set it before running tests.

> `EXCEPTION_HANDLER` stays commented out until A5-08 adds `trips/exceptions.py`; uncomment it in that task.

> **If DRF or drf-spectacular errors because `django.contrib.auth`/`contenttypes` aren't installed**, compare against
> MongoDB's project template for 5.2 (`django-admin startproject <name> --template
> https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/5.2.x.zip`). It configures the contrib apps
> with MongoDB-specific `MIGRATION_MODULES`.

### 5.3 `config/urls.py` (replace; the generated file imports the admin)

```python
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

urlpatterns = [
    path("api/", include("trips.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]
```

---

## 6. MongoDB Atlas (free M0 cluster)

There is **no local MongoDB and no Docker**. Every environment connects to one Atlas M0 cluster, and each environment
gets its own database name through `MONGODB_DB`.

1. In [Atlas](https://cloud.mongodb.com), create a free **M0** cluster on AWS `us-east-1` (same region as Render `virginia`).
2. **Database Access:** add a database user with *Read and write to any database* (pytest-django creates and drops
   `test_<MONGODB_DB>` databases).
3. **Network Access:** add `0.0.0.0/0`. Render free instances and GitHub Actions runners have no static outbound IP.
4. **Connect → Drivers:** copy the SRV string (`mongodb+srv://…`), fill in the password, and paste it into
   `MONGODB_URI` in `.env`. URL-encode special characters in the password.
5. Check the connection:

```bash
uv run python manage.py shell -c "from django.db import connection; print(connection.database.command('ping'))"
# → {'ok': 1.0, ...}
```

**Database names on the shared cluster**

| Environment | `MONGODB_DB` | Test DB created by pytest-django |
|---|---|---|
| Local dev | `eld_dev` | `test_eld_dev` |
| E2E (Playwright boots the API) | `eld_e2e` | — |
| CI (GitHub Actions) | `eld_ci` | `test_eld_ci` (separate, so CI can't clash with a local test run) |
| Render (production) | `eld` (set in `render.yaml`) | — |

> M0 limits: 512 MB storage, 500 collections, 100 databases, shared CPU. That's plenty for this project.

---

## 7. Test tooling config: `pyproject.toml`

Append (option A already has a `pyproject.toml`; option B creates one just for tool config):

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-q --cov=hos --cov=geo --cov=trips --cov-report=term-missing"
markers = ["live: hits real external APIs (never run in CI)"]

[tool.coverage.run]
omit = ["*/migrations/*", "config/*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "DJ"]
```

Tests use a separate database on the Atlas cluster: pytest-django creates `test_<MONGODB_DB>` and drops it afterwards.
The first test run is slower than it would be locally, because each connection goes over TLS to Atlas.

---

## 8. First TDD cycle: health endpoint (task A0-04)

**Red:** write the test first.

```python
# tests/api/test_health.py
import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_returns_ok():
    res = APIClient().get("/api/health/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
```

```bash
uv run pytest tests/api/test_health.py      # fails: trips.urls doesn't exist / 404
```

**Green:** minimum code.

```python
# trips/views.py
from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    def get(self, request):
        try:
            connection.database.command("ping")   # pymongo Database exposed by django-mongodb-backend
        except Exception:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})
```

```python
# trips/urls.py
from django.urls import path

from .views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
```

```bash
uv run pytest tests/api/test_health.py      # passes
```

---

## 9. Migrations and run

```bash
uv run python manage.py makemigrations trips      # once models exist (A5-02)
uv run python manage.py migrate                   # creates collections/indexes in MongoDB
uv run python manage.py runserver 8000
curl http://localhost:8000/api/health/            # {"status":"ok"}
curl http://localhost:8000/api/schema/ | head     # OpenAPI YAML
```

---

## 10. Other repo files

**`.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.env
.coverage
htmlcov/
.pytest_cache/
.ruff_cache/
.hypothesis/
```

**`render.yaml`**: see `02-architecture.md` §7.

**`.github/workflows/ci.yml`** (minimal; extended in A5 with contract drift checks). Add the Atlas URI as a repository
secret first: GitHub → *Settings → Secrets and variables → Actions* → `MONGODB_URI`.

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      MONGODB_URI: ${{ secrets.MONGODB_URI }}   # repo secret: the Atlas SRV URI
      MONGODB_DB: eld_ci
      GEO_PROVIDER: fake
      DJANGO_DEBUG: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - run: uv run ruff check . && uv run ruff format --check .
      - run: uv run pytest
      - run: uv export --no-dev --no-hashes -o requirements.txt && git diff --exit-code requirements.txt
```

---

## 11. Verification checklist

- [ ] `.venv/` exists and the editor uses it
- [ ] `uv run python -c "import django, rest_framework, django_mongodb_backend; print(django.get_version())"` prints `5.2.x`
- [ ] `MONGODB_URI` set in `.env` → Atlas ping ok (§6)
- [ ] `uv run pytest` → health test green
- [ ] `uv run ruff check .` clean
- [ ] `runserver` + `curl /api/health/` → `{"status":"ok"}`
- [ ] `requirements.txt` exported and committed; `.env` **not** committed
- [ ] `trips/apps.py` has no `BigAutoField` line

## 12. Common problems

| Symptom | Fix |
|---|---|
| `ImproperlyConfigured: MONGODB_URI is not set` | Copy `.env.example` to `.env` and paste the Atlas SRV URI (§6) |
| `ServerSelectionTimeoutError` | The Atlas Network Access list is missing `0.0.0.0/0` (or your IP), or the cluster is paused |
| `OperationFailure: bad auth` | Wrong DB user or password in the URI; URL-encode special characters in the password |
| Errors mentioning `BigAutoField` / `ObjectId` | Remove `default_auto_field` from the app's `AppConfig` (§4.1) |
| `Model class ... isn't in INSTALLED_APPS` for auth/contenttypes | Something imports a contrib model; see the template note in §5.2 |
| Browser CORS error from the web app | Add the exact origin (scheme + host + port) to `CORS_ALLOWED_ORIGINS` |
| Package versions conflict | Django and `django-mongodb-backend` must share major.minor (5.2 ↔ 5.2.x) |
| Windows: `source` not found | Use `.venv\Scripts\Activate.ps1` in PowerShell |
