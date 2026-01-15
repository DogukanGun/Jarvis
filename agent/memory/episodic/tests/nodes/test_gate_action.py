"""
Tests for gate_action router node.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.graphs.memory_write_graph.nodes.gate_action import gate_action


class TestGateAction:
    """Tests for gate_action router."""

    def test_no_candidates_returns_ignore(self):
        """Should return 'ignore' when no candidates."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [],
            "candidates_count": 0,
            "errors": []
        }

        result = gate_action(state)
        assert result == "ignore"

    def test_normal_candidates_returns_save(self):
        """Should return 'save' for normal candidates."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {
                    "text": "User sent an email",
                    "importance_score": 0.5,
                    "confidence": 0.7
                }
            ],
            "candidates_count": 1,
            "errors": []
        }

        result = gate_action(state)
        assert result == "save"

    def test_high_importance_returns_save_and_promote(self):
        """Should return 'save_and_promote' for high importance + confidence."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {
                    "text": "Critical user preference",
                    "importance_score": 0.9,  # >= 0.8
                    "confidence": 0.95  # >= 0.9
                }
            ],
            "candidates_count": 1,
            "errors": []
        }

        result = gate_action(state)
        assert result == "save_and_promote"

    def test_boundary_importance_08(self):
        """Boundary test: importance = 0.8, confidence = 0.9."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {
                    "text": "Boundary test",
                    "importance_score": 0.8,
                    "confidence": 0.9
                }
            ],
            "candidates_count": 1,
            "errors": []
        }

        result = gate_action(state)
        assert result == "save_and_promote"

    def test_below_boundary_returns_save(self):
        """Below boundary should return 'save'."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {
                    "text": "Test",
                    "importance_score": 0.79,  # Just below 0.8
                    "confidence": 0.9
                }
            ],
            "candidates_count": 1,
            "errors": []
        }

        result = gate_action(state)
        assert result == "save"

    def test_low_confidence_returns_save(self):
        """High importance but low confidence should return 'save'."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {
                    "text": "Test",
                    "importance_score": 0.9,
                    "confidence": 0.5  # Below 0.9
                }
            ],
            "candidates_count": 1,
            "errors": []
        }

        result = gate_action(state)
        assert result == "save"

    def test_missing_scores_defaults(self):
        """Should handle missing importance/confidence."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {"text": "No scores provided"}
            ],
            "candidates_count": 1,
            "errors": []
        }

        result = gate_action(state)
        # Should not crash, likely returns "save"
        assert result in ["save", "ignore", "save_and_promote"]

    def test_multiple_candidates_any_fast_track(self):
        """If any candidate qualifies, should fast-track."""
        state = {
            "user_id": "test_user",
            "episode_candidates": [
                {"text": "Low priority", "importance_score": 0.3, "confidence": 0.5},
                {"text": "High priority", "importance_score": 0.95, "confidence": 0.95}
            ],
            "candidates_count": 2,
            "errors": []
        }

        result = gate_action(state)
        assert result == "save_and_promote"
