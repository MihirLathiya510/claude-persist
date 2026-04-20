# tpl-claude-plugin

A production-ready template for building Claude Code plugins in 2026.  
Ships with agent teams, persistent SQLite memory, MCP-first tooling, and a self-validating structure out of the box.

---

## What this is

A skeleton that isn't empty.

Most plugin templates hand you a folder and a `hello-world` example. This one gives you a working architecture — agents that coordinate, hooks that enforce, memory that persists, and a validator that tells you when something's broken.

Clone it. Extend it. Ship it.

---

## Architecture at a glance

```
tpl-claude-plugin/
├── skills/          ← composable micro-skills (the core primitive)
├── agents/          ← 5 predefined agent roles for complex tasks
├── hooks/           ← automatic enforcement on write, commit, tool use, session start
├── mcp/             ← MCP server config and discovery
├── .claude-plugin/  ← plugin manifest + SQLite database (runtime)
└── tests/           ← structural validator
```

Everything connects. Skills invoke hooks. Hooks invoke skills. Agents coordinate via a shared task list. The validator makes sure none of it drifts.

---

## Skills

Skills are the atomic unit. Each one is a folder with a `SKILL.md`:

```
skills/
  security-auditor/        ← runs on every write and commit
  agent-team-orchestrator/ ← spawns and coordinates agent teams
  computer-use-safety/     ← gates Computer Use behind human confirmation
  self-improver/           ← lets the plugin refactor itself
  mcp-discovery/           ← finds MCP servers at session start
  plugin-dev/              ← scaffolds new skills with /create-micro-skill
  sqlite-init/             ← initializes the database and runs migrations
  sqlite-query/            ← natural language → validated SQL → JSON
  sqlite-memory/           ← typed agent memory (decisions, tasks, messages)
  sqlite-schema-manager/   ← migrations, health checks, schema inspection
  anatomy-indexer/         ← builds PROJECT_MAP.json at session start
  step-verifier/           ← gates agent progression behind test commands
  token-ledger/            ← per-session token spend report by skill
```

**Progressive disclosure** — frontmatter loads at session start (~8 tokens per skill). Body loads when a trigger fires. References load only when needed. The total context cost at session start: ~390 tokens for all 13 skills.

### Adding a skill

```
/plugin-dev:create-micro-skill
```

Enter a name, description, and triggers. The skill is scaffolded, registered in `plugin.json`, and validated automatically.

---

## Agent Teams

When a task touches more than 3 files or involves refactoring, the `agent-team-orchestrator` skill spawns a coordinated team:

| Agent | Role | Write access |
|-------|------|-------------|
| Planner | Breaks tasks into sequenced lists; loads prior context from SQLite | No |
| Coder | Implements; every write triggers the file-write hook | Yes |
| Reviewer | Approves output; queries audit_log to verify hook compliance | No |
| Security | Deep review on sensitive changes; holds veto power | No |
| Tester | Runs `plugin-validator`; blocks release on failure | No |

Trigger manually:
```
/orchestrate "describe what you want to build"
```

Triggered automatically when task scope exceeds 3 files.

---

## Hooks

Four hooks run automatically. One is opt-in:

| Hook | Fires on | What it does |
|------|----------|-------------|
| `session-start` | New session | Loads plugin config, warms skill index, runs MCP discovery, initializes SQLite, builds PROJECT_MAP.json |
| `file-write` | Every Write/Edit | Runs security-auditor; logs to audit_log |
| `commit` | Pre-commit | Runs security-auditor + validator on structural files; logs commit to audit_log |
| `tool-use` | Any tool call | Gates Computer Use through human confirmation |
| `step-verification` | Agent step complete | Runs test command; blocks progression until it passes (opt-in) |

Security violations are tiered: **critical** blocks the operation, **warning** requires confirmation, **info** logs silently.

---

## SQLite Memory

Every agent decision, task, message, hook trigger, and security event is persisted and queryable.

```
/sq show me all security violations from this session
/sq which skill used the most tokens today
/remember that the user prefers bundled PRs
/recall decisions by planner from the last session
/db-status
```

**Schema:** `decisions` · `tasks` · `messages` · `audit_log` · `usage_stats` · `schema_version` · `verification_log`  
**Search:** FTS5 full-text search across decisions, messages, and audit log  
**Safety:** `audit_log` is append-only. `reviewer` and `security` agents are read-only. Destructive queries (`DROP`, `DELETE` without `WHERE`) are blocked at the skill layer.

The database lives at `.claude-plugin/db/plugin.db` and is excluded from git.

---

## Anatomy Indexer

At session start, `anatomy-indexer` walks the repo and writes `.claude-plugin/PROJECT_MAP.json` — a file/symbol index with function names, class names, and exports at their line numbers.

Agents check the map before opening files. This eliminates redundant reads on large projects.

```
/map          ← rebuild the index on demand
```

The index is skipped if it's less than 1 hour old. It's excluded from git (generated at runtime).

---

## Step-Verification Gate

After each agent step, `/gate <command>` runs a test and blocks progression until it passes.

```
/gate "pytest tests/unit -q"
/gate "npm test"
/gate "./tests/plugin-validator"
```

Supports three verification modes: `exit-code`, `output-contains`, `regex-match`. Results (pass/fail/timing/retries) are logged to `verification_log`.

**Disabled by default.** Enable per project in `plugin.json`:

```json
"stepVerification": {
  "enabled": true,
  "maxRetries": 3,
  "timeoutMs": 30000
}
```

---

## Token Ledger

```
/usage        ← current session token spend by skill
/burn         ← alias for /usage
/usage --save ← write report to .claude-plugin/token-ledger-<session>.md
```

Output: markdown table with invocations, input tokens, output tokens, cache hit %, error rate, and % of session total. Helps identify which skills are expensive and where cache is missing.

---

## MCP

MCP servers are registered in `.mcp.json`. The `mcp-discovery` skill tests connectivity at session start and registers available servers in session state.

```json
{
  "servers": [
    {
      "name": "my-server",
      "command": "npx",
      "args": ["-y", "my-mcp-server"],
      "capabilities": ["read-files", "search"]
    }
  ]
}
```

When no MCP server covers a needed capability, the system falls back to Computer Use (gated by `computer-use-safety`).

---

## Validator

```bash
./tests/plugin-validator
```

Checks 143 structural invariants: every skill has a `SKILL.md`, every hook has the required sections, namespaces match directory names, write-touching skills reference `security-auditor`, migration files follow naming conventions, and more.

Zero tolerance — the validator exits 1 on any failure. Run it before every release.

---

## Decision tree

```
Task touches 1 file      →  single skill
Task touches 3+ files    →  /orchestrate (agent team)
Need an external tool    →  MCP first, Computer Use as fallback
Any write or commit      →  security-auditor runs automatically
Plugin needs improvement →  /self-improve
Add a skill              →  /plugin-dev:create-micro-skill
Refresh file index       →  /map
Verify an agent step     →  /gate <test-command>
Check token spend        →  /usage
Check DB health          →  /db-status
```

---

## Getting started

```bash
git clone <this repo>
cd tpl-claude-plugin
./tests/plugin-validator        # verify structure
claude-code --plugin-dir .      # load plugin in Claude Code
```

First session: `session-start` hook initializes the SQLite database, warms skill frontmatter, and discovers MCP servers. Everything else is on-demand.

---

## Extending

| Want to... | Do this |
|-----------|---------|
| Add a skill | `/plugin-dev:create-micro-skill` |
| Add an MCP server | Edit `.mcp.json`, run `/discover-mcp` |
| Run a migration | `/migrate` |
| Improve the template itself | `/self-improve` |
| Check DB health | `/db-status` |
| Refresh file/symbol index | `/map` |
| Gate an agent step | `/gate <test-command>` |
| See token spend by skill | `/usage` or `/burn` |
| Audit recent activity | `/sq select * from audit_log order by created_at desc limit 20` |

---

## Compatibility

- Claude Opus 4.6 / Sonnet 4.6+ (Agent Teams, MCP, Computer Use)
- VS Code extension, CLI, Cowork
- SQLite 3.38+ (JSON1 + FTS5, both built-in)
