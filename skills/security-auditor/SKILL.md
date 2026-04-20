---
name: security-auditor
description: Scans files for secrets and security violations; runs on every write and commit
triggers: [on-file-write, on-commit, /security-audit]
namespace: tpl-claude-plugin:security-auditor
---

## Usage

Invoked automatically by `hooks/file-write/HOOK.md` and `hooks/commit/HOOK.md`. Can also be triggered manually with `/security-audit`.

Accepts a list of file paths and their staged content. Returns a structured violation report.

## Steps

1. Receive file path list from the calling hook or user.
2. Pattern-match each file against secret regexes:
   - API keys: `[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]\s*\S+`
   - Tokens: `[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*[A-Za-z0-9+/]{20,}`
   - Private keys: `-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----`
   - Passwords: `[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[:=]\s*\S{8,}`
3. Check that no `.env` files with literal secrets are being written.
4. Verify hook registry: confirm `file-write` and `commit` hooks are present on disk.
5. Return violation report with severity for each finding.

## Output Format

```
VIOLATION critical <file>:<line> <pattern-name>: <snippet>
VIOLATION warning  <file>:<line> <pattern-name>: <snippet>
VIOLATION info     <file>:<line> <pattern-name>: <snippet>
PASS <file>
```

## Examples

```
/security-audit
> Scanning 3 files...
> PASS skills/mcp-discovery/SKILL.md
> VIOLATION critical config.json:12 api-key: "sk-abc123..."
> PASS agents/planner.md
```

<!-- References (lazy) -->
- `hooks/file-write/HOOK.md`
- `hooks/commit/HOOK.md`
