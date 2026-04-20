-- Migration: V004
-- Description: Add state table for persistent cross-session context engine (claude-persist)
-- Safe to run on: all versions >= 3
-- Data preservation: new table only; no existing data affected

BEGIN;

-- ── state ─────────────────────────────────────────────────────────────────────
-- Single-row key/value store for the persistent context engine.
-- key is always 'global'. value is a JSON object validated at write time.
-- No session_id — this table is intentionally cross-session.
-- Only claude-persist:state-updater may write to this table.
CREATE TABLE state (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL CHECK (json_valid(value)),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Seed the single global row with empty-but-valid default state.
-- All fields start empty; state-updater populates them from real exchanges.
INSERT INTO state (key, value) VALUES (
  'global',
  json('{"project":{"name":"","description":"","current_focus":"","stack":[]},"user":{"preferences":{"response_style":"","verbosity":""}},"session":{"current_task":"","active_context":[]}}')
);

INSERT INTO schema_version (version, description) VALUES (4, 'add_state_table');

COMMIT;
