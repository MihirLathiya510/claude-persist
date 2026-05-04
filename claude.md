# claude-persist

A Claude Code plugin that acts as a **persistent context engine** — Claude remembers your project, stack, preferences, and current task across sessions. You stop repeating yourself.

---

## How It Works

```
Session Start
    ↓
sqlite-init → state-updater:load → first-run-bootstrap → context-builder:build
    ↓
[claude-persist] context block injected before your first prompt
    ↓
You work. Claude responds with full project awareness.
    ↓
state-updater:extract → merge → UPDATE state table
    ↓
Next session picks up where you left off.
```

---

## Core Skills

### state-updater
- **Sole writer of the `state` table** — no other skill touches it
- `load` — reads state at session start; seeds defaults if the row is missing
- `extract` — infers updates from each exchange (name, stack, focus, preferences)
- `merge` — applies dot-path patches with size / secret / root-key / no-op guards
- Commands: `/state-update`, `/state-reset`, `/state-edit`

### first-run-bootstrap
- **Runs only once** — when state is completely empty (first-ever session)
- Parses `package.json` → project name + stack inference
- Reads `README.md` first 300 lines → project description
- Runs `git log --oneline -15` → infers current focus from commit paths
- Passes patch to `state-updater` (never writes state directly)
- Lightweight: < 200 ms; exits immediately if any state field is non-empty

### context-builder
- **Read-only** — reads `state`, never writes
- `build` — maps non-empty state fields to a ≤10-line block (≤ 1KB); skips empty fields
- `inspect` — `/state` shows the formatted block + raw JSON
- Skips injection entirely when all state fields are empty (no noise on fresh install)
- Commands: `/state`, `/context-build`

### persist
- **Unified command router** — the primary user-facing entry point
- `/persist status` — hero dashboard: project context, DB health, bootstrap status
- `/persist remember <fact>` — store a fact via state-updater
- `/persist forget <topic>` — clear a field via state-updater
- `/persist log` — recent audit log activity
- `/persist map` — trigger anatomy-indexer on demand
- `/persist help` — show all commands

### state table (SQLite — migration V004)
- Single row: `key = 'global'`, `value = JSON`
- Cross-session — no `session_id` column (intentional)
- JSON validated at DB level via `CHECK (json_valid(value))`
- Size limit enforced at skill layer (< 2048 bytes)

---

## State Structure

```json
{
  "project": {
    "name": "",
    "description": "",
    "current_focus": "",
    "stack": []
  },
  "user": {
    "preferences": {
      "response_style": "",
      "verbosity": ""
    }
  },
  "session": {
    "current_task": "",
    "active_context": []
  }
}
```

---

## Context Block Format

```
[claude-persist]
Project: MyApp
About: SaaS billing platform
Focus: Subscription webhook handling
Stack: Node.js, Stripe, Postgres
Style: concise
Task: Debug failed webhook retry logic
---
```

Rules: empty / whitespace-only fields are skipped. Empty state = no injection.

---

## Session-Start Execution Order

1. Parse and validate `.claude-plugin/plugin.json`
2. Warm skill frontmatter index (read YAML only from each `SKILL.md`)
3. Run `mcp-discovery` — detect available MCP servers
4. Run `sqlite-init` — initialize DB at `~/.claude/projects/<hash>/plugin.db` and apply any pending migrations
5. Run `state-updater:load` — read or seed global state row
6. Run `first-run-bootstrap` — if state is empty, auto-populate from package.json + README.md + git log
7. Run `context-builder:build` — inject context block if any field is non-empty

Each step degrades gracefully on failure — session always starts.

---

## Decision Tree

```
1 file change           →  single skill
3+ files or refactor    →  /orchestrate (agent team)
Need external tool      →  MCP first, Computer Use fallback
Any write or commit     →  security-auditor auto-runs
View persisted context  →  /persist status
Clear context           →  /persist forget all  (or /state-reset)
Manually set context    →  /persist remember <fact>  (or /state-edit)
Refresh file index      →  /persist map
Verify agent step       →  /gate <test-command>
Check token spend       →  /usage
Check DB health         →  /db-status
```

---

## All Skills

| Skill | Command(s) | Purpose |
|---|---|---|
| `persist` | `/persist status/remember/forget/log/map/help` | Unified command router (primary entry point) |
| `state-updater` | `/state-reset` `/state-edit` | Sole writer of global state |
| `context-builder` | `/state` `/context-build` | Builds and injects context block |
| `first-run-bootstrap` | — (auto, session-start only) | First-session project auto-detection |
| `sqlite-init` | `/sqlite-init` `/sqlite-reset` | DB init and migrations |
| `sqlite-query` | `/sq` | Natural language → validated SQL |
| `sqlite-memory` | `/remember` `/recall` | Typed agent memory (no raw SQL) |
| `sqlite-schema-manager` | `/migrate` `/db-status` | Schema versioning and health |
| `security-auditor` | `/security-audit` | Scans every write and commit for secrets |
| `agent-team-orchestrator` | `/orchestrate` | Planner → Coder → Reviewer pipeline |
| `anatomy-indexer` | `/persist map` | File and symbol index (opt-in, on demand) |
| `step-verifier` | `/gate` | Test gate between agent steps |
| `token-ledger` | `/usage` | Per-skill token spend report |
| `mcp-discovery` | — | MCP server detection at session start |
| `computer-use-safety` | — | Human-gated Computer Use |
| `plugin-dev` | `/create-micro-skill` | Scaffold new skills |
| `self-improver` | `/self-improve` | Plugin self-refactor pipeline |

---

## Guards and Limits

| Guard | Rule |
|---|---|
| State size | Merge rejected if result > 2048 bytes |
| Context block | Iterative line-drop until ≤ 1024 bytes |
| State writers | `state-updater` only — enforced by convention |
| Allowed state roots | `project`, `user`, `session` only |
| Sensitive data | Rejected at merge time (API keys, tokens, passwords, private keys) |
| Whitespace values | Stripped before empty check — whitespace-only treated as empty |
| SQL queries | 10 forbidden patterns, 12-table allowlist, LIMIT 100 injected, capped at 500 |
| Read-only agents | `reviewer`, `security` — SELECT only via `sqlite-query` |

---

## SQLite Schema

```
decisions       tasks           messages        audit_log
usage_stats     schema_version  toggle_history  verification_log
state           decisions_fts   messages_fts    audit_log_fts
```

DB: `~/.claude/projects/<hash>/plugin.db` (per-project, outside the repo)
Migrations: `skills/sqlite-init/migrations/` (V001–V005)

---

## Hooks

| Hook | Fires on | What it does |
|---|---|---|
| `session-start` | Every session open | Runs the 7-step init sequence above |
| `file-write` | Every Write/Edit tool call | Scans content for secrets before persisting |
| `commit` | Every git commit | Security audit + plugin-validator gate |
| `tool-use` | Every tool call | Routes Computer Use through human confirmation |
| `step-verification` | `/gate` or `on-step-complete` | Blocks agent until test command passes |

Hook registry: `hooks/hooks.json` (machine-readable, auto-registered on `claude plugin install`)

---

## Agents

| Agent | Role |
|---|---|
| `planner` | Breaks intent into sequenced tasks, assigns to team |
| `coder` | Implements tasks; all writes trigger file-write hook |
| `reviewer` | Reviews Coder output; read-only DB access |
| `security` | Deep security review on sensitive changes; veto power |
| `tester` | Runs `tests/plugin-validator`; blocks release on failure |

---

## Test Suite

```bash
python3 tests/integration-tests.py   # 276 tests — schema, guards, patterns, structure
python3 tests/user-flow-tests.py     # 106 tests — end-to-end user scenarios
bash tests/plugin-validator          # structural completeness check
```

All three must pass before any release.

---

## Extending State

To add a new remembered field:

1. Add it to the default JSON seed in `skills/sqlite-init/migrations/V004__add_state_table.sql`
   (or create `V006` for existing installs)
2. Add an extraction rule in `skills/state-updater/SKILL.md` → `extract` section
3. Add a render mapping in `skills/context-builder/SKILL.md` → field table
