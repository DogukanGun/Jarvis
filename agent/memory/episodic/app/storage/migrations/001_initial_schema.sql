-- Initial schema for episodic memory storage
-- Version: 001

-- Episodes table: Short-term memory storage
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,

    -- Content
    text TEXT NOT NULL,
    summary TEXT,

    -- Metadata
    episode_type TEXT NOT NULL DEFAULT 'interaction',
    task_type TEXT,
    app TEXT,
    entities TEXT,  -- JSON array

    -- Temporal
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,

    -- Embedding (BLOB for efficiency)
    embedding BLOB,
    embedding_model TEXT,

    -- Quality metrics
    importance_score REAL DEFAULT 0.5,
    confidence REAL DEFAULT 1.0,
    reinforcement_count INTEGER DEFAULT 1,

    -- Status
    is_deleted INTEGER DEFAULT 0,
    promoted_to_mem0 INTEGER DEFAULT 0,
    promotion_proposal_id TEXT,

    -- Audit
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Indexes for episodes
CREATE INDEX IF NOT EXISTS idx_episodes_user_id ON episodes(user_id);
CREATE INDEX IF NOT EXISTS idx_episodes_fingerprint ON episodes(fingerprint);
CREATE INDEX IF NOT EXISTS idx_episodes_user_fingerprint ON episodes(user_id, fingerprint);
CREATE INDEX IF NOT EXISTS idx_episodes_task_type ON episodes(task_type);
CREATE INDEX IF NOT EXISTS idx_episodes_app ON episodes(app);
CREATE INDEX IF NOT EXISTS idx_episodes_episode_type ON episodes(episode_type);
CREATE INDEX IF NOT EXISTS idx_episodes_last_seen ON episodes(last_seen);
CREATE INDEX IF NOT EXISTS idx_episodes_promoted ON episodes(promoted_to_mem0);
CREATE INDEX IF NOT EXISTS idx_episodes_deleted ON episodes(is_deleted);


-- Promotion proposals table
CREATE TABLE IF NOT EXISTS promotion_proposals (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    user_id TEXT NOT NULL,

    -- Proposal content
    target_path TEXT,
    proposed_value TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence TEXT,  -- JSON array of episode IDs

    -- Status
    status TEXT DEFAULT 'pending',
    user_response TEXT,

    -- Temporal
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    resolved_at TEXT,

    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Indexes for promotion proposals
CREATE INDEX IF NOT EXISTS idx_proposals_status ON promotion_proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_user_id ON promotion_proposals(user_id);
CREATE INDEX IF NOT EXISTS idx_proposals_expires ON promotion_proposals(expires_at);
CREATE INDEX IF NOT EXISTS idx_proposals_episode ON promotion_proposals(episode_id);


-- User decisions log (for learning preferences)
CREATE TABLE IF NOT EXISTS user_decisions (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    user_id TEXT NOT NULL,

    decision TEXT NOT NULL,
    original_value TEXT,
    final_value TEXT,
    reason TEXT,

    created_at TEXT NOT NULL,

    FOREIGN KEY (proposal_id) REFERENCES promotion_proposals(id)
);

-- Indexes for user decisions
CREATE INDEX IF NOT EXISTS idx_decisions_user ON user_decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_proposal ON user_decisions(proposal_id);
CREATE INDEX IF NOT EXISTS idx_decisions_decision ON user_decisions(decision);


-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Record this migration
INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (1, datetime('now'));
