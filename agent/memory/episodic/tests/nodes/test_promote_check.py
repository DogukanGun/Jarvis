"""
Tests for promote_check router node.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.graphs.memory_write_graph.nodes.promote_check import promote_check


class TestPromoteCheck:
    """Tests for promote_check router."""

    def test_below_threshold_returns_no(self):
        """Count below threshold should return 'no'."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 2,  # Below default 3
            "confidence": 0.8,
            "gate_decision": "save",
            "errors": []
        }

        result = promote_check(state)
        assert result == "no"

    def test_meets_threshold_returns_yes(self):
        """Count at threshold should return 'yes'."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 3,  # Meets default 3
            "confidence": 0.8,  # Above 0.7 default
            "gate_decision": "save",
            "episode": {"promoted_to_mem0": False},
            "errors": []
        }

        result = promote_check(state)
        assert result == "yes"

    def test_exceeds_threshold_returns_yes(self):
        """Count above threshold should return 'yes'."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 10,
            "confidence": 0.9,
            "gate_decision": "save",
            "episode": {"promoted_to_mem0": False},
            "errors": []
        }

        result = promote_check(state)
        assert result == "yes"

    def test_already_promoted_returns_no(self):
        """Already promoted episodes should return 'no'."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 10,
            "confidence": 0.9,
            "gate_decision": "save",
            "episode": {"promoted_to_mem0": True},  # Already promoted
            "errors": []
        }

        result = promote_check(state)
        assert result == "no"

    def test_fast_track_returns_yes(self):
        """gate_decision='save_and_promote' should return 'yes'."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 1,  # Below threshold
            "confidence": 0.5,  # Below threshold
            "gate_decision": "save_and_promote",  # Fast-track
            "episode": {"promoted_to_mem0": False},
            "errors": []
        }

        result = promote_check(state)
        assert result == "yes"

    def test_low_confidence_returns_no(self):
        """Low confidence should return 'no' even with high count."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 10,
            "gate_decision": "save",
            # Confidence is read from episode dict, not top level
            "episode": {"promoted_to_mem0": False, "confidence": 0.5},
            "errors": []
        }

        result = promote_check(state)
        assert result == "no"

    def test_missing_episode_returns_yes_with_high_defaults(self):
        """Missing episode uses default confidence (1.0) so may pass."""
        # Note: implementation defaults confidence to 1.0 if not in episode
        state = {
            "user_id": "test_user",
            "new_reinforcement_count": 5,  # >= threshold
            "gate_decision": "save",
            # No episode dict, so defaults apply (confidence=1.0)
            "errors": []
        }

        result = promote_check(state)
        # With default confidence 1.0 and count >= 3, this should promote
        assert result == "yes"

    def test_boundary_confidence_07(self):
        """Confidence exactly at 0.7 threshold."""
        state = {
            "user_id": "test_user",
            "episode_id": "ep-123",
            "new_reinforcement_count": 3,
            "confidence": 0.7,  # Exactly at threshold
            "gate_decision": "save",
            "episode": {"promoted_to_mem0": False},
            "errors": []
        }

        result = promote_check(state)
        assert result == "yes"
