# CLAUDE.md — ELD Trip Planner · API (backend repo)

Instructions for Claude Code in **`eld-trip-planner-api`**. Read fully before every task.

## The system (two repos)

| Repo | What | Hosting |
|---|---|---|
| **`eld-trip-planner-api`** (this repo) | Django 5.2 + DRF + MongoDB. HOS engine, log builder, routing/geocoding adapters, REST API | **Render** (Web Service) + MongoDB Atlas |
| `eld-trip-planner-web` | React + Vite SPA. Form, map, log-sheet rendering, **Playwright E2E suite** | **Vercel** |

Local layout expected by both repos (siblings in one plain folder, which is **not** itself a git repo):

```
eld-trip-planner/
├─ eld-trip-planner-api/   ← you are here
└─ eld-trip-planner-web/
```

Run Claude Code with the other repo attached when a task crosses repos:
`claude --add-dir ../eld-trip-planner-web`

## What this repo does

Input: current, pickup, dropoff locations + current cycle used (hrs).
Output (`POST /api/trips/`): route geometry, every required stop, and **filled daily logs** (segments, totals, remarks,
header, recap) — so the frontend only draws, never computes HOS.

## Source-of-truth documents

| Doc | Use it for |
|---|---|
| `docs/01-business-rules.md` | **Canonical** HOS rules (R-xx), assumptions (A-xx), glossary, worked example. The engine must match it exactly. |
| `docs/02-architecture.md` | Modules, engine + log-builder algorithms, **API contract**, data model, Render deployment |
| `docs/03-implementation-plan.md` | API phases/tasks (`A#-##`) with **status tracker** — update as you work |
| `docs/04-testing-strategy.md` | Backend test pyramid, **canonical scenarios SC-1…SC-7**, fake provider, contract fixtures |
| `docs/05-getting-started.md` | Onboarding, TDD loop, Render deploy |
| `docs/06-project-setup.md` | Virtual environment, Django + DRF + MongoDB install and settings, test tooling |
| `../eld-trip-planner-web/docs/01-definition-of-done.md` | Product acceptance criteria (AC-xx) and task DoD |
| `docs/reference/` | Company's blank log template + FMCSA HOS guide (source material) |

If code and docs disagree, **stop and ask** — never silently change a business rule.

## Non-negotiable rules

1. **Playwright first.** No feature work (phase A2+) until web phase **W1 (Playwright harness + acceptance specs)** and
   this repo's **A1 (acceptance tests)** are ✅. Check both trackers.
2. **Strict TDD, double loop.** Outer loop: enable the acceptance test (pytest `tests/acceptance/` here, Playwright in the
   web repo) → red. Inner loop: failing unit test → minimum code → refactor. Never write production code without a
   failing test demanding it. Never weaken or delete a test to go green — fix the code, or ask.
3. **Show the red.** Run the new test and confirm it fails for the right reason before implementing.
4. **`hos/` is pure Python** — standard library only. No Django, HTTP or DB imports (`test_purity.py` enforces this).
5. **Time is integer minutes** in the engine. Every segment boundary is a multiple of 15.
6. **Log times use the home-terminal time zone** (R-08). Store UTC; convert only in `log_builder` / serializers.
7. Every status change gets a remark "City, ST" (R-09). Every daily log totals exactly 24.00 h (R-08).
8. **The API contract is shared with the web repo.** Any change to request/response shape must:
   update `docs/02-architecture.md` §5 → regenerate `openapi.yaml` → regenerate `tests/fixtures/responses/*.json` →
   note it in the commit as `BREAKING:`/`contract:` so the web repo can run `npm run sync-contract`.
9. External services (OpenRouteService, Photon) stay behind the `geo.GeoProvider` interface. All automated tests use
   `GEO_PROVIDER=fake` — never call real APIs in tests.
10. **Update the tracker** (`docs/03-implementation-plan.md`) in the same commit that changes a task's state.
11. No features outside scope (no auth, no split sleeper berth, no team drivers) without asking.
12. **No explanatory comments.** Write the code itself. Add a comment only when it is necessary (a non-obvious "why", or
    a rule-ID citation such as `# R-01`). Never narrate what the code does, in code or config files.
13. **PRs only.** Never commit or push to `main`. Work on a `feat/*`/`fix/*`/`chore/*` branch and open a PR into `main`
    (`/push-to-git`). There is no `development` or `staging` branch.

## Repo layout

```
eld-trip-planner-api/
├─ CLAUDE.md · README.md · .env.example · pyproject.toml · uv.lock · requirements.txt · openapi.yaml
├─ config/          # settings (env-driven), urls, wsgi
├─ hos/             # PURE PYTHON: models.py (dataclasses), rules.py, engine.py, log_builder.py, time_utils.py
├─ geo/             # provider.py, ors.py, photon.py, fake.py, route_math.py, timezone.py, cache.py, fixtures/scenarios/
├─ trips/           # Django app: models.py, serializers.py, views.py, services.py, urls.py, management/commands/
├─ tests/
│  ├─ unit/hos/  unit/geo/     # no DB, no network
│  ├─ api/                     # pytest-django + Atlas test DB (test_<MONGODB_DB>)
│  ├─ acceptance/              # SC-1…SC-7 over HTTP (outer loop for this repo)
│  └─ fixtures/responses/      # generated contract fixtures (sc1.json … sc7.json) consumed by the web repo
├─ docs/
└─ .github/workflows/ci.yml
```

## Commands

```bash
cp .env.example .env                               # set MONGODB_URI (MongoDB Atlas; no local Mongo/Docker)
uv run pytest                                      # everything
uv run pytest tests/unit/hos -q                    # engine only (fast)
uv run pytest tests/acceptance -q                  # scenario acceptance tests
uv run ruff check . && uv run ruff format --check .
uv run python manage.py runserver 8000             # GEO_PROVIDER=fake by default locally
uv run python manage.py dump_scenarios             # regenerate tests/fixtures/responses/*.json
uv run python manage.py spectacular --file openapi.yaml   # regenerate OpenAPI schema
uv export --no-dev --no-hashes -o requirements.txt # after changing deps (Render installs from this)
```

## Conventions

- Python 3.12, type hints, `ruff`. Frozen dataclasses in `hos/`.
- Names follow the glossary: `DutyStatus.OFF | SB | D | ON`, `Segment`, `Stop`, `DailyLog`, `Recap`.
- Rule constants live in `hos/rules.py` and cite rule IDs: `MAX_DRIVING_MIN = 11 * 60  # R-01`.
- **Descriptive names, never spec IDs.** Functions, tests, variables and constants say what they are or prove, so a new
  dev can read them without the docs open: `test_break_required_after_8_hours_of_driving`, `TWO_DAY_WORKED_EXAMPLE_TRIP`,
  `trip_plan`, `driving_since_break_min` — not `test_r03_…`, `test_sc2_ac33_…`, `sc2`, `res`, `d`. Cite the ID in a comment
  above the test instead (`# R-03`, `# SC-2 · AC-33`); IDs may also appear in strings and data (`spec_id="SC-2"`,
  assert messages). Single-letter names only for trivial comprehensions.
- Conventional commits with task IDs: `test(hos): A2-04 failing test for 30-min break` → `feat(hos): A2-04 …`.

## Task script (follow for every task)

1. Read the task row in `docs/03-implementation-plan.md` and its R-xx / AC-xx.
2. Mark it 🟨.
3. Write/enable the failing test(s); run; show the failure.
4. Minimum code to green; run.
5. Refactor with tests green.
6. Run `uv run pytest` (and the web repo's `npm run e2e` if the API contract or behavior changed).
7. Mark ✅; commit with the task ID.

## Per-task Definition of Done

- [ ] Test written first and seen failing
- [ ] Unit + API + acceptance tests green; coverage gates hold (`hos/` ≥ 95 %, overall ≥ 85 %)
- [ ] ruff clean; `requirements.txt` in sync with `uv.lock`
- [ ] Contract artifacts regenerated if the API changed (`openapi.yaml`, `tests/fixtures/responses/`)
- [ ] Rule IDs cited where rules are implemented
- [ ] Tracker updated in the same commit
