# COGSPACE Database Utilities

**IMPORTANT**: This directory contains database **utilities and schema definitions**, NOT runtime data.

## Where Is The Actual Database?

| Location | Purpose | Contents |
|----------|---------|----------|
| `cogspace/db/` | **Utilities & Schema** | Manager code, schema.sql, helpers |
| `.cogspace/cogspace.db` | **Runtime Session Data** | Actual sessions, memories, context |

**The database file in this directory (if present) is a template/placeholder only.**

## Runtime Database Location

Session data is stored at the **project root** in a hidden directory:

```
my-project/
├── .cogspace/
│   └── cogspace.db    ← ACTUAL SESSION DATA (SQLite)
├── cogspace/
│   └── db/
│       ├── README.md           ← You are here
│       ├── database-manager.cjs
│       ├── schema.sql
│       └── cogspace.db         ← TEMPLATE ONLY (0 bytes)
```

## Why This Architecture?

1. **Separation of Concerns**: Code (cogspace/db/) vs. Data (.cogspace/)
2. **Git-Friendly**: `.cogspace/` is gitignored; session data stays local
3. **DNA Sync Safe**: Code syncs from DNA source; runtime data is preserved
4. **Multi-Project**: Each project has its own `.cogspace/` with isolated data

## Database Schema

The runtime database contains these tables:

| Table | Purpose |
|-------|---------|
| `sessions` | Core session metadata (ID, project, timestamps, score) |
| `mental_models` | Cognitive state per session |
| `work_narratives` | Session story, achievements, challenges |
| `decision_contexts` | Decisions made during sessions |
| `executable_continuity` | Next actions for continuation |
| `continuity_scores` | Quality/completeness scores |
| `tool_usage` | Tool usage statistics |
| `git_operations` | Git operation history |
| `performance_metrics` | Performance measurements |

## Querying Session Data

```bash
# Find the correct database
ls -la .cogspace/cogspace.db

# Query sessions
sqlite3 .cogspace/cogspace.db "SELECT id, project, created_at, score, version FROM sessions ORDER BY created_at DESC LIMIT 5"

# Query mental models
sqlite3 .cogspace/cogspace.db "SELECT * FROM mental_models WHERE session_id='YOUR_SESSION_ID'"
```

## Files In This Directory

| File | Purpose |
|------|---------|
| `database-manager.cjs` | Database operations (read/write/query) |
| `schema.sql` | SQLite schema definitions |
| `cogspace.db` | Template file (empty placeholder) |
| `README.md` | This documentation |

---

*COGSPACE v55.0.0 - Database Architecture Documentation*
