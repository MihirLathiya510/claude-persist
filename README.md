<div align="center">
  <img src="logo.svg" width="88" height="88" alt="claude-persist" />
  <h1>claude-persist</h1>
  <p><strong>Claude forgets everything when you close the tab. This plugin fixes that.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/version-1.3.0-blue?style=flat-square" alt="version" />
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="license" />
    <img src="https://img.shields.io/badge/tests-488%20passing-brightgreen?style=flat-square" alt="tests" />
    <img src="https://img.shields.io/badge/SQLite-3.38%2B-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="sqlite" />
    <img src="https://img.shields.io/badge/Claude-Sonnet%204.6%2B-orange?style=flat-square" alt="claude" />
  </p>
  <p>
    Every session you start fresh — re-explaining your project, your stack, what you were working on.<br/>
    claude-persist makes Claude remember all of it automatically, from natural conversation.<br/>
    No config. No commands. Just works.
  </p>
</div>

---

## Before / After

<table>
<tr>
<td width="50%" valign="top">

**Without claude-persist — every session:**
```
You: I'm working on a Node.js app with Postgres
     and Stripe webhooks. Keep your answers concise.
     I'm trying to fix a retry bug in the webhook
     handler...
```

</td>
<td width="50%" valign="top">

**With claude-persist — Claude already knows:**
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

</td>
</tr>
</table>

That block is injected silently before every prompt. You never type it. Claude picks it up from natural conversation over time.

---

## Install

```bash
git clone https://github.com/mihir/claude-persist
cd claude-persist
claude plugin install ./
```

That's it. No config files to edit. No API keys. No setup.

On first session: claude-persist initializes its SQLite database and waits. As you work, it quietly learns your project. By session two, Claude already knows who you are and what you're building.

---

## How it works

```
┌─ Session opens ─────────────────────────────────────────┐
│  1. SQLite DB initializes (or loads from last session)  │
│  2. State row read → context block built                │
│  3. Block injected before your first prompt             │
└─────────────────────────────────────────────────────────┘
         ↓
┌─ You work normally ─────────────────────────────────────┐
│  Claude responds with full project context              │
│  After each turn: signals extracted, state updated      │
└─────────────────────────────────────────────────────────┘
         ↓
┌─ Next session ──────────────────────────────────────────┐
│  Picks up exactly where you left off                    │
└─────────────────────────────────────────────────────────┘
```

**Why auto-extract instead of asking you to configure it?** Because the best memory system is one you never have to think about. If you have to run a command to save context, you won't. claude-persist listens instead.

The context block is always ≤ 10 lines and ≤ 1KB — small enough to never bloat your token budget.

---

## What Claude learns automatically

| What you say | What gets stored |
|---|---|
| `"I'm building a billing app called PayFlow"` | `project.name = "PayFlow"` |
| `"We use Node.js, Stripe, and Postgres"` | `project.stack = ["Node.js", "Stripe", "Postgres"]` |
| `"Right now I'm focused on webhook retries"` | `project.current_focus = "webhook retries"` |
| `"Keep answers concise"` | `user.preferences.response_style = "concise"` |
| `"Help me fix the failing payment intent handler"` | `session.current_task = "Fix payment intent handler"` |

---

## Commands

### Inspect and correct state

| Command | What it does |
|---|---|
| `/state` | See exactly what Claude currently remembers |
| `/state-edit <patch>` | Correct or add something manually |
| `/state-reset` | Wipe the slate and start fresh |
| `/context-build` | Force a context block refresh |

**See what Claude knows right now:**
```
/state
```
```
[claude-persist]
Project: PayFlow
Stack: Node.js, Stripe, Postgres
Style: concise
---

Raw state (updated 3 minutes ago):
{ "project": { "name": "PayFlow", ... } }
```

**Fix something Claude got wrong:**
```
/state-edit {"project.stack": ["Node.js", "Stripe", "Postgres", "Redis"]}
```

### Query project memory

| Command | What it does |
|---|---|
| `/sq <query>` | Natural language or SQL against your project's memory |

```
/sq show me all decisions made in the last 3 sessions
/sq select * from state
```

### Agent team

| Command | What it does |
|---|---|
| `/orchestrate <task>` | Spawn Planner → Coder → Reviewer → Security → Tester pipeline |
| `/gate <command>` | Block agent progression until a test command passes |

### Code quality

| Command | What it does |
|---|---|
| `/security-audit` | Scan staged files for hardcoded secrets |

Every file write and commit is scanned automatically. This runs without being called.

### Project tools

| Command | What it does |
|---|---|
| `/map` | Rebuild the file and symbol index |
| `/usage` | Token spend per skill this session |
| `/db-status` | Database health check |
| `/migrate` | Run any pending schema migrations |
| `/self-improve` | Let the plugin refactor itself |

---

## Data and privacy

<table>
<tr>
<td align="center" width="25%"><strong>Fully local</strong><br/>Everything lives in <code>.claude-plugin/db/plugin.db</code> inside your project</td>
<td align="center" width="25%"><strong>No cloud</strong><br/>No accounts, no API calls, no telemetry. Just SQLite on your machine</td>
<td align="center" width="25%"><strong>Gitignored</strong><br/>The database is never committed. Your context stays private</td>
<td align="center" width="25%"><strong>Capped at 2KB</strong><br/>Claude learns what matters, not everything</td>
</tr>
</table>

---

## Compatibility

| Platform | Support |
|---|---|
| Claude Code CLI | ✓ |
| VS Code extension | ✓ |
| Claude.ai | ✓ |
| Claude Sonnet 4.6 / Opus 4.6+ | ✓ |
| SQLite 3.38+ | required — ships with macOS and most Linux distributions |

---

## For developers

```bash
python3 tests/integration-tests.py   # 276 tests — schema, state, security, structure
python3 tests/user-flow-tests.py     # 106 tests — end-to-end user scenarios
bash tests/plugin-validator          # structural completeness check
```

**Add a new remembered field:**
1. Add it to the default JSON in `skills/sqlite-init/migrations/V004__add_state_table.sql`
   (or create a `V005` migration for existing installs)
2. Add an extraction rule in `skills/state-updater/SKILL.md`
3. Add a render mapping in `skills/context-builder/SKILL.md`

**Plugin structure:**
```
.claude-plugin/plugin.json   ← manifest (name, version, author)
skills/                      ← slash commands (one folder = one command)
hooks/                       ← lifecycle events (session-start, file-write, commit)
agents/                      ← Planner, Coder, Reviewer, Security, Tester
skills/sqlite-init/
  schema.sql                 ← baseline DB schema
  migrations/                ← versioned migrations (V001–V004)
```
