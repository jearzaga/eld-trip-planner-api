# 04 — Testing Strategy (API)

> The system-level strategy (Playwright E2E, test-ID contract) lives in the web repo:
> `eld-trip-planner-web/docs/04-testing-strategy.md`. This doc covers the backend and owns the **canonical scenarios**.

## 1. Principles

1. **Playwright first, system-wide.** The web repo's W1 phase (Playwright harness + every acceptance spec as `fixme`)
   must be ✅ before feature work here. This repo adds its own fast outer loop: **pytest acceptance tests**.
2. **Double-loop TDD.**
   ```
   OUTER  tests/acceptance/test_scenarios.py  (+ Playwright api-contract.spec.ts in the web repo)
     └─ INNER  tests/unit/…  →  red → green → refactor  (repeat)
   ```
3. **Deterministic.** Every automated test runs with `GEO_PROVIDER=fake`. No network.
4. **Rules are tested where they live** — `hos/` gets exhaustive unit + property tests.
5. **Never weaken a test to go green.**

## 2. Test pyramid

| Layer | Tool | Location | Needs | Target |
|---|---|---|---|---|
| Unit — engine, log builder | pytest + Hypothesis | `tests/unit/hos/` | nothing | ms; `hos/` coverage ≥ 95 % |
| Unit — geo | pytest + respx | `tests/unit/geo/` | recorded JSON | ms |
| API | pytest-django + DRF `APIClient` | `tests/api/` | Atlas test DB (`test_<MONGODB_DB>`) | < 1 s each |
| **Acceptance** | pytest + `APIClient` | `tests/acceptance/` | Atlas test DB, fake geo | SC-1…SC-7 end-to-end over HTTP |
| Contract | pytest | `tests/contract/` | — | `openapi.yaml` + response fixtures not stale |
| System E2E | Playwright (web repo) | `eld-trip-planner-web/e2e/` | both apps | UI + consumer contract |

## 3. Canonical scenarios (fake-provider fixtures)

Fixtures: `geo/fixtures/scenarios/sc1.json … sc7.json` (routes, geocode suggestions, reverse labels) consumed by
`geo/fake.py`. Locations use real city coordinates; **leg distances/durations are synthetic** so results are easy to
verify by hand. All start **06:00 home-terminal time** on a fixed date.
Expected values were verified with a prototype of the algorithm; A2 freezes the exact segment lists as golden data.

| ID | Name | Legs (mi / h) | Cycle | Expected |
|---|---|---|---|---|
| **SC-1** | Short day | 60 / 1 · 180 / 3 | 0 | 1 sheet; no break/rest/fuel; OFF 17.5 · D 4 · ON 2.5 |
| **SC-2** | Two-day (worked example) | 120 / 2 · 1,080 / 18 | 20 | Exactly `01-business-rules.md` §8 — Day 1 OFF 6.5 / SB 5.25 / D 11 / ON 1.25; Day 2 OFF 8.5 / SB 4.75 / D 9 / ON 1.75; stops pickup → 30-min → 10-hr → fuel → dropoff |
| **SC-3** | Cycle-limited | 120 / 2 · 1,080 / 18 | 65 | Cycle hits 70 after 1.75 h of leg-2 driving → 34-hr restart; 4 sheets |
| **SC-4** | Cycle full | 60 / 1 · 180 / 3 | 70 | Starts with a 34-hr restart; 2 sheets (Day 1 = 24 h OFF) |
| **SC-5** | Cross-country | 300 / 5 · 2,500 / 42 | 10 | 2 fuel · 4 × 10-hr · 2 × 30-min; 5 sheets; every sheet 24 h |
| **SC-6** | Unroutable | provider raises `RouteNotFound` | 0 | `422 ROUTE_NOT_FOUND` |
| **SC-7** | Pickup at current location | 0 / 0 · 180 / 3 | 0 | Pickup right after pre-trip; 1 sheet |

The fake geocoder answers the queries used in tests (e.g. `"Rich"` → Richmond, VA). The fake provider is selected when
the request's coordinates match a scenario; unknown coordinates get a straight-line route at 55 mph (so manual local
testing works without keys).

## 4. Acceptance tests (outer loop for this repo)

`tests/acceptance/test_scenarios.py` — written in **A1** with `@pytest.mark.skip(reason="enable in A5")`, one test per
scenario and per HOS criterion (AC-30…AC-35). Enabling = deleting the skip marker → red.

```python
# SC-2 · AC-33
@pytest.mark.skip(reason="enable in A5-01")
@pytest.mark.django_db
def test_two_day_trip_matches_business_rules_worked_example(api_client):
    trip_plan = plan_trip(api_client, TWO_DAY_WORKED_EXAMPLE_TRIP)
    assert daily_totals(trip_plan) == [
        {"OFF": 6.5, "SB": 5.25, "D": 11.0, "ON": 1.25},
        {"OFF": 8.5, "SB": 4.75, "D": 9.0,  "ON": 1.75},
    ]
    assert stop_types_in_order(trip_plan) == ["pickup", "break_30", "rest_10", "fuel", "dropoff"]
```

A2–A4 (pure engine / builder / geo) use the **golden unit tests** as their outer loop, because the HTTP path doesn't exist yet.

## 5. Unit-test conventions

- **Table-driven:** legs + cycle → expected `(status, start, end)` list or expected stop types.
- **Behavior-named, ID-cited:** the name says what the test proves; the spec ID goes in a comment above it, never in
  the name — `# R-02` over `def test_on_duty_allowed_after_14th_hour`, `# A-12` over `def test_fuel_then_rest_on_tie`.
- **Goldens:** `test_two_day_worked_example_segments` (exact segments), `test_john_doe_example_log_matches_totals_and_remarks`
  (totals 10 / 1.75 / 7.75 / 4.5 + 6 remarks).
- **Property tests (Hypothesis):** random legs (0–3,000 mi, 40–65 mph) × cycle (0–70, step 0.25) × start time →
  every invariant in `02-architecture.md` §4.1 holds and every day totals 24.
- **Purity:** `test_purity.py` parses `hos/*.py` imports and fails on anything outside the standard library.
- **Geo adapters:** respx with recorded ORS/Photon JSON in `tests/fixtures/http/`; `respx.mock(assert_all_mocked=True)`.

## 6. Contract artifacts & drift checks

| Check | How |
|---|---|
| OpenAPI up to date | CI: `manage.py spectacular --file openapi.yaml && git diff --exit-code openapi.yaml` |
| Response fixtures up to date | CI: `manage.py dump_scenarios && git diff --exit-code tests/fixtures/responses/` |
| Deps exported for Render | CI: `uv export --no-dev --no-hashes -o requirements.txt && git diff --exit-code requirements.txt` |

The web repo syncs from these files (`npm run sync-contract`) and runs `api-contract.spec.ts` (Playwright, consumer side).

## 7. CI (`.github/workflows/ci.yml`)

> ⏭️ **Deferred (2026-09-23).** The workflow was removed; this section is the plan for when it returns, with a
> MongoDB service container instead of the Atlas secret (see `03-implementation-plan.md` *Decision log*).
> Until then, run ruff, pytest and the §6 drift checks locally before each PR.

```
jobs:
  test:
    env: MONGODB_URI from the repo secret (Atlas), MONGODB_DB=eld_ci. No Mongo service container.
    steps: checkout → setup uv + Python 3.12 → uv sync
           → ruff check + ruff format --check
           → pytest (unit, api, acceptance, contract) with coverage gates (hos ≥ 95 %, total ≥ 85 %)
           → drift checks (§6)
  notify-web (optional, on push to main):
    → repository_dispatch "api-updated" to eld-trip-planner-web (needs a PAT secret) so its E2E runs against the new API
```

Render auto-deploys `main` only after these checks pass.
