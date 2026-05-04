---
event: session-start
description: Runs at the start of every session; initializes plugin state, loads persistent context, and warms skill index
---

## Trigger

A new Claude Code session begins (CLI launch, IDE attach, or Cowork join).

## Actions

1. Load and parse `.claude-plugin/plugin.json`; validate it is well-formed JSON.
2. Warm the skill frontmatter index: read only the YAML frontmatter block of each SKILL.md in `skills/`.
3. Run `tpl-claude-plugin:mcp-discovery` to detect available MCP servers and register them in session state.
4. Invoke `tpl-claude-plugin:sqlite-init` to initialize or verify the database (per-project path resolved at this step). If sqlite-init detects pending migrations, surface the migration prompt to the user before proceeding.
5. Invoke `claude-persist:state-updater` with operation `load`: read the global state row from the `state` table. If the row is missing, INSERT the default state structure. If state size exceeds 2KB, warn and reset to defaults. Emit loaded state to session context as `active_state`.
6. Invoke `claude-persist:first-run-bootstrap`: if all state fields are empty (first-ever session), silently parse `package.json`, `README.md`, and `git log` to populate initial project context via state-updater. Exits immediately if any state field is already populated.
7. Invoke `claude-persist:context-builder` with operation `build`: read current state and generate the context block. If at least one state field is non-empty, inject the context block into session state as `active_context`. If all fields are empty, skip injection silently — no noise for fresh installs.

## Enforcement

- If `plugin.json` is missing or malformed → warn user and degrade gracefully (skills still load, MCP discovery skipped).
- If a skill directory has no SKILL.md → warn and skip that skill.
- If `sqlite-init` fails (schema error, permission error) → log the error to session state and degrade gracefully; do not block session start.
- If `state-updater` fails → log warning to session state; skip context injection; do not block session start. Session proceeds without persistent context.
- If `first-run-bootstrap` fails for any reason → log warning; session proceeds normally with empty context. Never block session start.
- If `context-builder` output exceeds 1KB → iteratively drop the last line until ≤ 1024 bytes, log warning with count of dropped lines, inject truncated block.
- Never fail hard at session start; always allow the session to proceed with a degraded capability report.
- Frontmatter warm is read-only; skill bodies are never loaded unless a trigger fires.
