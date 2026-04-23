---
name: plugin-dev
description: Developer tooling for creating new micro-skills and extending the plugin
---

## Usage

Primary command: `/plugin-dev:create-micro-skill`

Scaffolds a new micro-skill with correct frontmatter, registers it in `plugin.json`, and runs the validator.

## Steps

1. Prompt user for:
   - Skill name (must be kebab-case, e.g. `rate-limiter`)
   - One-sentence description
   - Trigger list (comma-separated slash commands or event names)
2. Validate name is kebab-case; reject if not.
3. Auto-construct namespace: `claude-persist:<skill-name>`.
4. Scaffold `skills/<skill-name>/SKILL.md` with frontmatter only (body left empty for the developer to fill in).
5. Verify `skills/<skill-name>/SKILL.md` was written correctly (frontmatter present, no extra keys).
6. Invoke `tpl-claude-plugin:security-auditor` on the two written files.
7. Run `tests/plugin-validator`; surface any failures before reporting success.

## Scaffolded SKILL.md Template

```markdown
---
name: <skill-name>
description: <description>
---

## Usage

<!-- Describe when and how this skill is invoked -->

## Steps

<!-- Step-by-step execution logic -->

## Examples

<!-- Usage examples -->

<!-- References (lazy) -->
```

## Examples

```
/plugin-dev:create-micro-skill
> Skill name: rate-limiter
> Description: Enforces rate limits on outbound API calls
> Triggers: /rate-limit, on-api-call
> Creating skills/rate-limiter/SKILL.md...
> Updating .claude-plugin/plugin.json...
> [security-auditor] PASS
> [plugin-validator] All checks passed.
> Skill claude-persist:rate-limiter created successfully.
```

## Constraints

- New skills **must not** write to the `state` table directly. Only `claude-persist:state-updater` may write to `state`. If a new skill needs to update project/user/session context, it must call `state-updater` with a dot-path patch, not issue its own SQL against `state`.

<!-- References (lazy) -->
- `tpl-claude-plugin:security-auditor`
- `claude-persist:state-updater`
- `.claude-plugin/plugin.json`
- `tests/plugin-validator`
