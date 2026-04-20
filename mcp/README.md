# MCP Server Configuration

MCP servers are registered in `.mcp.json` at the project root and discovered at session start by the `mcp-discovery` skill.

## Adding a Server

Add an entry to the `servers` array in `.mcp.json`:

```json
{
  "name": "my-server",
  "command": "npx",
  "args": ["-y", "my-mcp-server"],
  "capabilities": ["read-files", "search"]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Unique identifier used by skills to reference this server |
| `command` | yes | Executable to launch the server |
| `args` | yes | Arguments passed to the command |
| `capabilities` | yes | List of capability tags — used by `mcp-discovery` to match user requests |

## Security

- Never commit credentials or tokens directly in `.mcp.json`.
- Use environment variable references: `"env": { "API_KEY": "$MY_API_KEY" }`.
- The `security-auditor` skill scans `.mcp.json` on every write.

## Testing Connectivity

After adding a server, run:

```
/discover-mcp
```

This invokes `tpl-claude-plugin:mcp-discovery`, which tests each server and reports status.

## Fallback Behavior

If no MCP server covers a requested capability, the system falls back to Computer Use via `tpl-claude-plugin:computer-use-safety` (human confirmation required).
