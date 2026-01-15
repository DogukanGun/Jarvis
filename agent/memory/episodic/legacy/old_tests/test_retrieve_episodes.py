"""
Unit tests for retrieve_episodes_node.py

Tests cover:
- Query building from state
- Episode retrieval with filters
- Semantic search and ranking
- Error handling
- Utility functions
"""

import pytest
from datetime import datetime, timedelta
from episode_schema import create_episode, EpisodeType, Episode
from episode_storage import InMemoryEpisodeStorage
from retrieve_episodes_node import (
    build_episode_query,
    retrieve_episodes,
    filter_episodes_by_relevance,
    get_top_episodes,
    extract_episode_context,
    GraphState,
)


# ============================================================================
# FIXTURES AND HELPERS
# ============================================================================

def create_test_storage_with_episodes() -> InMemoryEpisodeStorage:
    """Create storage with test episodes"""
    storage = InMemoryEpisodeStorage()

    # Episode 1: Email task, high importance
    ep1 = create_episode(
        user_id="test_user",
        text="Sent email to john@example.com about project update",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="send_email",
        app="gmail",
        entities=["john@example.com", "gmail"],
        importance_score=0.8,
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]  # Dummy embedding
    )
    storage.insert(ep1)

    # Episode 2: Form filling, medium importance
    ep2 = create_episode(
        user_id="test_user",
        text="Filled out job application form on LinkedIn",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="fill_form",
        app="linkedin",
        entities=["linkedin"],
        importance_score=0.6,
        embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
    )
    storage.insert(ep2)

    # Episode 3: Login, recent
    ep3 = create_episode(
        user_id="test_user",
        text="Logged into Gmail with 2FA authentication",
        episode_type=EpisodeType.INTERACTION,
        task_type="login_auth",
        app="gmail",
        entities=["gmail"],
        importance_score=0.5,
        embedding=[0.3, 0.4, 0.5, 0.6, 0.7]
    )
    storage.insert(ep3)

    # Episode 4: Different user (should not match)
    ep4 = create_episode(
        user_id="other_user",
        text="Other user's email task",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="send_email",
        app="gmail",
        entities=["gmail"],
        importance_score=0.9
    )
    storage.insert(ep4)

    # Episode 5: Low importance (below threshold)
    ep5 = create_episode(
        user_id="test_user",
        text="Minor system observation",
        episode_type=EpisodeType.OBSERVATION,
        importance_score=0.2,
        embedding=[0.1, 0.1, 0.1, 0.1, 0.1]
    )
    storage.insert(ep5)

    return storage


# ============================================================================
# TESTS: build_episode_query
# ============================================================================

class TestBuildEpisodeQuery:
    """Tests for build_episode_query function"""

    def test_basic_query_construction(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "send email to john",
        }

        query = build_episode_query(state)

        assert query["user_id"] == "test_user"
        assert query["query_text"] == "send email to john"
        assert query["limit"] == 10  # DEFAULT_LIMIT
        assert query["boost_recent"] is True
        assert query["boost_reinforced"] is True

    def test_query_with_task_type(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "send email",
            "task_type": "send_email",
        }

        query = build_episode_query(state)

        assert "task_types" in query
        assert query["task_types"] == ["send_email"]

    def test_query_skips_unknown_task_type(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "hello",
            "task_type": "unknown",
        }

        query = build_episode_query(state)

        assert "task_types" not in query

    def test_query_skips_chat_task_type(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "how are you",
            "task_type": "chat",
        }

        query = build_episode_query(state)

        assert "task_types" not in query

    def test_query_with_app(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "check email",
            "app": "gmail",
        }

        query = build_episode_query(state)

        assert "apps" in query
        assert query["apps"] == ["gmail"]

    def test_query_with_entities(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "email to john@test.com",
            "entities": ["john@test.com", "gmail"],
        }

        query = build_episode_query(state)

        assert "entities" in query
        assert query["entities"] == ["john@test.com", "gmail"]

    def test_query_with_embedding(self):
        embedding = [0.1, 0.2, 0.3]
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "test query",
            "query_embedding": embedding,
        }

        query = build_episode_query(state)

        assert query["query_embedding"] == embedding

    def test_query_with_context_overrides(self):
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "test",
            "context": {
                "episode_limit": 5,
                "episode_min_importance": 0.7,
                "episode_min_confidence": 0.8,
                "episode_recent_days": 7,
            }
        }

        query = build_episode_query(state)

        assert query["limit"] == 5
        assert query["min_importance"] == 0.7
        assert query["min_confidence"] == 0.8
        assert query["recent_days"] == 7


# ============================================================================
# TESTS: retrieve_episodes
# ============================================================================

class TestRetrieveEpisodes:
    """Tests for retrieve_episodes node function"""

    def test_missing_user_id_returns_error(self):
        state: GraphState = {
            "normalized_prompt": "test query"
        }

        result = retrieve_episodes(state)

        assert result["episode_retrieval_error"] is not None
        assert "user_id" in result["episode_retrieval_error"]
        assert result["retrieved_episodes"] == []

    def test_retrieve_with_empty_storage(self):
        storage = InMemoryEpisodeStorage()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "send email",
        }

        result = retrieve_episodes(state, storage=storage)

        assert result["episode_retrieval_error"] is None
        assert result["retrieved_episodes"] == []
        assert result["episode_retrieval_meta"]["episodes_found"] == 0

    def test_retrieve_basic(self):
        storage = create_test_storage_with_episodes()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "email",
        }

        result = retrieve_episodes(state, storage=storage)

        assert result["episode_retrieval_error"] is None
        episodes = result["retrieved_episodes"]
        assert len(episodes) > 0

        # Should only get test_user's episodes
        for ep_result in episodes:
            assert ep_result["episode"]["user_id"] == "test_user"

    def test_retrieve_filters_by_task_type(self):
        storage = create_test_storage_with_episodes()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "send email",
            "task_type": "send_email",
        }

        result = retrieve_episodes(state, storage=storage)

        episodes = result["retrieved_episodes"]

        # Should only get send_email tasks
        for ep_result in episodes:
            episode = ep_result["episode"]
            assert episode.get("task_type") == "send_email"

    def test_retrieve_filters_by_app(self):
        storage = create_test_storage_with_episodes()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "check gmail",
            "app": "gmail",
        }

        result = retrieve_episodes(state, storage=storage)

        episodes = result["retrieved_episodes"]

        # Should only get gmail episodes
        for ep_result in episodes:
            episode = ep_result["episode"]
            assert episode.get("app") == "gmail"

    def test_retrieve_filters_by_entities(self):
        storage = create_test_storage_with_episodes()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "email john",
            "entities": ["john@example.com"],
        }

        result = retrieve_episodes(state, storage=storage)

        episodes = result["retrieved_episodes"]

        # Should get episodes with matching entities
        for ep_result in episodes:
            episode = ep_result["episode"]
            ep_entities = episode.get("entities", [])
            assert "john@example.com" in ep_entities

    def test_retrieve_respects_min_importance(self):
        storage = create_test_storage_with_episodes()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "task",
            "context": {
                "episode_min_importance": 0.5
            }
        }

        result = retrieve_episodes(state, storage=storage)

        episodes = result["retrieved_episodes"]

        # All episodes should have importance >= 0.5
        for ep_result in episodes:
            episode = ep_result["episode"]
            assert episode.get("importance_score", 0.0) >= 0.5

    def test_retrieve_with_semantic_search(self):
        storage = create_test_storage_with_episodes()

        # Query embedding similar to episode 1
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "email task",
            "query_embedding": query_embedding,
        }

        result = retrieve_episodes(state, storage=storage)

        episodes = result["retrieved_episodes"]
        assert len(episodes) > 0

        # Episodes should be ranked by similarity
        # First episode should have highest score
        scores = [ep["score"] for ep in episodes]
        assert scores == sorted(scores, reverse=True)

    def test_retrieve_metadata(self):
        storage = create_test_storage_with_episodes()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "email",
        }

        result = retrieve_episodes(state, storage=storage)

        meta = result["episode_retrieval_meta"]
        assert meta["query_built"] is True
        assert "episodes_found" in meta
        assert "query_time_ms" in meta
        assert "used_filters" in meta

    def test_retrieve_handles_exception(self):
        # Create a storage that will raise an error
        class BrokenStorage(InMemoryEpisodeStorage):
            def search(self, query):
                raise Exception("Storage error")

        storage = BrokenStorage()
        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "test",
        }

        result = retrieve_episodes(state, storage=storage)

        assert result["episode_retrieval_error"] is not None
        assert "Error retrieving episodes" in result["episode_retrieval_error"]
        assert result["retrieved_episodes"] == []


# ============================================================================
# TESTS: Utility Functions
# ============================================================================

class TestFilterEpisodesByRelevance:
    """Tests for filter_episodes_by_relevance"""

    def test_filters_by_min_score(self):
        episodes = [
            {"episode": {"id": "1"}, "score": 0.8, "match_reasons": []},
            {"episode": {"id": "2"}, "score": 0.5, "match_reasons": []},
            {"episode": {"id": "3"}, "score": 0.2, "match_reasons": []},
        ]

        filtered = filter_episodes_by_relevance(episodes, min_score=0.4)

        assert len(filtered) == 2
        assert filtered[0]["episode"]["id"] == "1"
        assert filtered[1]["episode"]["id"] == "2"

    def test_empty_list_returns_empty(self):
        filtered = filter_episodes_by_relevance([], min_score=0.5)
        assert filtered == []


class TestGetTopEpisodes:
    """Tests for get_top_episodes"""

    def test_gets_top_n(self):
        episodes = [
            {"episode": {"id": str(i)}, "score": 1.0 - i * 0.1, "match_reasons": []}
            for i in range(10)
        ]

        top = get_top_episodes(episodes, n=3)

        assert len(top) == 3
        assert top[0]["episode"]["id"] == "0"
        assert top[1]["episode"]["id"] == "1"
        assert top[2]["episode"]["id"] == "2"

    def test_handles_less_than_n(self):
        episodes = [
            {"episode": {"id": "1"}, "score": 0.9, "match_reasons": []},
        ]

        top = get_top_episodes(episodes, n=5)
        assert len(top) == 1


class TestExtractEpisodeContext:
    """Tests for extract_episode_context"""

    def test_empty_episodes(self):
        context = extract_episode_context([])

        assert context["has_episodes"] is False
        assert context["episode_count"] == 0

    def test_extracts_common_patterns(self):
        episodes = [
            {
                "episode": create_episode(
                    user_id="user",
                    text="task 1",
                    episode_type=EpisodeType.TASK_COMPLETION,
                    task_type="send_email",
                    app="gmail",
                    entities=["john@test.com", "gmail"],
                    importance_score=0.8
                ),
                "score": 0.9,
                "match_reasons": []
            },
            {
                "episode": create_episode(
                    user_id="user",
                    text="task 2",
                    episode_type=EpisodeType.TASK_COMPLETION,
                    task_type="send_email",
                    app="gmail",
                    entities=["jane@test.com", "gmail"],
                    importance_score=0.6
                ),
                "score": 0.7,
                "match_reasons": []
            },
        ]

        context = extract_episode_context(episodes)

        assert context["has_episodes"] is True
        assert context["episode_count"] == 2
        assert context["most_common_task_type"] == "send_email"
        assert context["most_common_app"] == "gmail"
        assert "gmail" in context["top_entities"]
        assert context["avg_importance"] == 0.7  # (0.8 + 0.6) / 2
        assert context["avg_score"] == 0.8  # (0.9 + 0.7) / 2

    def test_handles_missing_fields(self):
        episodes = [
            {
                "episode": create_episode(
                    user_id="user",
                    text="minimal episode",
                    episode_type=EpisodeType.OBSERVATION
                ),
                "score": 0.5,
                "match_reasons": []
            }
        ]

        context = extract_episode_context(episodes)

        assert context["has_episodes"] is True
        assert context["most_common_task_type"] is None
        assert context["most_common_app"] is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEpisodeRetrievalIntegration:
    """Integration tests for full retrieval flow"""

    def test_full_flow_with_filters(self):
        """Test complete flow: state -> query -> retrieval -> results"""
        storage = create_test_storage_with_episodes()

        # Simulate state after preprocessing and mem0 loading
        state: GraphState = {
            "user_id": "test_user",
            "prompt": "send email to john",
            "normalized_prompt": "send email to john",
            "task_type": "send_email",
            "app": "gmail",
            "entities": ["john@example.com"],
            "context": {
                "episode_limit": 5,
                "episode_min_importance": 0.3,
            },
            "mem0_items": []
        }

        # Retrieve episodes
        result = retrieve_episodes(state, storage=storage)

        # Verify results
        assert result["episode_retrieval_error"] is None
        episodes = result["retrieved_episodes"]
        assert len(episodes) > 0

        # Verify filtering worked
        for ep_result in episodes:
            episode = ep_result["episode"]
            assert episode["user_id"] == "test_user"
            assert episode["task_type"] == "send_email"
            assert episode["app"] == "gmail"
            assert episode["importance_score"] >= 0.3

        # Verify metadata
        meta = result["episode_retrieval_meta"]
        assert meta["episodes_found"] > 0
        assert "query_time_ms" in meta

    def test_flow_with_no_matches(self):
        """Test flow when no episodes match filters"""
        storage = create_test_storage_with_episodes()

        state: GraphState = {
            "user_id": "test_user",
            "normalized_prompt": "test",
            "task_type": "fill_form",
            "app": "outlook",  # No episodes with outlook
        }

        result = retrieve_episodes(state, storage=storage)

        assert result["episode_retrieval_error"] is None
        assert len(result["retrieved_episodes"]) == 0
        assert result["episode_retrieval_meta"]["episodes_found"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
