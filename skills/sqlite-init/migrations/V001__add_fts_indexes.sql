-- Migration: V001
-- Description: Add FTS5 virtual tables for full-text search on decisions, messages, audit_log
-- Safe to run on: all versions >= 0
-- Data preservation: virtual tables only; no data loss; triggers keep indexes current

BEGIN;

-- ── decisions_fts ────────────────────────────────────────────────────────────
CREATE VIRTUAL TABLE decisions_fts USING fts5(
  summary,
  reasoning,
  content='decisions',
  content_rowid='id'
);

-- Backfill existing rows
INSERT INTO decisions_fts(rowid, summary, reasoning)
  SELECT id, summary, COALESCE(reasoning, '') FROM decisions;

-- Keep in sync on new inserts
CREATE TRIGGER decisions_fts_insert AFTER INSERT ON decisions BEGIN
  INSERT INTO decisions_fts(rowid, summary, reasoning)
    VALUES (new.id, new.summary, COALESCE(new.reasoning, ''));
END;

-- ── messages_fts ─────────────────────────────────────────────────────────────
CREATE VIRTUAL TABLE messages_fts USING fts5(
  content,
  content='messages',
  content_rowid='id'
);

INSERT INTO messages_fts(rowid, content)
  SELECT id, content FROM messages;

CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

-- ── audit_log_fts ────────────────────────────────────────────────────────────
CREATE VIRTUAL TABLE audit_log_fts USING fts5(
  detail,
  target,
  content='audit_log',
  content_rowid='id'
);

INSERT INTO audit_log_fts(rowid, detail, target)
  SELECT id, COALESCE(detail, ''), COALESCE(target, '') FROM audit_log;

CREATE TRIGGER audit_log_fts_insert AFTER INSERT ON audit_log BEGIN
  INSERT INTO audit_log_fts(rowid, detail, target)
    VALUES (new.id, COALESCE(new.detail, ''), COALESCE(new.target, ''));
END;

-- Record migration
INSERT INTO schema_version (version, description) VALUES (1, 'add_fts_indexes');

COMMIT;
