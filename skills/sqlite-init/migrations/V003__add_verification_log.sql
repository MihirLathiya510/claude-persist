-- Migration: V003
-- Description: Add verification_log table for step-verification gate results
-- Safe to run on: all versions >= 2
-- Data preservation: new table only; no existing data affected

BEGIN;

CREATE TABLE verification_log (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id        TEXT NOT NULL,
  agent             TEXT NOT NULL,
  test_command      TEXT NOT NULL,
  verification_type TEXT NOT NULL
                    CHECK (verification_type IN ('exit-code','output-contains','regex-match')),
  expected_result   TEXT NOT NULL,
  actual_result     TEXT,
  passed            INTEGER NOT NULL CHECK (passed IN (0, 1)),
  exit_code         INTEGER,
  stdout            TEXT,
  stderr            TEXT,
  duration_ms       INTEGER,
  retries_used      INTEGER NOT NULL DEFAULT 0,
  created_at        INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX idx_verif_session ON verification_log(session_id);
CREATE INDEX idx_verif_passed  ON verification_log(passed);
CREATE INDEX idx_verif_agent   ON verification_log(agent);
CREATE INDEX idx_verif_created ON verification_log(created_at DESC);

INSERT INTO schema_version (version, description) VALUES (3, 'add_verification_log');

COMMIT;
