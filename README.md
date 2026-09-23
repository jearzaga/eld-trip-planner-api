# ELD Trip Planner — API

Django REST API that plans a legal truck trip under FMCSA Hours-of-Service rules and returns the route, every required
stop, and fully computed Driver's Daily Logs.

| | |
|---|---|
| Frontend repo | `https://github.com/<you>/eld-trip-planner-web` |
| Live app | _TBD — https://<app>.vercel.app_ |
| Live API | _TBD — https://<api>.onrender.com/api/health/_ |
| Loom | _TBD_ |

> 🚧 In development — tracker: [`docs/03-implementation-plan.md`](docs/03-implementation-plan.md)

> ℹ️ Hosted on Render's free tier: the first request after ~15 idle minutes can take up to about a minute while the service wakes.

## What it does

`POST /api/trips/` with current location, pickup, dropoff and current cycle used (hrs) →

- route geometry (OpenRouteService, truck profile)
- stops: pickup, dropoff, fuel (≤ 1,000 mi), 30-min breaks, 10-hr rests, 34-hr restarts
- daily logs: per-day duty segments, totals (sum 24 h), remarks (City, ST), header fields, 70-hr/8-day recap

Rules implemented: 11-hr driving, 14-hr window, 30-min break, 70-hr/8-day cycle, 34-hr restart, fueling, 1-hr
pickup/dropoff. See [`docs/01-business-rules.md`](docs/01-business-rules.md).

## Stack

Django 5.2 LTS · Django REST Framework · MongoDB Atlas via `django-mongodb-backend` · OpenRouteService · Photon ·
pytest + Hypothesis · Render

## Run locally

```bash
cp .env.example .env                        # set MONGODB_URI to your MongoDB Atlas (M0) SRV URI
uv sync
uv run python manage.py runserver 8000      # GEO_PROVIDER=fake → no API keys needed
uv run pytest
```

## Docs

[Business rules](docs/01-business-rules.md) · [Architecture & API contract](docs/02-architecture.md) ·
[Implementation plan](docs/03-implementation-plan.md) · [Testing strategy](docs/04-testing-strategy.md) ·
[Getting started](docs/05-getting-started.md) · [Project setup](docs/06-project-setup.md)
