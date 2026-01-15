"""
Ollama Embeddings Client

Local embedding generation via Ollama.
"""

from .client import OllamaEmbeddingClient, get_embedding_client

__all__ = ["OllamaEmbeddingClient", "get_embedding_client"]
