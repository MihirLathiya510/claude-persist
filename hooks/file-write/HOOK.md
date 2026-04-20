---
event: file-write
description: Runs on every file write; enforces security before content is persisted
---

## Trigger

Any invocation of the Write or Edit tool that produces a new or modified file.

## Actions

1. Invoke `tpl-claude-plugin:security-auditor` with the target file path and staged content.
2. Pattern-match against secret regexes (API keys, tokens, passwords, private keys).
3. Check that no `.env` files containing literal secrets are being written.
4. Collect violation report (severity: critical / warning / info).
5. If `sqlite.enabled` is `true` and the write is not blocked: INSERT into `audit_log` via `tpl-claude-plugin:sqlite-query` with `event_type='hook-trigger'`, `actor=<calling agent>`, `target=<file path>`, `severity='info'`, `detail='file-write hook ran'`.

## Enforcement

- **critical** violations → block the write, surface the violation to the user, do not persist the file.
- **warning** violations → warn the user, allow write only after explicit confirmation.
- **info** violations → log to session state, do not block.
- All violations are appended to the session audit log.
