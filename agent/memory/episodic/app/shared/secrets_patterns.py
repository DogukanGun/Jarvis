"""
Secret Detection and Redaction Patterns

Regex patterns for detecting and masking sensitive data before storage.
"""

import re
from typing import List, Tuple, Dict, Any


# Pattern definitions: (name, replacement, pattern)
SECRET_PATTERNS: List[Tuple[str, str, re.Pattern]] = [
    # OTP/Verification codes (4-8 digits near keywords)
    (
        "OTP",
        "[REDACTED_OTP]",
        re.compile(
            r'(?:otp|code|verification|verify|2fa|token)[:\s]+(\d{4,8})\b',
            re.IGNORECASE
        )
    ),
    (
        "OTP",
        "[REDACTED_OTP]",
        re.compile(
            r'\b(\d{6})\b(?=.*(?:otp|verification|code|2fa))',
            re.IGNORECASE
        )
    ),

    # Passwords
    (
        "PASSWORD",
        "[REDACTED_PASSWORD]",
        re.compile(
            r'(?:password|passwd|pwd|pass)[:\s]+([^\s]{4,})',
            re.IGNORECASE
        )
    ),
    (
        "PASSWORD",
        "[REDACTED_PASSWORD]",
        re.compile(
            r'(?:password|passwd|pwd)[:\s]*["\']([^"\']+)["\']',
            re.IGNORECASE
        )
    ),

    # JWT Tokens
    (
        "JWT",
        "[REDACTED_JWT]",
        re.compile(
            r'(eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)'
        )
    ),

    # Bearer Tokens
    (
        "BEARER_TOKEN",
        "[REDACTED_TOKEN]",
        re.compile(
            r'Bearer\s+([A-Za-z0-9_\-\.]{20,})',
            re.IGNORECASE
        )
    ),

    # API Keys (common patterns)
    (
        "API_KEY",
        "[REDACTED_API_KEY]",
        re.compile(
            r'(?:api[_-]?key|apikey|api_secret)[:\s]+([A-Za-z0-9_\-]{16,})',
            re.IGNORECASE
        )
    ),
    (
        "API_KEY",
        "[REDACTED_API_KEY]",
        re.compile(
            r'(?:sk|pk|api)[_-][a-zA-Z0-9]{20,}'
        )
    ),

    # AWS Keys
    (
        "AWS_KEY",
        "[REDACTED_AWS_KEY]",
        re.compile(r'(AKIA[A-Z0-9]{16})')
    ),
    (
        "AWS_SECRET",
        "[REDACTED_AWS_SECRET]",
        re.compile(
            r'(?:aws[_-]?secret|secret[_-]?key)[:\s]+([A-Za-z0-9/+=]{40})',
            re.IGNORECASE
        )
    ),

    # Credit Card Numbers (basic pattern)
    (
        "CREDIT_CARD",
        "[REDACTED_CC]",
        re.compile(r'\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b')
    ),

    # SSN (US format)
    (
        "SSN",
        "[REDACTED_SSN]",
        re.compile(r'\b(\d{3}-\d{2}-\d{4})\b')
    ),

    # Private Keys
    (
        "PRIVATE_KEY",
        "[REDACTED_PRIVATE_KEY]",
        re.compile(
            r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
            re.IGNORECASE
        )
    ),

    # Generic secrets (key=value patterns)
    (
        "SECRET",
        "[REDACTED_SECRET]",
        re.compile(
            r'(?:secret|token|auth)[_-]?(?:key|token)?[:\s=]+["\']?([A-Za-z0-9_\-\.]{16,})["\']?',
            re.IGNORECASE
        )
    ),
]


def redact_secrets(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Redact secrets from text.

    Args:
        text: Text to scan and redact

    Returns:
        Tuple of (redacted_text, redaction_log)

    Example:
        >>> text = "My OTP is 123456 and password: secret123"
        >>> redacted, log = redact_secrets(text)
        >>> print(redacted)
        "My OTP is [REDACTED_OTP] and password: [REDACTED_PASSWORD]"
    """
    if not text:
        return text, []

    redaction_log: List[Dict[str, Any]] = []
    redacted_text = text

    for secret_type, replacement, pattern in SECRET_PATTERNS:
        matches = list(pattern.finditer(redacted_text))

        # Process matches in reverse order to preserve positions
        for match in reversed(matches):
            # Get the captured group (the actual secret value)
            if match.groups():
                # Replace only the captured group, not the whole match
                group_start = match.start(1)
                group_end = match.end(1)
                secret_value = match.group(1)
            else:
                # No capture group, replace whole match
                group_start = match.start()
                group_end = match.end()
                secret_value = match.group()

            # Log the redaction
            redaction_log.append({
                "type": secret_type,
                "position": (group_start, group_end),
                "length": len(secret_value),
                "pattern": pattern.pattern[:50] + "..." if len(pattern.pattern) > 50 else pattern.pattern
            })

            # Perform redaction
            redacted_text = (
                redacted_text[:group_start] +
                replacement +
                redacted_text[group_end:]
            )

    return redacted_text, redaction_log


def contains_secrets(text: str) -> bool:
    """
    Check if text contains any secrets (quick check).

    Args:
        text: Text to scan

    Returns:
        True if secrets detected, False otherwise
    """
    if not text:
        return False

    for _, _, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return True

    return False


def get_secret_types(text: str) -> List[str]:
    """
    Get list of secret types found in text.

    Args:
        text: Text to scan

    Returns:
        List of secret type names found
    """
    if not text:
        return []

    found_types = set()

    for secret_type, _, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            found_types.add(secret_type)

    return list(found_types)
