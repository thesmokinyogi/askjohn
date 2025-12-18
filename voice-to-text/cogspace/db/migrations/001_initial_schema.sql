-- COGSPACE Per-Project Database Schema v1
-- Migration 001: Initial Schema
-- Created: 2025-12-03

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Core sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    project_path TEXT,
    session_start DATETIME,
    session_end DATETIME,
    duration_seconds INTEGER,
    continuity_score INTEGER DEFAULT 100,
    trigger_type TEXT DEFAULT 'manual',
    cogspace_version TEXT,
    sleep_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Mental models - understanding of project/domain
CREATE TABLE IF NOT EXISTS mental_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    current_understanding TEXT,
    work_summary TEXT,
    key_concepts TEXT,  -- JSON array
    domain_knowledge TEXT,  -- JSON object
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Work narratives - story of what happened
CREATE TABLE IF NOT EXISTS work_narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    session_story TEXT,
    previous_chapter TEXT,
    current_chapter TEXT,
    next_chapter TEXT,
    narrative_complexity TEXT,
    achievements TEXT,  -- JSON array
    challenges TEXT,  -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Decision contexts - why decisions were made
CREATE TABLE IF NOT EXISTS decision_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    decision_type TEXT,
    description TEXT,
    rationale TEXT,
    alternatives_considered TEXT,  -- JSON array
    outcome TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Immediate actions - next steps
CREATE TABLE IF NOT EXISTS immediate_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    action_type TEXT,
    description TEXT,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Developer notes - quick notes during session
CREATE TABLE IF NOT EXISTS developer_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    developer_name TEXT,
    note_content TEXT,
    note_type TEXT DEFAULT 'general',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Git operations tracking
CREATE TABLE IF NOT EXISTS git_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    operation TEXT,
    branch TEXT,
    commit_hash TEXT,
    files_changed INTEGER,
    insertions INTEGER,
    deletions INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    metric_name TEXT,
    metric_value REAL,
    metric_unit TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Full-text search on session content
CREATE VIRTUAL TABLE IF NOT EXISTS session_content_fts USING fts5(
    session_id,
    work_summary,
    session_story,
    sleep_message,
    notes,
    content='',
    tokenize='porter'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name);
CREATE INDEX IF NOT EXISTS idx_sessions_end ON sessions(session_end DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_score ON sessions(continuity_score);
CREATE INDEX IF NOT EXISTS idx_mental_models_session ON mental_models(session_id);
CREATE INDEX IF NOT EXISTS idx_work_narratives_session ON work_narratives(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_session ON decision_contexts(session_id);
CREATE INDEX IF NOT EXISTS idx_actions_session ON immediate_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON immediate_actions(status);
CREATE INDEX IF NOT EXISTS idx_notes_session ON developer_notes(session_id);
CREATE INDEX IF NOT EXISTS idx_git_session ON git_operations(session_id);

-- Record this migration
INSERT INTO schema_version (version, description) VALUES (1, 'Initial per-project database schema');
