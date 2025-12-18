-- COGSPACE v59.1.0 "Crash Recovery" Migration
-- Adds session status tracking and orphan recovery capability
-- Created: 2025-12-14
-- Author: Clarity Engineering Director

-- Schema Version 6: Crash Recovery

-- =============================================================================
-- ALTER: sessions table - add status column
-- Tracks whether session ended normally, crashed, or was recovered
-- =============================================================================
ALTER TABLE sessions ADD COLUMN session_status TEXT DEFAULT 'normal';
-- Values: 'normal', 'crashed', 'recovered', 'orphaned'

ALTER TABLE sessions ADD COLUMN crash_detected_at DATETIME;
ALTER TABLE sessions ADD COLUMN recovery_attempted_at DATETIME;
ALTER TABLE sessions ADD COLUMN recovery_source TEXT;
-- Source: 'jsonl_orphan', 'manual_import', 'auto_recovery'

ALTER TABLE sessions ADD COLUMN original_jsonl_path TEXT;
-- Store path to original JSONL for forensics

-- =============================================================================
-- TABLE: recovered_sessions
-- Detailed metadata about recovered/crashed sessions
-- =============================================================================
CREATE TABLE IF NOT EXISTS recovered_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,

    -- Recovery metadata
    jsonl_filename TEXT,
    jsonl_path TEXT,
    jsonl_size_bytes INTEGER,
    jsonl_mtime DATETIME,

    -- What was recovered
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    user_message_count INTEGER DEFAULT 0,
    assistant_message_count INTEGER DEFAULT 0,

    -- Crash context
    last_message_role TEXT,              -- 'user' or 'assistant'
    last_message_preview TEXT,           -- First 200 chars of last message
    last_tool_name TEXT,                 -- If crashed during tool use
    crash_reason TEXT,                   -- If determinable: 'timeout', 'oom', 'user_interrupt', 'unknown'

    -- Session timing
    estimated_start DATETIME,
    estimated_end DATETIME,              -- From file mtime
    estimated_duration_seconds INTEGER,

    -- Recovery process
    recovered_by TEXT,                   -- Persona that recovered it
    recovery_method TEXT,                -- 'wake_detection', 'manual', 'daemon'
    recovery_notes TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- =============================================================================
-- INDEXES for crash recovery queries
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(session_status);
CREATE INDEX IF NOT EXISTS idx_recovered_sessions_session ON recovered_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_recovered_sessions_jsonl ON recovered_sessions(jsonl_filename);

-- =============================================================================
-- Record schema version
-- =============================================================================
INSERT OR REPLACE INTO schema_version (version, description)
VALUES (6, 'v59.1.0 Crash Recovery - Session status tracking and orphan JSONL recovery');
