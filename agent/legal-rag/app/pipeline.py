"""RagPipeline — orchestrates ingest and query end-to-end."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.config import config
from app.ingest.embedder import FaissEmbedder
from app.ingest.bm25_builder import BM25Index
from app.ingest.graph_builder import KnowledgeGraphBuilder
from app.ingest.orchestrator import ChunkStore, IngestOrchestrator
from app.llm.client import LegalLLMClient
from app.llm import prompts as P
from app.models import Citation, IngestStatus, QueryRequest, QueryResponse
from app.retrieval.retriever import HybridRetriever
from app.retrieval.graph_retriever import AugmentedResult, GraphRetriever
from app.routing.query_router import QueryRouter

logger = logging.getLogger(__name__)


class RagPipeline:
    def __init__(self) -> None:
        self.embedder = FaissEmbedder()
        self.bm25 = BM25Index()
        self.chunk_store = ChunkStore()
        self.llm = LegalLLMClient()
        self.graph_builder = KnowledgeGraphBuilder(llm_client=self.llm)
        self.orchestrator = IngestOrchestrator(
            embedder=self.embedder,
            bm25=self.bm25,
            graph_builder=self.graph_builder,
            chunk_store=self.chunk_store,
        )
        self.retriever: Optional[HybridRetriever] = None
        self.graph_retriever: Optional[GraphRetriever] = None
        self.query_router = QueryRouter()
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing indexes from disk (if present)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.chunk_store.load)
        await loop.run_in_executor(None, self.embedder.load)
        await loop.run_in_executor(None, self.bm25.load)
        graph = await loop.run_in_executor(None, self.graph_builder.load)

        self.retriever = HybridRetriever(self.embedder, self.bm25, self.chunk_store)
        self.graph_retriever = GraphRetriever(graph, self.chunk_store)
        self._initialized = True
        logger.info("RagPipeline initialized — %d chunks on disk", len(self.chunk_store.all()))

    # ── Ingest ────────────────────────────────────────────────────────────────

    async def ingest(self, pdf_bytes: bytes, filename: str) -> str:
        return await self.orchestrator.run(pdf_bytes, filename)

    def ingest_status(self, ingest_id: str) -> Optional[IngestStatus]:
        return self.orchestrator.get_status(ingest_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    async def query(self, req: QueryRequest) -> QueryResponse:
        if not self._initialized:
            await self.initialize()

        if not self.chunk_store.all():
            return QueryResponse(
                response="No legal documents have been ingested yet. Please upload a PDF first.",
                tools_used=["legal-rag"],
            )

        # 1. Classify
        classification = await self.query_router.classify(req.message)

        # 2. Base retrieval
        assert self.retriever is not None
        base_chunks = await self.retriever.retrieve(req.message, top_k_final=classification.top_k)

        # 3. Graph augmentation
        assert self.graph_retriever is not None
        aug: AugmentedResult = await asyncio.get_event_loop().run_in_executor(
            None, self.graph_retriever.augment, req.message, base_chunks
        )

        # 4. Multi-hop decomposition (if required)
        if classification.requires_multihop and len(aug.augmented_chunks) > 0:
            aug = await self._multihop(req.message, aug)

        # 5. Assemble context
        context, citations = self._assemble_context(aug.augmented_chunks)
        graph_triplets_str = _format_triplets(aug.graph_triplets)

        # 6. Generate
        system = P.get_system_prompt(classification.task_type, context, graph_triplets_str)
        user = P.get_user_prompt(req.message)
        response_text = await self.llm.generate(system, user)

        return QueryResponse(
            response=response_text,
            citations=citations,
            task_type=classification.task_type,
            graph_paths=[{"path": p} for p in aug.paths_found[:5]],
            tools_used=["legal-rag", f"strategy:{classification.task_type}"],
        )

    async def _multihop(self, question: str, base_aug: AugmentedResult) -> AugmentedResult:
        """Decompose question into sub-questions and merge retrieval results."""
        try:
            raw = await self.llm.extract_json(
                P.MULTIHOP_DECOMPOSE_SYSTEM,
                P.MULTIHOP_DECOMPOSE_USER.format(question=question),
            )
            raw = _strip_fences(raw)
            sub_questions: List[str] = json.loads(raw)
        except Exception:
            return base_aug

        assert self.retriever is not None
        assert self.graph_retriever is not None

        all_chunks = list(base_aug.augmented_chunks)
        all_triplets = list(base_aug.graph_triplets)
        existing_ids = {sc.chunk.chunk_id for sc in all_chunks}

        for sub_q in sub_questions[:4]:
            sub_base = await self.retriever.retrieve(sub_q, top_k_final=6)
            sub_aug = await asyncio.get_event_loop().run_in_executor(
                None, self.graph_retriever.augment, sub_q, sub_base
            )
            for sc in sub_aug.augmented_chunks:
                if sc.chunk.chunk_id not in existing_ids:
                    all_chunks.append(sc)
                    existing_ids.add(sc.chunk.chunk_id)
            all_triplets.extend(sub_aug.graph_triplets)

        all_chunks.sort(key=lambda x: x.score, reverse=True)
        return AugmentedResult(
            augmented_chunks=all_chunks[:config.TOP_K_RERANKED + 5],
            graph_triplets=all_triplets[:20],
            paths_found=base_aug.paths_found,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assemble_context(self, scored_chunks) -> tuple:
        context_parts = []
        citations: List[Citation] = []

        for i, sc in enumerate(scored_chunks, 1):
            c = sc.chunk
            label = f"[{i}]"
            header = f"{label} {c.source}"
            if c.article:
                header += f" — {c.article}"
            elif c.section:
                header += f" — {c.section}"
            elif c.chapter:
                header += f" — {c.chapter}"
            context_parts.append(f"{header}\n{c.text[:1200]}")
            citations.append(
                Citation(
                    chunk_id=c.chunk_id,
                    source=c.source,
                    section=c.article or c.section or c.chapter,
                    text_excerpt=c.text[:200],
                    score=sc.score,
                )
            )

        return "\n\n---\n\n".join(context_parts), citations


def _format_triplets(triplets: List[Dict]) -> str:
    if not triplets:
        return ""
    lines = []
    for t in triplets[:15]:
        sem = t.get("sem_type", "")
        sem_suffix = f" [{sem}]" if sem and sem != "general" else ""
        lines.append(f"• {t['node1']} —[{t['edge']}]→ {t['node2']}{sem_suffix}")
    return "\n".join(lines)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text.rstrip())
    return text.strip()
