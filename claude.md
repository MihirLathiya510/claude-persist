# tpl-claude-plugin

A Claude Code plugin template with agent teams, persistent SQLite memory, MCP-first tooling, context intelligence, and a self-validating structure.

## Built-in Components

1. **Skills** — core primitive
   - Location: `skills/<kebab-name>/SKILL.md`
   - Progressive disclosure: YAML frontmatter (always loaded) → body (on-demand) → references (lazy)
   - Namespace: `tpl-claude-plugin:<skill-name>`
   - Active skills: security-auditor, agent-team-orchestrator, computer-use-safety, self-improver, mcp-discovery, plugin-dev, sqlite-init, sqlite-query, sqlite-memory, sqlite-schema-manager, anatomy-indexer, step-verifier, token-ledger

2. **Agent Teams**
   - Use for any task touching > 3 files or any refactoring.
   - Roles in `agents/`: Planner, Coder, Reviewer, Security, Tester.
   - Trigger: `agent-team-orchestrator` skill or `/orchestrate`.

3. **MCP-First Tooling**
   - Prefer MCP servers (discovery via `.mcp.json`).
   - Fallback to Computer Use only when no MCP covers the capability.

4. **Computer Use**
   - Always route through `computer-use-safety` skill.
   - Human confirmation required. 30s timeout. Sandbox recommended.

5. **Hooks**
   - `hooks/<event>/HOOK.md` for: `file-write`, `commit`, `tool-use`, `session-start`, `step-verification`.
   - Security-auditor runs automatically on every write and commit.
   - SQLite audit_log is written on every hook trigger and commit.

6. **SQLite Memory**
   - DB at `.claude-plugin/db/plugin.db` (excluded from git).
   - Schema: decisions, tasks, messages, audit_log, usage_stats, schema_version, verification_log.
   - FTS5 search on decisions, messages, audit_log.
   - Migrations in `skills/sqlite-init/migrations/` (V[N]__description.sql).
   - Reviewer and Security agents are read-only. audit_log is append-only.

7. **Anatomy Indexer**
   - Runs at session start; builds `.claude-plugin/PROJECT_MAP.json`.
   - Maps every source file's symbols (functions, classes, exports) with line numbers.
   - Agents check the map before opening files — eliminates redundant reads.
   - Refresh manually with `/map`.

8. **Step-Verification Gate**
   - Disabled by default. Enable via `stepVerification.enabled` in plugin.json.
   - Agent calls `/gate <command>` after each step; blocked until test passes.
   - Logs all results (pass/fail/timing/retries) to `verification_log`.
   - Configurable: `maxRetries` (default 3), `timeoutMs` (default 30000).

9. **Token Ledger**
   - Run `/usage` or `/burn` to see per-skill token spend for the current session.
   - Shows: invocations, input/output tokens, cache hit %, error rate, % of session total.
   - Save a report with `/usage --save`.

10. **plugin.json**
    - Source of truth for all capabilities. Keep in sync with files on disk.
    - Semantic versioning only. Validator enforces this.

## Decision Tree

- 1 file change → single Skill
- 3+ files or refactor → `/orchestrate` (Agent Team)
- External tool needed → MCP first, Computer Use as fallback
- Any write or commit → security-auditor runs automatically
- Plugin needs improvement → `/self-improve`
- Add a skill → `/plugin-dev:create-micro-skill`
- Check DB health → `/db-status`
- Refresh file index → `/map`
- Verify a step → `/gate <test-command>`
- Check token spend → `/usage`

## Constraints

- Every write/commit triggers security-auditor. No exceptions.
- Computer Use always has human-in-the-loop.
- `tests/plugin-validator` must pass before any release.
- Skill frontmatter is always loaded; never put heavy context there.
- Context budget: < 8k tokens per session.
- `stepVerification` is opt-in — enable per project in plugin.json.

## Compatibility

- Claude Sonnet 4.6 / Opus 4.6+
- VS Code extension, CLI, Cowork
- SQLite 3.38+ (JSON1 + FTS5 built-in)
