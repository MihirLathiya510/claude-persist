---
name: state-updater
description: Extracts meaningful updates from each exchange and merges them into persistent global state via dot-path patching — the sole writer of the state table
---

## Usage

The single gatekeeper for the `state` table. No other skill writes to `state` directly.

Invoked automatically at session start (to load or initialize state) and after each response (to extract and persist meaningful updates). Can also be triggered manually for inspection or reset.

DB path is resolved by `sqlite-init` at session start (per-project: `~/.claude/projects/<hash>/plugin.db`).

If `sqlite.enabled` is false, all operations return `null` and log a note to session state.

## Operations

**`load` (on-session-start)**
1. Check `sqlite.enabled`. If false, skip and log warning.
2. `SELECT value FROM state WHERE key = 'global'`
3. If no row found: INSERT the default state structure (see Default State below). Log "State initialized with defaults."
4. If row found but `length(value) > 2048`: log warning "State exceeds 2KB — resetting to defaults." Reset to default structure.
5. Emit loaded state to session context as `active_state`.

**`extract` (on-post-response)**
1. Receive `{ user_message, claude_response }`.
2. Scan for meaningful signals:
   - Project name: explicit mentions of app/project name
   - Stack mentions: language, framework, database, tool names
   - Current focus: what the user is actively working on
   - Current task: the immediate goal of this session
   - Response style preference: explicit requests like "be concise", "give me detail"
   - Verbosity: explicit requests like "shorter", "more explanation"
3. Build a dot-path patch — only include fields where a clear, confident signal was found. Empty patch = no-op (skip merge entirely).
4. Pass patch to `merge` operation.

**`merge` (internal)**
1. Load current state JSON from `SELECT value FROM state WHERE key = 'global'`.
2. For each `"dot.path": value` in the patch:
   - Split key by `.` — traverse the JSON object to the parent node, set the leaf.
   - Arrays (`stack`, `active_context`): replace entirely with the new value (no append).
3. Run guards:
   - **Root key guard**: reject any key not in `["project", "user", "session"]`. Log and skip the offending key.
   - **Size guard**: `length(json(merged)) > 2048` → reject entire merge, log "Merge rejected: state would exceed 2KB."
   - **Secret guard**: value matches any secret pattern (API key, token, password, private key) → reject that key, log warning.
   - **No-op guard**: value is empty string, whitespace-only string (strip before check), empty array, or identical to current → skip that key silently.
4. On success: `UPDATE state SET value = json(merged), updated_at = unixepoch() WHERE key = 'global'`
5. Emit "State updated: N field(s) changed." to session context.

**`reset` (/state-reset)**
1. Confirm operation with user ("This will clear all persisted state. Proceed?").
2. `UPDATE state SET value = <default_json>, updated_at = unixepoch() WHERE key = 'global'`
3. Emit "State reset to defaults."

**`edit` (/state-edit)**
1. Accept a user-provided JSON patch in dot-path format: `{ "project.name": "MyApp", "user.preferences.verbosity": "low" }`.
2. Validate: must be a flat object (no nesting in values for scalar fields; arrays allowed for stack/active_context).
3. Pass directly to `merge` operation with the same guards.
4. Emit result of merge.

## Default State Structure

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

## Extract Output Format

```json
{
  "updates": {
    "project.current_focus": "Implementing JWT refresh token flow",
    "project.stack": ["TypeScript", "Postgres", "Redis"],
    "user.preferences.response_style": "concise",
    "session.current_task": "Debug failed webhook retry logic"
  }
}
```

## Guards Summary

| Guard | Rule | Action on violation |
|-------|------|---------------------|
| Root key | Only `project`, `user`, `session` | Skip key, log warning |
| Size | Merged JSON ≤ 2048 bytes | Reject entire merge |
| Secret | No API keys, tokens, passwords, private keys | Skip key, log warning |
| No-op | Empty or unchanged values | Skip key silently |
| Schema | sqlite.enabled must be true | Return null, log note |

## Examples

```
on-session-start
> load
> SELECT value FROM state WHERE key = 'global'
> State loaded: project.name="MyApp", session.current_task="Build state updater"

on-post-response [user said: "let's work on the Stripe webhook handler, keep it concise"]
> extract → { "updates": { "session.current_task": "Stripe webhook handler", "user.preferences.response_style": "concise" } }
> merge → 2 field(s) updated

/state-reset
> "This will clear all persisted state. Proceed?" → confirmed
> State reset to defaults.

/state-edit { "project.name": "claude-persist", "project.stack": ["SQLite", "Claude Code"] }
> merge → 2 field(s) updated
```

<!-- References (lazy) -->
- `tpl-claude-plugin:security-auditor`
- `tpl-claude-plugin:sqlite-query`
- `tpl-claude-plugin:sqlite-init`
- `skills/sqlite-init/migrations/V004__add_state_table.sql`
