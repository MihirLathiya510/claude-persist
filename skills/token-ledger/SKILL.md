---
name: token-ledger
description: Renders a per-session token usage report from usage_stats — shows spend per skill with cache hit rate and error rate
triggers: [/token-ledger, /usage, /burn]
namespace: tpl-claude-plugin:token-ledger
---

## Usage

Run `/usage` or `/burn` at any point in a session to see where tokens are going. Useful for understanding which skills are expensive, how well the cache is working, and whether any skills are erroring frequently.

Reads from `usage_stats` via `tpl-claude-plugin:sqlite-query`. Read-only — no writes.

## Steps

1. Accept optional inputs: `session_id` (default: current session), `skill` filter, `since` (epoch timestamp for date range).
2. Query `usage_stats` via `tpl-claude-plugin:sqlite-query`:
   ```sql
   SELECT skill,
          SUM(invocation_count)              AS invocations,
          SUM(input_tokens)                  AS input_tokens,
          SUM(output_tokens)                 AS output_tokens,
          SUM(input_tokens + output_tokens)  AS total_tokens,
          SUM(cache_hits)                    AS cache_hits,
          SUM(error_count)                   AS errors
   FROM usage_stats
   WHERE session_id = ?
   GROUP BY skill
   ORDER BY total_tokens DESC;
   ```
3. Compute derived columns:
   - `cache_hit_%` = `cache_hits / invocations * 100` (0 if invocations = 0)
   - `error_%` = `errors / invocations * 100`
   - `% of session` = `total_tokens / session_total * 100`
4. Render as a markdown table:

   ```
   | Skill                    | Calls | Input  | Output | Total  | Cache% | Err% | % Session |
   |--------------------------|------:|-------:|-------:|-------:|-------:|-----:|----------:|
   | sqlite-query             |    12 |  8,400 |  1,200 |  9,600 |  83.3% | 0.0% |     42.1% |
   | agent-team-orchestrator  |     3 |  5,100 |  2,300 |  7,400 |   0.0% | 0.0% |     32.5% |
   | security-auditor         |     8 |  2,800 |    400 |  3,200 |  75.0% | 0.0% |     14.0% |
   | mcp-discovery            |     1 |  2,600 |    600 |  3,200 |   0.0% | 0.0% |      1.9% |
   | **TOTAL**                |    24 | 18,900 |  4,500 | 23,400 |  66.7% | 0.0% |    100.0% |
   ```

5. Add a summary section below the table:
   - Most expensive skill (by total tokens)
   - Best cache hit rate (skill with highest %)
   - Any skills with error rate > 10% (flag these)
   - Estimated session budget remaining (if `sqlite.tokenBudget` set in plugin.json)
6. Optionally write full report to `.claude-plugin/token-ledger-<session_id>.md` if user passes `--save` flag.

## Decision Rule

- `/usage` → current session, all skills, no save
- `/burn` → same as /usage (alias, shorter to type)
- `/usage --save` → generate report + write to `.claude-plugin/`
- `/usage --skill sqlite-query` → filter to one skill across all sessions
- `/usage --since 7d` → last 7 days across all sessions

## Examples

```
/usage
> Token usage for current session:
> | Skill            | Calls | Total  | Cache% |
> |------------------|------:|-------:|-------:|
> | sqlite-query     |    12 |  9,600 | 83.3%  |
> | security-auditor |     8 |  3,200 | 75.0%  |
> | TOTAL            |    20 | 12,800 | 80.0%  |
> Most expensive: sqlite-query (75.0% of session)
> Cache saved ~8,400 tokens this session.

/burn --save
> Report written to .claude-plugin/token-ledger-abc123.md
```

<!-- References (lazy) -->
- `tpl-claude-plugin:sqlite-query`
- `skills/sqlite-init/schema.sql`
