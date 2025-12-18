-- COGSPACE v56.0.0 "Database First" Schema Migration
-- Migration: 004_v56_database_first.sql
-- Purpose: Add tables for full JSON parity + distributed consciousness capture
-- Author: Clarity Engineer
-- Date: 2025-12-13

-- ============================================================================
-- HIGH PRIORITY: Conversation Messages
-- Stores full conversation history including agent messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_index INTEGER,
    role TEXT,  -- 'user' | 'assistant'
    content TEXT,
    timestamp DATETIME,
    intent TEXT,  -- approval, clarification, question, feedback
    sentiment TEXT,  -- positive, neutral, negative
    topics TEXT,  -- JSON array
    agent_id TEXT,  -- Track which agent said what (null for main session)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- HIGH PRIORITY: Semantic Summaries
-- Stores what/why/how summaries for session understanding
-- ============================================================================
CREATE TABLE IF NOT EXISTS semantic_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    what_summary TEXT,
    why_summary TEXT,
    how_summary TEXT,
    work_classification TEXT,  -- JSON: primaryType, domains, complexity
    outcomes TEXT,  -- JSON: achieved, blockers, impact, learnings
    related_goals TEXT,  -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- MEDIUM PRIORITY: User Context
-- Stores user preferences and communication style
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    communication_style TEXT,
    working_style TEXT,
    message_complexity TEXT,
    preferences TEXT,  -- JSON object
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- MEDIUM PRIORITY: Environment Context
-- Stores environment information for portable context
-- ============================================================================
CREATE TABLE IF NOT EXISTS environment_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    hostname TEXT,
    platform TEXT,
    architecture TEXT,
    node_version TEXT,
    timezone TEXT,
    ide_environment TEXT,
    dependency_fingerprint TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- LOW PRIORITY: Git File Changes
-- Stores per-file change tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS git_file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    file_path TEXT,
    change_type TEXT,  -- added, modified, deleted
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    category TEXT,  -- code, documentation, configuration, other
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- v56.0.0: Distributed Consciousness Manifest
-- Tracks main session + agent session relationships
-- ============================================================================
CREATE TABLE IF NOT EXISTS distributed_manifests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    total_files INTEGER DEFAULT 0,
    main_session_count INTEGER DEFAULT 0,
    agent_session_count INTEGER DEFAULT 0,
    captured_at DATETIME,
    manifest_json TEXT,  -- Full manifest as JSON for detailed inspection
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- v56.0.0: Fallback Forensics Log
-- Tracks when and why fallback to JSON occurs
-- ============================================================================
CREATE TABLE IF NOT EXISTS fallback_forensics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,  -- May be null if no session found
    fallback_type TEXT NOT NULL,  -- 'json_discovery', 'db_empty', 'db_error', 'no_sessions'
    reason TEXT,
    db_exists BOOLEAN DEFAULT 0,
    db_size_bytes INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0,
    json_files_found INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Add command column to immediate_actions (if table exists)
-- ============================================================================
-- Note: Using ALTER TABLE which will fail silently if column exists
-- SQLite doesn't support IF NOT EXISTS for columns
ALTER TABLE immediate_actions ADD COLUMN command TEXT;

-- ============================================================================
-- Create indexes for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_role ON conversation_messages(session_id, role);
CREATE INDEX IF NOT EXISTS idx_semantic_summaries_session ON semantic_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_user_contexts_session ON user_contexts(session_id);
CREATE INDEX IF NOT EXISTS idx_environment_contexts_session ON environment_contexts(session_id);
CREATE INDEX IF NOT EXISTS idx_git_file_changes_session ON git_file_changes(session_id);
CREATE INDEX IF NOT EXISTS idx_distributed_manifests_session ON distributed_manifests(session_id);
CREATE INDEX IF NOT EXISTS idx_fallback_forensics_timestamp ON fallback_forensics(timestamp DESC);

-- Add indexes for sessions if they don't exist
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name, created_at DESC);

-- ============================================================================
-- Record migration in schema_version
-- ============================================================================
INSERT INTO schema_version (version, applied_at, description)
VALUES (4, datetime('now'), 'v56.0.0 Database First: 7 new tables for full JSON parity');
