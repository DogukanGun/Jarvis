"""
Tests for episode schema and Pydantic models.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from pydantic import ValidationError
from app.storage.episode_schema import (
    Episode,
    EpisodeCandidate,
    PromotionProposal,
    UserDecision,
    EpisodeQuery,
    EpisodeSearchResult,
    EpisodeSearchResponse,
)


class TestEpisode:
    """Tests for Episode model."""

    def test_create_minimal_episode(self):
        """Should create episode with minimal required fields."""
        episode = Episode(
            user_id="test_user",
            fingerprint="abc123",
            text="Test content",
            episode_type="interaction"
        )

        assert episode.user_id == "test_user"
        assert episode.fingerprint == "abc123"
        assert episode.text == "Test content"
        assert episode.id is not None  # Auto-generated

    def test_uuid_generation(self):
        """ID should be auto-generated as UUID."""
        episode1 = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )
        episode2 = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )

        assert episode1.id != episode2.id
        assert len(episode1.id) == 36  # UUID format

    def test_datetime_defaults(self):
        """first_seen and last_seen should have defaults."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )

        assert episode.first_seen is not None
        assert episode.last_seen is not None
        assert isinstance(episode.first_seen, datetime)

    def test_importance_score_bounds(self):
        """importance_score should be between 0 and 1."""
        # Valid values
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction",
            importance_score=0.5
        )
        assert episode.importance_score == 0.5

        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction",
            importance_score=0.0
        )
        assert episode.importance_score == 0.0

        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction",
            importance_score=1.0
        )
        assert episode.importance_score == 1.0

    def test_confidence_bounds(self):
        """confidence should be between 0 and 1."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction",
            confidence=0.75
        )
        assert episode.confidence == 0.75

    def test_reinforcement_count_default(self):
        """reinforcement_count should default to 1."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )
        assert episode.reinforcement_count == 1

    def test_boolean_defaults(self):
        """Boolean fields should have correct defaults."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )

        assert episode.is_deleted is False
        assert episode.promoted_to_mem0 is False

    def test_entities_default_empty(self):
        """entities should default to empty list."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )
        assert episode.entities == []

    def test_model_dump(self):
        """Should serialize to dict."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )
        data = episode.model_dump()

        assert isinstance(data, dict)
        assert data["user_id"] == "test"
        assert "id" in data


class TestEpisodeCandidate:
    """Tests for EpisodeCandidate model."""

    def test_create_candidate(self):
        """Should create candidate with required fields."""
        candidate = EpisodeCandidate(
            text="Test candidate",
            episode_type="interaction"
        )

        assert candidate.text == "Test candidate"
        assert candidate.episode_type == "interaction"

    def test_optional_fields(self):
        """Optional fields should be None by default."""
        candidate = EpisodeCandidate(
            text="Test",
            episode_type="interaction"
        )

        assert candidate.summary is None
        assert candidate.task_type is None
        assert candidate.app is None


class TestPromotionProposal:
    """Tests for PromotionProposal model."""

    def test_create_proposal(self):
        """Should create proposal with required fields."""
        now = datetime.utcnow()
        proposal = PromotionProposal(
            episode_id="ep-123",
            user_id="test_user",
            target_path="patterns.email",
            proposed_value="User sends emails frequently",
            confidence=0.85,
            evidence=["ep-1", "ep-2"],
            created_at=now,
            expires_at=now + timedelta(minutes=5)
        )

        assert proposal.episode_id == "ep-123"
        assert proposal.status == "pending"  # default
        assert proposal.id is not None

    def test_status_default(self):
        """status should default to 'pending'."""
        proposal = PromotionProposal(
            episode_id="ep-123",
            user_id="test",
            target_path="path",
            proposed_value="value",
            confidence=0.8,
            evidence=[],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow()
        )
        assert proposal.status == "pending"


class TestUserDecision:
    """Tests for UserDecision model."""

    def test_create_decision(self):
        """Should create decision record."""
        decision = UserDecision(
            proposal_id="prop-123",
            user_id="test_user",
            decision="approve",
            original_value="User prefers morning meetings"
        )

        assert decision.decision == "approve"
        assert decision.id is not None
        assert decision.original_value == "User prefers morning meetings"

    def test_optional_fields(self):
        """Optional fields for editing."""
        decision = UserDecision(
            proposal_id="prop-123",
            user_id="test",
            decision="edit",
            original_value="old value",
            final_value="new value",
            reason="User corrected it"
        )

        assert decision.final_value == "new value"
        assert decision.reason == "User corrected it"


class TestEpisodeQuery:
    """Tests for EpisodeQuery model."""

    def test_minimal_query(self):
        """Should create query with just user_id."""
        query = EpisodeQuery(user_id="test_user")

        assert query.user_id == "test_user"
        assert query.limit == 10  # default

    def test_query_with_filters(self):
        """Should accept various filters."""
        query = EpisodeQuery(
            user_id="test",
            task_types=["email", "calendar"],
            apps=["mail", "gcal"],
            recent_days=7,
            min_importance=0.5
        )

        assert query.task_types == ["email", "calendar"]
        assert query.recent_days == 7

    def test_pagination(self):
        """Should accept pagination params."""
        query = EpisodeQuery(
            user_id="test",
            limit=20,
            offset=10
        )

        assert query.limit == 20
        assert query.offset == 10


class TestEpisodeSearchResult:
    """Tests for EpisodeSearchResult model."""

    def test_create_result(self):
        """Should wrap episode with score."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )

        result = EpisodeSearchResult(
            episode=episode,
            score=0.85,
            match_reasons=["semantic_match", "recent"]
        )

        assert result.score == 0.85
        assert "semantic_match" in result.match_reasons


class TestEpisodeSearchResponse:
    """Tests for EpisodeSearchResponse model."""

    def test_create_response(self):
        """Should contain results and metadata."""
        episode = Episode(
            user_id="test",
            fingerprint="fp",
            text="text",
            episode_type="interaction"
        )
        result = EpisodeSearchResult(
            episode=episode,
            score=0.8,
            match_reasons=[]
        )

        response = EpisodeSearchResponse(
            episodes=[result],
            total_count=1,
            query_time_ms=5.2,
            used_filters={"user_id": "test"}
        )

        assert len(response.episodes) == 1
        assert response.total_count == 1
        assert response.query_time_ms == 5.2
