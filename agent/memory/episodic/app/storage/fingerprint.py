"""
Fingerprint Generation for Episode Deduplication

Generates deterministic hashes for episodes to detect duplicates.
"""

import hashlib
import re
from typing import List, Optional


def normalize_text(text: str) -> str:
    """
    Normalize text for fingerprinting.

    - Lowercase
    - Collapse whitespace
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def generate_fingerprint(
    episode_type: str,
    task_type: Optional[str] = None,
    app: Optional[str] = None,
    entities: Optional[List[str]] = None,
    summary: Optional[str] = None,
    text: Optional[str] = None
) -> str:
    """
    Generate SHA256 fingerprint hash for episode deduplication.

    Fingerprint is based on:
    - episode_type (required)
    - task_type (normalized)
    - app (normalized)
    - entities (sorted, first 5, normalized)
    - summary OR text (normalized, first 200 chars)

    Same semantic intent = same fingerprint, allowing deduplication.

    Args:
        episode_type: Type of episode (interaction, task_completion, etc.)
        task_type: Task type if detected
        app: Application if detected
        entities: List of entities (emails, URLs, names)
        summary: Optional summary text
        text: Full text (used if summary not provided)

    Returns:
        SHA256 hash string (64 characters)
    """
    entities = entities or []

    # Normalize all components
    norm_type = normalize_text(episode_type)
    norm_task = normalize_text(task_type or "")
    norm_app = normalize_text(app or "")

    # Sort and normalize entities (take first 5)
    norm_entities = sorted(normalize_text(e) for e in entities if e)[:5]
    entities_str = "|".join(norm_entities)

    # Use summary if available, otherwise use text (truncated)
    content = summary or text or ""
    norm_content = normalize_text(content)[:200]

    # Build fingerprint input
    components = [
        norm_type,
        norm_task,
        norm_app,
        entities_str,
        norm_content
    ]

    fingerprint_input = "::".join(components)

    # Generate SHA256 hash
    return hashlib.sha256(fingerprint_input.encode('utf-8')).hexdigest()


def fingerprints_match(fp1: Optional[str], fp2: Optional[str]) -> bool:
    """
    Check if two fingerprints match (case-insensitive).

    None values are treated as empty strings.
    """
    fp1 = fp1 or ""
    fp2 = fp2 or ""
    return fp1.lower() == fp2.lower()
