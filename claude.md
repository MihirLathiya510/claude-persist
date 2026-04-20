# claude-persist

A Claude Code plugin that acts as a **persistent, self-updating context engine** — transforming Claude from a stateless responder into a state-aware collaborator.

Claude remembers your project, stack, preferences, and current focus across sessions. You stop repeating yourself.

## How It Works

```
Session Start
    ↓
sqlite-init → state-updater:load → context-builder:build
    ↓
[claude-persist] context block injected before your first prompt
    ↓
You work. Claude responds with state awareness.
    ↓
state-updater:extract → merge → UPDATE state table
    ↓
Next session picks up where you left off.
```

## Core Components

### 1. state-updater (`claude-persist:state-updater`)
- **The sole writer of the `state` table** — no other skill touches it
- `load`: reads state at session start; seeds defaults if missing
- `extract`: infers updates from each exchange (project name, stack, focus, preferences)
- `merge`: applies dot-path patches with size/secret/schema guards
- Triggers: `on-session-start`, `on-post-response`, `/state-update`, `/state-reset`, `/state-edit`

### 2. context-builder (`claude-persist:context-builder`)
- **Read-only** — only reads `state`, never writes
- `build`: maps non-empty state fields → minimal ≤10-line context block (≤ 1KB)
- `inspect`: `/state` command shows formatted block + raw JSON
- Skips injection entirely when all state fields are empty (no noise)
- Triggers: `on-session-start`, `on-pre-prompt`, `/state`, `/context-build`

### 3. state table (SQLite, migration V004)
- Single row: `key = 'global'`, `value = JSON`
- Cross-session — no `session_id` column (intentional)
- JSON validated at write time via `json_valid()`
- Size enforced at skill layer (< 2KB)

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

## Context Block (injected before each prompt)

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

Empty fields are skipped. Empty state = no injection.

## Commands

| Command | Action |
|---------|--------|
| `/state` | View current state (formatted block + raw JSON) |
| `/state-reset` | Clear state back to defaults (with confirmation) |
| `/state-edit <json-patch>` | Manually update state with dot-path patch |
| `/context-build` | Force regenerate and display context block |
| `/sq select * from state` | Inspect raw DB row |

## Session-Start Execution Order

1. Parse `plugin.json`
2. Warm skill frontmatter index
3. Run `mcp-discovery`
4. Log install profile
5. `sqlite-init` — DB init + run pending migrations (including V004)
6. **`state-updater:load`** — load or seed global state ← new
7. **`context-builder:build`** — inject context block if non-empty ← new
8. `anatomy-indexer` — build PROJECT_MAP.json

## Inherited Components (from template)

| Skill | Purpose |
|-------|---------|
| `security-auditor` | Scans every write and commit for secrets |
| `agent-team-orchestrator` | Spawns agent teams for complex tasks (`/orchestrate`) |
| `sqlite-memory` | Typed agent memory — decisions, tasks, messages |
| `sqlite-query` | Natural language → validated SQL → JSON (`/sq`) |
| `sqlite-schema-manager` | Migrations and DB health (`/migrate`, `/db-status`) |
| `anatomy-indexer` | File/symbol index at session start (`/map`) |
| `step-verifier` | Test gate between agent steps (`/gate`) |
| `token-ledger` | Per-skill token spend report (`/usage`) |
| `mcp-discovery` | MCP server detection at session start |
| `computer-use-safety` | Human-gated Computer Use |
| `plugin-dev` | Scaffold new skills (`/create-micro-skill`) |
| `self-improver` | Plugin self-refactor (`/self-improve`) |

## Guards and Constraints

| Constraint | Limit |
|-----------|-------|
| State JSON size | < 2048 bytes |
| Context block size | < 1024 bytes (≤ 10 lines) |
| State writers | `state-updater` only |
| Allowed state roots | `project`, `user`, `session` only |
| Sensitive data | Rejected at merge time (same patterns as security-auditor) |
| Context token budget | < 8k tokens/session |

## Decision Tree

```
1 file change           →  single skill
3+ files or refactor    →  /orchestrate (agent team)
Need external tool      →  MCP first, Computer Use fallback
Any write or commit     →  security-auditor auto-runs
View persisted context  →  /state
Clear context           →  /state-reset
Manually set context    →  /state-edit
Refresh file index      →  /map
Verify agent step       →  /gate <test-command>
Check token spend       →  /usage
Check DB health         →  /db-status
```

## SQLite Schema

```
decisions       tasks           messages        audit_log
usage_stats     schema_version  toggle_history  verification_log
state           decisions_fts   messages_fts    audit_log_fts
```

DB at `.claude-plugin/db/plugin.db` (git-excluded). Migrations in `skills/sqlite-init/migrations/`.

## Constraints

- Every write/commit triggers security-auditor. No exceptions.
- Computer Use always has human-in-the-loop.
- `tests/plugin-validator` must pass before any release.
- Skill frontmatter is always loaded; never put heavy context there.
- `state` table has one writer: `claude-persist:state-updater`.
- `stepVerification` is opt-in — enable per project in plugin.json.

## Compatibility

- Claude Sonnet 4.6 / Opus 4.6+
- VS Code extension, CLI, Cowork
- SQLite 3.38+ (JSON1 + FTS5 built-in)
