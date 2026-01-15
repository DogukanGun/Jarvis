"""
Memory Write Graph State Definition

State schema for the async memory write pipeline.
"""

from typing import TypedDict, Optional, List, Dict, Any


class MemoryWriteState(TypedDict, total=False):
    """
    State for memory_write_graph.

    Tracks the episode through fingerprinting, deduplication,
    storage, embedding, and optional promotion.
    """

    # =========================================================================
    # Input (from enqueue_memory_write_graph)
    # =========================================================================
    user_id: str
    task_type: Optional[str]
    app: Optional[str]
    entities: List[str]
    prompt: str
    llm_output: Any
    memory_intents: Optional[Dict[str, Any]]
    timestamp: str

    # =========================================================================
    # build_episode_candidates
    # =========================================================================
    episode_candidates: List[Dict[str, Any]]
    candidates_count: int

    # =========================================================================
    # gate_action (router decision)
    # =========================================================================
    gate_decision: str  # "save", "ignore", "save_and_promote"

    # =========================================================================
    # redact_secrets
    # =========================================================================
    redacted_candidates: List[Dict[str, Any]]
    redaction_log: List[Dict[str, Any]]
    secrets_found: bool

    # =========================================================================
    # fingerprint
    # =========================================================================
    fingerprint: str
    fingerprint_input: str  # For debugging

    # =========================================================================
    # dedupe_lookup
    # =========================================================================
    existing_episode_id: Optional[str]
    existing_episode: Optional[Dict[str, Any]]
    is_duplicate: bool

    # =========================================================================
    # insert_episode / reinforce_episode
    # =========================================================================
    episode_id: str
    episode: Dict[str, Any]
    action_taken: str  # "inserted" or "reinforced"
    new_reinforcement_count: int

    # =========================================================================
    # embed_episode
    # =========================================================================
    embedding: Optional[List[float]]
    embedding_model: Optional[str]
    embedding_error: Optional[str]

    # =========================================================================
    # promote_check
    # =========================================================================
    should_promote: bool
    promotion_reason: Optional[str]

    # =========================================================================
    # create_promotion_proposal
    # =========================================================================
    proposal_id: Optional[str]
    proposal: Optional[Dict[str, Any]]

    # =========================================================================
    # Error tracking
    # =========================================================================
    errors: List[str]
    completed: bool
