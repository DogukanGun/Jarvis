"""
Episode Repository

SQLite-based storage for episodes with CRUD operations.
"""

import sqlite3
import json
import struct
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
import logging

from .episode_schema import (
    Episode,
    EpisodeQuery,
    EpisodeSearchResult,
    EpisodeSearchResponse,
    PromotionProposal,
    UserDecision,
)

logger = logging.getLogger(__name__)


def _serialize_embedding(embedding: Optional[List[float]]) -> Optional[bytes]:
    """Serialize embedding list to bytes for SQLite BLOB storage"""
    if embedding is None:
        return None
    return struct.pack(f'{len(embedding)}f', *embedding)


def _deserialize_embedding(blob: Optional[bytes]) -> Optional[List[float]]:
    """Deserialize bytes back to embedding list"""
    if blob is None:
        return None
    count = len(blob) // 4  # 4 bytes per float
    return list(struct.unpack(f'{count}f', blob))


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EpisodeRepository:
    """SQLite repository for episode storage"""

    def __init__(self, db_path: str):
        """
        Initialize repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _ensure_schema(self):
        """Ensure database schema is initialized"""
        migrations_dir = Path(__file__).parent / "migrations"
        migration_file = migrations_dir / "001_initial_schema.sql"

        if migration_file.exists():
            with open(migration_file, 'r') as f:
                schema_sql = f.read()

            conn = self._get_connection()
            conn.executescript(schema_sql)
            conn.commit()
            logger.info(f"Database schema initialized at {self.db_path}")

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    # =========================================================================
    # Episode CRUD
    # =========================================================================

    def insert_episode(self, episode: Episode) -> str:
        """
        Insert a new episode.

        Args:
            episode: Episode to insert

        Returns:
            Episode ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        episode.created_at = datetime.fromisoformat(now)
        episode.updated_at = datetime.fromisoformat(now)

        cursor.execute("""
            INSERT INTO episodes (
                id, user_id, fingerprint, text, summary,
                episode_type, task_type, app, entities,
                first_seen, last_seen, embedding, embedding_model,
                importance_score, confidence, reinforcement_count,
                is_deleted, promoted_to_mem0, promotion_proposal_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.id,
            episode.user_id,
            episode.fingerprint,
            episode.text,
            episode.summary,
            episode.episode_type,
            episode.task_type,
            episode.app,
            json.dumps(episode.entities),
            episode.first_seen.isoformat(),
            episode.last_seen.isoformat(),
            _serialize_embedding(episode.embedding),
            episode.embedding_model,
            episode.importance_score,
            episode.confidence,
            episode.reinforcement_count,
            1 if episode.is_deleted else 0,
            1 if episode.promoted_to_mem0 else 0,
            episode.promotion_proposal_id,
            now,
            now
        ))

        conn.commit()
        logger.debug(f"Inserted episode: {episode.id}")
        return episode.id

    def get_episode_by_id(self, episode_id: str) -> Optional[Episode]:
        """Get episode by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_episode(row)

    def get_episode_by_fingerprint(
        self,
        user_id: str,
        fingerprint: str
    ) -> Optional[Episode]:
        """
        Get episode by user_id and fingerprint.

        Used for deduplication lookup.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM episodes
            WHERE user_id = ? AND fingerprint = ? AND is_deleted = 0
            ORDER BY last_seen DESC
            LIMIT 1
        """, (user_id, fingerprint))

        row = cursor.fetchone()
        if row is None:
            return None

        return self._row_to_episode(row)

    def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update episode fields.

        Args:
            episode_id: Episode ID
            updates: Dict of field names to new values

        Returns:
            True if updated, False if not found
        """
        if not updates:
            return False

        conn = self._get_connection()
        cursor = conn.cursor()

        # Always update updated_at
        updates['updated_at'] = datetime.utcnow().isoformat()

        # Handle special fields
        if 'entities' in updates and isinstance(updates['entities'], list):
            updates['entities'] = json.dumps(updates['entities'])
        if 'embedding' in updates:
            updates['embedding'] = _serialize_embedding(updates['embedding'])
        if 'is_deleted' in updates:
            updates['is_deleted'] = 1 if updates['is_deleted'] else 0
        if 'promoted_to_mem0' in updates:
            updates['promoted_to_mem0'] = 1 if updates['promoted_to_mem0'] else 0

        # Build UPDATE query
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [episode_id]

        cursor.execute(f"""
            UPDATE episodes SET {set_clause} WHERE id = ?
        """, values)

        conn.commit()
        return cursor.rowcount > 0

    def reinforce_episode(self, episode_id: str) -> bool:
        """
        Reinforce an episode (increment count, update last_seen).

        Args:
            episode_id: Episode ID

        Returns:
            True if reinforced, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute("""
            UPDATE episodes
            SET reinforcement_count = reinforcement_count + 1,
                last_seen = ?,
                updated_at = ?
            WHERE id = ? AND is_deleted = 0
        """, (now, now, episode_id))

        conn.commit()
        return cursor.rowcount > 0

    def soft_delete_episode(self, episode_id: str) -> bool:
        """Soft delete an episode"""
        return self.update_episode(episode_id, {'is_deleted': True})

    # =========================================================================
    # Episode Search
    # =========================================================================

    def search_episodes(self, query: EpisodeQuery) -> EpisodeSearchResponse:
        """
        Search episodes with filters and ranking.

        Args:
            query: Search query parameters

        Returns:
            Search response with ranked results
        """
        import time
        start_time = time.time()

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build WHERE clause
        conditions = ["user_id = ?", "is_deleted = 0"]
        params: List[Any] = [query.user_id]
        used_filters: Dict[str, Any] = {"user_id": query.user_id}

        # Task type filter
        if query.task_types:
            placeholders = ",".join("?" * len(query.task_types))
            conditions.append(f"task_type IN ({placeholders})")
            params.extend(query.task_types)
            used_filters["task_types"] = query.task_types

        # App filter
        if query.apps:
            placeholders = ",".join("?" * len(query.apps))
            conditions.append(f"app IN ({placeholders})")
            params.extend(query.apps)
            used_filters["apps"] = query.apps

        # Episode type filter
        if query.episode_types:
            placeholders = ",".join("?" * len(query.episode_types))
            conditions.append(f"episode_type IN ({placeholders})")
            params.extend([str(t) for t in query.episode_types])
            used_filters["episode_types"] = [str(t) for t in query.episode_types]

        # Temporal filters
        if query.after_timestamp:
            conditions.append("last_seen >= ?")
            params.append(query.after_timestamp.isoformat())
            used_filters["after_timestamp"] = query.after_timestamp.isoformat()

        if query.before_timestamp:
            conditions.append("last_seen <= ?")
            params.append(query.before_timestamp.isoformat())
            used_filters["before_timestamp"] = query.before_timestamp.isoformat()

        if query.recent_days:
            cutoff = datetime.utcnow() - timedelta(days=query.recent_days)
            conditions.append("last_seen >= ?")
            params.append(cutoff.isoformat())
            used_filters["recent_days"] = query.recent_days

        # Quality filters
        if query.min_importance is not None:
            conditions.append("importance_score >= ?")
            params.append(query.min_importance)
            used_filters["min_importance"] = query.min_importance

        if query.min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(query.min_confidence)
            used_filters["min_confidence"] = query.min_confidence

        if query.min_reinforcement is not None:
            conditions.append("reinforcement_count >= ?")
            params.append(query.min_reinforcement)
            used_filters["min_reinforcement"] = query.min_reinforcement

        # Build and execute query
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM episodes WHERE {where_clause}"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Convert to episodes and score
        results: List[EpisodeSearchResult] = []
        for row in rows:
            episode = self._row_to_episode(row)
            score, reasons = self._score_episode(episode, query)
            results.append(EpisodeSearchResult(
                episode=episode,
                score=score,
                match_reasons=reasons
            ))

        # Sort by score (descending)
        results.sort(key=lambda r: r.score, reverse=True)

        # Get total count before pagination
        total_count = len(results)

        # Apply pagination
        start = query.offset
        end = start + query.limit
        paginated = results[start:end]

        query_time_ms = (time.time() - start_time) * 1000

        return EpisodeSearchResponse(
            episodes=paginated,
            total_count=total_count,
            query_time_ms=query_time_ms,
            used_filters=used_filters
        )

    def _score_episode(
        self,
        episode: Episode,
        query: EpisodeQuery
    ) -> Tuple[float, List[str]]:
        """
        Score an episode based on query relevance.

        Returns:
            Tuple of (score, match_reasons)
        """
        score = 0.0
        reasons: List[str] = []

        # Semantic similarity (if embeddings available)
        if query.query_embedding and episode.embedding:
            sim = _cosine_similarity(query.query_embedding, episode.embedding)
            score += sim * 0.6  # 60% weight
            if sim > 0.7:
                reasons.append(f"semantic_match:{sim:.2f}")

        # Text overlap (fallback if no embeddings)
        if query.query_text and not query.query_embedding:
            query_words = set(query.query_text.lower().split())
            episode_words = set(episode.text.lower().split())
            if query_words and episode_words:
                overlap = len(query_words & episode_words) / len(query_words | episode_words)
                score += overlap * 0.4
                if overlap > 0.3:
                    reasons.append(f"text_overlap:{overlap:.2f}")

        # Entity matching
        if query.entities and episode.entities:
            query_entities = set(e.lower() for e in query.entities)
            episode_entities = set(e.lower() for e in episode.entities)
            matches = query_entities & episode_entities
            if matches:
                entity_score = len(matches) / len(query_entities)
                score += entity_score * 0.2
                reasons.append(f"entity_match:{len(matches)}")

        # Importance score contribution
        score += episode.importance_score * 0.1
        if episode.importance_score > 0.7:
            reasons.append("high_importance")

        # Recency boost
        if query.boost_recent:
            days_old = (datetime.utcnow() - episode.last_seen).days
            recency_boost = max(0, 1 - (days_old / 30)) * 0.1
            score += recency_boost
            if days_old < 7:
                reasons.append("recent")

        # Reinforcement boost
        if query.boost_reinforced:
            reinforcement_boost = min(episode.reinforcement_count / 10, 0.1)
            score += reinforcement_boost
            if episode.reinforcement_count >= 3:
                reasons.append(f"reinforced:{episode.reinforcement_count}x")

        # Confidence scaling
        score *= episode.confidence

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        return score, reasons

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        """Convert SQLite row to Episode model"""
        return Episode(
            id=row['id'],
            user_id=row['user_id'],
            fingerprint=row['fingerprint'],
            text=row['text'],
            summary=row['summary'],
            episode_type=row['episode_type'],
            task_type=row['task_type'],
            app=row['app'],
            entities=json.loads(row['entities']) if row['entities'] else [],
            first_seen=datetime.fromisoformat(row['first_seen']),
            last_seen=datetime.fromisoformat(row['last_seen']),
            embedding=_deserialize_embedding(row['embedding']),
            embedding_model=row['embedding_model'],
            importance_score=row['importance_score'],
            confidence=row['confidence'],
            reinforcement_count=row['reinforcement_count'],
            is_deleted=bool(row['is_deleted']),
            promoted_to_mem0=bool(row['promoted_to_mem0']),
            promotion_proposal_id=row['promotion_proposal_id'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    # =========================================================================
    # Promotion Proposals
    # =========================================================================

    def insert_proposal(self, proposal: PromotionProposal) -> str:
        """Insert a new promotion proposal"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO promotion_proposals (
                id, episode_id, user_id, target_path, proposed_value,
                confidence, evidence, status, user_response,
                created_at, expires_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal.id,
            proposal.episode_id,
            proposal.user_id,
            proposal.target_path,
            proposal.proposed_value,
            proposal.confidence,
            json.dumps(proposal.evidence),
            proposal.status,
            proposal.user_response,
            proposal.created_at.isoformat(),
            proposal.expires_at.isoformat(),
            proposal.resolved_at.isoformat() if proposal.resolved_at else None
        ))

        conn.commit()
        return proposal.id

    def get_pending_proposals(self, user_id: Optional[str] = None) -> List[PromotionProposal]:
        """Get all pending proposals, optionally filtered by user"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if user_id:
            cursor.execute("""
                SELECT * FROM promotion_proposals
                WHERE status = 'pending' AND user_id = ?
                ORDER BY created_at ASC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM promotion_proposals
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)

        rows = cursor.fetchall()
        return [self._row_to_proposal(row) for row in rows]

    def update_proposal_status(
        self,
        proposal_id: str,
        status: str,
        user_response: Optional[str] = None
    ) -> bool:
        """Update proposal status"""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute("""
            UPDATE promotion_proposals
            SET status = ?, user_response = ?, resolved_at = ?
            WHERE id = ?
        """, (status, user_response, now, proposal_id))

        conn.commit()
        return cursor.rowcount > 0

    def _row_to_proposal(self, row: sqlite3.Row) -> PromotionProposal:
        """Convert SQLite row to PromotionProposal model"""
        return PromotionProposal(
            id=row['id'],
            episode_id=row['episode_id'],
            user_id=row['user_id'],
            target_path=row['target_path'],
            proposed_value=row['proposed_value'],
            confidence=row['confidence'],
            evidence=json.loads(row['evidence']) if row['evidence'] else [],
            status=row['status'],
            user_response=row['user_response'],
            created_at=datetime.fromisoformat(row['created_at']),
            expires_at=datetime.fromisoformat(row['expires_at']),
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None
        )

    # =========================================================================
    # User Decisions
    # =========================================================================

    def insert_decision(self, decision: UserDecision) -> str:
        """Insert a user decision record"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_decisions (
                id, proposal_id, user_id, decision,
                original_value, final_value, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.id,
            decision.proposal_id,
            decision.user_id,
            decision.decision,
            decision.original_value,
            decision.final_value,
            decision.reason,
            decision.created_at.isoformat()
        ))

        conn.commit()
        return decision.id

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_recent_episodes(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 100
    ) -> List[Episode]:
        """Get recent episodes for reflection graph"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = datetime.utcnow() - timedelta(days=days)

        cursor.execute("""
            SELECT * FROM episodes
            WHERE user_id = ? AND last_seen >= ? AND is_deleted = 0
            ORDER BY last_seen DESC
            LIMIT ?
        """, (user_id, cutoff.isoformat(), limit))

        rows = cursor.fetchall()
        return [self._row_to_episode(row) for row in rows]

    def get_promotion_candidates(
        self,
        user_id: str,
        min_count: int = 3,
        min_confidence: float = 0.7
    ) -> List[Episode]:
        """Get episodes ready for promotion"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM episodes
            WHERE user_id = ?
              AND reinforcement_count >= ?
              AND confidence >= ?
              AND promoted_to_mem0 = 0
              AND is_deleted = 0
            ORDER BY reinforcement_count DESC, last_seen DESC
        """, (user_id, min_count, min_confidence))

        rows = cursor.fetchall()
        return [self._row_to_episode(row) for row in rows]

    def get_active_users(self, days: int = 7) -> List[str]:
        """
        Get list of users with recent activity.

        Args:
            days: Number of days to look back

        Returns:
            List of user IDs
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = datetime.utcnow() - timedelta(days=days)

        cursor.execute("""
            SELECT DISTINCT user_id FROM episodes
            WHERE last_seen >= ? AND is_deleted = 0
            ORDER BY user_id
        """, (cutoff.isoformat(),))

        rows = cursor.fetchall()
        return [row['user_id'] for row in rows]

    def get_proposal(self, proposal_id: str) -> Optional[PromotionProposal]:
        """
        Get a promotion proposal by ID.

        Args:
            proposal_id: Proposal ID

        Returns:
            PromotionProposal or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM promotion_proposals WHERE id = ?
        """, (proposal_id,))

        row = cursor.fetchone()
        if row is None:
            return None

        return self._row_to_proposal(row)

    def get_episodes_by_fingerprints(
        self,
        user_id: str,
        fingerprints: List[str]
    ) -> Dict[str, Episode]:
        """
        Get multiple episodes by their fingerprints.

        Args:
            user_id: User ID
            fingerprints: List of fingerprints

        Returns:
            Dict mapping fingerprint to Episode
        """
        if not fingerprints:
            return {}

        conn = self._get_connection()
        cursor = conn.cursor()

        placeholders = ",".join("?" * len(fingerprints))
        cursor.execute(f"""
            SELECT * FROM episodes
            WHERE user_id = ? AND fingerprint IN ({placeholders}) AND is_deleted = 0
        """, [user_id] + fingerprints)

        rows = cursor.fetchall()
        return {row['fingerprint']: self._row_to_episode(row) for row in rows}


# Global repository instance
_repository_instance: Optional[EpisodeRepository] = None
_repository_lock = threading.Lock()


def get_episode_repository(db_path: Optional[str] = None) -> EpisodeRepository:
    """
    Get singleton repository instance.

    Args:
        db_path: Optional database path override

    Returns:
        EpisodeRepository instance
    """
    global _repository_instance

    with _repository_lock:
        if _repository_instance is None:
            from app.config import config
            path = db_path or config.SQLITE_DB_PATH
            _repository_instance = EpisodeRepository(path)

        return _repository_instance


def _reset_repository():
    """Reset repository instance (for testing)"""
    global _repository_instance
    with _repository_lock:
        if _repository_instance:
            _repository_instance.close()
        _repository_instance = None
