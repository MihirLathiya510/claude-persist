---
name: sqlite-init
description: Initializes the plugin SQLite database, runs schema bootstrap and pending migrations
triggers: [on-session-start, /sqlite-init, /sqlite-reset]
namespace: tpl-claude-plugin:sqlite-init
---

## Usage

Invoked automatically by `hooks/session-start/HOOK.md` at the start of every session. Also callable manually with `/sqlite-init` (re-runs idempotently) or `/sqlite-reset` (drops and recreates — requires CONFIRM prompt).

All other sqlite skills gate on `sqlite.enabled` in plugin.json. If disabled, this skill logs a note and returns immediately.

## Steps

1. Read `sqlite.enabled` from plugin.json. If `false`, log "SQLite disabled, skipping init" and return.
2. Resolve DB path from `sqlite.dbPath` (default: `.claude-plugin/db/plugin.db`). Create `db/` directory if absent.
3. Set permissions: `chmod 700 .claude-plugin/db/`, `chmod 600 plugin.db` (Unix only; log warning on Windows).
4. Open connection. Execute: `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`
5. Check if `schema_version` table exists. If absent, run `schema.sql` in a single transaction (idempotent first-run bootstrap). On any error: rollback, report failure — do not leave a half-initialized DB.
6. Query `MAX(version)` from `schema_version`. Scan `migrations/` for files matching `V[0-9]+__*.sql` with version number > current. Sort ascending.
7. For each pending migration: copy `plugin.db` to `plugin.db.bak` (rolling backup), then apply migration inside a transaction. Update `schema_version` after each.
8. Report: "SQLite initialized at .claude-plugin/db/plugin.db, schema version N."

## Decision Rule

- `/sqlite-reset` → prompt user: "Type CONFIRM to reset the database. All data will be lost." Only proceed on exact match.
- If a migration fails mid-apply: rollback the failed migration, restore from `.bak`, surface error to user. Do not apply subsequent migrations.

## Examples

```
[session-start] Invoking tpl-claude-plugin:sqlite-init...
> SQLite initialized at .claude-plugin/db/plugin.db, schema version 2.

/sqlite-init
> Already initialized. Schema version 2. No pending migrations.

/sqlite-reset
> Type CONFIRM to reset the database. All data will be lost.
> CONFIRM
> Database reset. Schema version 2.
```

<!-- References (lazy) -->
- `tpl-claude-plugin:security-auditor`
- `skills/sqlite-init/schema.sql`
- `skills/sqlite-init/migrations/`
- `hooks/session-start/HOOK.md`
