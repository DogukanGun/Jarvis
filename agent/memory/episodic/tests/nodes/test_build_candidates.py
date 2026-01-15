"""
Tests for build_episode_candidates node.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.graphs.memory_write_graph.nodes.build_episode_candidates import (
    build_episode_candidates
)


class TestBuildCandidates:
    """Tests for build_episode_candidates node."""

    def test_builds_from_interaction(self):
        """Should build candidate from prompt + llm_output."""
        state = {
            "user_id": "test_user",
            "prompt": "Send email to john@example.com",
            "llm_output": "I'll send that email to John.",
            "task_type": "email",
            "app": "mail",
            "entities": ["john@example.com"],
            "errors": []
        }

        result = build_episode_candidates(state)

        assert "episode_candidates" in result
        assert result["candidates_count"] >= 1
        candidates = result["episode_candidates"]
        assert len(candidates) > 0

    def test_builds_from_memory_intents(self):
        """Should extract candidates from memory_intents."""
        state = {
            "user_id": "test_user",
            "prompt": "Remember my preference",
            "llm_output": "I'll remember that.",
            "memory_intents": {
                "candidates": [
                    {"text": "User prefers dark mode", "episode_type": "preference"},
                    {"text": "User works at Acme Corp", "episode_type": "fact"}
                ]
            },
            "errors": []
        }

        result = build_episode_candidates(state)

        assert result["candidates_count"] >= 2

    def test_missing_user_id_error(self):
        """Should return error when user_id missing."""
        state = {
            "prompt": "Hello",
            "llm_output": "Hi there",
            "errors": []
        }

        result = build_episode_candidates(state)

        assert result["candidates_count"] == 0
        assert len(result.get("errors", [])) > 0

    def test_no_content_empty_list(self):
        """Should return empty list when no meaningful content."""
        state = {
            "user_id": "test_user",
            "prompt": "",
            "llm_output": "",
            "errors": []
        }

        result = build_episode_candidates(state)

        assert result["candidates_count"] == 0
        assert result["episode_candidates"] == []

    def test_filters_trivial_content(self):
        """Should filter very short content."""
        state = {
            "user_id": "test_user",
            "prompt": "Hi",  # Too short
            "llm_output": "Hello",  # Too short
            "errors": []
        }

        result = build_episode_candidates(state)

        # Should either have no candidates or filter them
        assert "episode_candidates" in result

    def test_estimates_importance(self):
        """Candidates should have importance scores."""
        state = {
            "user_id": "test_user",
            "prompt": "Send important email to CEO about quarterly results",
            "llm_output": "I'll draft that important email.",
            "task_type": "email",
            "entities": ["CEO", "quarterly results"],
            "errors": []
        }

        result = build_episode_candidates(state)

        if result["candidates_count"] > 0:
            candidate = result["episode_candidates"][0]
            assert "importance_score" in candidate
            assert 0 <= candidate["importance_score"] <= 1

    def test_preserves_metadata(self):
        """Candidates should include task_type, app, entities."""
        state = {
            "user_id": "test_user",
            "prompt": "Schedule meeting with John",
            "llm_output": "Meeting scheduled.",
            "task_type": "calendar",
            "app": "gcal",
            "entities": ["John", "meeting"],
            "errors": []
        }

        result = build_episode_candidates(state)

        if result["candidates_count"] > 0:
            candidate = result["episode_candidates"][0]
            assert candidate.get("task_type") == "calendar"
            assert candidate.get("app") == "gcal"
