---
name: first-run-bootstrap
description: On the very first session (empty state), auto-populates project context from package.json, README.md, and git log — silently, before context-builder runs
---

## Usage

Called automatically by `hooks/session-start/HOOK.md` after `state-updater:load` and before `context-builder:build`. Runs silently — no user interaction required.

This skill runs only once (when state is completely empty) and is intentionally lightweight (< 200 ms on typical projects). On subsequent sessions, if any state field is non-empty, this skill exits immediately without doing any work.

## Steps

1. **Guard check:** Call `state-updater:load` output from session context (`active_state`). If any of the following is non-empty, exit silently — bootstrap already ran:
   - `project.name`, `project.description`, `project.current_focus`, `project.stack` (non-empty array), `user.preferences.response_style`, `user.preferences.verbosity`, `session.current_task`
2. **If state is fully empty — bootstrap:**

   **a. package.json** (if present in cwd):
   - Parse JSON. Extract `name` → candidate for `project.name`.
   - Merge keys from `dependencies` and `devDependencies` into a framework/language inference list.
     Map well-known package names to human-readable labels (e.g. `react` → `React`, `express` → `Express`, `typescript` → `TypeScript`, `@prisma/client` → `Prisma`, `postgres`/`pg` → `Postgres`, `mongoose` → `MongoDB`, `stripe` → `Stripe`, `next` → `Next.js`, `fastapi` → `FastAPI`, `flask` → `Flask`).
   - Collect up to 5 inferred labels → `project.stack`.
   - On parse error: log "bootstrap: package.json unreadable — skipping"; continue.

   **b. README.md** (if present in cwd):
   - Read first 300 lines. Skip lines that are: empty, HTML tags, badge lines (`[![`, `<img`), heading-only lines (`# ...`), or horizontal rules (`---`, `===`).
   - Take the first non-skipped line or paragraph as `project.description`. Truncate to 120 characters.
   - On any read error: log "bootstrap: README.md unreadable — skipping"; continue.

   **c. git log** (if `.git/` exists in cwd):
   - Run `git log --oneline -15 --name-only` (read-only). Capture output.
   - Extract file paths from the output. Split paths by `/`, collect the top-level directories (e.g. `src/`, `api/`, `components/`). The most frequently appearing top-level prefix (if it appears in ≥ 3 commits) becomes `project.current_focus` (e.g. "Active work in src/").
   - On command failure or no `.git/`: log "bootstrap: git log unavailable — skipping"; continue.

3. **Patch state:** Build a dot-path patch from any fields successfully extracted. Pass to `claude-persist:state-updater` merge operation — never write to `state` directly.
4. **Log:** Emit to session state: "First-run bootstrap completed. Project: <name> | Stack: <stack items> | Focus: <focus>"
   If no fields were extracted (no package.json, no README, no git): emit "First-run bootstrap: no project files detected. Use /persist remember to set context manually."

## Failure Modes

- Missing files → skip that source, continue with others
- JSON parse error → skip package.json, continue
- git unavailable → skip focus inference, continue
- state-updater merge rejected → log warning, do not retry; session proceeds normally

## Examples

```
[session-start] Invoking claude-persist:first-run-bootstrap...
> State is empty — running first-run bootstrap
> Parsed package.json: name="my-saas-app", stack=["Node.js", "Express", "Stripe", "Postgres"]
> Parsed README.md: description="A SaaS billing platform for usage-based pricing"
> git log: top prefix="src/" (8 of 15 commits) → focus="Active work in src/"
> Passed patch to state-updater → 4 fields updated
> First-run bootstrap completed. Project: my-saas-app | Stack: Node.js, Express, Stripe, Postgres

[session-start] Invoking claude-persist:first-run-bootstrap...
> State has data (project.name="my-saas-app") — skipping bootstrap
```

<!-- References (lazy) -->
- `claude-persist:state-updater`
- `hooks/session-start/HOOK.md`
