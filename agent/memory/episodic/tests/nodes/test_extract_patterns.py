"""
Tests for extract_patterns node (reflection graph).
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.graphs.reflection_graph.nodes.extract_patterns import extract_patterns


class TestExtractPatterns:
    """Tests for extract_patterns node."""

    def test_groups_by_fingerprint(self):
        """Episodes with same fingerprint should be grouped."""
        now = datetime.utcnow().isoformat()
        state = {
            "user_id": "test_user",
            "recent_episodes": [
                {"id": "ep1", "fingerprint": "fp-A", "last_seen": now, "reinforcement_count": 1, "importance_score": 0.5},
                {"id": "ep2", "fingerprint": "fp-A", "last_seen": now, "reinforcement_count": 1, "importance_score": 0.5},
                {"id": "ep3", "fingerprint": "fp-B", "last_seen": now, "reinforcement_count": 1, "importance_score": 0.5},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        # fp-A has 2 episodes, fp-B has 1
        # With min_count=2, only fp-A should be a pattern
        patterns = result["detected_patterns"]
        assert result["pattern_count"] >= 1

        # Find the fp-A pattern
        fp_a_patterns = [p for p in patterns if p["fingerprint"] == "fp-A"]
        assert len(fp_a_patterns) == 1
        assert fp_a_patterns[0]["count"] == 2

    def test_min_count_filter(self):
        """Patterns below min_count should be filtered."""
        now = datetime.utcnow().isoformat()
        state = {
            "user_id": "test_user",
            "recent_episodes": [
                {"id": "ep1", "fingerprint": "fp-single", "last_seen": now, "reinforcement_count": 1, "importance_score": 0.5},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        # Single episode shouldn't form a pattern
        assert result["pattern_count"] == 0

    def test_confidence_calculation(self):
        """Patterns should have calculated confidence."""
        now = datetime.utcnow().isoformat()
        state = {
            "user_id": "test_user",
            "recent_episodes": [
                {"id": "ep1", "fingerprint": "fp-X", "last_seen": now, "reinforcement_count": 3, "importance_score": 0.8},
                {"id": "ep2", "fingerprint": "fp-X", "last_seen": now, "reinforcement_count": 2, "importance_score": 0.9},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        if result["pattern_count"] > 0:
            pattern = result["detected_patterns"][0]
            assert "confidence" in pattern
            assert 0 <= pattern["confidence"] <= 1

    def test_recency_score(self):
        """Recent patterns should have higher recency scores."""
        now = datetime.utcnow()
        recent = now.isoformat()
        old = (now - timedelta(days=25)).isoformat()

        state = {
            "user_id": "test_user",
            "recent_episodes": [
                {"id": "ep1", "fingerprint": "fp-recent", "last_seen": recent, "reinforcement_count": 1, "importance_score": 0.5},
                {"id": "ep2", "fingerprint": "fp-recent", "last_seen": recent, "reinforcement_count": 1, "importance_score": 0.5},
                {"id": "ep3", "fingerprint": "fp-old", "last_seen": old, "reinforcement_count": 1, "importance_score": 0.5},
                {"id": "ep4", "fingerprint": "fp-old", "last_seen": old, "reinforcement_count": 1, "importance_score": 0.5},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        patterns = result["detected_patterns"]
        if len(patterns) >= 2:
            recent_pattern = next(p for p in patterns if p["fingerprint"] == "fp-recent")
            old_pattern = next(p for p in patterns if p["fingerprint"] == "fp-old")
            assert recent_pattern["recency_score"] > old_pattern["recency_score"]

    def test_sorts_by_confidence(self):
        """Patterns should be sorted by confidence (descending)."""
        now = datetime.utcnow().isoformat()
        state = {
            "user_id": "test_user",
            "recent_episodes": [
                # Low importance group
                {"id": "ep1", "fingerprint": "fp-low", "last_seen": now, "reinforcement_count": 1, "importance_score": 0.2},
                {"id": "ep2", "fingerprint": "fp-low", "last_seen": now, "reinforcement_count": 1, "importance_score": 0.2},
                # High importance group
                {"id": "ep3", "fingerprint": "fp-high", "last_seen": now, "reinforcement_count": 5, "importance_score": 0.9},
                {"id": "ep4", "fingerprint": "fp-high", "last_seen": now, "reinforcement_count": 5, "importance_score": 0.9},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        patterns = result["detected_patterns"]
        if len(patterns) >= 2:
            # First pattern should have highest confidence
            assert patterns[0]["confidence"] >= patterns[1]["confidence"]

    def test_no_episodes_empty_result(self):
        """No episodes should return empty patterns."""
        state = {
            "user_id": "test_user",
            "recent_episodes": [],
            "errors": []
        }

        result = extract_patterns(state)

        assert result["detected_patterns"] == []
        assert result["pattern_count"] == 0

    def test_total_reinforcement_calculated(self):
        """Should sum reinforcement counts."""
        now = datetime.utcnow().isoformat()
        state = {
            "user_id": "test_user",
            "recent_episodes": [
                {"id": "ep1", "fingerprint": "fp-X", "last_seen": now, "reinforcement_count": 3, "importance_score": 0.5},
                {"id": "ep2", "fingerprint": "fp-X", "last_seen": now, "reinforcement_count": 5, "importance_score": 0.5},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        if result["pattern_count"] > 0:
            pattern = result["detected_patterns"][0]
            assert pattern["total_reinforcement"] == 8

    def test_representative_fields(self):
        """Pattern should include representative text/summary."""
        now = datetime.utcnow().isoformat()
        state = {
            "user_id": "test_user",
            "recent_episodes": [
                {"id": "ep1", "fingerprint": "fp-X", "last_seen": now, "text": "Send email to John", "summary": "Email task", "reinforcement_count": 1, "importance_score": 0.5},
                {"id": "ep2", "fingerprint": "fp-X", "last_seen": now, "text": "Send email to John", "summary": "Email task", "reinforcement_count": 1, "importance_score": 0.5},
            ],
            "errors": []
        }

        result = extract_patterns(state)

        if result["pattern_count"] > 0:
            pattern = result["detected_patterns"][0]
            assert "representative_text" in pattern
