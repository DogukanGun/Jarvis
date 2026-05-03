"""Hybrid retriever: FAISS + BM25 → RRF fusion → BGE reranker."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.config import config
from app.ingest.chunker import Chunk
from app.ingest.embedder import FaissEmbedder
from app.ingest.bm25_builder import BM25Index
from app.ingest.orchestrator import ChunkStore

logger = logging.getLogger(__name__)


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float
    rank: int = 0


class HybridRetriever:
    def __init__(
        self,
        embedder: FaissEmbedder,
        bm25: BM25Index,
        chunk_store: ChunkStore,
    ) -> None:
        self.embedder = embedder
        self.bm25 = bm25
        self.chunk_store = chunk_store
        self._reranker: Optional[object] = None

    def _load_reranker(self) -> None:
        if not config.ENABLE_RERANKER:
            return
        if self._reranker is None:
            try:
                from FlagEmbedding import FlagReranker  # type: ignore
                logger.info("Loading reranker: %s (fp16=%s)", config.RERANKER_MODEL, config.RERANKER_USE_FP16)
                self._reranker = FlagReranker(config.RERANKER_MODEL, use_fp16=config.RERANKER_USE_FP16)
            except Exception as e:
                logger.warning("Reranker unavailable (%s) — skipping reranking step", e)

    async def retrieve(self, query: str, top_k_final: Optional[int] = None) -> List[ScoredChunk]:
        if top_k_final is None:
            top_k_final = config.TOP_K_RERANKED

        loop = asyncio.get_event_loop()
        dense_res, sparse_res = await asyncio.gather(
            loop.run_in_executor(None, self.embedder.search, query, config.TOP_K_DENSE),
            loop.run_in_executor(None, self.bm25.search, query, config.TOP_K_SPARSE),
        )

        fused = _rrf_fuse(dense_res, sparse_res, config.RRF_K, config.RRF_WEIGHT_DENSE, config.RRF_WEIGHT_SPARSE)
        fused = fused[: config.TOP_K_FUSED]

        # Resolve chunk objects
        scored: List[ScoredChunk] = []
        for chunk_id, score in fused:
            chunk = self.chunk_store.by_id(chunk_id)
            if chunk:
                scored.append(ScoredChunk(chunk=chunk, score=score))

        if not scored:
            return scored

        # Rerank
        scored = await loop.run_in_executor(None, self._rerank, query, scored)
        return scored[:top_k_final]

    def _rerank(self, query: str, candidates: List[ScoredChunk]) -> List[ScoredChunk]:
        self._load_reranker()
        if self._reranker is None:
            for i, c in enumerate(candidates):
                c.rank = i
            return candidates
        try:
            pairs = [(query, c.chunk.text[:512]) for c in candidates]
            scores = self._reranker.compute_score(pairs)  # type: ignore[union-attr]
            for c, s in zip(candidates, scores):
                c.score = float(s)
            candidates.sort(key=lambda x: x.score, reverse=True)
            for i, c in enumerate(candidates):
                c.rank = i
        except Exception as e:
            logger.warning("Reranking failed: %s", e)
            for i, c in enumerate(candidates):
                c.rank = i
        return candidates


def _rrf_fuse(
    dense: List[Tuple[str, float]],
    sparse: List[Tuple[str, float]],
    k: int,
    w_dense: float,
    w_sparse: float,
) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}

    for rank, (chunk_id, _) in enumerate(dense):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + w_dense / (k + rank + 1)

    for rank, (chunk_id, _) in enumerate(sparse):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + w_sparse / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
