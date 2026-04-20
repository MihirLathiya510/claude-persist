---
name: agent-team-orchestrator
description: Spawns and coordinates agent teams for complex multi-file tasks
triggers: [/orchestrate, on-complex-task, on-multi-file-change]
namespace: tpl-claude-plugin:agent-team-orchestrator
---

## Usage

Automatically triggered when a task spans more than 3 files or involves refactoring. Can be invoked manually with `/orchestrate <task description>`.

Coordinates the five predefined agent roles: Planner, Coder, Reviewer, Security, Tester.

## Decision Rule

Trigger this skill when ANY of:
- Task touches > 3 files
- Task involves refactoring existing code
- Task requires parallel workstreams
- User explicitly invokes `/orchestrate`

## Steps

1. Assess task scope (file count, refactor vs. new, external dependencies).
2. Select relevant agents from `agents/` based on task type.
3. Planner produces sequenced task list and distributes via shared channel.
4. Coder implements tasks; Reviewer approves each before proceeding.
5. Security agent runs in parallel on any sensitive file changes.
6. Tester runs `tests/plugin-validator` after all Coder tasks complete.
7. Collect and synthesize outputs; surface final result to user.
8. Orchestration is complete only when Tester reports `DONE: all checks passed`.

## Examples

```
/orchestrate "Add a new skill for rate-limiting"
> Planner: scoping task...
> [CODER] Create skills/rate-limiter/SKILL.md
> [CODER] Update .claude-plugin/plugin.json capabilities
> [TESTER] Run tests/plugin-validator
> DONE: all checks passed
```

<!-- References (lazy) -->
- `agents/planner.md`
- `agents/coder.md`
- `agents/reviewer.md`
- `agents/security.md`
- `agents/tester.md`
