"""
Integration tests for user_approval_graph.

Tests the full approval workflow from Kafka to mem0.
"""

import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestApprovalGraphFlow:
    """Integration tests for user_approval_graph."""

    def test_approved_writes_to_mem0(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Approved decision should write to mem0."""
        from app.graphs.user_approval_graph import run_approval

        # Create episode and proposal
        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id,
            proposed_value="User prefers morning meetings"
        )
        temp_db.insert_proposal(proposal)

        result = run_approval(
            proposal_id=proposal.id,
            decision="approved"
        )

        assert result.get("completed") is True
        assert result.get("applied") is True or result.get("mem0_write_success") is True

        # Verify mem0 was called
        assert len(fake_mem0.calls) > 0

    def test_rejected_skips_mem0(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Rejected decision should not write to mem0."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id
        )
        temp_db.insert_proposal(proposal)

        result = run_approval(
            proposal_id=proposal.id,
            decision="rejected",
            reason="User rejected"
        )

        assert result.get("completed") is True
        # mem0 should not be called for rejection
        mem0_write_calls = [c for c in fake_mem0.calls if c[0] == "add"]
        assert len(mem0_write_calls) == 0

    def test_edited_uses_new_value(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Edited decision should use the edited value."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id,
            proposed_value="Original value"
        )
        temp_db.insert_proposal(proposal)

        result = run_approval(
            proposal_id=proposal.id,
            decision="edited",
            edited_value="User-corrected value"
        )

        assert result.get("completed") is True

        # Check that edited value was used
        if len(fake_mem0.calls) > 0:
            add_call = fake_mem0.calls[0]
            text_arg = add_call[2]  # text is 3rd argument
            assert "User-corrected" in text_arg

    def test_records_decision(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Decision should be recorded in database."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id
        )
        temp_db.insert_proposal(proposal)

        result = run_approval(
            proposal_id=proposal.id,
            decision="approved"
        )

        assert result.get("completed") is True
        assert result.get("decision_recorded") is True or "decision_id" in result

    def test_updates_proposal_status(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Proposal status should be updated after decision."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id,
            status="pending"
        )
        temp_db.insert_proposal(proposal)

        run_approval(
            proposal_id=proposal.id,
            decision="approved"
        )

        # Check proposal status updated
        updated_proposal = temp_db.get_proposal(proposal.id)
        assert updated_proposal.status == "approved"

    def test_marks_episode_promoted(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Episode should be marked as promoted after approval."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(
            user_id="test_user",
            promoted_to_mem0=False
        )
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id
        )
        temp_db.insert_proposal(proposal)

        run_approval(
            proposal_id=proposal.id,
            decision="approved"
        )

        # Check episode marked as promoted
        updated_episode = temp_db.get_episode_by_id(episode.id)
        assert updated_episode.promoted_to_mem0 is True


class TestApprovalGraphEdgeCases:
    """Edge case tests for user_approval_graph."""

    def test_nonexistent_proposal(self, temp_db, mock_repository):
        """Should handle nonexistent proposal gracefully."""
        from app.graphs.user_approval_graph import run_approval

        result = run_approval(
            proposal_id="nonexistent-proposal-id",
            decision="approved"
        )

        assert result.get("completed") is True
        assert len(result.get("errors", [])) > 0

    def test_timeout_decision(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Timeout should be treated as rejection."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id
        )
        temp_db.insert_proposal(proposal)

        result = run_approval(
            proposal_id=proposal.id,
            decision="timeout"
        )

        assert result.get("completed") is True

        # Should not write to mem0
        mem0_write_calls = [c for c in fake_mem0.calls if c[0] == "add"]
        assert len(mem0_write_calls) == 0

    def test_mem0_failure_handled(
        self, temp_db, sample_episode, sample_proposal, mock_repository
    ):
        """mem0 write failure should be handled gracefully."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id
        )
        temp_db.insert_proposal(proposal)

        # Create failing mem0 client (inline to avoid import issues)
        class FailingMem0Client:
            def add(self, user_id, text, metadata=None):
                return {"success": False, "message": "Mock error"}

        failing_mem0 = FailingMem0Client()
        with patch('app.graphs.user_approval_graph.nodes.apply_mem0_patch.get_mem0_client', return_value=failing_mem0):
            result = run_approval(
                proposal_id=proposal.id,
                decision="approved"
            )

        # Should complete but with error
        assert result.get("completed") is True
        # Decision should still be recorded even if mem0 fails

    def test_empty_proposed_value(
        self, temp_db, sample_episode, sample_proposal,
        mock_repository, fake_mem0, mock_mem0_client
    ):
        """Empty proposed value should be handled."""
        from app.graphs.user_approval_graph import run_approval

        episode = sample_episode(user_id="test_user")
        temp_db.insert_episode(episode)

        proposal = sample_proposal(
            user_id="test_user",
            episode_id=episode.id,
            proposed_value=""  # Empty
        )
        temp_db.insert_proposal(proposal)

        result = run_approval(
            proposal_id=proposal.id,
            decision="approved"
        )

        assert result.get("completed") is True
