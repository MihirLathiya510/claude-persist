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
4. Log the active install profile (from plugin.json `installProfiles`) to session state.
5. If `sqlite.enabled` is `true` in plugin.json, invoke `tpl-claude-plugin:sqlite-init` to initialize or verify the database. If sqlite-init detects pending migrations, surface the migration prompt to the user before proceeding.
6. Invoke `claude-persist:state-updater` with operation `load`: read the global state row from the `state` table. If the row is missing, INSERT the default state structure. If state size exceeds 2KB, warn and reset to defaults. Emit loaded state to session context as `active_state`.
7. Invoke `claude-persist:context-builder` with operation `build`: read current state and generate the context block. If at least one state field is non-empty, inject the context block into session state as `active_context`. If all fields are empty, skip injection silently — no noise for fresh installs.
8. Invoke `tpl-claude-plugin:anatomy-indexer` to build or refresh `PROJECT_MAP.json` (skipped if index is < 1 hour old). Agents use this map to avoid redundant file reads.

## Enforcement

- If `plugin.json` is missing or malformed → warn user and degrade gracefully (skills still load, MCP discovery skipped).
- If a skill listed in `capabilities.skills` has no corresponding SKILL.md → warn and skip that skill.
- If `sqlite-init` fails (schema error, permission error) → log the error to session state and degrade gracefully; do not block session start.
- If `state-updater` fails → log warning to session state; skip context injection; do not block session start. Session proceeds without persistent context.
- If `context-builder` output exceeds 1KB → truncate to first 10 lines, log warning, inject truncated block.
- If `anatomy-indexer` fails → log warning to session state; agents fall back to direct file reads; do not block session start.
- If pending migrations are found → surface prompt; session proceeds but agents are warned that schema may be behind.
- Never fail hard at session start; always allow the session to proceed with a degraded capability report.
- Frontmatter warm is read-only; skill bodies are never loaded unless a trigger fires.
