---
name: step-verifier
description: Blocks the agent from proceeding until a user-defined test command passes; logs all results to verification_log
triggers: [/verify-step, /gate, on-step-complete]
namespace: tpl-claude-plugin:step-verifier
---

## Usage

Called by the agent after completing each step to verify correctness before moving forward. Configurable via `stepVerification` in plugin.json (disabled by default — opt in per project).

Prevents the compounding failure problem: a 10-step task with 90% per-step accuracy succeeds only 34.8% of the time without gates. With gates, each step is confirmed before the next starts.

## Steps

1. Check `stepVerification.enabled` in plugin.json. If `false`, return `{ "passed": true, "skipped": true }` immediately.
2. Accept inputs: `test_command` (string), `verification_type` (exit-code | output-contains | regex-match), `expected_result` (string), optional `agent` (defaults to calling agent), optional `tags` (array).
3. Validate `test_command` safety via `tpl-claude-plugin:security-auditor`: block commands matching `rm -rf`, `DROP`, `DELETE /`, `format`, `mkfs`, or credential-exfiltration patterns.
4. Execute `test_command` in a subprocess with timeout from `stepVerification.timeoutMs` (default 30000ms). Capture stdout, stderr, exit code, and elapsed duration.
5. Evaluate result against `verification_type`:
   - `exit-code` → pass if `exit_code == parseInt(expected_result)`
   - `output-contains` → pass if stdout contains `expected_result` (case-sensitive)
   - `regex-match` → pass if stdout matches regex pattern in `expected_result`
6. INSERT into `verification_log`: session_id, agent, test_command, verification_type, expected_result, actual_result, passed (0/1), exit_code, stdout, stderr, duration_ms, retries_used.
7. **If passed** → return `{ "passed": true, "duration_ms": N }`. Agent proceeds.
8. **If failed** → show stdout/stderr to agent. If `retries_used < stepVerification.maxRetries`: increment retry count, prompt agent to fix and re-invoke. If retries exhausted: return `{ "passed": false, "error": "Max retries reached" }`. Agent is blocked.
9. **If timeout** → log to `audit_log` with `severity='critical'`, `event_type='tool-call'`. Return `{ "passed": false, "error": "Verification timed out after Nms" }`. Agent is blocked.

## Decision Rule

Gates fire automatically when `on-step-complete` trigger matches (agent signals step done). Use `/gate` for manual one-off verification. Use `/verify-step` for scripted pipelines.

## Examples

```
/gate npm test
> Running: npm test (timeout: 30s)
> ✓ Passed in 4.2s (exit code 0)
> { "passed": true, "duration_ms": 4200 }

/gate --type output-contains --expected "All tests passed" npm test
> Running: npm test
> ✗ Failed — stdout did not contain "All tests passed"
> stdout: "5 passed, 1 failed"
> Retry 1/3 — fix the issue and re-run /gate

/gate pytest tests/
> Running: pytest tests/ (timeout: 30s)
> TIMEOUT after 30000ms
> { "passed": false, "error": "Verification timed out after 30000ms" }
> [CRITICAL logged to audit_log]
```

## Query Verification History

```
/sq select test_command, passed, duration_ms, retries_used from verification_log where session_id = '<current>' order by created_at desc limit 20
```

<!-- References (lazy) -->
- `tpl-claude-plugin:security-auditor`
- `tpl-claude-plugin:sqlite-query`
- `hooks/step-verification/HOOK.md`
- `skills/sqlite-init/migrations/V003__add_verification_log.sql`
