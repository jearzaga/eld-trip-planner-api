# 03 — Implementation Plan & Status Tracker (API)

> - Task IDs: `A<phase>-<nn>` (API repo). Web tasks are `W<phase>-<nn>` in `eld-trip-planner-web/docs/03-implementation-plan.md`,
>   which also holds the **system-wide progress overview**.
> - Commit with the task ID: `feat(hos): A2-04 …`. Update **Status** in the same commit.
> - A phase is ✅ when all tasks are ✅ and its **Gate** passes.
> - **Feature work (A2+) is blocked until W1 (Playwright harness + acceptance specs) and A1 are ✅.**
> - "Test first" = the test you write/enable and watch fail before the code.

**Status:** ⬜ Not started · 🟨 In progress · ✅ Done · ⛔ Blocked · ⏭️ Deferred (stretch)

## Cross-repo order

```
A0 ─┐
    ├─► W1 (Playwright) ─┬─► A2 → A3 → A4 → A5 ─┬─► W6 → W7 → W8 → W9 ─┐
W0 ─┘         A1 ────────┘                      │                      ├─► A10 + W10 → A11 + W11
                                                 └── (contract synced) ─┘
```

W1 needs A0's `/api/health/` and the fake-provider switch so Playwright can boot the backend.

## What's left (next up)

_Updated 2026-09-24 after A4 (geo services) landed._

1. **A1 ✅ (merged, PR #2).** SC-1…SC-7 + AC-30…AC-35 acceptance tests are collected and skipped (`enable in A5-01`);
   the AC-34 John Doe golden is a skipped placeholder in `tests/unit/hos/test_log_builder_golden.py` (`enable in A3-04`).
2. **W1 ✅ (merged, web PR #2).** Playwright harness + every AC as a `fixme` spec; W1-07 CI deferred.
3. **A2 ✅ A3 ✅** (HOS engine, log builder). `plan_timeline` → `build_daily_logs` reproduces SC-1…SC-5 sheets, each totalling 24 h.
   **Next: A5 (API + contract).**
4. **A4 ✅** (geo services). Fake provider serves SC-1…SC-7; `GEO_PROVIDER=live` = ORS `driving-hgv` + Photon behind
   the Mongo TTL caches; `ensure_indexes` is back in the Render build command.
5. **A0 ✅.** Render service configured in the dashboard, health endpoint live at
   `https://eld-trip-planner-api-ozav.onrender.com/api/health/`. **A0-07 CI is ⏭️ deferred** (see *Decision log*):
   run the checks locally before each PR until it is re-added.
6. **A10, A11** at the end (production deploy, README / Loom).

## Progress overview (API)

| Phase | Name | Est. | Status | Gate |
|---|---|---|---|---|
| A0 | Repo & tooling foundation | 0.5 d | ✅ | Health endpoint green locally and on Render (CI deferred) |
| A1 | Acceptance tests (pytest, skipped) | 0.25 d | ✅ | All SC-1…SC-7 acceptance tests exist and are collected (skipped) |
| A2 | HOS engine (pure Python) | 1 d | ✅ | Goldens + property tests green; `hos/` ≥ 95 % |
| A3 | Log builder | 0.5 d | ✅ | John Doe golden + SC-1…SC-5 logs total 24 |
| A4 | Geo services | 0.5 d | ✅ | Adapters tested with recorded fixtures; fake serves all scenarios |
| A5 | API, persistence, contract | 0.75 d | ⬜ | Acceptance tests green; web `api-contract.spec.ts` green; artifacts published |
| A10 | Production deploy (Render) | 0.25 d | ⬜ | Live provider works on Render; web `@smoke` green |
| A11 | Deliverables (API) | 0.25 d | ⬜ | README final |

---

## A0 — Repo & tooling foundation

| ID | Task | Test first | Status |
|---|---|---|---|
| A0-01 | Create GitHub repo `eld-trip-planner-api` (public); `.gitignore`, `.editorconfig`, `README.md`, `CLAUDE.md`, `docs/` | — | ✅ |
| A0-02 | MongoDB Atlas M0 cluster + DB user + network access `0.0.0.0/0`; `MONGODB_URI` in `.env` (no local MongoDB / Docker) | Atlas ping via `manage.py shell` (`06-project-setup.md` §6) | ✅ |
| A0-03 | Per `06-project-setup.md`: venv (`uv init`); deps: Django 5.2, DRF, `django-mongodb-backend>=5.2.1,<5.3`, django-cors-headers, httpx, timezonefinder, python-dotenv, gunicorn, drf-spectacular; dev: pytest, pytest-django, pytest-cov, hypothesis, respx, ruff. Env-driven `config/settings.py`; packages `hos`, `geo`, app `trips` | `uv run pytest` collects without error | ✅ |
| A0-04 | `GET /api/health/` (pings Mongo) | `tests/api/test_health.py` | ✅ |
| A0-05 | `GEO_PROVIDER` factory with a stub `FakeGeoProvider` (straight-line route); `MONGODB_DB` override for test/E2E | `tests/unit/geo/test_provider_factory.py` | ✅ |
| A0-06 | CORS from env (`CORS_ALLOWED_ORIGINS`, `CORS_ALLOWED_ORIGIN_REGEXES`) | `tests/api/test_cors.py` (localhost:5173 allowed, other origin not) | ✅ |
| A0-07 | CI: ruff + pytest against Atlas (`MONGODB_URI` repo secret, `MONGODB_DB=eld_ci`); `requirements.txt` export + drift check | push → green | ⏭️ |
| A0-08 | Render Web Service (dashboard config, reuses the A0-02 Atlas cluster); first Render deploy of health endpoint (`GEO_PROVIDER=fake` for now) | `curl https://<api>.onrender.com/api/health/` → ok | ✅ |

**Gate:** health green locally and on Render (CI deferred, see *Decision log*). → unblocks **W1**.

> A0-07 is ⏭️ deferred and `.github/workflows/ci.yml` was removed (see *Decision log*). A0-08 is done: the Render service is configured in the dashboard and
> `https://eld-trip-planner-api-ozav.onrender.com/api/health/` returns `200 {"status":"ok"}` (verified 2026-09-23).
> W1 only needs A0-04 + A0-05 (health + fake provider) locally, so it can start now.

## A1 — Acceptance tests (outer loop, written up front)

| ID | Task | Test first | Status |
|---|---|---|---|
| A1-01 | `tests/conftest.py`: `api_client` fixture | — | ✅ |
| A1-02 | `tests/acceptance/test_scenarios.py`: SC-1…SC-7 + AC-30…AC-35 assertions, each `@pytest.mark.skip(reason="enable in A5-01")`; AC-34 placeholder in `tests/unit/hos/test_log_builder_golden.py` (skip until A3-04) | `pytest tests/acceptance` → all collected, all skipped | ✅ |
| A1-03 | Named scenario constants (`SHORT_DAY_TRIP`, …) with inputs + expectations in `tests/fixtures/scenarios.py` (from `04-testing-strategy.md` §3) | — | ✅ |

**Gate:** acceptance suite collected (skipped). Together with W1 ✅ → feature work may start.

## A2 — HOS engine (`hos/`)

Outer loop: golden tests A2-11 / A2-13 (HTTP not available yet).

| ID | Task | Test first | Status |
|---|---|---|---|
| A2-01 | `hos/models.py` dataclasses (`DutyStatus`, `Leg`, `TripInput`, `Segment`, `Stop`, `Timeline`); `hos/rules.py` constants with R-IDs | `test_models.py` | ✅ |
| A2-02 | `ceil_q` / `floor_q` helpers | `test_time_utils.py` | ✅ |
| A2-03 | Basic sequence pre-trip → leg 1 → pickup → leg 2 → dropoff → post-trip (SC-1) | `test_engine_basic.py` | ✅ |
| A2-04 | R-03 30-min break; non-driving ≥ 30 min resets (pickup/fuel count; 15 ON + 15 OFF counts; split 15s don't) | `test_engine_break.py` | ✅ |
| A2-05 | R-01 + R-05 11-h limit → 10-h SB reset; new shift after ≥ 10 h OFF/SB | `test_engine_11h.py` | ✅ |
| A2-06 | R-02 14-h window; breaks don't extend it; ON allowed after 14th hour | `test_engine_14h.py` (guide p.6: on at 06:00 → no driving after 20:00) | ✅ |
| A2-07 | R-06 + A-09 fuel ≤ 1,000 mi, 30 min ON, rounded down; counts as break | `test_engine_fuel.py` | ✅ |
| A2-08 | R-04 + A-05 70-h cycle; 34-h restart mid-trip (SC-3) and at start (SC-4) | `test_engine_cycle.py` | ✅ |
| A2-09 | A-12 tie-break | `test_engine_ties.py` | ✅ |
| A2-10 | Edge cases: zero-mile leg (SC-7), inspections off | `test_engine_edges.py` | ✅ |
| A2-11 | **Golden** SC-2 exact segments = business rules §8 | `test_engine_worked_example.py` | ✅ |
| A2-12 | **Property tests** (Hypothesis) — invariants from architecture §4.1 | `test_engine_invariants.py` | ✅ |
| A2-13 | Stops carry `mile_marker`; SC-5 expectations | `test_engine_stops.py` | ✅ |
| A2-14 | Purity guard | `test_purity.py` | ✅ |

**Gate:** `pytest tests/unit/hos` green; `hos/` coverage ≥ 95 %.

## A3 — Log builder (`hos/log_builder.py`)

| ID | Task | Test first | Status |
|---|---|---|---|
| A3-01 | Trip minutes → aware datetimes in home tz; pad OFF to local midnights | `test_log_builder_padding.py` | ✅ |
| A3-02 | Split at local midnight (rest crossing midnight) | `test_log_builder_split.py` | ✅ |
| A3-03 | Totals per status; sum 24 | `test_log_builder_totals.py` | ✅ |
| A3-04 | **Golden** John Doe: totals 10 / 1.75 / 7.75 / 4.5 + 6 remarks | `test_john_doe_example_log_matches_totals_and_remarks` | ✅ |
| A3-05 | Remarks at every status change (R-09) | `test_log_builder_remarks.py` | ✅ |
| A3-06 | Header fields (R-11) | `test_log_builder_header.py` | ✅ |
| A3-07 | Recap A/B/C + restart flag (R-12, A-14): SC-2 Day 1 A 32.25 / B 37.75, Day 2 A 43 / B 27 | `test_log_builder_recap.py` | ✅ |
| A3-08 | Time zone: Pacific start, Eastern home terminal → Eastern times | `test_log_builder_timezone.py` | ✅ |
| A3-09 | ⏭️ Stretch: `prior_daily_hours[7]` true rolling 8-day (guide p.11: 67 → 73 → 63) | `test_rolling_cycle.py` | ⏭️ |

**Gate:** SC-1…SC-5 daily logs total 24; John Doe golden green.

## A4 — Geo services (`geo/`)

| ID | Task | Test first | Status |
|---|---|---|---|
| A4-01 | `GeoProvider` protocol finalized (`route`, `geocode`, `reverse`) | `test_provider_factory.py` | ✅ |
| A4-02 | `route_math.py`: haversine, cumulative distance, `point_at_mile` | `test_route_math.py` | ✅ |
| A4-03 | `ors.py` `driving-hgv` → legs (mi, h) + GeoJSON; errors → `RouteNotFound` / `ProviderUnavailable` | `test_ors.py` (respx) | ✅ |
| A4-04 | `photon.py` search + reverse → "City, ST" | `test_photon.py` (respx) | ✅ |
| A4-05 | `fake.py` full scenario fixtures SC-1…SC-7 (SC-6 raises) + straight-line fallback | `test_fake_provider.py` | ✅ |
| A4-06 | `timezone.py` | `test_timezone.py` | ✅ |
| A4-07 | Mongo caches with TTL + `ensure_indexes` command | `test_cache.py` | ✅ |

**Gate:** `pytest tests/unit/geo` green; no real network (respx `assert_all_mocked`).

## A5 — API, persistence, contract

Outer loop: remove `skip` from `tests/acceptance/` → red. Web repo: enable `e2e/tests/api-contract.spec.ts` → red.

| ID | Task | Test first | Status |
|---|---|---|---|
| A5-01 | Enable acceptance tests | `pytest tests/acceptance` → red | ⬜ |
| A5-02 | Models: `Trip` + embedded `Location`, `LogMeta`, `Stop`, `DailyLog`, `DutySegment`, `Remark` | `tests/api/test_models.py` round-trip | ✅ |
| A5-03 | Request serializer + validation | `test_trips_validation.py` | ✅ |
| A5-04 | `services.plan_trip()` orchestration | `test_services.py` | ✅ |
| A5-05 | `POST /api/trips/` → 201 per contract | `test_trips_create.py` | ⬜ |
| A5-06 | `GET /api/trips/{id}/`, 404 shape | `test_trips_retrieve.py` | ⬜ |
| A5-07 | `GET /api/geocode/?q=` | `test_geocode_api.py` | ✅ |
| A5-08 | Error mapping (400 / 422 / 502) in the standard error shape | `test_trips_errors.py` | ✅ |
| A5-09 | drf-spectacular + committed `openapi.yaml` + drift check | `tests/contract/test_openapi_fresh.py` | ⬜ |
| A5-10 | `dump_scenarios` → `tests/fixtures/responses/sc1…sc7.json` + drift check | `tests/contract/test_fixtures_fresh.py` | ⬜ |
| A5-11 | Notify web repo: run `npm run sync-contract` there and enable `api-contract.spec.ts` (W-side task W5-01) | web Playwright red → green | ⬜ |

**Gate:** backend suite green, coverage ≥ 85 %; acceptance green; web `api-contract.spec.ts` green.

## A10 — Production deploy (Render)

| ID | Task | Test first | Status |
|---|---|---|---|
| A10-01 | OpenRouteService key; `GEO_PROVIDER=live` on Render; one manual live trip | manual (live markers not in CI) | ⬜ |
| A10-02 | `CORS_ALLOWED_ORIGINS` = Vercel prod URL; preview regex | browser call from Vercel app succeeds | ⬜ |
| A10-03 | Cold-start plan: uptime pinger every 10 min during grading window (or Starter plan) | `curl` after 20 min idle responds < 5 s | ⬜ |
| A10-04 | Verify with web `@smoke` suite | web `W10-04` green | ⬜ |

## A11 — Deliverables (API)

| ID | Task | Status |
|---|---|---|
| A11-01 | README: live URLs, link to web repo, rules R-xx, assumptions A-xx, run/test commands, cold-start note | ⬜ |
| A11-02 | Code walkthrough section for the Loom (engine loop, golden tests) | ⬜ |

## Decision log

| Date | Decision | Ref |
|---|---|---|
| 2026-09-23 | Two repos (API on Render, web on Vercel) instead of monorepo | 02 §1 |
| 2026-09-23 | Contract shared via committed `openapi.yaml` + response fixtures | 02 §5.1 |
| 2026-09-23 | 10-h resets logged as SB; inspections 15 min each, default on | A-06, A-07 |
| 2026-09-23 | Cycle-used treated as non-rolling during trip (conservative) | A-04 |
| 2026-09-23 | MongoDB Atlas M0 in every environment (dev, tests, E2E, CI, Render); no local MongoDB or Docker. One DB name per environment via `MONGODB_DB` | 06 §6 |
| 2026-09-23 | **No `render.yaml`.** The Render service was created in the dashboard, so a Blueprint file would be ignored and could drift from the real config. Settings are documented in `02-architecture.md` §7 instead | 02 §7 |
| 2026-09-23 | **Engine ↔ log builder contract.** `Segment` carries `mile_marker` (miles at segment start) and an optional `location`; `trips/services.py` fills `location` from reverse geocoding before the log builder writes remarks. `build_daily_logs(timeline, *, start_utc, home_tz, cycle_used_min, meta)` takes the engine's `Timeline`, so A2 and A3 can be built in parallel | 02 §4 |
| 2026-09-23 | **CI deferred (A0-07, and web W0-05/W1-07).** Removed `.github/workflows/ci.yml` from both repos. Every run would connect to the shared Atlas cluster, and CI adds little while one person builds the foundation. Until it returns, run the checks locally before each PR (`CLAUDE.md` definition of done). When re-added, use a throwaway MongoDB service container (`mongo:8`, `MONGODB_URI=mongodb://localhost:27017`) instead of an Atlas secret, then switch Render Auto-Deploy to *After CI checks pass* | 04 §7 |

## Blockers / open questions

| # | Question | Status |
|---|---|---|
| 1 | A0-07: add the `MONGODB_URI` GitHub Actions secret to this repo, then push to get the first green CI run (`.github/workflows/ci.yml` already exists) | ⏭️ deferred 2026-09-23 — CI removed for now (see *Decision log*) |
| 2 | A0-08: create a Render account and deploy the health endpoint | ✅ resolved 2026-09-23 — Render deployed |
| 3 | The Render build command in `02-architecture.md` §7 runs `manage.py ensure_indexes`, which A4-07 creates. For A0-08, drop that build step until A4-07, or add a no-op command now? | ✅ resolved — dropped `ensure_indexes` from the build command until A4-07 adds it back |
