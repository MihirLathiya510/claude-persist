---
name: computer-use-safety
description: Gates all Computer Use tool calls behind human confirmation; executes in sandbox
---

## Usage

Automatically invoked by `hooks/tool-use/HOOK.md` whenever a Computer Use tool is called. Can also be triggered directly with `/computer-use <description>`.

Never executes a Computer Use action without explicit human approval.

## Steps

1. Receive the Computer Use tool call (action type, target, parameters).
2. Compose a plain-language description of the intended action (e.g. "Take a screenshot of the current screen" or "Click the Submit button on example.com").
3. Present description to the user and await explicit `yes` / `no` confirmation.
4. On `no` or timeout (30s) → abort, log the attempt, return without executing.
5. On `yes` → execute the action inside the configured sandbox/Docker container.
6. Capture result and screenshot proof; log both to session state.
7. Return result to the caller.

## Examples

```
[computer-use-safety] Requested action: Take a screenshot of the current screen.
Confirm? (yes/no): yes
> Executing in sandbox...
> Screenshot captured. Result returned.
```

## Sandbox Pattern

Recommended: run Computer Use inside an isolated Docker container with no access to host filesystem or network beyond what is explicitly permitted. See project docs for container setup.

<!-- References (lazy) -->
- `hooks/tool-use/HOOK.md`
