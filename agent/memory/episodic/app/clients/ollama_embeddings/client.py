"""
Ollama Embedding Client

Generates embeddings locally using Ollama models.
"""

import httpx
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    """Client for generating embeddings via Ollama"""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0
    ):
        """
        Initialize Ollama embedding client.

        Args:
            model: Embedding model name (e.g., nomic-embed-text, mxbai-embed-large)
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout)

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats, or None on error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            response = self.client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding")
            if embedding:
                logger.debug(f"Generated embedding of dimension {len(embedding)}")
                return embedding

            logger.warning("No embedding in response")
            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (same order as input, None for failures)
        """
        results = []
        for text in texts:
            embedding = self.embed(text)
            results.append(embedding)
        return results

    def health_check(self) -> bool:
        """Check if Ollama is available and model is loaded"""
        try:
            # Check if Ollama is running
            response = self.client.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                return False

            # Check if embedding model is available
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            # Check for model (with or without tag)
            model_base = self.model.split(":")[0]
            for model in models:
                if model.startswith(model_base):
                    return True

            logger.warning(f"Embedding model '{self.model}' not found in Ollama")
            return False

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Factory function
_client_instance: Optional[OllamaEmbeddingClient] = None


def get_embedding_client(
    model: Optional[str] = None,
    base_url: Optional[str] = None
) -> OllamaEmbeddingClient:
    """
    Get embedding client instance.

    Args:
        model: Optional model override
        base_url: Optional base URL override

    Returns:
        OllamaEmbeddingClient instance
    """
    global _client_instance

    if _client_instance is None:
        from app.config import config
        _client_instance = OllamaEmbeddingClient(
            model=model or config.EMBEDDING_MODEL,
            base_url=base_url or config.OLLAMA_BASE_URL
        )

    return _client_instance
