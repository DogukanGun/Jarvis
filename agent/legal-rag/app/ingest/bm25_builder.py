"""BM25 sparse index builder and searcher."""

from __future__ import annotations

import logging
import os
import pickle
import re
from typing import List, Optional, Tuple

from app.config import config
from app.ingest.chunker import Chunk

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class BM25Index:
    def __init__(self) -> None:
        self._index: Optional[object] = None
        self._chunk_ids: List[str] = []

    def build(self, chunks: List[Chunk]) -> None:
        from rank_bm25 import BM25Okapi  # type: ignore

        tokenized = [_tokenize(c.text) for c in chunks]
        self._index = BM25Okapi(tokenized)
        self._chunk_ids = [c.chunk_id for c in chunks]
        logger.info("BM25 index built: %d documents", len(chunks))

    def add_chunks(self, new_chunks: List[Chunk], all_chunks: List[Chunk]) -> None:
        """Rebuild BM25 index from all chunks (BM25Okapi is not incremental)."""
        self.build(all_chunks)

    def search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if self._index is None or not self._chunk_ids:
            return []
        tokens = _tokenize(query)
        scores = self._index.get_scores(tokens)  # type: ignore[union-attr]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(self._chunk_ids[i], float(s)) for i, s in ranked[:top_k] if s > 0]

    def save(self) -> None:
        os.makedirs(os.path.dirname(config.BM25_PATH) or ".", exist_ok=True)
        with open(config.BM25_PATH, "wb") as f:
            pickle.dump({"index": self._index, "chunk_ids": self._chunk_ids}, f)
        logger.info("BM25 index saved to %s", config.BM25_PATH)

    def load(self) -> bool:
        if not os.path.exists(config.BM25_PATH):
            return False
        with open(config.BM25_PATH, "rb") as f:
            data = pickle.load(f)
        self._index = data["index"]
        self._chunk_ids = data["chunk_ids"]
        logger.info("BM25 index loaded: %d documents", len(self._chunk_ids))
        return True
