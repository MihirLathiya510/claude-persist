---
name: mcp-discovery
description: Discovers available MCP servers from .mcp.json and registers them in session state
triggers: [on-session-start, /discover-mcp, /mcp-list]
namespace: tpl-claude-plugin:mcp-discovery
---

## Usage

Runs automatically via `hooks/session-start/HOOK.md` at the start of every session. Can be re-triggered manually with `/discover-mcp` or `/mcp-list`.

## Steps

1. Locate `.mcp.json` in the project root (fall back to `~/.claude/mcp.json` if absent).
2. Parse the `servers` array; skip gracefully if empty.
3. For each server entry, test connectivity by launching the server command with a `ping` handshake.
4. Register available servers (name + capabilities) in session state.
5. For any server that fails connectivity, log a warning — do not hard-fail the session.
6. Report discovered servers and their capabilities to the user.
7. If no server covers a needed capability, note that `computer-use-safety` is the fallback.

## Output Format

```
[mcp-discovery] Scanning .mcp.json...
  ✓ my-server (capabilities: read-files, search)
  ✗ other-server (connection failed: ECONNREFUSED)
Active MCP servers: 1
Fallback: tpl-claude-plugin:computer-use-safety
```

## Examples

```
/discover-mcp
> [mcp-discovery] No servers configured in .mcp.json.
> Fallback: tpl-claude-plugin:computer-use-safety
```

<!-- References (lazy) -->
- `.mcp.json`
- `mcp/README.md`
