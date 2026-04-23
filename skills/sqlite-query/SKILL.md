---
name: sqlite-query
description: Translates natural language to validated SQL, executes against plugin.db, returns structured JSON results
---

## Usage

Accepts a natural language query or raw SQL. Validates against the forbidden pattern list, enforces read-only rules for reviewer/security agents, checks the session cache, then executes and returns structured JSON.

Never exposes raw SQL errors to agents — always returns the structured error format.

## Steps

1. Accept query string. If natural language, generate candidate SQL (SELECT or INSERT/UPDATE as appropriate).
2. Validate against forbidden patterns in `validators.md` (lazy-loaded). Reject immediately on any match.
3. Classify: starts with SELECT (or WITH...SELECT) → read path. Otherwise → write path.
4. **Write path:** check caller agent is not in the read-only agents list (`reviewer`, `security`). If violation, log to `audit_log` and reject.
5. **Read path:** normalize SQL (lowercase + collapse whitespace). Check session cache. If hit, return cached result with `"cached": true`. Bypass cache if query contains time functions.
6. Inject `LIMIT 100` if absent on SELECT; clamp to 500 if exceeded.
7. Check table allowlist — reject unknown tables.
8. Execute with parameterized statement. On `SQLITE_BUSY`, retry per policy in `validators.md`.
9. Store result in session cache (read path only). Return structured JSON.

## Output Format

```json
{
  "query": "SELECT ...",
  "rows": [ { "col": "value" }, ... ],
  "row_count": 42,
  "cached": false,
  "error": null
}
```

## Examples

```
/sq show me all critical security violations from this session
> Generated SQL: SELECT id, actor, target, detail, created_at
>   FROM audit_log
>   WHERE severity = 'critical' AND session_id = '<current>'
>   ORDER BY created_at DESC LIMIT 100;
> { "rows": [], "row_count": 0, "cached": false, "error": null }

/sq total tokens used per skill today
> Generated SQL: SELECT skill, SUM(input_tokens + output_tokens) as total_tokens
>   FROM usage_stats
>   WHERE recorded_at >= unixepoch('now', 'start of day')
>   GROUP BY skill ORDER BY total_tokens DESC LIMIT 100;
> { "rows": [...], "row_count": 3, "cached": false, "error": null }
```

<!-- References (lazy) -->
- `skills/sqlite-query/validators.md`
- `tpl-claude-plugin:sqlite-init`
