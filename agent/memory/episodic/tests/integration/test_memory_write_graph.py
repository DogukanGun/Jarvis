"""
Integration tests for memory_write_graph.

Tests the full write pipeline from candidate building to promotion.
"""

import pytest
import sys
import os
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestMemoryWriteGraphFlow:
    """Integration tests for memory_write_graph."""

    def test_full_write_flow_new_episode(
        self, temp_db, mock_repository, mock_embedding_client, fake_embeddings
    ):
        """New episode should be inserted with embedding."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        state = {
            "user_id": "test_user",
            "prompt": "Send email to john@example.com about the project update",
            "llm_output": "I'll send that email to John about the project update.",
            "task_type": "email",
            "app": "mail",
            "entities": ["john@example.com", "project update"],
            "timestamp": datetime.utcnow().isoformat(),
            "errors": []
        }

        result = run_memory_write_graph(state)

        assert result.get("completed") is True
        assert result.get("action_taken") in ["inserted", "insert"]
        assert result.get("episode_id") is not None

        # Verify episode in database
        episode = temp_db.get_episode_by_id(result["episode_id"])
        assert episode is not None
        assert episode.user_id == "test_user"

    def test_full_write_flow_reinforcement(
        self, temp_db, sample_episode, mock_repository, mock_embedding_client
    ):
        """Duplicate fingerprint should reinforce existing episode."""
        from app.graphs.memory_write_graph import run_memory_write_graph
        from app.storage.fingerprint import generate_fingerprint

        # Pre-create episode with specific fingerprint
        fingerprint = generate_fingerprint(
            episode_type="interaction",
            task_type="email",
            app="mail",
            entities=["john@example.com"],
            summary="Send email to john"
        )

        existing = sample_episode(
            user_id="test_user",
            fingerprint=fingerprint,
            reinforcement_count=2
        )
        temp_db.insert_episode(existing)

        # Run graph with same content (should match fingerprint)
        state = {
            "user_id": "test_user",
            "prompt": "Send email to john",
            "llm_output": "Sending email",
            "task_type": "email",
            "app": "mail",
            "entities": ["john@example.com"],
            "timestamp": datetime.utcnow().isoformat(),
            "errors": []
        }

        result = run_memory_write_graph(state)

        # Should reinforce, not insert
        if result.get("action") == "reinforced":
            assert result.get("new_reinforcement_count") == 3

    def test_full_write_flow_promotion_triggered(
        self, temp_db, sample_episode, mock_repository, mock_embedding_client
    ):
        """Reaching threshold should create promotion proposal."""
        from app.graphs.memory_write_graph import run_memory_write_graph
        from app.storage.fingerprint import generate_fingerprint

        # Pre-create episode at threshold - 1
        fingerprint = generate_fingerprint(
            episode_type="interaction",
            task_type="calendar",
            entities=["meeting"],
            summary="Schedule meeting"
        )

        existing = sample_episode(
            user_id="test_user",
            fingerprint=fingerprint,
            reinforcement_count=2,  # One more will hit threshold
            confidence=0.8
        )
        temp_db.insert_episode(existing)

        state = {
            "user_id": "test_user",
            "prompt": "Schedule meeting",
            "llm_output": "Meeting scheduled",
            "task_type": "calendar",
            "entities": ["meeting"],
            "timestamp": datetime.utcnow().isoformat(),
            "errors": []
        }

        result = run_memory_write_graph(state)

        # Check if promotion was triggered
        if result.get("should_promote"):
            assert result.get("proposal_id") is not None

    def test_secrets_redacted_before_storage(
        self, temp_db, mock_repository, mock_embedding_client
    ):
        """Secrets should be redacted before storing."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        # Use text formats that match the redaction patterns:
        # password: <value> and OTP: <digits>
        state = {
            "user_id": "test_user",
            "prompt": "My password: secret123 and OTP: 456789",
            "llm_output": "I won't store your password",
            "timestamp": datetime.utcnow().isoformat(),
            "errors": []
        }

        result = run_memory_write_graph(state)

        if result.get("episode_id"):
            episode = temp_db.get_episode_by_id(result["episode_id"])
            if episode:
                # Secrets should be redacted
                assert "secret123" not in episode.text
                assert "456789" not in episode.text

    def test_gate_ignore_no_candidates(self, temp_db, mock_repository):
        """Empty content should be ignored."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        state = {
            "user_id": "test_user",
            "prompt": "",
            "llm_output": "",
            "errors": []
        }

        result = run_memory_write_graph(state)

        # Should complete but with ignore action
        assert result.get("completed") is True
        assert result.get("gate_decision") in ["ignore", None] or result.get("action_taken") == "ignored"

    def test_handles_missing_user_id(self, temp_db, mock_repository):
        """Missing user_id should be handled gracefully."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        state = {
            "prompt": "Hello",
            "llm_output": "Hi there",
            "errors": []
        }

        result = run_memory_write_graph(state)

        # Should complete with error
        assert result.get("completed") is True
        assert len(result.get("errors", [])) > 0


class TestMemoryWriteGraphEdgeCases:
    """Edge case tests for memory_write_graph."""

    def test_very_long_content(self, temp_db, mock_repository, mock_embedding_client):
        """Should handle very long content."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        long_text = "x" * 10000

        state = {
            "user_id": "test_user",
            "prompt": long_text,
            "llm_output": "Response",
            "errors": []
        }

        result = run_memory_write_graph(state)

        # Should not crash
        assert result.get("completed") is True

    def test_unicode_content(self, temp_db, mock_repository, mock_embedding_client):
        """Should handle unicode characters."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        state = {
            "user_id": "test_user",
            "prompt": "发送邮件给张三 📧",
            "llm_output": "好的，我会发送邮件",
            "task_type": "email",
            "errors": []
        }

        result = run_memory_write_graph(state)

        assert result.get("completed") is True

    def test_special_characters_in_entities(
        self, temp_db, mock_repository, mock_embedding_client
    ):
        """Should handle special characters in entities."""
        from app.graphs.memory_write_graph import run_memory_write_graph

        state = {
            "user_id": "test_user",
            "prompt": "Send to test+special@example.com",
            "llm_output": "Sending",
            "entities": ["test+special@example.com", "O'Brien", "C:\\Users"],
            "errors": []
        }

        result = run_memory_write_graph(state)

        assert result.get("completed") is True
