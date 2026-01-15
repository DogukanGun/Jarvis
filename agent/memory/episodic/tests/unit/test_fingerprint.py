"""
Tests for fingerprint generation and matching.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.storage.fingerprint import (
    generate_fingerprint,
    normalize_text,
    fingerprints_match
)


class TestGenerateFingerprint:
    """Tests for generate_fingerprint()"""

    def test_same_input_same_fingerprint(self):
        """Same inputs should produce identical fingerprints."""
        fp1 = generate_fingerprint(
            episode_type="interaction",
            task_type="email",
            app="mail",
            entities=["john@example.com"],
            summary="Send email to John"
        )
        fp2 = generate_fingerprint(
            episode_type="interaction",
            task_type="email",
            app="mail",
            entities=["john@example.com"],
            summary="Send email to John"
        )
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex digest

    def test_different_input_different_fingerprint(self):
        """Different inputs should produce different fingerprints."""
        fp1 = generate_fingerprint(
            episode_type="interaction",
            task_type="email",
            summary="Send email to John"
        )
        fp2 = generate_fingerprint(
            episode_type="interaction",
            task_type="calendar",
            summary="Schedule meeting"
        )
        assert fp1 != fp2

    def test_empty_inputs_still_generates_hash(self):
        """Empty inputs should still generate a deterministic hash."""
        fp = generate_fingerprint(
            episode_type="",
            task_type=None,
            app=None,
            entities=None,
            summary=None,
            text=None
        )
        # Should still produce a hash (from empty components)
        assert len(fp) == 64  # SHA256 hex digest length
        # Should be deterministic
        fp2 = generate_fingerprint("", None, None, None, None, None)
        assert fp == fp2

    def test_entity_sorting(self):
        """Entities should be sorted for consistent fingerprints."""
        fp1 = generate_fingerprint(
            episode_type="interaction",
            entities=["charlie", "alice", "bob"]
        )
        fp2 = generate_fingerprint(
            episode_type="interaction",
            entities=["alice", "bob", "charlie"]
        )
        assert fp1 == fp2

    def test_entity_limit(self):
        """Only first 5 entities should be used."""
        entities_many = ["a", "b", "c", "d", "e", "f", "g"]
        entities_five = ["a", "b", "c", "d", "e"]

        fp1 = generate_fingerprint(
            episode_type="interaction",
            entities=entities_many
        )
        fp2 = generate_fingerprint(
            episode_type="interaction",
            entities=entities_five
        )
        assert fp1 == fp2

    def test_text_truncation(self):
        """Only first 200 chars of text should be used."""
        long_text = "x" * 500
        short_text = "x" * 200

        fp1 = generate_fingerprint(
            episode_type="interaction",
            summary=long_text
        )
        fp2 = generate_fingerprint(
            episode_type="interaction",
            summary=short_text
        )
        assert fp1 == fp2

    def test_prefers_summary_over_text(self):
        """Summary should be used if both summary and text provided."""
        fp_summary = generate_fingerprint(
            episode_type="interaction",
            summary="Use this summary"
        )
        fp_text = generate_fingerprint(
            episode_type="interaction",
            text="Use this text"
        )
        fp_both = generate_fingerprint(
            episode_type="interaction",
            summary="Use this summary",
            text="Use this text"
        )
        assert fp_both == fp_summary
        assert fp_both != fp_text

    def test_episode_type_affects_fingerprint(self):
        """Different episode types should produce different fingerprints."""
        fp1 = generate_fingerprint(
            episode_type="interaction",
            summary="Test"
        )
        fp2 = generate_fingerprint(
            episode_type="preference",
            summary="Test"
        )
        assert fp1 != fp2


class TestNormalizeText:
    """Tests for normalize_text()"""

    def test_whitespace_normalization(self):
        """Multiple spaces should be collapsed."""
        result = normalize_text("hello    world")
        assert result == "hello world"

    def test_strip_leading_trailing(self):
        """Leading/trailing whitespace should be stripped."""
        result = normalize_text("  hello world  ")
        assert result == "hello world"

    def test_lowercase(self):
        """Text should be lowercased."""
        result = normalize_text("Hello World")
        assert result == "hello world"

    def test_newlines_to_spaces(self):
        """Newlines should become spaces."""
        result = normalize_text("hello\nworld")
        assert result == "hello world"

    def test_tabs_to_spaces(self):
        """Tabs should become spaces."""
        result = normalize_text("hello\tworld")
        assert result == "hello world"

    def test_empty_string(self):
        """Empty string should return empty."""
        result = normalize_text("")
        assert result == ""

    def test_none_returns_empty(self):
        """None should return empty string."""
        result = normalize_text(None)
        assert result == ""


class TestFingerprintsMatch:
    """Tests for fingerprints_match()"""

    def test_exact_match(self):
        """Identical fingerprints should match."""
        fp = "abc123def456"
        assert fingerprints_match(fp, fp) is True

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        assert fingerprints_match("ABC123", "abc123") is True

    def test_different_fingerprints(self):
        """Different fingerprints should not match."""
        assert fingerprints_match("abc123", "xyz789") is False

    def test_empty_fingerprints(self):
        """Empty fingerprints should match each other."""
        assert fingerprints_match("", "") is True

    def test_none_handling(self):
        """None should be treated as empty."""
        assert fingerprints_match(None, None) is True
        assert fingerprints_match(None, "") is True
        assert fingerprints_match("abc", None) is False
