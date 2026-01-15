"""
Tests for EpisodeRepository SQLite operations.
"""

import pytest
import sys
import os
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.storage.episode_schema import Episode, EpisodeQuery, PromotionProposal


class TestEpisodeCRUD:
    """Tests for basic CRUD operations."""

    def test_insert_and_retrieve(self, temp_db, sample_episode):
        """Should insert and retrieve episode."""
        episode = sample_episode(user_id="test_user", text="Hello world")

        # Insert
        episode_id = temp_db.insert_episode(episode)
        assert episode_id == episode.id

        # Retrieve
        retrieved = temp_db.get_episode_by_id(episode_id)
        assert retrieved is not None
        assert retrieved.user_id == "test_user"
        assert retrieved.text == "Hello world"

    def test_get_nonexistent_episode(self, temp_db):
        """Should return None for nonexistent episode."""
        result = temp_db.get_episode_by_id("nonexistent-id")
        assert result is None

    def test_get_by_fingerprint(self, temp_db, sample_episode):
        """Should find episode by user_id and fingerprint."""
        episode = sample_episode(
            user_id="test_user",
            fingerprint="unique-fp-123"
        )
        temp_db.insert_episode(episode)

        # Find by fingerprint
        found = temp_db.get_episode_by_fingerprint("test_user", "unique-fp-123")
        assert found is not None
        assert found.id == episode.id

    def test_get_by_fingerprint_wrong_user(self, temp_db, sample_episode):
        """Should not find episode for different user."""
        episode = sample_episode(
            user_id="user1",
            fingerprint="fp-123"
        )
        temp_db.insert_episode(episode)

        # Different user shouldn't find it
        found = temp_db.get_episode_by_fingerprint("user2", "fp-123")
        assert found is None

    def test_update_episode(self, temp_db, sample_episode):
        """Should update episode fields."""
        episode = sample_episode(importance_score=0.5)
        temp_db.insert_episode(episode)

        # Update
        success = temp_db.update_episode(episode.id, {
            "importance_score": 0.9,
            "task_type": "email"
        })
        assert success is True

        # Verify
        updated = temp_db.get_episode_by_id(episode.id)
        assert updated.importance_score == 0.9
        assert updated.task_type == "email"

    def test_update_nonexistent(self, temp_db):
        """Should return False for nonexistent episode."""
        success = temp_db.update_episode("nonexistent", {"importance_score": 0.5})
        assert success is False


class TestReinforcement:
    """Tests for episode reinforcement."""

    def test_reinforce_increments_count(self, temp_db, sample_episode):
        """Should increment reinforcement_count."""
        episode = sample_episode(reinforcement_count=1)
        temp_db.insert_episode(episode)

        # Reinforce
        success = temp_db.reinforce_episode(episode.id)
        assert success is True

        # Verify
        reinforced = temp_db.get_episode_by_id(episode.id)
        assert reinforced.reinforcement_count == 2

    def test_reinforce_updates_last_seen(self, temp_db, sample_episode):
        """Should update last_seen timestamp."""
        episode = sample_episode()
        original_last_seen = episode.last_seen
        temp_db.insert_episode(episode)

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        # Reinforce
        temp_db.reinforce_episode(episode.id)

        # Verify
        reinforced = temp_db.get_episode_by_id(episode.id)
        assert reinforced.last_seen >= original_last_seen

    def test_reinforce_multiple_times(self, temp_db, sample_episode):
        """Should increment count multiple times."""
        episode = sample_episode(reinforcement_count=1)
        temp_db.insert_episode(episode)

        # Reinforce 3 times
        for _ in range(3):
            temp_db.reinforce_episode(episode.id)

        # Verify
        reinforced = temp_db.get_episode_by_id(episode.id)
        assert reinforced.reinforcement_count == 4


class TestSoftDelete:
    """Tests for soft delete."""

    def test_soft_delete_sets_flag(self, temp_db, sample_episode):
        """Should set is_deleted flag."""
        episode = sample_episode()
        temp_db.insert_episode(episode)

        # Delete
        success = temp_db.soft_delete_episode(episode.id)
        assert success is True

        # Verify - can still retrieve
        deleted = temp_db.get_episode_by_id(episode.id)
        assert deleted.is_deleted is True

    def test_soft_delete_excludes_from_fingerprint_lookup(self, temp_db, sample_episode):
        """Deleted episodes should not be found by fingerprint."""
        episode = sample_episode(fingerprint="fp-to-delete")
        temp_db.insert_episode(episode)

        # Delete
        temp_db.soft_delete_episode(episode.id)

        # Should not find by fingerprint
        found = temp_db.get_episode_by_fingerprint(episode.user_id, "fp-to-delete")
        assert found is None


class TestSearch:
    """Tests for episode search."""

    def test_search_by_user_id(self, temp_db, sample_episode):
        """Should filter by user_id."""
        # Create episodes for different users
        ep1 = sample_episode(user_id="user1", fingerprint="fp1")
        ep2 = sample_episode(user_id="user2", fingerprint="fp2")
        temp_db.insert_episode(ep1)
        temp_db.insert_episode(ep2)

        # Search for user1
        query = EpisodeQuery(user_id="user1")
        results = temp_db.search_episodes(query)

        assert results.total_count == 1
        assert results.episodes[0].episode.user_id == "user1"

    def test_search_by_task_type(self, temp_db, sample_episode):
        """Should filter by task_type."""
        ep1 = sample_episode(task_type="email", fingerprint="fp1")
        ep2 = sample_episode(task_type="calendar", fingerprint="fp2")
        temp_db.insert_episode(ep1)
        temp_db.insert_episode(ep2)

        query = EpisodeQuery(user_id="test_user", task_types=["email"])
        results = temp_db.search_episodes(query)

        assert results.total_count == 1
        assert results.episodes[0].episode.task_type == "email"

    def test_search_by_app(self, temp_db, sample_episode):
        """Should filter by app."""
        ep1 = sample_episode(app="mail", fingerprint="fp1")
        ep2 = sample_episode(app="slack", fingerprint="fp2")
        temp_db.insert_episode(ep1)
        temp_db.insert_episode(ep2)

        query = EpisodeQuery(user_id="test_user", apps=["mail"])
        results = temp_db.search_episodes(query)

        assert results.total_count == 1

    def test_search_recent_days(self, temp_db, sample_episode):
        """Should filter by recent_days."""
        # Recent episode
        ep_recent = sample_episode(fingerprint="fp-recent")
        temp_db.insert_episode(ep_recent)

        # Old episode (manually set old date)
        ep_old = sample_episode(fingerprint="fp-old")
        temp_db.insert_episode(ep_old)
        old_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        temp_db.update_episode(ep_old.id, {"last_seen": old_date})

        query = EpisodeQuery(user_id="test_user", recent_days=7)
        results = temp_db.search_episodes(query)

        # Should only find recent
        assert results.total_count == 1

    def test_search_min_importance(self, temp_db, sample_episode):
        """Should filter by min_importance."""
        ep_high = sample_episode(importance_score=0.9, fingerprint="fp1")
        ep_low = sample_episode(importance_score=0.2, fingerprint="fp2")
        temp_db.insert_episode(ep_high)
        temp_db.insert_episode(ep_low)

        query = EpisodeQuery(user_id="test_user", min_importance=0.5)
        results = temp_db.search_episodes(query)

        assert results.total_count == 1
        assert results.episodes[0].episode.importance_score >= 0.5

    def test_search_pagination(self, temp_db, sample_episode):
        """Should respect limit and offset."""
        # Create 5 episodes
        for i in range(5):
            ep = sample_episode(fingerprint=f"fp-{i}")
            temp_db.insert_episode(ep)

        # Get page 1 (limit 2)
        query = EpisodeQuery(user_id="test_user", limit=2, offset=0)
        page1 = temp_db.search_episodes(query)

        assert len(page1.episodes) == 2
        assert page1.total_count == 5

        # Get page 2
        query = EpisodeQuery(user_id="test_user", limit=2, offset=2)
        page2 = temp_db.search_episodes(query)

        assert len(page2.episodes) == 2

    def test_search_scoring(self, temp_db, sample_episode):
        """Results should have scores."""
        ep = sample_episode()
        temp_db.insert_episode(ep)

        query = EpisodeQuery(user_id="test_user")
        results = temp_db.search_episodes(query)

        assert len(results.episodes) == 1
        assert results.episodes[0].score >= 0


class TestPromotionCandidates:
    """Tests for promotion candidate queries."""

    def test_get_promotion_candidates(self, temp_db, sample_episode):
        """Should find episodes meeting promotion criteria."""
        # Episode meeting criteria
        ep_ready = sample_episode(
            reinforcement_count=5,
            confidence=0.8,
            fingerprint="fp-ready"
        )
        temp_db.insert_episode(ep_ready)

        # Episode not meeting criteria
        ep_not_ready = sample_episode(
            reinforcement_count=1,
            confidence=0.5,
            fingerprint="fp-not-ready"
        )
        temp_db.insert_episode(ep_not_ready)

        candidates = temp_db.get_promotion_candidates(
            user_id="test_user",
            min_count=3,
            min_confidence=0.7
        )

        assert len(candidates) == 1
        assert candidates[0].id == ep_ready.id

    def test_excludes_already_promoted(self, temp_db, sample_episode):
        """Should exclude already promoted episodes."""
        ep = sample_episode(
            reinforcement_count=5,
            confidence=0.9,
            promoted_to_mem0=True
        )
        temp_db.insert_episode(ep)

        candidates = temp_db.get_promotion_candidates("test_user")
        assert len(candidates) == 0


class TestActiveUsers:
    """Tests for get_active_users."""

    def test_get_active_users(self, temp_db, sample_episode):
        """Should return distinct user IDs."""
        # Create episodes for different users
        for user in ["user1", "user2", "user3"]:
            ep = sample_episode(user_id=user, fingerprint=f"fp-{user}")
            temp_db.insert_episode(ep)

        users = temp_db.get_active_users(days=7)
        assert len(users) == 3
        assert "user1" in users
        assert "user2" in users
        assert "user3" in users

    def test_excludes_old_users(self, temp_db, sample_episode):
        """Should exclude users without recent activity."""
        # Recent user
        ep_recent = sample_episode(user_id="recent_user", fingerprint="fp1")
        temp_db.insert_episode(ep_recent)

        # Old user
        ep_old = sample_episode(user_id="old_user", fingerprint="fp2")
        temp_db.insert_episode(ep_old)
        old_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        temp_db.update_episode(ep_old.id, {"last_seen": old_date})

        users = temp_db.get_active_users(days=7)
        assert "recent_user" in users
        assert "old_user" not in users


class TestProposalCRUD:
    """Tests for promotion proposal operations."""

    def test_insert_and_get_proposal(self, temp_db, sample_proposal):
        """Should insert and retrieve proposal."""
        proposal = sample_proposal()

        proposal_id = temp_db.insert_proposal(proposal)
        assert proposal_id == proposal.id

        retrieved = temp_db.get_proposal(proposal_id)
        assert retrieved is not None
        assert retrieved.proposed_value == proposal.proposed_value

    def test_get_pending_proposals(self, temp_db, sample_proposal):
        """Should find pending proposals."""
        p1 = sample_proposal(status="pending")
        p2 = sample_proposal(status="approved")
        temp_db.insert_proposal(p1)
        temp_db.insert_proposal(p2)

        pending = temp_db.get_pending_proposals()
        assert len(pending) == 1
        assert pending[0].status == "pending"

    def test_update_proposal_status(self, temp_db, sample_proposal):
        """Should update proposal status."""
        proposal = sample_proposal(status="pending")
        temp_db.insert_proposal(proposal)

        success = temp_db.update_proposal_status(
            proposal.id,
            status="approved",
            user_response="User approved"
        )
        assert success is True

        updated = temp_db.get_proposal(proposal.id)
        assert updated.status == "approved"
        assert updated.user_response == "User approved"


class TestThreadSafety:
    """Tests for thread-local connection handling."""

    def test_thread_local_connection(self, temp_db, sample_episode):
        """Each thread should have its own connection."""
        results = []

        def worker(user_id):
            ep = sample_episode(user_id=user_id, fingerprint=f"fp-{user_id}")
            temp_db.insert_episode(ep)
            retrieved = temp_db.get_episode_by_id(ep.id)
            results.append(retrieved is not None)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(f"user_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert all(results)
