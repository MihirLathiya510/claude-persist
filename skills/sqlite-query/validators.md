# SQLite Query Validator — Forbidden Patterns

This file is a lazy-loaded reference for `tpl-claude-plugin:sqlite-query`.
It defines the canonical forbidden pattern list and enforcement rules.

## Forbidden Patterns (case-insensitive regex)

These patterns are checked against the full SQL string before execution.
Any match causes the query to be rejected with a descriptive error.

```
DROP\s+(TABLE|INDEX|VIEW|TRIGGER)
DELETE\s+FROM\b(?!.*\bWHERE\b)
TRUNCATE
ATTACH\s+DATABASE
DETACH\b
ALTER\s+TABLE
PRAGMA(?!\s*(journal_mode|foreign_keys|wal_checkpoint|integrity_check))
CREATE\b
UPDATE\s+.*\bAUDIT_LOG\b
DELETE\s+.*\bAUDIT_LOG\b
```

## Known Tables (Allowlist)

Queries may only reference these tables:

```
decisions
tasks
messages
audit_log
usage_stats
schema_version
toggle_history
verification_log
decisions_fts
messages_fts
audit_log_fts
state
```

Any other table reference → reject with "Unknown table: <name>".

## Read-Only Agent Enforcement

Agents `reviewer` and `security` may only execute SELECT statements.
Any write attempt from these agents → INSERT into `audit_log` with `event_type='security-violation'`, `severity='warning'`, then reject the query.

## LIMIT Injection Rules

- SELECT with no LIMIT clause → inject `LIMIT 100`
- SELECT with `LIMIT N` where N > 500 → clamp to 500
- Queries using `unixepoch()`, `datetime()`, `date()`, `time()`, or `strftime()` → bypass session cache

## Retry Policy (SQLITE_BUSY)

Retry 3 times with delays: 50ms → 100ms → 200ms.
After 3 failures: return `{ "error": "Database busy, retry later", "rows": [] }`.

## Error Response Format

```json
{
  "query": "<attempted sql>",
  "rows": [],
  "row_count": 0,
  "cached": false,
  "error": "<descriptive error message>"
}
```
