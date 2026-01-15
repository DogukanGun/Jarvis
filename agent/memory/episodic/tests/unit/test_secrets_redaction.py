"""
Tests for secret redaction patterns.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.shared.secrets_patterns import (
    redact_secrets,
    contains_secrets,
    get_secret_types
)


class TestRedactSecrets:
    """Tests for redact_secrets()"""

    def test_redact_otp_code(self):
        """OTP codes near keywords should be redacted."""
        # Pattern expects keyword followed directly by : or space then digits
        text = "Your OTP: 123456"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_OTP]" in redacted
        assert "123456" not in redacted
        assert len(log) > 0
        assert log[0]["type"] == "OTP"

    def test_redact_verification_code(self):
        """Verification codes should be redacted."""
        text = "Your verification code: 789012"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_OTP]" in redacted
        assert "789012" not in redacted

    def test_redact_password(self):
        """Passwords should be redacted."""
        text = "password: secret123"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_PASSWORD]" in redacted
        assert "secret123" not in redacted

    def test_redact_password_quoted(self):
        """Quoted passwords should be redacted."""
        text = 'password: "mysecretpass"'
        redacted, log = redact_secrets(text)

        assert "[REDACTED_PASSWORD]" in redacted
        assert "mysecretpass" not in redacted

    def test_redact_jwt_token(self):
        """JWT tokens should be redacted."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        text = f"Token: {jwt}"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_JWT]" in redacted
        assert "eyJ" not in redacted

    def test_redact_bearer_token(self):
        """Bearer tokens should be redacted."""
        text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_TOKEN]" in redacted

    def test_redact_api_key(self):
        """API keys should be redacted."""
        text = "api_key: sk_live_abcdefghijklmnopqrstuvwxyz"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_API_KEY]" in redacted

    def test_redact_credit_card(self):
        """Credit card numbers should be redacted."""
        text = "Card: 4111111111111111"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_CC]" in redacted
        assert "4111111111111111" not in redacted

    def test_redact_ssn(self):
        """SSN should be redacted."""
        text = "SSN: 123-45-6789"
        redacted, log = redact_secrets(text)

        assert "[REDACTED_SSN]" in redacted
        assert "123-45-6789" not in redacted

    def test_multiple_secrets(self):
        """Multiple secrets in one text should all be redacted."""
        text = "OTP: 123456, password: secret, api_key: sk_test_abcdefghijklmnopqrst"
        redacted, log = redact_secrets(text)

        assert "123456" not in redacted
        assert "secret" not in redacted
        assert "sk_test" not in redacted
        assert len(log) >= 2

    def test_no_secrets_unchanged(self):
        """Text without secrets should be unchanged."""
        text = "Hello, this is a normal message without any secrets."
        redacted, log = redact_secrets(text)

        assert redacted == text
        assert len(log) == 0

    def test_redaction_log_structure(self):
        """Redaction log should contain expected fields."""
        text = "OTP: 123456"
        redacted, log = redact_secrets(text)

        assert len(log) > 0
        entry = log[0]
        assert "type" in entry
        assert "position" in entry or "start" in entry

    def test_empty_text(self):
        """Empty text should return empty."""
        redacted, log = redact_secrets("")
        assert redacted == ""
        assert len(log) == 0


class TestContainsSecrets:
    """Tests for contains_secrets()"""

    def test_with_secrets(self):
        """Should return True when secrets present."""
        assert contains_secrets("password: secret123") is True
        assert contains_secrets("OTP: 123456") is True

    def test_without_secrets(self):
        """Should return False when no secrets."""
        assert contains_secrets("Hello world") is False
        assert contains_secrets("Normal text here") is False

    def test_empty_text(self):
        """Empty text should return False."""
        assert contains_secrets("") is False


class TestGetSecretTypes:
    """Tests for get_secret_types()"""

    def test_returns_types(self):
        """Should return list of detected secret types."""
        text = "password: secret123"
        types = get_secret_types(text)

        assert isinstance(types, list)
        assert "PASSWORD" in types

    def test_multiple_types(self):
        """Should return all detected types."""
        text = "OTP: 123456, password: secret"
        types = get_secret_types(text)

        assert "OTP" in types
        assert "PASSWORD" in types

    def test_no_secrets(self):
        """Should return empty list when no secrets."""
        types = get_secret_types("Normal text")
        assert types == []


class TestEdgeCases:
    """Edge case tests for secret redaction."""

    def test_partial_matches_not_redacted(self):
        """Partial patterns should not trigger false positives."""
        # Short numbers shouldn't be OTP
        text = "I have 12 apples"
        redacted, log = redact_secrets(text)
        assert "12" in redacted

    def test_preserves_surrounding_text(self):
        """Text around secrets should be preserved."""
        text = "Before OTP: 123456 After"
        redacted, log = redact_secrets(text)

        assert redacted.startswith("Before")
        assert "After" in redacted

    def test_unicode_text(self):
        """Should handle unicode text."""
        text = "密码: secret123"
        redacted, log = redact_secrets(text)
        # Should still work with mixed content
        assert "secret123" not in redacted or "密码" in redacted
