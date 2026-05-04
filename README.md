<div align="center">
  <img src="logo.svg" width="88" height="88" alt="claude-persist" />
  <h1>claude-persist</h1>
  <p><strong>Claude finally remembers your project. You never have to remind it again.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/version-1.4.0-blue?style=flat-square" alt="version" />
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

That block is injected silently before every prompt. You never type it. Claude picks it up from natural conversation over time — and on the very first session, it auto-detects your project from `package.json` and `git log`.

---

## Install

```bash
git clone https://github.com/mihir/claude-persist
cd claude-persist
claude plugin install ./
```

That's it. No config files to edit. No API keys. No setup.

On first session: claude-persist auto-detects your project name, stack, and recent focus from `package.json`, `README.md`, and `git log`. By the time you type your first message, Claude already knows who you are and what you're building.

---

## What's New in v1.4

- **Zero-friction first-run:** Auto-bootstraps project context from `package.json` + `README.md` + `git log` on first session — no setup required
- **Per-project DB isolation:** Each project gets its own DB at `~/.claude/projects/<hash>/plugin.db` — no cross-project bleed
- **`/persist status` dashboard:** One command shows everything Claude knows, DB health, context size, and bootstrap status
- **Unified `/persist` command family:** Six commands replace the scattered 15-command surface — one entry point for daily use
- **anatomy-indexer is now opt-in:** Removed from auto session-start; only runs when you explicitly call `/persist map`
- **Machine-readable hook registry:** `hooks/hooks.json` declares all hooks — no manual settings.json editing

---

## How it works

```
┌─ Session opens ─────────────────────────────────────────────┐
│  1. SQLite DB initializes at ~/.claude/projects/<hash>/     │
│  2. State row read (or bootstrapped from package.json+git)  │
│  3. Context block built and injected before your first msg  │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─ You work normally ─────────────────────────────────────────┐
│  Claude responds with full project context                  │
│  After each turn: signals extracted, state updated          │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─ Next session ──────────────────────────────────────────────┐
│  Picks up exactly where you left off                        │
└─────────────────────────────────────────────────────────────┘
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

### Core commands (`/persist` family)

| Command | What it does |
|---|---|
| `/persist status` | Hero dashboard — project context, DB path, health, bootstrap status |
| `/persist remember <fact>` | Store a fact into project memory |
| `/persist forget <topic>` | Clear a specific memory field |
| `/persist log` | Recent session activity from the audit log |
| `/persist map` | Rebuild the file and symbol index |
| `/persist help` | Show all commands with descriptions |

**See what Claude knows right now:**
```
/persist status
```
```
[claude-persist v1.4]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project:   PayFlow
Stack:     Node.js, Stripe, Postgres
Focus:     Subscription webhook handling
Style:     concise
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context:   4 fields injected  (≈ 210 B of 1024 B limit)
DB:        ~/.claude/projects/a3f8c12d9e44/plugin.db  (40 KB)
Schema:    v5  |  Health: OK  |  Updated: 3 min ago
Bootstrap: Auto-completed — parsed package.json + git log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Fix something Claude got wrong:**
```
/persist remember we use Redis for caching too
/persist forget focus
```

---

### Advanced / power user commands

These commands still work and are documented in their individual skill files:

| Command | What it does |
|---|---|
| `/state` | Raw state inspection with JSON |
| `/state-edit <patch>` | Manual dot-path patch |
| `/state-reset` | Wipe state and start fresh |
| `/sq <query>` | Natural language or SQL against project memory |
| `/orchestrate <task>` | Spawn Planner → Coder → Reviewer → Security → Tester pipeline |
| `/gate <command>` | Block agent progression until a test passes |
| `/security-audit` | Scan staged files for hardcoded secrets |
| `/usage` | Token spend per skill this session |
| `/db-status` | Database health check |
| `/migrate` | Run any pending schema migrations |
| `/self-improve` | Let the plugin refactor itself |

---

## Data and privacy

<table>
<tr>
<td align="center" width="25%"><strong>Fully local</strong><br/>Everything lives in <code>~/.claude/projects/&lt;hash&gt;/plugin.db</code> — per-project, on your machine</td>
<td align="center" width="25%"><strong>No cloud</strong><br/>No accounts, no API calls, no telemetry. Just SQLite on your machine</td>
<td align="center" width="25%"><strong>Never committed</strong><br/>The database is outside your project tree — it can't be accidentally committed</td>
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
   (or create a `V006` migration for existing installs)
2. Add an extraction rule in `skills/state-updater/SKILL.md`
3. Add a render mapping in `skills/context-builder/SKILL.md`

**Plugin structure:**
```
.claude-plugin/plugin.json   ← manifest (name, version, author, hooks pointer)
hooks/hooks.json             ← machine-readable hook registry
skills/                      ← slash commands (one folder = one command)
hooks/                       ← lifecycle events (session-start, file-write, commit)
agents/                      ← Planner, Coder, Reviewer, Security, Tester
skills/sqlite-init/
  schema.sql                 ← baseline DB schema
  migrations/                ← versioned migrations (V001–V005)
```
