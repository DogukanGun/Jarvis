"""
Embed Episode Node

Generates embedding for episode using Ollama and stores it.
"""

from typing import Dict, Any
import logging

from ..state import MemoryWriteState
from app.storage import get_episode_repository
from app.clients.ollama_embeddings import get_embedding_client

logger = logging.getLogger(__name__)


def embed_episode(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Generate and store embedding for episode.

    Uses Ollama to generate embedding from episode text.
    Updates the stored episode with the embedding.

    Args:
        state: Current graph state

    Returns:
        State updates with embedding, embedding_model, embedding_error
    """
    episode_id = state.get("episode_id")
    episode = state.get("episode", {})

    if not episode_id:
        logger.warning("No episode_id for embedding")
        return {
            "embedding": None,
            "embedding_model": None,
            "embedding_error": "No episode to embed"
        }

    # Get text to embed
    text = episode.get("text", "")
    summary = episode.get("summary")

    # Prefer summary for embedding if available
    embed_text = summary or text
    if not embed_text:
        logger.warning("No text to embed")
        return {
            "embedding": None,
            "embedding_model": None,
            "embedding_error": "No text to embed"
        }

    try:
        # Get embedding client
        client = get_embedding_client()

        # Check if embedding model is available
        if not client.health_check():
            logger.warning("Embedding model not available, skipping embedding")
            return {
                "embedding": None,
                "embedding_model": None,
                "embedding_error": "Embedding model not available"
            }

        # Generate embedding
        embedding = client.embed(embed_text)

        if not embedding:
            logger.warning("Failed to generate embedding")
            return {
                "embedding": None,
                "embedding_model": None,
                "embedding_error": "Embedding generation failed"
            }

        # Update episode in storage
        repo = get_episode_repository()
        from app.config import config

        repo.update_episode(episode_id, {
            "embedding": embedding,
            "embedding_model": config.EMBEDDING_MODEL
        })

        logger.info(f"Embedded episode {episode_id} with {len(embedding)} dimensions")

        return {
            "embedding": embedding,
            "embedding_model": config.EMBEDDING_MODEL,
            "embedding_error": None
        }

    except Exception as e:
        error_msg = f"Embedding error: {str(e)}"
        logger.error(error_msg)
        return {
            "embedding": None,
            "embedding_model": None,
            "embedding_error": error_msg
        }
