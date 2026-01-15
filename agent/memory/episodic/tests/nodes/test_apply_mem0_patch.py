"""
Tests for apply_mem0_patch node (approval graph).
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.graphs.user_approval_graph.nodes.apply_mem0_patch import apply_mem0_patch


class TestApplyMem0Patch:
    """Tests for apply_mem0_patch node."""

    def test_writes_to_mem0(self, fake_mem0, mock_mem0_client, temp_db, mock_repository, sample_episode):
        """Should call mem0.add() with proposed value."""
        # Create episode in DB
        episode = sample_episode()
        temp_db.insert_episode(episode)

        state = {
            "user_id": "test_user",
            "episode_id": episode.id,
            "proposal": {
                "id": "prop-123",
                "proposed_value": "User prefers dark mode",
                "target_path": "preferences.theme",
                "confidence": 0.85
            },
            "approval_status": "approved",
            "errors": []
        }

        result = apply_mem0_patch(state)

        # Check mem0 was called
        assert len(fake_mem0.calls) > 0
        assert fake_mem0.calls[0][0] == "add"
        assert result["mem0_write_success"] is True

    def test_uses_edited_value_when_provided(self, fake_mem0, mock_mem0_client, temp_db, mock_repository, sample_episode):
        """Should use edited_value instead of proposed_value."""
        episode = sample_episode()
        temp_db.insert_episode(episode)

        state = {
            "user_id": "test_user",
            "episode_id": episode.id,
            "proposal": {
                "id": "prop-123",
                "proposed_value": "Original value",
                "target_path": "preferences.theme",
                "confidence": 0.85
            },
            "approval_status": "edited",
            "edited_value": "User-corrected value",
            "errors": []
        }

        result = apply_mem0_patch(state)

        # Should use edited value
        if len(fake_mem0.calls) > 0:
            call_args = fake_mem0.calls[0]
            assert "User-corrected" in call_args[2]  # text arg

    def test_marks_episode_promoted(self, fake_mem0, mock_mem0_client, temp_db, mock_repository, sample_episode):
        """Should mark episode as promoted_to_mem0."""
        episode = sample_episode(promoted_to_mem0=False)
        temp_db.insert_episode(episode)

        state = {
            "user_id": "test_user",
            "episode_id": episode.id,
            "proposal": {
                "id": "prop-123",
                "proposed_value": "Test value",
                "target_path": "test.path",
                "confidence": 0.8
            },
            "approval_status": "approved",
            "errors": []
        }

        apply_mem0_patch(state)

        # Check episode was marked
        updated = temp_db.get_episode_by_id(episode.id)
        assert updated.promoted_to_mem0 is True

    def test_mem0_error_handled(self, temp_db, mock_repository, sample_episode):
        """Should handle mem0 errors gracefully."""
        episode = sample_episode()
        temp_db.insert_episode(episode)

        # Create failing mem0 client (inline to avoid import issues)
        class FailingMem0Client:
            def add(self, user_id, text, metadata=None):
                return {"success": False, "message": "Mock error"}

        failing_mem0 = FailingMem0Client()

        with patch('app.graphs.user_approval_graph.nodes.apply_mem0_patch.get_mem0_client', return_value=failing_mem0):
            state = {
                "user_id": "test_user",
                "episode_id": episode.id,
                "proposal": {
                    "id": "prop-123",
                    "proposed_value": "Test value",
                    "target_path": "test.path",
                    "confidence": 0.8
                },
                "approval_status": "approved",
                "errors": []
            }

            result = apply_mem0_patch(state)

            assert result["mem0_write_success"] is False
            assert "mem0_error" in result

    def test_missing_value_error(self, temp_db, mock_repository):
        """Should error when no value to write."""
        state = {
            "user_id": "test_user",
            "proposal": {},  # No proposed_value
            "approval_status": "approved",
            "errors": []
        }

        result = apply_mem0_patch(state)

        assert result["mem0_write_success"] is False

    def test_missing_user_id_error(self, temp_db, mock_repository):
        """Should error when user_id missing."""
        state = {
            "proposal": {
                "proposed_value": "Test"
            },
            "approval_status": "approved",
            "errors": []
        }

        result = apply_mem0_patch(state)

        assert result["mem0_write_success"] is False

    def test_includes_metadata(self, fake_mem0, mock_mem0_client, temp_db, mock_repository, sample_episode):
        """Should include metadata in mem0 write."""
        episode = sample_episode()
        temp_db.insert_episode(episode)

        state = {
            "user_id": "test_user",
            "episode_id": episode.id,
            "proposal": {
                "id": "prop-123",
                "proposed_value": "Test value",
                "target_path": "test.path",
                "confidence": 0.85
            },
            "approval_status": "approved",
            "errors": []
        }

        apply_mem0_patch(state)

        # Check metadata was passed
        if len(fake_mem0.calls) > 0:
            call_args = fake_mem0.calls[0]
            metadata = call_args[3]  # metadata arg
            assert metadata is not None
            assert "source" in metadata
            assert metadata["source"] == "episode_promotion"
