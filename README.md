# claude-persist

A Claude Code plugin that gives Claude **persistent state awareness** across sessions.

Claude learns your project, stack, preferences, and current task — automatically, from natural conversation. No configuration required. No repeating yourself.

---

## What it does

Every exchange teaches Claude something. After you mention your stack, Claude knows your stack. After you say "keep it concise," Claude remembers that preference. After you describe what you're working on, Claude carries that context into the next session.

The context is stored in SQLite, injected before each prompt as a compact block (≤ 10 lines), and updated after each response — silently, in the background.

---

## Context block (what Claude sees before your prompt)

```
[claude-persist]
Project: MyApp
About: SaaS billing platform
Focus: Subscription webhook handling
Stack: Node.js, Stripe, Postgres
Style: concise
Task: Debug failed webhook retry logic
---
```

Empty fields are skipped. Fresh install = no injection = no noise.

---

## Architecture

```
claude-persist/
├── skills/
│   ├── state-updater/        ← sole writer of global state
│   ├── context-builder/      ← reads state, emits context block
│   └── sqlite-init/
│       └── migrations/
│           └── V004__add_state_table.sql
├── hooks/
│   └── session-start/        ← loads state + injects context on boot
└── .claude-plugin/
    └── plugin.json           ← v1.3.0, namespace: claude-persist
```

**Data flow:**

```
session-start
  → state-updater:load   (SELECT state, seed if missing)
  → context-builder:build (map fields → context block, inject)

post-response
  → state-updater:extract (infer updates from exchange)
  → state-updater:merge   (dot-path patch, guards, UPDATE state)
```

---

## State schema

```json
{
  "project": {
    "name": "",
    "description": "",
    "current_focus": "",
    "stack": []
  },
  "user": {
    "preferences": {
      "response_style": "",
      "verbosity": ""
    }
  },
  "session": {
    "current_task": "",
    "active_context": []
  }
}
```

Single row in SQLite (`state` table, `key = 'global'`). Cross-session — no `session_id`. Size limit: 2KB.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/state` | Show current context block + raw JSON |
| `/state-reset` | Clear state to defaults (asks for confirmation) |
| `/state-edit <json-patch>` | Manually set state fields with dot-path patch |
| `/context-build` | Force rebuild and display context block |

---

## Guards

The `state-updater` runs these checks on every merge:

- **Root key guard** — only `project`, `user`, `session` allowed as top-level keys
- **Size guard** — merged JSON must be < 2048 bytes, or merge is rejected
- **Secret guard** — API keys, tokens, passwords, private keys are rejected (same patterns as `security-auditor`)
- **No-op guard** — empty or unchanged values are skipped silently

---

## Getting started

```bash
git clone <this repo>
cd claude-persist
./tests/plugin-validator    # verify structure passes
claude-code --plugin-dir .  # load plugin in Claude Code
```

First session: `session-start` hook initializes SQLite (running V004 migration), loads state (empty by default), and skips context injection since state is empty. As you work, state fills in automatically.

---

## Extending state

To add a new field to state:

1. Add the field to the default JSON in `V004__add_state_table.sql` (or create a `V005` migration that updates the seed row)
2. Add an extraction rule to `state-updater` (Steps → extract section)
3. Add a mapping line to `context-builder` (Steps → build table)

The `state` table is intentionally simple — no schema migration needed for adding JSON fields.

---

## Inherited from template

This plugin builds on [tpl-claude-plugin](https://github.com/mihir/tpl-claude-plugin). The following components ship unchanged:

**Skills:** security-auditor, agent-team-orchestrator, sqlite-memory, sqlite-query, sqlite-schema-manager, anatomy-indexer, step-verifier, token-ledger, mcp-discovery, computer-use-safety, plugin-dev, self-improver

**Hooks:** file-write (security scan), commit (pre-commit gate), tool-use (Computer Use safety), step-verification (agent step gate)

**Agents:** Planner, Coder, Reviewer, Security, Tester

---

## Compatibility

- Claude Sonnet 4.6 / Opus 4.6+
- VS Code extension, CLI, Cowork
- SQLite 3.38+ (JSON1 built-in)
