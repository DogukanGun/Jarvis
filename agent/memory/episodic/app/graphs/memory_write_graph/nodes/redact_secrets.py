"""
Redact Secrets Node

Masks sensitive data (OTP, passwords, tokens) before storage.
"""

from typing import Dict, Any, List
import logging

from ..state import MemoryWriteState
from app.shared.secrets_patterns import redact_secrets as do_redact

logger = logging.getLogger(__name__)


def redact_secrets(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Redact secrets from episode candidates.

    Scans and masks:
    - OTP/verification codes
    - Passwords
    - API keys/tokens
    - Credit card numbers
    - SSNs

    Args:
        state: Current graph state

    Returns:
        State updates with redacted_candidates, redaction_log
    """
    candidates = state.get("episode_candidates", [])
    redacted_candidates: List[Dict[str, Any]] = []
    all_redactions: List[Dict[str, Any]] = []
    secrets_found = False

    for i, candidate in enumerate(candidates):
        redacted_candidate = candidate.copy()

        # Redact text field
        if "text" in redacted_candidate:
            redacted_text, redactions = do_redact(redacted_candidate["text"])
            redacted_candidate["text"] = redacted_text

            if redactions:
                secrets_found = True
                for r in redactions:
                    r["candidate_index"] = i
                    r["field"] = "text"
                all_redactions.extend(redactions)

        # Redact summary field
        if redacted_candidate.get("summary"):
            redacted_summary, redactions = do_redact(redacted_candidate["summary"])
            redacted_candidate["summary"] = redacted_summary

            if redactions:
                secrets_found = True
                for r in redactions:
                    r["candidate_index"] = i
                    r["field"] = "summary"
                all_redactions.extend(redactions)

        redacted_candidates.append(redacted_candidate)

    if secrets_found:
        logger.warning(f"Redacted {len(all_redactions)} secrets from candidates")
    else:
        logger.debug("No secrets found in candidates")

    return {
        "redacted_candidates": redacted_candidates,
        "redaction_log": all_redactions,
        "secrets_found": secrets_found
    }
