"""FAISS HNSW embedder using BGE sentence-transformers."""

from __future__ import annotations

import logging
import os
import pickle
from typing import List, Optional, Tuple

import numpy as np

from app.config import config
from app.ingest.chunker import Chunk

logger = logging.getLogger(__name__)


class FaissEmbedder:
    def __init__(self) -> None:
        self._model: Optional[object] = None
        self._index: Optional[object] = None
        self._chunk_ids: List[str] = []

    def _load_model(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("Loading BGE model: %s", config.BGE_MODEL)
            self._model = SentenceTransformer(config.BGE_MODEL)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        self._load_model()
        vecs = self._model.encode(  # type: ignore[union-attr]
            texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
        )
        return np.array(vecs, dtype=np.float32)

    def build_index(self, chunks: List[Chunk]) -> None:
        import faiss  # type: ignore

        texts = [c.text for c in chunks]
        vecs = self.embed_texts(texts)
        dim = vecs.shape[1]

        index = faiss.IndexHNSWFlat(dim, 32)
        index.hnsw.efConstruction = 200
        index.hnsw.efSearch = 64
        index.add(vecs)

        self._index = index
        self._chunk_ids = [c.chunk_id for c in chunks]
        logger.info("FAISS index built: %d vectors, dim=%d", len(chunks), dim)

    def add_chunks(self, new_chunks: List[Chunk]) -> None:
        """Incrementally add new chunks to an existing index."""
        if self._index is None:
            self.build_index(new_chunks)
            return
        vecs = self.embed_texts([c.text for c in new_chunks])
        self._index.add(vecs)  # type: ignore[union-attr]
        self._chunk_ids.extend(c.chunk_id for c in new_chunks)

    def search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if self._index is None or not self._chunk_ids:
            return []
        q_vec = self.embed_texts([query])
        distances, indices = self._index.search(q_vec, min(top_k, len(self._chunk_ids)))  # type: ignore[union-attr]
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_ids):
                continue
            results.append((self._chunk_ids[idx], float(dist)))
        return results

    def save(self) -> None:
        import faiss  # type: ignore

        os.makedirs(os.path.dirname(config.FAISS_INDEX_PATH) or ".", exist_ok=True)
        faiss.write_index(self._index, config.FAISS_INDEX_PATH)  # type: ignore[arg-type]
        ids_path = config.FAISS_INDEX_PATH + ".ids"
        with open(ids_path, "wb") as f:
            pickle.dump(self._chunk_ids, f)
        logger.info("FAISS index saved to %s", config.FAISS_INDEX_PATH)

    def load(self) -> bool:
        import faiss  # type: ignore

        if not os.path.exists(config.FAISS_INDEX_PATH):
            return False
        ids_path = config.FAISS_INDEX_PATH + ".ids"
        if not os.path.exists(ids_path):
            return False
        self._index = faiss.read_index(config.FAISS_INDEX_PATH)
        with open(ids_path, "rb") as f:
            self._chunk_ids = pickle.load(f)
        logger.info("FAISS index loaded: %d vectors", len(self._chunk_ids))
        return True
