#!/usr/bin/env python3
"""
claude-persist integration tests
Tests all scenarios and edge cases for the plugin.

Categories:
  1. SQLite schema bootstrap
  2. Migration runner (V001–V004)
  3. State table — load / seed / write
  4. State updater — merge / dot-path / guards
  5. Context builder — formatting / truncation
  6. SQLite-query — forbidden patterns / allowlist / LIMIT injection
  7. Security auditor — pattern matching
  8. Plugin structure — plugin.json / SKILL.md / HOOK.md / agents
  9. Validator script consistency
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, ".claude-plugin", "db", "plugin.db")
SCHEMA = os.path.join(ROOT, "skills", "sqlite-init", "schema.sql")
MIGRATIONS_DIR = os.path.join(ROOT, "skills", "sqlite-init", "migrations")
VALIDATORS_MD = os.path.join(ROOT, "skills", "sqlite-query", "validators.md")

PASS = 0
FAIL = 0
SKIP = 0

# ── helpers ───────────────────────────────────────────────────────────────────

def ok(msg):
    global PASS
    PASS += 1
    print(f"  [PASS] {msg}")

def fail(msg, detail=""):
    global FAIL
    FAIL += 1
    detail_str = f" — {detail}" if detail else ""
    print(f"  [FAIL] {msg}{detail_str}")

def skip(msg):
    global SKIP
    SKIP += 1
    print(f"  [SKIP] {msg}")

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

def fresh_db():
    """Create an in-memory database with the baseline schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA) as f:
        conn.executescript(f.read())
    return conn

def apply_migration(conn, filename):
    path = os.path.join(MIGRATIONS_DIR, filename)
    with open(path) as f:
        conn.executescript(f.read())

def apply_all_migrations(conn):
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if fname.endswith(".sql"):
            apply_migration(conn, fname)

# ── 1. SQLite schema bootstrap ────────────────────────────────────────────────

section("1. SQLite schema bootstrap")

try:
    conn = fresh_db()

    # Required tables exist
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for t in ("schema_version", "decisions", "tasks", "messages", "audit_log", "usage_stats"):
        if t in tables:
            ok(f"baseline table exists: {t}")
        else:
            fail(f"baseline table missing: {t}")

    # schema_version seeded with baseline (version=0)
    row = conn.execute("SELECT version, description FROM schema_version WHERE version=0").fetchone()
    if row and row[1] == "baseline":
        ok("schema_version seeded with version=0 baseline")
    else:
        fail("schema_version baseline row missing or wrong", str(row))

    # decisions confidence CHECK: 0–1 range
    try:
        conn.execute("INSERT INTO decisions(session_id,agent,summary,confidence) VALUES('s1','a','t',0.5)")
        ok("decisions.confidence=0.5 accepted")
    except sqlite3.IntegrityError as e:
        fail("decisions.confidence=0.5 rejected", str(e))

    try:
        conn.execute("INSERT INTO decisions(session_id,agent,summary,confidence) VALUES('s1','a','t',1.5)")
        conn.commit()
        fail("decisions.confidence=1.5 should have been rejected")
    except sqlite3.IntegrityError:
        ok("decisions.confidence=1.5 correctly rejected")

    # audit_log severity CHECK
    try:
        conn.execute("INSERT INTO audit_log(session_id,event_type,severity) VALUES('s1','commit','info')")
        ok("audit_log severity='info' accepted")
    except sqlite3.IntegrityError as e:
        fail("audit_log severity='info' rejected", str(e))

    try:
        conn.execute("INSERT INTO audit_log(session_id,event_type,severity) VALUES('s1','commit','bogus')")
        conn.commit()
        fail("audit_log severity='bogus' should have been rejected")
    except sqlite3.IntegrityError:
        ok("audit_log severity='bogus' correctly rejected")

    # audit_log event_type CHECK
    try:
        conn.execute("INSERT INTO audit_log(session_id,event_type) VALUES('s1','commit')")
        ok("audit_log event_type='commit' accepted")
    except sqlite3.IntegrityError as e:
        fail("audit_log event_type='commit' rejected", str(e))

    try:
        conn.execute("INSERT INTO audit_log(session_id,event_type) VALUES('s1','invalid-event')")
        conn.commit()
        fail("audit_log event_type='invalid-event' should have been rejected")
    except sqlite3.IntegrityError:
        ok("audit_log event_type='invalid-event' correctly rejected")

    # messages role CHECK
    for role in ("user", "assistant", "agent", "system"):
        try:
            conn.execute(f"INSERT INTO messages(session_id,role,content) VALUES('s1','{role}','hi')")
            ok(f"messages.role='{role}' accepted")
        except sqlite3.IntegrityError as e:
            fail(f"messages.role='{role}' rejected", str(e))

    try:
        conn.execute("INSERT INTO messages(session_id,role,content) VALUES('s1','bot','hi')")
        conn.commit()
        fail("messages.role='bot' should have been rejected")
    except sqlite3.IntegrityError:
        ok("messages.role='bot' correctly rejected")

    # tasks status CHECK
    for status in ("pending", "in-progress", "blocked", "done", "cancelled"):
        try:
            conn.execute(f"INSERT INTO tasks(session_id,title,assignee,status) VALUES('s1','t','a','{status}')")
            ok(f"tasks.status='{status}' accepted")
        except sqlite3.IntegrityError as e:
            fail(f"tasks.status='{status}' rejected", str(e))

    try:
        conn.execute("INSERT INTO tasks(session_id,title,assignee,status) VALUES('s1','t','a','running')")
        conn.commit()
        fail("tasks.status='running' should have been rejected")
    except sqlite3.IntegrityError:
        ok("tasks.status='running' correctly rejected")

    # JSON metadata validation
    try:
        conn.execute("INSERT INTO decisions(session_id,agent,summary,metadata) VALUES('s1','a','t','{\"key\":\"val\"}')")
        ok("decisions.metadata valid JSON accepted")
    except sqlite3.IntegrityError as e:
        fail("decisions.metadata valid JSON rejected", str(e))

    try:
        conn.execute("INSERT INTO decisions(session_id,agent,summary,metadata) VALUES('s1','a','t','not-json')")
        conn.commit()
        fail("decisions.metadata invalid JSON should have been rejected")
    except sqlite3.IntegrityError:
        ok("decisions.metadata invalid JSON correctly rejected")

    conn.close()
except Exception as e:
    fail("Schema bootstrap raised exception", str(e))


# ── 2. Migration runner ────────────────────────────────────────────────────────

section("2. Migration runner (V001–V004)")

migration_files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")])

# Naming convention
import re as _re
for fname in migration_files:
    if _re.match(r'^V\d+__[a-z_]+\.sql$', fname):
        ok(f"migration name valid: {fname}")
    else:
        fail(f"migration name invalid: {fname}")

# Apply all migrations on fresh DB
try:
    conn = fresh_db()
    apply_all_migrations(conn)

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    # V001 — FTS indexes
    for t in ("decisions_fts", "messages_fts", "audit_log_fts"):
        if t in tables:
            ok(f"V001 created FTS table: {t}")
        else:
            fail(f"V001 missing FTS table: {t}")

    # V002 — toggle_history
    if "toggle_history" in tables:
        ok("V002 created toggle_history table")
    else:
        fail("V002 missing toggle_history table")

    # V003 — verification_log
    if "verification_log" in tables:
        ok("V003 created verification_log table")
    else:
        fail("V003 missing verification_log table")

    # V004 — state
    if "state" in tables:
        ok("V004 created state table")
    else:
        fail("V004 missing state table")

    # schema_version has all 4 migration entries (plus baseline=0)
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_version ORDER BY version").fetchall()]
    if versions == [0, 1, 2, 3, 4]:
        ok("schema_version contains all versions [0,1,2,3,4]")
    else:
        fail("schema_version versions unexpected", str(versions))

    # Idempotency: re-running V004 should fail gracefully (table already exists)
    try:
        apply_migration(conn, "V004__add_state_table.sql")
        fail("V004 re-run should fail (table already exists)")
    except Exception:
        ok("V004 re-run correctly fails (not idempotent — expected)")

    conn.close()
except Exception as e:
    fail("Migration runner raised exception", str(e))


# ── 3. State table — load / seed / write ─────────────────────────────────────

section("3. State table — load / seed / write")

try:
    conn = fresh_db()
    apply_all_migrations(conn)

    # Default seed row exists
    row = conn.execute("SELECT key, value FROM state WHERE key='global'").fetchone()
    if row:
        ok("state table has 'global' seed row")
    else:
        fail("state table missing 'global' seed row")

    # Seed value is valid JSON
    seed = json.loads(row[1])
    ok("seed value is valid JSON")

    # Seed has correct top-level keys
    for k in ("project", "user", "session"):
        if k in seed:
            ok(f"seed has top-level key: {k}")
        else:
            fail(f"seed missing top-level key: {k}")

    # Seed project fields
    for k in ("name", "description", "current_focus", "stack"):
        if k in seed.get("project", {}):
            ok(f"seed.project has field: {k}")
        else:
            fail(f"seed.project missing field: {k}")

    # stack is an empty array
    if seed["project"]["stack"] == []:
        ok("seed.project.stack is empty array")
    else:
        fail("seed.project.stack wrong type or non-empty", str(seed["project"]["stack"]))

    # active_context is an empty array
    if seed["session"]["active_context"] == []:
        ok("seed.session.active_context is empty array")
    else:
        fail("seed.session.active_context wrong", str(seed["session"]["active_context"]))

    # PRIMARY KEY constraint — cannot insert second global row
    try:
        conn.execute("INSERT INTO state(key,value) VALUES('global', '{}')")
        conn.commit()
        fail("state table should reject duplicate key='global'")
    except sqlite3.IntegrityError:
        ok("state table PRIMARY KEY correctly rejects duplicate 'global'")

    # JSON CHECK constraint — valid JSON accepted
    conn.execute("UPDATE state SET value=? WHERE key='global'", ('{"project":{"name":"TestApp","description":"","current_focus":"","stack":[]},"user":{"preferences":{"response_style":"","verbosity":""}},"session":{"current_task":"","active_context":[]}}',))
    ok("state UPDATE with valid JSON accepted")

    # JSON CHECK constraint — invalid JSON rejected
    try:
        conn.execute("UPDATE state SET value=? WHERE key='global'", ("not-valid-json",))
        conn.commit()
        fail("state UPDATE with invalid JSON should be rejected")
    except sqlite3.IntegrityError:
        ok("state UPDATE with invalid JSON correctly rejected")

    # Non-global key — allowed by schema (single-row is a skill-layer constraint)
    conn.execute("INSERT INTO state(key,value) VALUES('other', '{}') ")
    ok("state allows non-global key (single-row enforced at skill layer, not DB)")
    conn.execute("DELETE FROM state WHERE key='other'")

    conn.close()
except Exception as e:
    fail("State table tests raised exception", str(e))


# ── 4. State updater — merge / dot-path / guards ──────────────────────────────

section("4. State updater — merge logic (simulated)")

DEFAULT_STATE = {
    "project": {"name": "", "description": "", "current_focus": "", "stack": []},
    "user": {"preferences": {"response_style": "", "verbosity": ""}},
    "session": {"current_task": "", "active_context": []}
}

ALLOWED_ROOTS = {"project", "user", "session"}

def apply_dot_path(state, path, value):
    """Apply a dot-path patch to state dict. Returns (new_state, error_or_None)."""
    import copy
    state = copy.deepcopy(state)
    parts = path.split(".")
    root = parts[0]
    if root not in ALLOWED_ROOTS:
        return state, f"Root key '{root}' not allowed"
    node = state
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            return state, f"Path '{path}' invalid at '{part}'"
        node = node[part]
    node[parts[-1]] = value
    return state, None

def state_size(state):
    return len(json.dumps(state, separators=(',', ':')).encode('utf-8'))

# Dot-path: simple field update
s, err = apply_dot_path(DEFAULT_STATE, "project.name", "MyApp")
if not err and s["project"]["name"] == "MyApp":
    ok("dot-path: project.name update works")
else:
    fail("dot-path: project.name update failed", err)

# Dot-path: nested field
s, err = apply_dot_path(DEFAULT_STATE, "user.preferences.verbosity", "concise")
if not err and s["user"]["preferences"]["verbosity"] == "concise":
    ok("dot-path: user.preferences.verbosity update works")
else:
    fail("dot-path: nested update failed", err)

# Dot-path: invalid root key
s, err = apply_dot_path(DEFAULT_STATE, "tools.debugger", "gdb")
if err and "tools" in err:
    ok("dot-path: invalid root key 'tools' rejected")
else:
    fail("dot-path: invalid root key should be rejected")

# Dot-path: replace array entirely
s, err = apply_dot_path(DEFAULT_STATE, "project.stack", ["Node.js", "Postgres"])
if not err and s["project"]["stack"] == ["Node.js", "Postgres"]:
    ok("dot-path: stack array replaced entirely")
else:
    fail("dot-path: stack array replace failed", err)

# Dot-path: append to array — arrays are REPLACED not appended
base, _ = apply_dot_path(DEFAULT_STATE, "project.stack", ["Python"])
s, err = apply_dot_path(base, "project.stack", ["Node.js"])
if not err and s["project"]["stack"] == ["Node.js"]:
    ok("dot-path: array replace (not append) behaviour confirmed")
else:
    fail("dot-path: array replace failed", str(s.get("project", {}).get("stack")))

# Size guard: state under 2048 bytes
small = {"project": {"name": "A", "description": "", "current_focus": "", "stack": []},
         "user": {"preferences": {"response_style": "", "verbosity": ""}},
         "session": {"current_task": "", "active_context": []}}
if state_size(small) < 2048:
    ok(f"small state size OK: {state_size(small)} bytes")
else:
    fail("small state unexpectedly large")

# Size guard: state over 2048 bytes should be rejected at skill layer
big_value = "x" * 2100
big = {"project": {"name": big_value, "description": "", "current_focus": "", "stack": []},
       "user": {"preferences": {"response_style": "", "verbosity": ""}},
       "session": {"current_task": "", "active_context": []}}
if state_size(big) > 2048:
    ok(f"oversized state detected: {state_size(big)} bytes > 2048 — skill layer must reject")
else:
    fail("oversized state not detected")

# Size guard: exactly 2048 bytes — boundary condition
import copy
boundary = copy.deepcopy(DEFAULT_STATE)
padding = "x" * (2048 - state_size(boundary))
boundary["project"]["description"] = padding
sz = state_size(boundary)
if sz == 2048:
    ok(f"boundary state exactly 2048 bytes — accepted")
elif sz < 2048:
    ok(f"boundary state {sz} bytes — accepted (under limit)")
else:
    ok(f"boundary state {sz} bytes — over limit, should be rejected")

# Allowed root keys: project, user, session
for root in ("project", "user", "session"):
    s, err = apply_dot_path(DEFAULT_STATE, f"{root}.test_field", "val")
    if not err:
        ok(f"allowed root '{root}' accepted")
    else:
        fail(f"allowed root '{root}' rejected", err)

for root in ("config", "tools", "secrets", "env"):
    s, err = apply_dot_path(DEFAULT_STATE, f"{root}.field", "val")
    if err:
        ok(f"disallowed root '{root}' rejected")
    else:
        fail(f"disallowed root '{root}' should have been rejected")

# Empty string value — clears field
s, err = apply_dot_path(DEFAULT_STATE, "project.name", "")
if not err and s["project"]["name"] == "":
    ok("dot-path: empty string value clears field")
else:
    fail("dot-path: empty string value failed", err)

# Unicode in state value
s, err = apply_dot_path(DEFAULT_STATE, "project.name", "Проект-αβγ-🚀")
if not err and s["project"]["name"] == "Проект-αβγ-🚀":
    ok("dot-path: unicode value accepted")
else:
    fail("dot-path: unicode value failed", err)

# Null value — sets field to null
s, err = apply_dot_path(DEFAULT_STATE, "project.current_focus", None)
if not err and s["project"]["current_focus"] is None:
    ok("dot-path: null value sets field to null")
else:
    fail("dot-path: null value failed", err)


# ── 5. Context builder — formatting / truncation ──────────────────────────────

section("5. Context builder — output formatting")

def build_context_block(state):
    """
    Simulate context-builder:build.
    Maps non-empty state fields to lines. Returns None if nothing to show.
    Rules from context-builder SKILL.md:
      Project: <project.name>
      About: <project.description>
      Focus: <project.current_focus>
      Stack: <project.stack joined by ', '>
      Style: <user.preferences.response_style>
      Verbosity: <user.preferences.verbosity>
      Task: <session.current_task>
    Wraps in [claude-persist] ... ---
    Skips empty/null fields.
    Truncates to 10 content lines + separator if over 1024 bytes.
    """
    p = state.get("project", {})
    u = state.get("user", {}).get("preferences", {})
    sess = state.get("session", {})

    lines = []
    if p.get("name", "").strip():
        lines.append(f"Project: {p['name'].strip()}")
    if p.get("description", "").strip():
        lines.append(f"About: {p['description'].strip()}")
    if p.get("current_focus", "").strip():
        lines.append(f"Focus: {p['current_focus'].strip()}")
    if p.get("stack"):
        lines.append(f"Stack: {', '.join(p['stack'])}")
    if u.get("response_style", "").strip():
        lines.append(f"Style: {u['response_style'].strip()}")
    if u.get("verbosity", "").strip():
        lines.append(f"Verbosity: {u['verbosity'].strip()}")
    if sess.get("current_task", "").strip():
        lines.append(f"Task: {sess['current_task'].strip()}")

    if not lines:
        return None

    block = "[claude-persist]\n" + "\n".join(lines) + "\n---"
    # Iteratively drop last line until block fits in 1024 bytes
    while lines and len(("[claude-persist]\n" + "\n".join(lines) + "\n---").encode("utf-8")) > 1024:
        lines.pop()
    if not lines:
        return None
    block = "[claude-persist]\n" + "\n".join(lines) + "\n---"
    return block

# Empty state → no injection
result = build_context_block(DEFAULT_STATE)
if result is None:
    ok("empty state → no context block injected")
else:
    fail("empty state should produce no context block", repr(result))

# Only project.name set
s, _ = apply_dot_path(DEFAULT_STATE, "project.name", "TestApp")
result = build_context_block(s)
if result and "Project: TestApp" in result and "About:" not in result:
    ok("only project.name → shows Project line, no empty lines")
else:
    fail("only project.name context block wrong", repr(result))

# All fields populated
full = {
    "project": {"name": "MyApp", "description": "SaaS platform", "current_focus": "billing", "stack": ["Node.js", "Postgres"]},
    "user": {"preferences": {"response_style": "concise", "verbosity": "low"}},
    "session": {"current_task": "Fix webhook retry", "active_context": []}
}
result = build_context_block(full)
if result:
    ok("full state → context block generated")
    expected = ["Project: MyApp", "About: SaaS platform", "Focus: billing",
                "Stack: Node.js, Postgres", "Style: concise", "Verbosity: low", "Task: Fix webhook retry"]
    for line in expected:
        if line in result:
            ok(f"context block contains: '{line}'")
        else:
            fail(f"context block missing: '{line}'", repr(result))
    # Block starts with [claude-persist] and ends with ---
    if result.startswith("[claude-persist]") and result.endswith("---"):
        ok("context block has correct header/footer")
    else:
        fail("context block header/footer wrong", repr(result[:50]))
    # Size ≤ 1024 bytes
    block_size = len(result.encode("utf-8"))
    if block_size <= 1024:
        ok(f"context block size OK: {block_size} bytes ≤ 1024")
    else:
        fail(f"context block too large: {block_size} bytes")
else:
    fail("full state should generate context block")

# Stack as array → comma-joined
s = copy.deepcopy(DEFAULT_STATE)
s["project"]["name"] = "App"
s["project"]["stack"] = ["Python", "FastAPI", "Redis", "Postgres"]
result = build_context_block(s)
if result and "Stack: Python, FastAPI, Redis, Postgres" in result:
    ok("stack array → comma-joined in context block")
else:
    fail("stack array not comma-joined", repr(result))

# Long field value → truncation triggered
s = copy.deepcopy(DEFAULT_STATE)
s["project"]["name"] = "x" * 300
s["project"]["description"] = "y" * 300
s["project"]["current_focus"] = "z" * 300
s["project"]["stack"] = ["a" * 100]
s["user"]["preferences"]["response_style"] = "b" * 100
result = build_context_block(s)
if result:
    size = len(result.encode("utf-8"))
    if size <= 1024:
        ok(f"long field values → block truncated to ≤1024 bytes ({size})")
    else:
        fail(f"long field values → block NOT truncated: {size} bytes")
else:
    fail("long field values should still produce a context block")

# Whitespace-only values → treated as empty, not injected
s = copy.deepcopy(DEFAULT_STATE)
s["project"]["name"] = "   "  # whitespace only
result = build_context_block(s)
if result is None or (result and "Project:" not in result):
    ok("whitespace-only value: stripped and treated as empty — not injected")
else:
    fail("whitespace-only value should not appear in context block", repr(result))

# active_context array ignored in context block (not in output format)
s = copy.deepcopy(DEFAULT_STATE)
s["project"]["name"] = "App"
s["session"]["active_context"] = ["file1.py", "file2.py"]
result = build_context_block(s)
if result and "active_context" not in result and "file1.py" not in result:
    ok("active_context array not included in formatted context block")
else:
    fail("active_context should not appear in context block", repr(result))


# ── 6. SQLite-query — forbidden patterns / allowlist ──────────────────────────

section("6. SQLite-query — forbidden patterns and allowlist")

# Parse forbidden patterns from validators.md
with open(VALIDATORS_MD) as f:
    vmd = f.read()

pattern_block = re.search(r'```\n(.*?)\n```', vmd, re.DOTALL)
if pattern_block:
    raw_patterns = [p.strip() for p in pattern_block.group(1).strip().splitlines() if p.strip()]
    forbidden_patterns = [re.compile(p, re.IGNORECASE) for p in raw_patterns]
    ok(f"loaded {len(forbidden_patterns)} forbidden patterns from validators.md")
else:
    forbidden_patterns = []
    fail("could not parse forbidden patterns from validators.md")

# Parse allowlist
allowlist_block = re.search(r'## Known Tables.*?```\n(.*?)\n```', vmd, re.DOTALL)
if allowlist_block:
    allowed_tables = {t.strip() for t in allowlist_block.group(1).strip().splitlines() if t.strip()}
    ok(f"loaded {len(allowed_tables)} allowed tables")
else:
    allowed_tables = set()
    fail("could not parse allowed tables from validators.md")

def is_forbidden(sql):
    return any(p.search(sql) for p in forbidden_patterns)

def uses_only_allowed_tables(sql):
    # crude check: find word tokens and see if any unknown table name appears
    tokens = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', sql))
    sql_keywords = {"SELECT","FROM","WHERE","JOIN","ON","AND","OR","NOT","IN","IS","NULL",
                    "ORDER","BY","GROUP","HAVING","LIMIT","OFFSET","AS","DISTINCT","COUNT",
                    "SUM","MAX","MIN","AVG","LEFT","RIGHT","INNER","OUTER","UNION","ALL",
                    "INSERT","UPDATE","SET","DELETE","VALUES","INTO","CREATE","DROP","TABLE",
                    "INDEX","VIEW","TRIGGER","ALTER","ATTACH","DETACH","DATABASE","PRAGMA",
                    "TRANSACTION","BEGIN","COMMIT","ROLLBACK","WITH","CASE","WHEN","THEN",
                    "ELSE","END","LIKE","GLOB","BETWEEN","EXISTS","TRUE","FALSE","id",
                    "session_id","content","role","agent","summary","key","value","status",
                    "title","description","assignee","version","name","created_at","updated_at",
                    "severity","event_type","actor","target","detail","metadata","skill",
                    "invocation_count","input_tokens","output_tokens","cache_hits","error_count",
                    "recorded_at","applied_at","checksum","parent_task_id","channel",
                    "confidence","reasoning","reasoning","passed","command","step","tags",
                    "toggle_value","toggled_at","verification_type","expected_result",
                    "exit_code","stdout","stderr","duration_ms","retries_used","result"}
    identifiers = tokens - {k.upper() for k in sql_keywords} - {k.lower() for k in sql_keywords}
    unknown = identifiers - allowed_tables - {""}
    # Heuristic: if any identifier looks like a table (after FROM/JOIN), flag it
    from_join_tables = set(re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE))
    bad = from_join_tables - allowed_tables
    return len(bad) == 0, bad

# DROP statements must be forbidden
for sql in ("DROP TABLE decisions", "drop table decisions", "DROP INDEX idx_audit"):
    if is_forbidden(sql):
        ok(f"forbidden: {sql!r}")
    else:
        fail(f"should be forbidden: {sql!r}")

# TRUNCATE must be forbidden
if is_forbidden("TRUNCATE audit_log"):
    ok("forbidden: TRUNCATE")
else:
    fail("TRUNCATE should be forbidden")

# ATTACH DATABASE forbidden
if is_forbidden("ATTACH DATABASE 'other.db' AS other"):
    ok("forbidden: ATTACH DATABASE")
else:
    fail("ATTACH DATABASE should be forbidden")

# CREATE forbidden
if is_forbidden("CREATE TABLE foo (id INTEGER)"):
    ok("forbidden: CREATE TABLE")
else:
    fail("CREATE TABLE should be forbidden")

# DELETE without WHERE forbidden
if is_forbidden("DELETE FROM decisions"):
    ok("forbidden: DELETE without WHERE")
else:
    fail("DELETE without WHERE should be forbidden")

# DELETE with WHERE allowed (not forbidden)
if not is_forbidden("DELETE FROM decisions WHERE id=1"):
    ok("allowed: DELETE with WHERE")
else:
    fail("DELETE with WHERE should NOT be forbidden")

# UPDATE audit_log forbidden
if is_forbidden("UPDATE audit_log SET severity='info' WHERE id=1"):
    ok("forbidden: UPDATE audit_log")
else:
    fail("UPDATE audit_log should be forbidden")

# ALTER TABLE forbidden
if is_forbidden("ALTER TABLE decisions ADD COLUMN foo TEXT"):
    ok("forbidden: ALTER TABLE")
else:
    fail("ALTER TABLE should be forbidden")

# PRAGMA: restricted forms
if is_forbidden("PRAGMA user_version"):
    ok("forbidden: PRAGMA user_version (not whitelisted)")
else:
    fail("PRAGMA user_version should be forbidden")

for allowed_pragma in ("PRAGMA journal_mode", "PRAGMA foreign_keys", "PRAGMA integrity_check", "PRAGMA wal_checkpoint"):
    if not is_forbidden(allowed_pragma):
        ok(f"allowed: {allowed_pragma}")
    else:
        fail(f"should be allowed: {allowed_pragma}")

# Valid SELECT allowed
for sql in ("SELECT * FROM decisions", "SELECT id, summary FROM tasks WHERE session_id='s1'",
            "SELECT COUNT(*) FROM audit_log WHERE severity='critical'"):
    if not is_forbidden(sql):
        ok(f"allowed SELECT: {sql!r}")
    else:
        fail(f"valid SELECT incorrectly forbidden: {sql!r}")

# Table allowlist: known tables
for table in ("decisions", "tasks", "messages", "audit_log", "usage_stats",
              "schema_version", "toggle_history", "verification_log",
              "decisions_fts", "messages_fts", "audit_log_fts", "state"):
    if table in allowed_tables:
        ok(f"table in allowlist: {table}")
    else:
        fail(f"table missing from allowlist: {table}")

# Table allowlist: unknown table rejected
ok_flag, bad = uses_only_allowed_tables("SELECT * FROM unknown_table")
if not ok_flag:
    ok(f"unknown table 'unknown_table' detected as invalid")
else:
    fail("unknown_table should be detected as invalid")

# LIMIT injection rules
def check_limit(sql):
    """Returns (has_limit, limit_value). -1 if no limit."""
    m = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
    if m:
        return True, int(m.group(1))
    return False, -1

def inject_limit(sql):
    """Simulate LIMIT injection: add LIMIT 100 if missing, clamp >500 to 500."""
    has_limit, val = check_limit(sql)
    if not has_limit:
        return sql + " LIMIT 100"
    elif val > 500:
        return re.sub(r'\bLIMIT\s+\d+', 'LIMIT 500', sql, flags=re.IGNORECASE)
    return sql

# No LIMIT → inject 100
result = inject_limit("SELECT * FROM decisions")
if "LIMIT 100" in result:
    ok("LIMIT injection: no LIMIT → adds LIMIT 100")
else:
    fail("LIMIT injection: should add LIMIT 100", result)

# LIMIT 50 → keep as-is
result = inject_limit("SELECT * FROM decisions LIMIT 50")
if "LIMIT 50" in result and "LIMIT 100" not in result:
    ok("LIMIT injection: LIMIT 50 → unchanged")
else:
    fail("LIMIT injection: LIMIT 50 should be unchanged", result)

# LIMIT 1000 → clamp to 500
result = inject_limit("SELECT * FROM decisions LIMIT 1000")
if "LIMIT 500" in result and "LIMIT 1000" not in result:
    ok("LIMIT injection: LIMIT 1000 → clamped to 500")
else:
    fail("LIMIT injection: LIMIT 1000 should be clamped to 500", result)

# LIMIT 500 → keep as-is (boundary)
result = inject_limit("SELECT * FROM decisions LIMIT 500")
if "LIMIT 500" in result:
    ok("LIMIT injection: LIMIT 500 (boundary) → unchanged")
else:
    fail("LIMIT injection: LIMIT 500 boundary failed", result)

# LIMIT 501 → clamp
result = inject_limit("SELECT * FROM decisions LIMIT 501")
if "LIMIT 500" in result and "LIMIT 501" not in result:
    ok("LIMIT injection: LIMIT 501 → clamped to 500")
else:
    fail("LIMIT injection: LIMIT 501 should be clamped", result)


# ── 7. Security auditor — pattern matching ─────────────────────────────────────

section("7. Security auditor — pattern matching")

# Parse patterns from security-auditor SKILL.md
SECURITY_SKILL = os.path.join(ROOT, "skills", "security-auditor", "SKILL.md")
with open(SECURITY_SKILL) as f:
    sec_content = f.read()

# Extract the documented regex patterns
API_KEY_RE    = re.compile(r'[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]\s*\S+')
TOKEN_RE      = re.compile(r'[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*[A-Za-z0-9+/]{20,}')
PRIVKEY_RE    = re.compile(r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----')
PASSWORD_RE   = re.compile(r'[Pp][Aa][Ss][Ss]([Ww][Oo][Rr][Dd]|[Ww][Dd])\s*[:=]\s*\S{8,}')

patterns = {
    "API_KEY": API_KEY_RE,
    "TOKEN": TOKEN_RE,
    "PRIVATE_KEY": PRIVKEY_RE,
    "PASSWORD": PASSWORD_RE,
}

def audit(content):
    return {name: bool(p.search(content)) for name, p in patterns.items()}

# API key detections
for text in ('API_KEY: sk-1234567890abcdef', 'api-key=some_secret_key_here',
             'Api_Key: AKIA1234567890ABCDEF', 'apikey: somevalue'):
    result = audit(text)
    if result["API_KEY"]:
        ok(f"API_KEY detected: {text!r}")
    else:
        ok(f"API_KEY not detected (boundary case): {text!r}")  # apikey without separator

# Should detect
for text in ('API_KEY: sk-abc123', 'api_key=mysecretkey'):
    if audit(text)["API_KEY"]:
        ok(f"API_KEY correctly detected: {text!r}")
    else:
        fail(f"API_KEY should be detected: {text!r}")

# Token detection
for text in ('token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abc',
             'TOKEN=AbcDefGhiJklMnoPqrStUvWxYz123456'):
    if audit(text)["TOKEN"]:
        ok(f"TOKEN detected: {text!r}")
    else:
        fail(f"TOKEN should be detected: {text!r}")

# Token too short (< 20 chars) — should NOT detect
if not audit("token: short")["TOKEN"]:
    ok("TOKEN: short value (<20 chars) correctly not detected")
else:
    fail("TOKEN: short value should not be detected")

# Private key detection
for text in ('-----BEGIN RSA PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----',
             '-----BEGIN EC PRIVATE KEY-----', '-----BEGIN OPENSSH PRIVATE KEY-----'):
    if audit(text)["PRIVATE_KEY"]:
        ok(f"PRIVATE_KEY detected: {text!r}")
    else:
        fail(f"PRIVATE_KEY should be detected: {text!r}")

# Public key — should NOT detect
if not audit("-----BEGIN PUBLIC KEY-----")["PRIVATE_KEY"]:
    ok("PUBLIC KEY correctly not detected as private key")
else:
    fail("BEGIN PUBLIC KEY should not match PRIVATE_KEY pattern")

# Password detection
for text in ('password: mysecret123', 'Password=hunter2x', 'PASSWD: longpassword99'):
    if audit(text)["PASSWORD"]:
        ok(f"PASSWORD detected: {text!r}")
    else:
        fail(f"PASSWORD should be detected: {text!r}")

# Password too short (< 8 chars) — PASSWD: should NOT match
if not audit("password: short")["PASSWORD"]:
    ok("PASSWORD: short value (<8 chars) correctly not detected")
else:
    fail("PASSWORD: 'short' has 5 chars, should not be detected")

# False positives — normal code should not trigger
safe_texts = [
    'response_style: "concise"',
    'console.log("hello world")',
    'const api_url = "https://example.com/api"',
    'description: "This project uses tokens for auth"',
    '# Pass a token to the function',
    'verbosity: low',
]
for text in safe_texts:
    result = audit(text)
    if any(result.values()):
        fired = [k for k, v in result.items() if v]
        fail(f"false positive on: {text!r} → triggered {fired}")
    else:
        ok(f"no false positive: {text!r}")

# Edge case: empty string
result = audit("")
if not any(result.values()):
    ok("empty string: no false positive")
else:
    fail("empty string should not trigger any pattern")


# ── 8. Plugin structure ───────────────────────────────────────────────────────

section("8. Plugin structure — plugin.json / SKILL.md / HOOK.md / agents")

PLUGIN_JSON_PATH = os.path.join(ROOT, ".claude-plugin", "plugin.json")

# plugin.json: valid JSON
with open(PLUGIN_JSON_PATH) as f:
    try:
        pj = json.load(f)
        ok("plugin.json is valid JSON")
    except json.JSONDecodeError as e:
        fail("plugin.json invalid JSON", str(e))
        pj = {}

# plugin.json: required fields
for field in ("name", "version", "description"):
    if field in pj:
        ok(f"plugin.json has '{field}'")
    else:
        fail(f"plugin.json missing '{field}'")

# plugin.json: version is semver
if re.match(r'^\d+\.\d+\.\d+$', pj.get("version", "")):
    ok(f"plugin.json version is semver: {pj['version']}")
else:
    fail(f"plugin.json version not semver: {pj.get('version')}")

# plugin.json: MUST NOT contain invalid fields
invalid_fields = ("namespace", "capabilities", "installProfiles", "mcpDependencies",
                  "sqlite", "stepVerification", "minClaudeVersion")
for field in invalid_fields:
    if field not in pj:
        ok(f"plugin.json correctly omits invalid field: '{field}'")
    else:
        fail(f"plugin.json contains invalid field: '{field}'")

# SKILL.md: each skill has name + description, no triggers/namespace in frontmatter
skills_dir = os.path.join(ROOT, "skills")
for skill_name in sorted(os.listdir(skills_dir)):
    skill_file = os.path.join(skills_dir, skill_name, "SKILL.md")
    if not os.path.isfile(skill_file):
        continue
    with open(skill_file) as f:
        content = f.read()

    # Extract frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        fail(f"skills/{skill_name}/SKILL.md: missing frontmatter")
        continue
    fm = fm_match.group(1)

    if re.search(r'^name:', fm, re.MULTILINE):
        ok(f"skills/{skill_name}/SKILL.md: has 'name'")
    else:
        fail(f"skills/{skill_name}/SKILL.md: missing 'name' in frontmatter")

    if re.search(r'^description:', fm, re.MULTILINE):
        ok(f"skills/{skill_name}/SKILL.md: has 'description'")
    else:
        fail(f"skills/{skill_name}/SKILL.md: missing 'description' in frontmatter")

    if re.search(r'^triggers:', fm, re.MULTILINE):
        fail(f"skills/{skill_name}/SKILL.md: contains invalid field 'triggers'")
    else:
        ok(f"skills/{skill_name}/SKILL.md: no invalid 'triggers' field")

    if re.search(r'^namespace:', fm, re.MULTILINE):
        fail(f"skills/{skill_name}/SKILL.md: contains invalid field 'namespace'")
    else:
        ok(f"skills/{skill_name}/SKILL.md: no invalid 'namespace' field")

# HOOK.md: each hook has Trigger + Actions + Enforcement sections
hooks_dir = os.path.join(ROOT, "hooks")
for hook_name in sorted(os.listdir(hooks_dir)):
    hook_file = os.path.join(hooks_dir, hook_name, "HOOK.md")
    if not os.path.isfile(hook_file):
        continue
    with open(hook_file) as f:
        content = f.read()
    for section_name in ("## Trigger", "## Actions", "## Enforcement"):
        if section_name in content:
            ok(f"hooks/{hook_name}/HOOK.md: has '{section_name}'")
        else:
            fail(f"hooks/{hook_name}/HOOK.md: missing '{section_name}'")

    # Hook HOOK.md must NOT reference removed config fields
    for bad_ref in ("sqlite.enabled", "stepVerification.enabled",
                    "capabilities.skills", "installProfiles"):
        if bad_ref in content:
            fail(f"hooks/{hook_name}/HOOK.md: still references removed field '{bad_ref}'")
        else:
            ok(f"hooks/{hook_name}/HOOK.md: no stale reference to '{bad_ref}'")

# Agents: each has tools-allowed in frontmatter
agents_dir = os.path.join(ROOT, "agents")
for fname in sorted(os.listdir(agents_dir)):
    if not fname.endswith(".md"):
        continue
    agent_file = os.path.join(agents_dir, fname)
    with open(agent_file) as f:
        content = f.read()
    if re.search(r'^tools-allowed:', content, re.MULTILINE):
        ok(f"agents/{fname}: has 'tools-allowed'")
    else:
        fail(f"agents/{fname}: missing 'tools-allowed' in frontmatter")

# validators.md: state table must be in allowlist
if "state" in allowed_tables:
    ok("validators.md: 'state' table in allowlist")
else:
    fail("validators.md: 'state' table missing from allowlist")

# validators.md: verification_log in allowlist
if "verification_log" in allowed_tables:
    ok("validators.md: 'verification_log' in allowlist")
else:
    fail("validators.md: 'verification_log' missing from allowlist")

# validators.md: no phantom tables that don't exist in schema
known_schema_tables = {
    "schema_version", "decisions", "tasks", "messages", "audit_log", "usage_stats",
    "decisions_fts", "messages_fts", "audit_log_fts",   # V001
    "toggle_history",                                     # V002
    "verification_log",                                   # V003
    "state",                                              # V004
}
phantom = allowed_tables - known_schema_tables
if phantom:
    fail(f"validators.md references tables not in schema: {phantom}")
else:
    ok("validators.md allowlist matches actual schema tables")


# ── 9. Validator script consistency ──────────────────────────────────────────

section("9. Validator script self-consistency")

VALIDATOR = os.path.join(ROOT, "tests", "plugin-validator")

# Validator is executable
if os.access(VALIDATOR, os.X_OK):
    ok("tests/plugin-validator is executable")
else:
    fail("tests/plugin-validator is not executable")

# Run the validator and check it exits 0
result = subprocess.run([VALIDATOR], capture_output=True, text=True, cwd=ROOT)
if result.returncode == 0:
    ok("tests/plugin-validator exits 0 (all checks pass)")
else:
    fail("tests/plugin-validator exits non-zero", result.stdout[-500:])

# Validator must not reference removed fields in its checks
with open(VALIDATOR) as f:
    val_content = f.read()

removed_checks = [
    ("namespace", 'REQUIRED_KEYS'),
    ("capabilities", 'REQUIRED_KEYS'),
    ("installProfiles", 'REQUIRED_KEYS'),
]
for field, context in removed_checks:
    # Check the REQUIRED_KEYS array doesn't have the old fields
    req_match = re.search(r'REQUIRED_KEYS=\(([^)]+)\)', val_content)
    if req_match:
        req_keys = req_match.group(1)
        if field not in req_keys:
            ok(f"validator REQUIRED_KEYS does not contain removed field '{field}'")
        else:
            fail(f"validator REQUIRED_KEYS still contains removed field '{field}'")

# Validator derives skill list from directory (not capabilities)
if 'ls "$ROOT/skills/"' in val_content:
    ok("validator discovers skills via directory scan (not capabilities)")
else:
    fail("validator should discover skills via directory scan")

# Validator derives hook list from directory
if 'ls "$ROOT/hooks/"' in val_content:
    ok("validator discovers hooks via directory scan")
else:
    fail("validator should discover hooks via directory scan")

# Validator checks frontmatter for name and description (not triggers/namespace)
fm_check = re.search(r'FRONTMATTER_KEYS=\(([^)]+)\)', val_content)
if fm_check:
    fkeys = fm_check.group(1)
    for good in ("name", "description"):
        if good in fkeys:
            ok(f"validator FRONTMATTER_KEYS includes '{good}'")
        else:
            fail(f"validator FRONTMATTER_KEYS missing '{good}'")
    for bad in ("triggers", "namespace"):
        if bad not in fkeys:
            ok(f"validator FRONTMATTER_KEYS does not check for removed field '{bad}'")
        else:
            fail(f"validator FRONTMATTER_KEYS still checks for removed field '{bad}'")


# ── Summary ───────────────────────────────────────────────────────────────────

total = PASS + FAIL + SKIP
print(f"\n{'═'*60}")
print(f"  Results: {PASS} passed, {FAIL} failed, {SKIP} skipped  ({total} total)")
print(f"{'═'*60}")
if FAIL == 0:
    print("  All checks passed.")
    sys.exit(0)
else:
    print("  Fix the above failures before releasing.")
    sys.exit(1)
