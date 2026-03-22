-- Migration 002: Add relational versioning and temporal grounding
-- Inspired by Supermemory's knowledge chains and dual-layer timestamps

-- When the referenced event occurred (vs first_seen = when the episode was stored)
ALTER TABLE episodes ADD COLUMN event_date TEXT;

-- Relational versioning: track how episodes relate to each other
ALTER TABLE episodes ADD COLUMN parent_episode_id TEXT;
ALTER TABLE episodes ADD COLUMN relation_type TEXT;  -- 'updates', 'extends', 'supersedes'

-- External ID after promotion to Supermemory
ALTER TABLE episodes ADD COLUMN supermemory_id TEXT;

-- Track schema version
INSERT INTO schema_version (version, description) VALUES (2, 'Add relations and temporal grounding');
