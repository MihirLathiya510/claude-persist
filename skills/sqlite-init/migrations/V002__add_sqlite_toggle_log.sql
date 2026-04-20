-- Migration: V002
-- Description: Add toggle_history table to audit sqlite enable/disable events
-- Safe to run on: all versions >= 1
-- Data preservation: new table only; no existing data affected

BEGIN;

CREATE TABLE toggle_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  action     TEXT NOT NULL CHECK (action IN ('enabled','disabled')),
  actor      TEXT NOT NULL DEFAULT 'user',
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX idx_toggle_created ON toggle_history(created_at DESC);

INSERT INTO schema_version (version, description) VALUES (2, 'add_sqlite_toggle_log');

COMMIT;
