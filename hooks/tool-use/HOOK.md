---
event: tool-use
description: Intercepts tool calls; gates Computer Use through the safety skill
---

## Trigger

Any tool invocation, evaluated before the tool executes.

## Actions

1. Inspect the tool name/type being invoked.
2. If the tool is a Computer Use tool (screenshot, browser action, desktop action), route through `tpl-claude-plugin:computer-use-safety`.
3. The safety skill will describe the intended action and await human confirmation before proceeding.

## Enforcement

- Computer Use calls that bypass `computer-use-safety` → reject immediately, log the attempt.
- Confirmed Computer Use actions → execute inside sandbox/Docker; log action + screenshot proof to session state.
- Non-Computer-Use tools → pass through with no intervention.
- Timeout (30s without human confirmation) → auto-abort the Computer Use call.
