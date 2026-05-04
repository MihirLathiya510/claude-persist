-- Migration: V005
-- Description: Record per-project DB path change (path logic handled at skill layer)
-- The actual DB relocation (from .claude-plugin/db/ to ~/.claude/projects/<hash>/)
-- is implemented in sqlite-init SKILL.md step 1. This entry is the schema version
-- bookmark that confirms the migration has been applied.
-- Safe to run on: all versions >= 4
-- Data preservation: no schema changes; bookmark only

BEGIN;

INSERT INTO schema_version (version, description) VALUES (5, 'per_project_db');

COMMIT;
