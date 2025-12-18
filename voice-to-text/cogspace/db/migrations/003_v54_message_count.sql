-- COGSPACE v54.0.0 Migration: Add message_count column
-- Date: 2025-12-13
-- Purpose: Track conversation message count for database-JSON parity

-- Add message_count to sessions table
ALTER TABLE sessions ADD COLUMN message_count INTEGER DEFAULT 0;

-- Update schema version tracking
INSERT INTO schema_version (version, applied_at, description)
VALUES (3, datetime('now'), 'v54.0.0: Add message_count column');
