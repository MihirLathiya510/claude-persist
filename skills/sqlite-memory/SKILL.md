---
name: sqlite-memory
description: Typed agent interface to persistent memory tables — decisions, tasks, messages — with no raw SQL surface
triggers: [/sqlite-memory, /remember, /recall, on-agent-decision, on-task-update]
namespace: tpl-claude-plugin:sqlite-memory
---

## Usage

Provides four typed operations to agents for reading and writing structured memory. No raw SQL is accepted — all writes use predefined parameterized statement templates. Reviewer and Security agents are read-only.

If `sqlite.enabled` is false, all operations return `null` and log a note to session state.

## Steps

**`remember-decision` (write)**
1. Check sqlite enabled + caller not in `readOnlyAgents`.
2. Validate: `summary` required, `confidence` between 0–1 if provided, `metadata` must be valid JSON if provided.
3. INSERT into `decisions` with current `session_id`, `agent`, `summary`, `reasoning`, `confidence`, `metadata`.
4. Emit session state notification: "Decision persisted (id: N)."

**`recall-decisions` (read)**
1. Accept optional filters: `agent`, `session_id`, `since` (epoch), `match` (FTS text).
2. Build SELECT with filters. If `match` provided, join `decisions_fts` with `MATCH`.
3. Return up to `rowLimit` results as JSON array.

**`update-task` (write)**
1. Check sqlite enabled + caller not in `readOnlyAgents`.
2. If task `id` provided → UPDATE `status`, `assignee`, `updated_at`, `metadata`.
3. If no `id` → INSERT new task with `session_id`, `title`, `description`, `assignee`, `status`, `parent_task_id`.
4. Confirm persistence in session state.

**`log-message` (write)**
1. Check sqlite enabled + caller not in `readOnlyAgents`.
2. Validate `role`, `channel` are allowed values.
3. INSERT into `messages` with `session_id`, `role`, `agent`, `channel`, `content`, `metadata`.

## Examples

```
on-agent-decision [planner]: "Use agent team for this task — touches 5 files"
> remember-decision { agent: "planner", summary: "Use agent team", confidence: 0.9 }
> Decision persisted (id: 1)

/recall decisions by planner from this session
> recall-decisions { agent: "planner", session_id: "<current>" }
> { "rows": [{ "id": 1, "summary": "Use agent team", ... }], "row_count": 1 }

/remember that the user prefers bundled PRs
> remember-decision { agent: "assistant", summary: "User prefers bundled PRs", confidence: 1.0 }
> Decision persisted (id: 2)
```

<!-- References (lazy) -->
- `tpl-claude-plugin:security-auditor`
- `tpl-claude-plugin:sqlite-init`
- `skills/sqlite-init/schema.sql`
