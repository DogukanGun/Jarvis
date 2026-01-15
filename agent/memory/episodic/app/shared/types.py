"""
Shared type definitions for MainGraph

Defines the complete state schema used across all nodes.
"""

from typing import TypedDict, Optional, List, Dict, Any


class MainGraphState(TypedDict, total=False):
    """
    Complete state schema for MainGraph.

    Fields are organized by the node that produces them.
    """
    # ========================================================================
    # INPUT (from user/application)
    # ========================================================================
    user_id: str                                # Required user identifier
    prompt: str                                 # Raw user prompt
    context: Optional[Dict[str, Any]]          # Optional context dict

    # ========================================================================
    # PREPROCESS_INPUT (Node 1)
    # ========================================================================
    normalized_prompt: str                      # Cleaned prompt
    task_type: str                             # Detected task type
    app: Optional[str]                         # Detected app
    entities: List[str]                        # Extracted entities
    preprocess_meta: Dict[str, Any]            # Metadata

    # ========================================================================
    # MEM0 HANDLING (Nodes 2-4)
    # ========================================================================
    force_mem0_reload: Optional[bool]          # Force reload flag
    mem0_state: Optional[Dict[str, Any]]       # Cached mem0 state
    mem0_items: List[Dict[str, Any]]           # Normalized mem0 items
    mem0_error: Optional[str]                  # Error message
    mem0_loaded: bool                          # Loaded this run?

    # ========================================================================
    # RETRIEVE_EPISODES (Node 5)
    # ========================================================================
    retrieved_episodes: List[Dict[str, Any]]   # Retrieved episodes
    retrieval_query: str                       # Query used for retrieval
    retrieval_error: Optional[str]             # Error message
    retrieve_limit: Optional[int]              # Max episodes to retrieve

    # ========================================================================
    # COMPOSE_CONTEXT (Node 6)
    # ========================================================================
    llm_context: Dict[str, Any]                # Composed context for LLM

    # ========================================================================
    # LLM_STEP (Node 7)
    # ========================================================================
    llm_output: Any                            # LLM response (str or dict)
    memory_intents: Optional[Any]              # Memory intents for background
    llm_error: Optional[str]                   # Error message

    # ========================================================================
    # RETURN_OUTPUT (Node 8)
    # ========================================================================
    response_payload: Optional[Dict[str, Any]] # Final response to user

    # ========================================================================
    # ENQUEUE_MEMORY_WRITE_GRAPH (Node 9)
    # ========================================================================
    memory_job_payload: Optional[Dict[str, Any]]  # Payload for background job
    enqueue_error: Optional[str]               # Error message
