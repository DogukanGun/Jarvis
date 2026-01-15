"""
Episode Storage Interface and Implementations

Provides abstract interface for episodic memory storage with in-memory
implementation for testing.
"""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from episode_schema import Episode, EpisodeQuery, EpisodeSearchResult, EpisodeRetrievalResult
import time


class EpisodeStorage(ABC):
    """Abstract interface for episode storage"""

    @abstractmethod
    def insert(self, episode: Episode) -> bool:
        """
        Insert a new episode.

        Args:
            episode: Episode to insert

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_by_id(self, episode_id: str) -> Optional[Episode]:
        """
        Retrieve episode by ID.

        Args:
            episode_id: Episode identifier

        Returns:
            Episode if found, None otherwise
        """
        pass

    @abstractmethod
    def search(self, query: EpisodeQuery) -> EpisodeRetrievalResult:
        """
        Search for episodes matching query.

        Args:
            query: Search query with filters and ranking

        Returns:
            Retrieval result with ranked episodes
        """
        pass

    @abstractmethod
    def update(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update episode fields.

        Args:
            episode_id: Episode to update
            updates: Field updates

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def delete(self, episode_id: str, soft: bool = True) -> bool:
        """
        Delete episode.

        Args:
            episode_id: Episode to delete
            soft: If True, set is_deleted flag; if False, remove completely

        Returns:
            True if successful
        """
        pass


class InMemoryEpisodeStorage(EpisodeStorage):
    """
    In-memory episode storage for testing and development.

    Implements simple semantic search using cosine similarity.
    """

    def __init__(self):
        """Initialize empty storage"""
        self.episodes: Dict[str, Episode] = {}

    def insert(self, episode: Episode) -> bool:
        """Insert episode into memory"""
        episode_id = episode.get("id")
        if not episode_id:
            return False

        self.episodes[episode_id] = episode
        return True

    def get_by_id(self, episode_id: str) -> Optional[Episode]:
        """Get episode by ID"""
        return self.episodes.get(episode_id)

    def search(self, query: EpisodeQuery) -> EpisodeRetrievalResult:
        """
        Search episodes with filtering, semantic search, and ranking.
        """
        start_time = time.time()

        user_id = query.get("user_id")
        if not user_id:
            return {
                "episodes": [],
                "total_count": 0,
                "query_time_ms": 0.0,
                "used_filters": {},
                "metadata": {"error": "user_id is required"}
            }

        # Step 1: Filter episodes
        candidates = self._filter_episodes(query)

        # Step 2: Compute scores (semantic + ranking)
        scored_results = self._score_episodes(candidates, query)

        # Step 3: Sort by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)

        # Step 4: Apply pagination
        limit = query.get("limit", 10)
        offset = query.get("offset", 0)
        total_count = len(scored_results)
        paginated = scored_results[offset:offset + limit]

        query_time_ms = (time.time() - start_time) * 1000

        return {
            "episodes": paginated,
            "total_count": total_count,
            "query_time_ms": query_time_ms,
            "used_filters": self._get_used_filters(query),
            "metadata": {}
        }

    def _filter_episodes(self, query: EpisodeQuery) -> List[Episode]:
        """Apply filters to episodes"""
        user_id = query.get("user_id")
        candidates = []

        for episode in self.episodes.values():
            # User filter
            if episode.get("user_id") != user_id:
                continue

            # Skip deleted (unless explicitly requested)
            if episode.get("is_deleted", False):
                continue

            # Task type filter
            task_types = query.get("task_types")
            if task_types and episode.get("task_type") not in task_types:
                continue

            # App filter
            apps = query.get("apps")
            if apps and episode.get("app") not in apps:
                continue

            # Episode type filter
            episode_types = query.get("episode_types")
            if episode_types and episode.get("episode_type") not in episode_types:
                continue

            # Entity filter (episode must contain at least one query entity)
            query_entities = query.get("entities")
            if query_entities:
                episode_entities = set(episode.get("entities", []))
                query_entity_set = set(query_entities)
                if not episode_entities.intersection(query_entity_set):
                    continue

            # Tags filter
            query_tags = query.get("tags")
            if query_tags:
                episode_tags = set(episode.get("tags", []))
                query_tag_set = set(query_tags)
                if not episode_tags.intersection(query_tag_set):
                    continue

            # Temporal filters
            after = query.get("after_timestamp")
            if after and episode.get("timestamp", "") < after:
                continue

            before = query.get("before_timestamp")
            if before and episode.get("timestamp", "") > before:
                continue

            # Quality filters
            min_importance = query.get("min_importance", 0.0)
            if episode.get("importance_score", 0.0) < min_importance:
                continue

            min_confidence = query.get("min_confidence", 0.0)
            if episode.get("confidence", 0.0) < min_confidence:
                continue

            # Verified only
            if query.get("verified_only", False) and not episode.get("verified", False):
                continue

            candidates.append(episode)

        return candidates

    def _score_episodes(
        self,
        candidates: List[Episode],
        query: EpisodeQuery
    ) -> List[EpisodeSearchResult]:
        """Score and rank episodes"""
        results = []

        query_text = query.get("query_text")
        query_embedding = query.get("query_embedding")

        for episode in candidates:
            score = 0.0
            match_reasons = []

            # Semantic similarity (if embeddings available)
            if query_embedding and episode.get("embedding"):
                semantic_score = self._cosine_similarity(
                    query_embedding,
                    episode["embedding"]
                )
                score += semantic_score * 0.6  # 60% weight for semantic match
                if semantic_score > 0.5:
                    match_reasons.append(f"Semantic similarity: {semantic_score:.2f}")

            # Text overlap (simple fallback if no embeddings)
            elif query_text:
                text_score = self._text_overlap_score(
                    query_text,
                    episode.get("text", "")
                )
                score += text_score * 0.4  # 40% weight for text overlap
                if text_score > 0.3:
                    match_reasons.append(f"Text overlap: {text_score:.2f}")

            # Base score from importance
            importance = episode.get("importance_score", 0.5)
            score += importance * 0.2  # 20% weight
            if importance > 0.7:
                match_reasons.append(f"High importance: {importance:.2f}")

            # Boost for reinforcement
            if query.get("boost_reinforced", True):
                reinforcement = episode.get("reinforcement_count", 0)
                if reinforcement > 0:
                    boost = min(0.1, reinforcement * 0.02)  # Up to 10% boost
                    score += boost
                    if reinforcement > 2:
                        match_reasons.append(f"Reinforced {reinforcement}x")

            # Boost for recency
            if query.get("boost_recent", True):
                recency_boost = self._recency_boost(episode.get("timestamp", ""))
                score += recency_boost * 0.1  # Up to 10% boost
                if recency_boost > 0.5:
                    match_reasons.append("Recent episode")

            # Confidence factor
            confidence = episode.get("confidence", 1.0)
            score *= confidence  # Scale by confidence

            # Normalize score to 0-1 range
            score = max(0.0, min(1.0, score))

            if not match_reasons:
                match_reasons.append("Base match")

            results.append({
                "episode": episode,
                "score": score,
                "match_reasons": match_reasons
            })

        return results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _text_overlap_score(self, text1: str, text2: str) -> float:
        """Simple text overlap scoring (Jaccard similarity)"""
        if not text1 or not text2:
            return 0.0

        # Tokenize and lowercase
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        return len(intersection) / len(union) if union else 0.0

    def _recency_boost(self, timestamp: str) -> float:
        """
        Calculate recency boost (0.0 to 1.0).

        More recent episodes get higher boost.
        """
        if not timestamp:
            return 0.0

        try:
            from datetime import datetime
            episode_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.utcnow()
            age_seconds = (now - episode_time.replace(tzinfo=None)).total_seconds()

            # Boost decays over 30 days
            max_age = 30 * 24 * 3600  # 30 days
            if age_seconds <= 0:
                return 1.0
            elif age_seconds >= max_age:
                return 0.0
            else:
                return 1.0 - (age_seconds / max_age)
        except Exception:
            return 0.0

    def _get_used_filters(self, query: EpisodeQuery) -> Dict[str, Any]:
        """Extract which filters were used"""
        used = {}

        filter_keys = [
            "task_types", "apps", "episode_types", "entities", "tags",
            "after_timestamp", "before_timestamp", "recent_days",
            "min_importance", "min_confidence", "verified_only"
        ]

        for key in filter_keys:
            value = query.get(key)
            if value is not None:
                used[key] = value

        return used

    def update(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        """Update episode fields"""
        episode = self.episodes.get(episode_id)
        if not episode:
            return False

        for key, value in updates.items():
            episode[key] = value

        return True

    def delete(self, episode_id: str, soft: bool = True) -> bool:
        """Delete episode"""
        if episode_id not in self.episodes:
            return False

        if soft:
            self.episodes[episode_id]["is_deleted"] = True
        else:
            del self.episodes[episode_id]

        return True

    def clear(self):
        """Clear all episodes (for testing)"""
        self.episodes.clear()

    def count(self) -> int:
        """Get total episode count"""
        return len(self.episodes)


# Global storage instance (can be replaced with persistent storage)
_storage_instance: Optional[EpisodeStorage] = None


def get_episode_storage() -> EpisodeStorage:
    """
    Factory function to get episode storage instance.

    Can be monkeypatched in tests or replaced with persistent storage.

    Returns:
        EpisodeStorage instance
    """
    global _storage_instance

    if _storage_instance is None:
        _storage_instance = InMemoryEpisodeStorage()

    return _storage_instance


def set_episode_storage(storage: EpisodeStorage):
    """
    Set the global storage instance.

    Args:
        storage: Storage implementation to use
    """
    global _storage_instance
    _storage_instance = storage
