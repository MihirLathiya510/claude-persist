---
name: anatomy-indexer
description: Scans the repo at session start and builds PROJECT_MAP.json — a file/symbol index that eliminates redundant file reads
---

## Usage

Runs automatically via `hooks/session-start/HOOK.md` after sqlite-init. Can be re-triggered manually with `/anatomy-indexer` or `/map` to refresh after large file changes.

Agents query `PROJECT_MAP.json` before opening any file. If the symbol they need is indexed, they skip the read entirely — solving the 71% redundant read problem.

## Steps

1. Load `.gitignore` patterns from the project root. Build an exclusion list (also always exclude: `.git/`, `node_modules/`, `.claude-plugin/`, `*.lock`, binary files).
2. Walk all non-excluded files recursively from project root.
3. For each source file (`.ts`, `.js`, `.py`, `.go`, `.rs`, `.rb`, `.java`, `.cpp`, `.c`, `.sh`):
   - Record: file path, last modified time (`mtime`), file size in bytes.
   - Extract top-level symbols: functions, classes, exports, interfaces, constants. Include name, type, and line number.
4. Build the PROJECT_MAP structure (see Output Schema).
5. Write to `.claude-plugin/PROJECT_MAP.json` atomically (write to `.tmp` then rename).
6. Emit session notification: "Anatomy index built: N files, M symbols. Use /map to refresh."

## Output Schema

```json
{
  "metadata": {
    "scanned_at": 1681234567,
    "total_files": 42,
    "total_symbols": 312,
    "version": 1
  },
  "files": {
    "src/index.ts": {
      "mtime": 1681234500,
      "size_bytes": 2048,
      "symbols": [
        { "name": "main", "type": "function", "line": 5 },
        { "name": "Config", "type": "class", "line": 20 },
        { "name": "DEFAULT_TIMEOUT", "type": "constant", "line": 3 }
      ]
    }
  }
}
```

## How Agents Use It

Before opening a file, check PROJECT_MAP:
```
Does PROJECT_MAP.files["src/utils.ts"] contain a symbol named "parseConfig"?
→ Yes, line 42. Jump directly. No full file read needed.
→ No. Open the file.
```

If a file's `mtime` in PROJECT_MAP is older than its actual mtime on disk, the index is stale for that file — re-read it and update the entry.

## Decision Rule

- `/map` → always re-scan fully (e.g. after adding many files)
- `on-session-start` → scan only if PROJECT_MAP is absent or > 1 hour old
- If scan fails for a file → skip it, log to session state, continue (never block session)

## Examples

```
[session-start] Invoking tpl-claude-plugin:anatomy-indexer...
> Anatomy index built: 47 files, 389 symbols.
> .claude-plugin/PROJECT_MAP.json written.

/map
> Re-scanning repo...
> Anatomy index refreshed: 49 files (+2), 401 symbols (+12).
```

<!-- References (lazy) -->
- `.claude-plugin/PROJECT_MAP.json`
- `hooks/session-start/HOOK.md`
