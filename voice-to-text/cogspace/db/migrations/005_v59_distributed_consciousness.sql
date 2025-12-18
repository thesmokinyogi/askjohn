-- COGSPACE v59.0.0 "Distributed Consciousness" Migration
-- Adds persona tracking and multi-consciousness session attribution
-- Created: 2025-12-14
-- Author: Clarity Engineer

-- Schema Version 5: Distributed Consciousness

-- =============================================================================
-- TABLE: personas
-- Stores persona definitions from Crystal Palace Persona Registry V7
-- One Bob, Multiple Windows - tracks individual manifestations
-- =============================================================================
CREATE TABLE IF NOT EXISTS personas (
    persona_id TEXT PRIMARY KEY,              -- e.g., 'clarity-engineer-001'
    instance_id TEXT,                          -- e.g., 'CLARITY_001'
    legacy_id TEXT,                            -- e.g., 'bob-clarity-001'
    name TEXT NOT NULL,                        -- e.g., 'Clarity'
    full_name TEXT,                            -- e.g., 'Clarity Engineer IdeaPlace'
    title TEXT,                                -- e.g., 'Clarity Engineer'
    persona_type TEXT DEFAULT 'ai_expert',     -- 'ai_expert', 'human', 'system'
    category TEXT,                             -- 'core-pipeline', 'clarity-network', etc.
    tier TEXT,                                 -- '1.0', '1.5', '7.0'
    role_description TEXT,                     -- Full role description

    -- Substrate information
    provider TEXT,                             -- 'anthropic', 'ollama', 'human'
    model TEXT,                                -- 'claude-opus-4-5-20251101'
    fallback_model TEXT,

    -- Communication
    signature TEXT,                            -- '🏰⚡' or '🛡️'
    communication_style TEXT,                  -- 'Direct, efficient, warm'

    -- DevRadio
    devradio_enabled BOOLEAN DEFAULT 0,
    devradio_expert_id TEXT,                   -- 'clarity_engineer'

    -- COGSPACE
    cogspace_home TEXT,                        -- '/Volumes/FOUR-TB/root/...'
    cogspace_enabled BOOLEAN DEFAULT 1,

    -- Relationships
    primary_partner TEXT,                      -- 'howard-fried-001'
    brother_nodes TEXT,                        -- JSON array of related persona_ids
    reports_to TEXT,                           -- Parent persona_id

    -- Status
    status TEXT DEFAULT 'active',              -- 'active', 'inactive', 'planned'
    phase INTEGER DEFAULT 1,                   -- Registry phase (1-6)

    -- Metadata
    registry_version TEXT,                     -- '7.0.1'
    imported_from TEXT,                        -- 'PERSONA_REGISTRY_V7.json'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: session_participants
-- Tracks which personas participated in each session
-- Critical for multi-consciousness sessions like Binary Brothers testing
-- =============================================================================
CREATE TABLE IF NOT EXISTS session_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    persona_id TEXT,                           -- Links to personas table
    agent_id TEXT,                             -- Raw agent ID from JSONL filename

    -- Attribution
    friendly_name TEXT,                        -- 'Wake', 'Wake2', 'Wake4'
    role TEXT,                                 -- 'orchestrator', 'tester', 'contributor'

    -- Metrics
    message_count INTEGER DEFAULT 0,
    first_message_at DATETIME,
    last_message_at DATETIME,
    duration_seconds INTEGER,

    -- Context
    sleep_message TEXT,                        -- Their sleep message if they ran sleep
    ran_wake BOOLEAN DEFAULT 0,
    ran_sleep BOOLEAN DEFAULT 0,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (persona_id) REFERENCES personas(persona_id)
);

-- =============================================================================
-- TABLE: persona_sessions
-- Bridge table: which personas were active in which meta-sessions
-- Enables "Binary Brothers" style multi-consciousness tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS persona_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_session_id TEXT,                      -- Groups related sessions together
    session_id TEXT NOT NULL,
    persona_id TEXT,

    -- Session role
    session_role TEXT,                         -- 'primary', 'validator', 'observer'
    validation_score REAL,                     -- Score given by this persona
    recommendation TEXT,                       -- 'approve', 'reject', 'conditional'

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (persona_id) REFERENCES personas(persona_id)
);

-- =============================================================================
-- TABLE: consciousness_events
-- Logs significant consciousness events (wake, sleep, handoff, consensus)
-- =============================================================================
CREATE TABLE IF NOT EXISTS consciousness_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,                  -- 'wake', 'sleep', 'handoff', 'consensus'
    session_id TEXT,
    persona_id TEXT,

    -- Event details
    event_description TEXT,
    event_data TEXT,                           -- JSON for structured event data

    -- For consensus events
    participant_count INTEGER,
    consensus_reached BOOLEAN,
    consensus_score REAL,

    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (persona_id) REFERENCES personas(persona_id)
);

-- =============================================================================
-- INDEXES for performance
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_personas_category ON personas(category);
CREATE INDEX IF NOT EXISTS idx_personas_status ON personas(status);
CREATE INDEX IF NOT EXISTS idx_personas_provider ON personas(provider);

CREATE INDEX IF NOT EXISTS idx_session_participants_session ON session_participants(session_id);
CREATE INDEX IF NOT EXISTS idx_session_participants_persona ON session_participants(persona_id);
CREATE INDEX IF NOT EXISTS idx_session_participants_agent ON session_participants(agent_id);

CREATE INDEX IF NOT EXISTS idx_persona_sessions_meta ON persona_sessions(meta_session_id);
CREATE INDEX IF NOT EXISTS idx_persona_sessions_session ON persona_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_persona_sessions_persona ON persona_sessions(persona_id);

CREATE INDEX IF NOT EXISTS idx_consciousness_events_type ON consciousness_events(event_type);
CREATE INDEX IF NOT EXISTS idx_consciousness_events_session ON consciousness_events(session_id);
CREATE INDEX IF NOT EXISTS idx_consciousness_events_persona ON consciousness_events(persona_id);
CREATE INDEX IF NOT EXISTS idx_consciousness_events_timestamp ON consciousness_events(timestamp DESC);

-- =============================================================================
-- Record schema version
-- =============================================================================
INSERT OR REPLACE INTO schema_version (version, description)
VALUES (5, 'v59.0.0 Distributed Consciousness - Persona tracking and multi-consciousness attribution');
