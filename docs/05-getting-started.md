# 05 — Getting Started (API)

> Setting up both repos side by side and the day-by-day schedule are covered in
> `eld-trip-planner-web/docs/05-getting-started.md`. This guide covers the API repo only.

## 1. Prerequisites

Python 3.12 · [uv](https://docs.astral.sh/uv/) · Git · Claude Code. No Docker: MongoDB is Atlas in every environment.
Accounts: GitHub, **Render**, **MongoDB Atlas** (M0 free), **OpenRouteService** (free key — needed from A10).

> Prefer pip? Use a venv, `pip install …`, and drop the `uv run` prefix. Update `CLAUDE.md` to match.

## 2. Workspace layout

```bash
mkdir -p ~/code/eld-trip-planner && cd ~/code/eld-trip-planner   # plain folder, not a repo
gh repo create eld-trip-planner-api --public --clone               # or create on github.com and clone
cd eld-trip-planner-api
# copy CLAUDE.md, README.md and docs/ from the planning package into this folder
git add . && git commit -m "docs: A0-01 business rules, architecture, plan"
```

## 3. Scaffold (A0-02 … A0-05)

Follow **`06-project-setup.md`**. It covers the virtual environment (uv or venv + pip), Django + DRF + MongoDB install,
settings, the MongoDB Atlas cluster, test config, and the first red → green health-check test.

## 4. CI (A0-07)

`.github/workflows/ci.yml`: `MONGODB_URI` from a repo secret (Atlas, `MONGODB_DB=eld_ci`) → `astral-sh/setup-uv` → `uv sync` → ruff → pytest → drift checks
(`requirements.txt` now; `openapi.yaml` and response fixtures from A5). See `04-testing-strategy.md` §7.

```bash
uv export --no-dev --no-hashes -o requirements.txt   # commit it; Render installs from this file
```

## 5. First Render deploy (A0-08) — do it on Day 1

1. **Atlas:** reuse the M0 cluster from A0-02 (`06-project-setup.md` §6). Copy its SRV URI.
2. Add `render.yaml` (see `02-architecture.md` §7) and push.
3. **Render → New → Blueprint** → select the repo → fill the `sync: false` env vars (`MONGODB_URI`, `CORS_ALLOWED_ORIGINS`,
   leave `ORS_API_KEY` blank for now) and set `GEO_PROVIDER=fake` until A10.
4. In the service settings, set **Auto-Deploy** to deploy only after CI checks pass.
5. `curl https://<api>.onrender.com/api/health/` → `{"status":"ok"}`. Tell the web repo the URL.

Free-tier note: the service sleeps after 15 idle minutes, and the first request then takes about a minute to wake it. The web app is built to cope with this (AC-46).

## 6. Daily TDD loop (from A2 on, after W1 + A1 are ✅)

```
1. Pick next ⬜ task in docs/03-implementation-plan.md → 🟨
2. OUTER: enable the acceptance test (A5) or rely on the phase's golden test (A2–A4) → red
3. INNER: smallest failing unit test (rule-named) → red → minimum code → green → refactor
4. uv run pytest   (all green)
5. Mark ✅, commit with the task ID
```

```bash
uv run pytest tests/unit/hos/test_engine_break.py -x      # one file
uv run pytest -k r03 -x                                    # by rule
uv run pytest tests/acceptance -q                          # outer loop
```

## 7. Claude Code prompts

> Read CLAUDE.md and docs/. Summarize rules R-01…R-12 and phase A0, then start A0-01 following the task script.

> Start A2-04. Mark it 🟨, write the failing tests from the plan, run them and show me the failure. Stop before implementing.

> Tests look right. Implement the minimum for A2-04, refactor, run the full suite, mark ✅ and commit.

> A5 changed the response shape. Regenerate openapi.yaml and the scenario fixtures, commit with `contract:`, then open
> ../eld-trip-planner-web and run `npm run sync-contract` and the Playwright api-contract spec.
> (Start Claude with `claude --add-dir ../eld-trip-planner-web` for this.)
