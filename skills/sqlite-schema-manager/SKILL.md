---
name: sqlite-schema-manager
description: Schema versioning, migration management, and DB health inspection for plugin.db
---

## Usage

Provides four commands for inspecting and evolving the database schema. All destructive migrations require explicit user confirmation. Only Planner or user-invoked triggers can run `/migrate` — Coder and Tester are blocked.

## Steps

**`/db-status`**
1. Query `schema_version` for current version and `applied_at` timestamp.
2. Query row counts for all tables: `decisions`, `tasks`, `messages`, `audit_log`, `usage_stats`, `toggle_history`, `verification_log`, `state`.
3. Report DB file size (bytes), WAL mode status (`PRAGMA journal_mode`), and last backup timestamp (mtime of `plugin.db.bak` if present).
4. Count pending migrations (migration files with version > current).

**`/migrate`**
1. Scan `skills/sqlite-init/migrations/` for pending files (version > current schema version).
2. Display list of pending migrations with descriptions.
3. Require user confirmation: "Apply N migration(s)? (yes/no)"
4. On yes: copy `plugin.db` to `plugin.db.bak`, then apply each migration in order via `sqlite-init`.
5. Report new schema version.

**`/sqlite-schema show <table>`**
1. Execute `SELECT sql FROM sqlite_master WHERE name = '<table>'`.
2. Also query `SELECT * FROM sqlite_master WHERE tbl_name = '<table>' AND type = 'index'` for all indexes.
3. Return formatted DDL + index list.

**`on-plugin-upgrade`**
1. Triggered when plugin.json version bumps (detected by session-start hook).
2. Compare plugin version against schema version.
3. If migration files exist for the new plugin version, surface prompt: "Schema migration available. Run /migrate to apply."
4. If no migration file corresponds to the new version, log info: "No schema migration required for this version."

## Decision Rule

- Only `planner` agent or direct user invocation may call `/migrate`.
- Any other agent attempting `/migrate` → log to `audit_log` with `severity='warning'` and reject.

## Examples

```
/db-status
> Schema version: 4 (applied 2026-04-20)
> Tables: decisions(0), tasks(0), messages(0), audit_log(0), usage_stats(0), toggle_history(0), verification_log(0), state(1)
> DB size: 40 KB | WAL: enabled | Backup: 2026-04-20 10:22:01
> Pending migrations: 0

/sqlite-schema show decisions
> CREATE TABLE decisions (
>   id INTEGER PRIMARY KEY AUTOINCREMENT,
>   session_id TEXT NOT NULL,
>   ...
> )
> Indexes: idx_decisions_session, idx_decisions_agent, idx_decisions_created

/migrate
> Pending: V003__add_embedding_path.sql
> Apply 1 migration(s)? (yes/no): yes
> Backed up to plugin.db.bak. Applying V003...
> Schema version: 3.
```

## Future Upgrade Path

sqlite-vss (vector similarity search) will be noted here as a candidate once the extension stabilizes cross-platform. When ready, add as a migration that loads the extension and creates a `USING vss0` virtual table on a new `embeddings` table.

<!-- References (lazy) -->
- `tpl-claude-plugin:sqlite-init`
- `skills/sqlite-init/migrations/`
