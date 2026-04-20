-- tpl-claude-plugin baseline schema
-- Applied once on first run inside a single transaction.
-- DO NOT modify this file after release — use migrations/ instead.

BEGIN;

-- ── schema_version ────────────────────────────────────────────────────────────
CREATE TABLE schema_version (
  version     INTEGER PRIMARY KEY,
  description TEXT NOT NULL,
  applied_at  INTEGER NOT NULL DEFAULT (unixepoch()),
  checksum    TEXT
);
INSERT INTO schema_version (version, description) VALUES (0, 'baseline');

-- ── decisions ────────────────────────────────────────────────────────────────
-- Persistent agent reasoning and decisions across sessions.
CREATE TABLE decisions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT NOT NULL,
  agent       TEXT NOT NULL,
  summary     TEXT NOT NULL,
  reasoning   TEXT,
  confidence  REAL CHECK (confidence BETWEEN 0 AND 1),
  metadata    TEXT CHECK (json_valid(metadata) OR metadata IS NULL),
  created_at  INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX idx_decisions_session ON decisions(session_id);
CREATE INDEX idx_decisions_agent   ON decisions(agent);
CREATE INDEX idx_decisions_created ON decisions(created_at DESC);

-- ── tasks ────────────────────────────────────────────────────────────────────
-- Planner task lists; hierarchical via parent_task_id.
CREATE TABLE tasks (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id     TEXT NOT NULL,
  title          TEXT NOT NULL,
  description    TEXT,
  assignee       TEXT NOT NULL,
  status         TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','in-progress','blocked','done','cancelled')),
  parent_task_id INTEGER REFERENCES tasks(id),
  metadata       TEXT CHECK (json_valid(metadata) OR metadata IS NULL),
  created_at     INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at     INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX idx_tasks_session    ON tasks(session_id);
CREATE INDEX idx_tasks_assignee   ON tasks(assignee);
CREATE INDEX idx_tasks_status     ON tasks(status);
CREATE INDEX idx_tasks_parent     ON tasks(parent_task_id);

-- ── messages ──────────────────────────────────────────────────────────────────
-- Inter-agent channel messages persisted for search and audit.
CREATE TABLE messages (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('user','assistant','agent','system')),
  agent       TEXT,
  channel     TEXT NOT NULL DEFAULT 'main'
              CHECK (channel IN ('main','security','review')),
  content     TEXT NOT NULL,
  metadata    TEXT CHECK (json_valid(metadata) OR metadata IS NULL),
  created_at  INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_channel ON messages(channel);
CREATE INDEX idx_messages_agent   ON messages(agent);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- ── audit_log ────────────────────────────────────────────────────────────────
-- Immutable append-only event record. No UPDATE or DELETE is permitted.
CREATE TABLE audit_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT NOT NULL,
  event_type  TEXT NOT NULL
              CHECK (event_type IN (
                'hook-trigger','security-violation','tool-call',
                'commit','skill-invoke','config-change'
              )),
  severity    TEXT CHECK (severity IN ('info','warning','critical')),
  actor       TEXT,
  target      TEXT,
  detail      TEXT,
  metadata    TEXT CHECK (json_valid(metadata) OR metadata IS NULL),
  created_at  INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX idx_audit_session  ON audit_log(session_id);
CREATE INDEX idx_audit_event    ON audit_log(event_type);
CREATE INDEX idx_audit_severity ON audit_log(severity);
CREATE INDEX idx_audit_created  ON audit_log(created_at DESC);

-- ── usage_stats ───────────────────────────────────────────────────────────────
-- Per-session, per-skill token and invocation analytics.
CREATE TABLE usage_stats (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id       TEXT NOT NULL,
  skill            TEXT NOT NULL,
  invocation_count INTEGER NOT NULL DEFAULT 1,
  input_tokens     INTEGER NOT NULL DEFAULT 0,
  output_tokens    INTEGER NOT NULL DEFAULT 0,
  cache_hits       INTEGER NOT NULL DEFAULT 0,
  error_count      INTEGER NOT NULL DEFAULT 0,
  recorded_at      INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX idx_usage_session  ON usage_stats(session_id);
CREATE INDEX idx_usage_skill    ON usage_stats(skill);
CREATE INDEX idx_usage_recorded ON usage_stats(recorded_at DESC);

COMMIT;
