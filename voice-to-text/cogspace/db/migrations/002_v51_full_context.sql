-- COGSPACE Per-Project Database Schema v2
-- Migration 002: Full Context Storage for v51.0.0
-- Created: 2025-12-10
-- Purpose: 100% fidelity storage - database becomes primary source of truth

-- ============================================================================
-- EXPANDED MENTAL MODELS - Complete cognitive state storage
-- ============================================================================

-- Add new columns to mental_models
ALTER TABLE mental_models ADD COLUMN work_description TEXT;
ALTER TABLE mental_models ADD COLUMN current_focus TEXT;
ALTER TABLE mental_models ADD COLUMN understanding_level TEXT;
ALTER TABLE mental_models ADD COLUMN problem_complexity TEXT;
ALTER TABLE mental_models ADD COLUMN cognitive_state TEXT;  -- JSON: energy, clarity, momentum
ALTER TABLE mental_models ADD COLUMN technical_definitions TEXT;  -- JSON array
ALTER TABLE mental_models ADD COLUMN project_patterns TEXT;  -- JSON object

-- ============================================================================
-- EXPANDED DECISION CONTEXTS - Full archaeology
-- ============================================================================

-- Add new columns to decision_contexts
ALTER TABLE decision_contexts ADD COLUMN confidence_level INTEGER;
ALTER TABLE decision_contexts ADD COLUMN evidence_basis TEXT;  -- JSON array
ALTER TABLE decision_contexts ADD COLUMN impact_assessment TEXT;
ALTER TABLE decision_contexts ADD COLUMN reversibility TEXT;  -- easy/moderate/difficult/irreversible

-- ============================================================================
-- NEW TABLE: Executable Continuity
-- ============================================================================

CREATE TABLE IF NOT EXISTS executable_continuity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    action_category TEXT,  -- immediate/next_session/blocked/followup
    action_content TEXT,
    priority INTEGER DEFAULT 5,  -- 1-10 scale
    estimated_complexity TEXT,  -- simple/moderate/complex
    dependencies TEXT,  -- JSON array of dependent actions
    target_session TEXT,  -- which session should handle this
    status TEXT DEFAULT 'pending',
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- NEW TABLE: Tool Usage Analytics
-- ============================================================================

CREATE TABLE IF NOT EXISTS tool_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    call_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_response_time_ms REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- NEW TABLE: Continuity Score Components
-- ============================================================================

CREATE TABLE IF NOT EXISTS continuity_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    -- Storage tier (40 points max)
    storage_sessions INTEGER DEFAULT 0,
    storage_mental_model INTEGER DEFAULT 0,
    storage_work_narrative INTEGER DEFAULT 0,
    storage_decisions INTEGER DEFAULT 0,
    storage_continuity INTEGER DEFAULT 0,
    storage_total INTEGER DEFAULT 0,
    -- Retrieval tier (30 points max)
    retrieval_sessions INTEGER DEFAULT 0,
    retrieval_mental_model INTEGER DEFAULT 0,
    retrieval_work_narrative INTEGER DEFAULT 0,
    retrieval_decisions INTEGER DEFAULT 0,
    retrieval_total INTEGER DEFAULT 0,
    -- Presentation tier (30 points max)
    presentation_terminal INTEGER DEFAULT 0,
    presentation_dashboard INTEGER DEFAULT 0,
    presentation_total INTEGER DEFAULT 0,
    -- Final score
    total_score INTEGER DEFAULT 0,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================================
-- NEW TABLE: Session Configuration
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT,
    config_type TEXT DEFAULT 'string',  -- string/boolean/integer/json
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configuration
INSERT OR IGNORE INTO session_config (config_key, config_value, config_type, description) VALUES
    ('display_level', 'full', 'string', 'Terminal display verbosity: minimal/standard/enhanced/full'),
    ('dashboard_auto_open', 'true', 'boolean', 'Auto-open dashboard in browser on wake'),
    ('display_score_table', 'true', 'boolean', 'Show continuity score breakdown table'),
    ('browser_preference', 'auto', 'string', 'Browser: auto/safari/chrome'),
    ('same_tab_reuse', 'true', 'boolean', 'Reuse same browser tab for dashboard');

-- ============================================================================
-- EXPANDED INDEXES for new queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_exec_continuity_session ON executable_continuity(session_id);
CREATE INDEX IF NOT EXISTS idx_exec_continuity_status ON executable_continuity(status);
CREATE INDEX IF NOT EXISTS idx_exec_continuity_priority ON executable_continuity(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_session ON tool_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_continuity_scores_session ON continuity_scores(session_id);

-- ============================================================================
-- MIGRATION RECORD
-- ============================================================================

INSERT INTO schema_version (version, description) VALUES (2, 'v51.0.0 Full context storage - database as primary source');
