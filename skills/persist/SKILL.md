---
name: persist
description: Unified command router for claude-persist — status dashboard, remember/forget, activity log, and file index
---

## Usage

The single entry point for everyday claude-persist interaction. Six commands cover everything most users need.

```
/persist status              ← hero dashboard: project context + DB health
/persist remember <fact>     ← store a fact into project state
/persist forget <topic>      ← clear a state field by topic
/persist log                 ← recent session activity
/persist map                 ← rebuild file and symbol index
/persist help                ← show this command list
```

Old commands (`/state`, `/state-edit`, `/sq`, `/map`, `/usage`, `/db-status`, etc.) still work via their individual skills — they are not removed.

## Commands

### `/persist status`

Renders the hero dashboard. Data is assembled from three sources:
1. `SELECT value, updated_at FROM state WHERE key = 'global'` — current state JSON
2. File stat on the per-project `plugin.db` — size in KB
3. `SELECT MAX(version) FROM schema_version` and `PRAGMA journal_mode` — schema version and WAL health

**Output format:**
```
[claude-persist v1.4]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project:   MyApp
Stack:     Node.js, Stripe, Postgres
Focus:     Subscription webhook handling
Style:     concise
Task:      Debug failed webhook retry logic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context:   5 fields injected  (≈ 320 B of 1024 B limit)
DB:        ~/.claude/projects/a3f8c12d9e44/plugin.db  (40 KB)
Schema:    v5  |  Health: OK  |  Updated: 3 min ago
Bootstrap: Auto-completed — parsed package.json + git log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/persist remember <fact>  ·  /persist forget <topic>  ·  /persist log  ·  /persist map
```

Rules:
- Skip any state line whose value is `""` or `[]`
- "Context: N fields injected" counts non-empty state fields; estimate bytes from context-builder block size
- "Bootstrap: Auto-completed" line appears only if `first-run-bootstrap` ran this session (session-scoped flag in `active_state`)
- If state is entirely empty: show the separator lines with "No context yet. Run /persist status after a few exchanges." in the data area
- Health: "OK" if WAL mode is on and state row exists; "WARN: <reason>" otherwise

### `/persist remember <fact>`

Stores a free-form fact into project state via state-updater.

Steps:
1. Receive `<fact>` as a natural language string (e.g. "we use Postgres not MySQL", "keep answers concise", "current focus is auth refactor").
2. Infer the appropriate dot-path:
   - Stack/tech mentions → `project.stack` (merge with existing, deduplicate)
   - Focus/working-on mentions → `project.current_focus`
   - Style/verbosity mentions → `user.preferences.response_style` or `user.preferences.verbosity`
   - Task/goal mentions → `session.current_task`
   - Description/about mentions → `project.description`
   - Project name mentions → `project.name`
3. Build dot-path patch and pass to `claude-persist:state-updater` merge operation.
4. Confirm: "Remembered: <field> = <value>"

### `/persist forget <topic>`

Clears a specific state field.

Steps:
1. Map `<topic>` to a dot-path (same inference logic as `remember`).
2. Pass a patch with the field set to `""` (string fields) or `[]` (array fields) to `claude-persist:state-updater` merge.
3. Confirm: "Cleared: <field>"

If topic is `all` or `everything`: confirm with user first ("This will clear all persisted state. Proceed?"), then invoke `state-updater` reset operation.

### `/persist log`

Shows recent session activity.

Steps:
1. Query via `tpl-claude-plugin:sqlite-query`:
   ```sql
   SELECT event_type, actor, target, detail, severity, created_at
   FROM audit_log
   ORDER BY created_at DESC LIMIT 20;
   ```
2. Also show: `SELECT value, updated_at FROM state WHERE key='global'` → display `updated_at` as human time.
3. Format as a clean log with timestamps.

### `/persist map`

Triggers a full anatomy-indexer scan of the project.

Steps:
1. Invoke `tpl-claude-plugin:anatomy-indexer` — full recursive scan (same logic as anatomy-indexer SKILL.md).
2. Report: "Index built: N files, M symbols. .claude-plugin/PROJECT_MAP.json updated."

### `/persist help`

Shows the command list with one-line descriptions.

Output:
```
[claude-persist v1.4] — commands

  /persist status              Show project context, DB health, and bootstrap status
  /persist remember <fact>     Store a fact into project memory
  /persist forget <topic>      Clear a specific memory field (or "all" to wipe)
  /persist log                 Show recent session activity from the audit log
  /persist map                 Rebuild the file and symbol index for this project
  /persist help                Show this message

Advanced:  /state · /state-edit · /state-reset · /sq · /usage · /db-status · /migrate · /security-audit · /orchestrate
```

## Examples

```
/persist status
> [claude-persist v1.4]
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> Project:   claude-persist
> Stack:     SQLite, Claude Code
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> Context:   2 fields injected  (≈ 88 B)
> DB:        ~/.claude/projects/a3f8c12d9e44/plugin.db  (40 KB)
> Schema:    v5  |  Health: OK  |  Updated: 2 min ago
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/persist remember we use Stripe for payments and Redis for caching
> Remembered: project.stack = ["SQLite", "Claude Code", "Stripe", "Redis"]

/persist forget focus
> Cleared: project.current_focus

/persist map
> Re-scanning repo...
> Index built: 47 files, 389 symbols. .claude-plugin/PROJECT_MAP.json updated.

/persist help
> [claude-persist v1.4] — commands
> ...
```

<!-- References (lazy) -->
- `claude-persist:state-updater`
- `tpl-claude-plugin:sqlite-query`
- `tpl-claude-plugin:anatomy-indexer`
- `skills/context-builder/SKILL.md`
- `hooks/session-start/HOOK.md`
