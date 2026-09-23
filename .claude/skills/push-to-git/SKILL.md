---
name: push-to-git
model: haiku
description: Commit and push eld-trip-planner-api changes using Conventional Commits on a feature branch, then open a Pull Request into main via gh. Use when the user says "commit this", "open a PR", "push my changes", or "let's ship this branch".
---

# Git Workflow & PR Strategy (eld-trip-planner-api)

Every change reaches `main` through a Pull Request. Nothing is ever pushed directly to `main`.

| Branch | Role |
| :--- | :--- |
| `main` | Production (deploys to Render). Protected: PRs only. |
| `feat/*` / `fix/*` / `chore/*` / `docs/*` / `test/*` | Short-lived branches cut from `main`, merged back via PR. |

There is no `development` or `staging` branch.

## 0. Verify the repo

Run every git command from this repo's root. Confirm git resolves to this folder, not a parent directory:

```bash
git rev-parse --show-toplevel
```

If it prints anything other than the `eld-trip-planner-api` folder, stop and tell the user. The repo isn't set up yet (task A0-01).

## 1. Branching

1. **Analyze changes**: review `git status`, `git diff`, and the chat history to understand intent and scope.
2. **Never commit on `main`**. If the current branch is `main`, create a branch from an up-to-date `main`:
   ```bash
   git fetch origin
   git switch -c feat/<task-id>-<short-slug> origin/main
   ```
   Use the prefix that matches the change type: `feat/`, `fix/`, `chore/`, `docs/`, `test/`, `refactor/`, `ci/`.
   Include the task ID when there is one, e.g. `feat/a2-04-30-min-break`.
   If the repo has no commits yet, create the branch from the current state with `git switch -c <branch>`.

## 2. Committing

1. **Generate the commit message** in strict **Conventional Commits** format with the task ID:
   `<type>(<scope>): <TASK-ID> <description>`, e.g. `feat(hos): A2-04 enforce 30-min break`.
   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
   API contract changes use the `contract:` prefix (`BREAKING:` if it breaks consumers).
2. **Run the gates** before committing and report the results:
   ```bash
   uv run pytest
   uv run ruff check . && uv run ruff format --check .
   ```
   If the contract changed, regenerate `openapi.yaml` and `tests/fixtures/responses/` first.
3. **Get approval**: present the message and file list to the user before committing.
4. **Stage deliberately**: add specific files by name. Never `git add -A` or `git add .`, so nothing untracked
   (`.env`, credentials, scratch files) slips in. Review `git status` / `git diff --staged` before committing.
5. **Commit**:
   ```bash
   git add <specific files>
   git commit -m "<type>(<scope>): <TASK-ID> <description>"
   ```

## 3. Pushing and Opening a PR (via GitHub CLI)

PRs always target `main`.

### a. Push the branch
```bash
git push -u origin <head-branch>
```

### b. Draft the PR
- **Title**: Conventional Commits format with the task ID (e.g. `feat(hos): A2-04 enforce 30-min break`).
- **Body** must include:
  - **Overview**: why this change is necessary and what it achieves.
  - **Key Changes**: bulleted list of modifications.
  - **Test Scenarios**: exact steps/criteria used to verify the change (reference `uv run pytest` tests, rule IDs
    R-xx, and scenarios SC-1…SC-7 where relevant).
  - **Contract impact**: `none`, or what changed and that the web repo needs `npm run sync-contract`.

### c. Ask for confirmation
> **You MUST present the proposed PR title and body in chat and get explicit user approval before running `gh pr create`.** Do not execute the command until approved.

### d. Create the PR
```bash
gh pr create --base main --head <head-branch> --title "<PR Title>" --body "<PR Description>"
```

## 4. Post-PR Cleanup

Once the PR is created, switch back to `main` and update it:
```bash
git switch main
git pull --ff-only origin main
```

## 5. Safety Notes

- Never push to `main`, and never commit on `main`. Every change goes through a PR, including one-line fixes and docs.
- Never merge the PR yourself unless the user explicitly asks.
- Never force-push, `git reset --hard`, or skip hooks (`--no-verify`) without explicit user instruction.
