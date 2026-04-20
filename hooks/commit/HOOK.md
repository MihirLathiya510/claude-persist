---
event: commit
description: Pre-commit hook; blocks commits that violate security or break plugin structure
---

## Trigger

Any git commit operation, including amended commits.

## Actions

1. Invoke `tpl-claude-plugin:security-auditor` on all staged files.
2. If any changed files are under `skills/`, `agents/`, or `.claude-plugin/`, run `tests/plugin-validator`.
3. Collect full violation report and validator output.
4. If `stepVerification.enabled` is `true` in plugin.json, invoke `tpl-claude-plugin:step-verifier` on the staged changes as a final gate before committing. Block commit if verification fails.
5. On successful commit: INSERT into `audit_log` via `tpl-claude-plugin:sqlite-query` with `event_type='commit'`, `target=<commit hash>`, `detail=<first line of commit message>`, `severity='info'`.

## Enforcement

- Any **critical** security violation → block commit, print diff of violations.
- Validator failure → block commit, print which checks failed.
- **warning** violations → surface to user; require explicit confirmation to proceed.
- On success → log commit hash + timestamp to session audit log.
