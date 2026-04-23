---
name: self-improver
description: Lets the plugin refactor itself using the agent team pipeline with full hook enforcement
---

## Usage

Triggered when the user requests improvements to the claude-persist plugin. Spawns an agent team via `agent-team-orchestrator` and routes all changes through the normal hook pipeline.

## Steps

1. Identify the improvement target (specific skill, hook, agent config, or plugin.json).
2. Spawn agent team via `tpl-claude-plugin:agent-team-orchestrator`.
3. All file writes trigger `hooks/file-write/HOOK.md` → `tpl-claude-plugin:security-auditor` runs automatically.
4. All commits trigger `hooks/commit/HOOK.md` → validator runs if structure files changed.
5. After all changes: Tester runs `tests/plugin-validator`; block if any check fails.
6. If plugin.json `version` needs a bump, present the proposed new version to the user for explicit confirmation before writing.
7. Report summary of what changed and new version (if bumped).

## Examples

```
/self-improve "Add rate-limiting skill to the template"
> Spawning agent team...
> [security-auditor] Scanning new files... PASS
> [plugin-validator] All checks passed.
> Proposed version bump: 1.0.0 → 1.1.0. Confirm? (yes/no):
```

## Constraints

- Never modify `claude.md` without explicit user instruction.
- Never auto-increment version; always require confirmation.
- Self-improvement changes go through the full review pipeline — no shortcuts.

<!-- References (lazy) -->
- `tpl-claude-plugin:security-auditor`
- `skills/agent-team-orchestrator/SKILL.md`
- `tests/plugin-validator`
