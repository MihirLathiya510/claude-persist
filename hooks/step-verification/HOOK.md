---
event: step-verification
description: Gates agent progression — blocks the next step until a test command passes
---

## Trigger

Fires when:
- An agent signals step completion (`on-step-complete` event)
- A user or agent explicitly calls `/gate` or `/verify-step`
- `stepVerification.enabled` is `true` in plugin.json (disabled by default)

Does nothing if `stepVerification.enabled` is `false`.

## Actions

1. Receive `test_command`, `verification_type`, and `expected_result` from the calling agent or user.
2. Delegate execution to `tpl-claude-plugin:step-verifier` which runs the command in a subprocess with the configured timeout.
3. Collect result: `passed` (bool), `exit_code`, `stdout`, `stderr`, `duration_ms`, `retries_used`.
4. If passed: emit `GATE_PASSED: <step>` to the agent's channel. Agent proceeds to next step.
5. If failed and retries remain: emit `GATE_FAILED: <reason> — retry N/maxRetries`. Surface stdout/stderr to agent for debugging.
6. If failed and retries exhausted: emit `GATE_BLOCKED: <step>` to Planner. Insert `audit_log` entry with `severity='warning'`.
7. If timeout: emit `GATE_TIMEOUT: <step>` to Planner. Insert `audit_log` entry with `severity='critical'`. Halt agent.

## Enforcement

- **Pass** → agent unblocked; proceed to next step; log to `verification_log` with `passed=1`.
- **Fail (retries remain)** → agent blocked; show output; prompt fix and retry.
- **Fail (retries exhausted)** → agent fully blocked; Planner notified; user must intervene or override with `/gate --skip`.
- **Timeout** → critical log to `audit_log`; agent halted; requires user acknowledgment before session continues.
- **Hook disabled** (`stepVerification.enabled=false`) → pass-through; no action taken; no log entry.
- Never block when `stepVerification.enabled` is `false` — this is an opt-in feature.
