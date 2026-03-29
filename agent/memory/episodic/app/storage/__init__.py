"""
Storage layer for episodic memory.

Provides SQLite-based episode storage with fingerprinting and deduplication.
"""

from .episode_schema import (
    Episode,
    EpisodeType,
    EpisodeCandidate,
    PromotionProposal,
    UserDecision,
    EpisodeQuery,
    EpisodeSearchResult,
    EpisodeSearchResponse,
)
from .episode_repository import EpisodeRepository, get_episode_repository
from .fingerprint import generate_fingerprint

__all__ = [
    "Episode",
    "EpisodeType",
    "EpisodeCandidate",
    "PromotionProposal",
    "UserDecision",
    "EpisodeQuery",
    "EpisodeSearchResult",
    "EpisodeSearchResponse",
    "EpisodeRepository",
    "get_episode_repository",
    "generate_fingerprint",
]
