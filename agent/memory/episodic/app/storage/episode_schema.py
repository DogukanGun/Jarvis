"""
Episode Schema Definitions

Pydantic models for episodes, promotion proposals, and user decisions.
"""

from typing import Optional, List, Literal, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class EpisodeType(str, Enum):
    """Types of episodes that can be stored"""
    INTERACTION = "interaction"
    TASK_COMPLETION = "task_completion"
    ERROR = "error"
    OBSERVATION = "observation"
    USER_FEEDBACK = "user_feedback"


class Episode(BaseModel):
    """
    Episode storage model for short-term memory.

    Episodes are deduplicated via fingerprinting and can be
    promoted to long-term memory (mem0) after reaching thresholds.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    fingerprint: str

    # Content
    text: str
    summary: Optional[str] = None

    # Metadata
    episode_type: EpisodeType = EpisodeType.INTERACTION
    task_type: Optional[str] = None
    app: Optional[str] = None
    entities: List[str] = Field(default_factory=list)

    # Temporal
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

    # Embedding (stored as list of floats)
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None

    # Quality metrics
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reinforcement_count: int = Field(default=1, ge=1)

    # Status
    is_deleted: bool = False
    promoted_to_mem0: bool = False
    promotion_proposal_id: Optional[str] = None

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class EpisodeCandidate(BaseModel):
    """
    Candidate for episode creation from memory_intents.

    This is the input format before fingerprinting and storage.
    """
    text: str
    summary: Optional[str] = None
    episode_type: EpisodeType = EpisodeType.INTERACTION
    task_type: Optional[str] = None
    app: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        use_enum_values = True


class PromotionProposal(BaseModel):
    """
    Proposal for promoting an episode to long-term memory (mem0).

    Requires user approval via Kafka communication.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    episode_id: str
    user_id: str

    # Proposal content
    target_path: Optional[str] = None  # mem0 section path
    proposed_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)  # Supporting episode IDs

    # Status
    status: Literal["pending", "approved", "rejected", "edited", "timeout"] = "pending"
    user_response: Optional[str] = None  # User's edit if applicable

    # Temporal
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime  # 5 minute timeout
    resolved_at: Optional[datetime] = None


class UserDecision(BaseModel):
    """
    Record of user decision on a promotion proposal.

    Used for learning user preferences over time.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proposal_id: str
    user_id: str

    decision: Literal["approve", "reject", "edit"]
    original_value: str
    final_value: Optional[str] = None  # After edit if applicable
    reason: Optional[str] = None  # Optional user explanation

    created_at: datetime = Field(default_factory=datetime.utcnow)


class EpisodeQuery(BaseModel):
    """Query parameters for episode search"""
    user_id: str

    # Text search
    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None

    # Filters
    task_types: Optional[List[str]] = None
    apps: Optional[List[str]] = None
    episode_types: Optional[List[EpisodeType]] = None
    entities: Optional[List[str]] = None

    # Temporal filters
    after_timestamp: Optional[datetime] = None
    before_timestamp: Optional[datetime] = None
    recent_days: Optional[int] = None

    # Quality filters
    min_importance: Optional[float] = None
    min_confidence: Optional[float] = None
    min_reinforcement: Optional[int] = None

    # Pagination
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    # Ranking options
    boost_recent: bool = True
    boost_reinforced: bool = True

    class Config:
        use_enum_values = True


class EpisodeSearchResult(BaseModel):
    """Single result from episode search"""
    episode: Episode
    score: float = Field(ge=0.0, le=1.0)
    match_reasons: List[str] = Field(default_factory=list)


class EpisodeSearchResponse(BaseModel):
    """Response from episode search"""
    episodes: List[EpisodeSearchResult]
    total_count: int
    query_time_ms: float
    used_filters: Dict[str, Any] = Field(default_factory=dict)
