---
name: context-builder
description: Reads global state and emits a minimal ≤10-line human-readable context block for injection before each prompt; handles /state inspection commands
triggers: [on-session-start, on-pre-prompt, /state, /context-build]
namespace: claude-persist:context-builder
---

## Usage

Generates the minimal context block that gets injected before every user prompt. Reads from the `state` table (written exclusively by `state-updater`). Never writes to the database.

Invoked at session start to produce the initial context, and before each prompt to keep context current. Also handles the `/state` command for user inspection.

If `sqlite.enabled` is false, returns empty string (no injection).

## Steps

**`build` (on-session-start, on-pre-prompt)**
1. `SELECT value FROM state WHERE key = 'global'` — load current state JSON.
2. If no row found, return empty string. Do not error.
3. Map non-empty fields to labeled lines (skip any field that is `""` or `[]`):

   | State path | Output line |
   |-----------|-------------|
   | `project.name` | `Project: <value>` |
   | `project.description` | `About: <value>` |
   | `project.current_focus` | `Focus: <value>` |
   | `project.stack` | `Stack: <comma-joined array>` |
   | `user.preferences.response_style` | `Style: <value>` |
   | `user.preferences.verbosity` | `Verbosity: <value>` |
   | `session.current_task` | `Task: <value>` |

4. If zero lines produced (all fields empty): return empty string. No block injected.
5. Wrap with header and separator:
   ```
   [claude-persist]
   <line 1>
   <line 2>
   ...
   ---
   ```
6. Size check: if output > 1024 bytes, truncate to first 10 lines + separator. Log warning.
7. Return context block for injection into session state as `active_context`.

**`inspect` (/state)**
1. Run `build` to get the formatted context block.
2. Also fetch raw state JSON: `SELECT value, updated_at FROM state WHERE key = 'global'`
3. Output both:
   ```
   Current context block:
   [claude-persist]
   Project: MyApp
   ...
   ---

   Raw state (updated <N> seconds ago):
   {
     "project": { ... },
     ...
   }
   ```
4. If state is all-empty, output: "No state set. Use /state-edit or interact with Claude to build context automatically."

**`rebuild` (/context-build)**
1. Force re-run of `build`.
2. Display the new context block to the user.
3. Emit "Context block rebuilt." to session state.

## Output Format

Context block (injected silently before each user prompt):
```
[claude-persist]
Project: MyApp
About: SaaS billing platform
Focus: Subscription webhook handling
Stack: Node.js, Stripe, Postgres
Style: concise
Task: Debug failed webhook retry logic
---
```

Empty state (no injection, no noise):
```
(empty string — nothing injected)
```

## Rules

- Max 10 content lines (between header and separator)
- No raw JSON in the injected block
- No session history, no logs, no audit data
- Skip any field that is empty string or empty array
- Total output ≤ 1024 bytes before injection
- Read-only: never writes to any table

## Examples

```
on-session-start [state has project.name="claude-persist", session.current_task="Build state table migration"]
> build
> SELECT value FROM state WHERE key = 'global'
> Output:
  [claude-persist]
  Project: claude-persist
  Task: Build state table migration
  ---

/state
> Current context block:
  [claude-persist]
  Project: claude-persist
  Task: Build state table migration
  ---

  Raw state (updated 42 seconds ago):
  {
    "project": { "name": "claude-persist", "description": "", "current_focus": "", "stack": [] },
    "user": { "preferences": { "response_style": "", "verbosity": "" } },
    "session": { "current_task": "Build state table migration", "active_context": [] }
  }

on-session-start [state is all-empty defaults]
> build
> (empty string — context injection skipped)
```

<!-- References (lazy) -->
- `claude-persist:state-updater`
- `tpl-claude-plugin:sqlite-query`
- `skills/sqlite-init/migrations/V004__add_state_table.sql`
