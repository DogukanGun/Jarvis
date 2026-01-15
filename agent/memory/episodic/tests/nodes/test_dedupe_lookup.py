"""
Tests for dedupe_lookup node.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.graphs.memory_write_graph.nodes.dedupe_lookup import dedupe_lookup


class TestDedupeLookup:
    """Tests for dedupe_lookup node."""

    def test_new_episode_not_duplicate(self, temp_db, mock_repository):
        """New fingerprint should return is_duplicate=False."""
        state = {
            "user_id": "test_user",
            "fingerprint": "brand-new-fingerprint-123",
            "errors": []
        }

        result = dedupe_lookup(state)

        assert result["is_duplicate"] is False
        assert result["existing_episode_id"] is None

    def test_existing_fingerprint_is_duplicate(self, temp_db, sample_episode, mock_repository):
        """Existing fingerprint should return is_duplicate=True."""
        # Create existing episode
        episode = sample_episode(fingerprint="existing-fp-456")
        temp_db.insert_episode(episode)

        state = {
            "user_id": "test_user",
            "fingerprint": "existing-fp-456",
            "errors": []
        }

        result = dedupe_lookup(state)

        assert result["is_duplicate"] is True
        assert result["existing_episode_id"] == episode.id

    def test_missing_fingerprint_graceful(self, temp_db, mock_repository):
        """Missing fingerprint should handle gracefully."""
        state = {
            "user_id": "test_user",
            "fingerprint": None,
            "errors": []
        }

        result = dedupe_lookup(state)

        assert result["is_duplicate"] is False
        assert result["existing_episode_id"] is None

    def test_missing_user_id_graceful(self, temp_db, mock_repository):
        """Missing user_id should handle gracefully."""
        state = {
            "fingerprint": "some-fingerprint",
            "errors": []
        }

        result = dedupe_lookup(state)

        assert result["is_duplicate"] is False

    def test_repository_error_treated_as_not_duplicate(self):
        """Repository errors should not block (treat as not duplicate)."""
        with patch('app.storage.get_episode_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_episode_by_fingerprint.side_effect = Exception("DB error")
            mock_get_repo.return_value = mock_repo

            state = {
                "user_id": "test_user",
                "fingerprint": "some-fingerprint",
                "errors": []
            }

            result = dedupe_lookup(state)

            # Should not crash, treat as not duplicate
            assert result["is_duplicate"] is False

    def test_returns_existing_episode_data(self, temp_db, sample_episode, mock_repository):
        """Should return full episode data when duplicate found."""
        episode = sample_episode(
            fingerprint="dup-fp",
            reinforcement_count=5
        )
        temp_db.insert_episode(episode)

        state = {
            "user_id": "test_user",
            "fingerprint": "dup-fp",
            "errors": []
        }

        result = dedupe_lookup(state)

        assert result["is_duplicate"] is True
        assert result["existing_episode"] is not None
        assert result["existing_episode"]["reinforcement_count"] == 5
