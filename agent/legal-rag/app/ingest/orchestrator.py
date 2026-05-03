"""Ingest orchestrator: PDF → chunks → FAISS + BM25 + graph."""

from __future__ import annotations

import asyncio
import logging
import os
import pickle
import uuid
from typing import Dict, List, Optional

from app.config import config
from app.ingest.chunker import ArticleChunker, Chunk
from app.ingest.embedder import FaissEmbedder
from app.ingest.bm25_builder import BM25Index
from app.ingest.graph_builder import KnowledgeGraphBuilder
from app.models import IngestStatus

logger = logging.getLogger(__name__)


class IngestOrchestrator:
    def __init__(
        self,
        embedder: FaissEmbedder,
        bm25: BM25Index,
        graph_builder: KnowledgeGraphBuilder,
        chunk_store: "ChunkStore",
    ) -> None:
        self.embedder = embedder
        self.bm25 = bm25
        self.graph_builder = graph_builder
        self.chunk_store = chunk_store
        self._status: Dict[str, IngestStatus] = {}

    def get_status(self, ingest_id: str) -> Optional[IngestStatus]:
        return self._status.get(ingest_id)

    async def run(self, pdf_bytes: bytes, filename: str) -> str:
        ingest_id = str(uuid.uuid4())
        status = IngestStatus(ingest_id=ingest_id, status="pending", filename=filename)
        self._status[ingest_id] = status

        asyncio.create_task(self._run_ingest(ingest_id, pdf_bytes, filename))
        return ingest_id

    async def _run_ingest(self, ingest_id: str, pdf_bytes: bytes, filename: str) -> None:
        status = self._status[ingest_id]
        try:
            status.status = "processing"

            # Step 1: PDF → text
            status.progress = 0.05
            text = await asyncio.get_event_loop().run_in_executor(None, _extract_text, pdf_bytes)
            if not text.strip():
                raise ValueError("No text extracted from PDF")

            # Step 2: chunk
            status.progress = 0.15
            chunker = ArticleChunker()
            chunks: List[Chunk] = await asyncio.get_event_loop().run_in_executor(
                None, chunker.chunk, text, filename
            )
            if not chunks:
                raise ValueError("No chunks produced")
            status.chunk_count = len(chunks)
            logger.info("[%s] %d chunks from %s", ingest_id, len(chunks), filename)

            # Step 3: save chunks
            existing_chunks = self.chunk_store.all()
            all_chunks = existing_chunks + chunks
            await asyncio.get_event_loop().run_in_executor(None, self.chunk_store.save_all, all_chunks)
            status.progress = 0.25

            # Step 4: FAISS
            status.progress = 0.35
            await asyncio.get_event_loop().run_in_executor(None, self.embedder.add_chunks, chunks)
            await asyncio.get_event_loop().run_in_executor(None, self.embedder.save)
            status.progress = 0.50

            # Step 5: BM25 (must rebuild from all chunks)
            await asyncio.get_event_loop().run_in_executor(None, self.bm25.build, all_chunks)
            await asyncio.get_event_loop().run_in_executor(None, self.bm25.save)
            status.progress = 0.60

            # Step 6–8: graph (LLM extraction + community + PageRank)
            status.progress = 0.65
            G = await self.graph_builder.build_full(chunks)
            status.entity_count = G.number_of_nodes()
            status.progress = 0.90

            # Merge with existing graph if any
            existing_G = self.graph_builder.load()
            if existing_G is not None:
                G = _merge_graphs(existing_G, G)
                # Recompute global metrics after merge
                self.graph_builder.compute_communities(G)
                self.graph_builder.compute_pagerank(G)

            await asyncio.get_event_loop().run_in_executor(None, self.graph_builder.save, G)
            status.progress = 1.0
            status.status = "done"
            logger.info("[%s] Ingest done: %d chunks, %d entities", ingest_id, len(chunks), G.number_of_nodes())

        except Exception as e:
            logger.error("[%s] Ingest failed: %s", ingest_id, e)
            status.status = "failed"
            status.error = str(e)


class ChunkStore:
    """Persist all ingested chunks to disk."""

    def __init__(self) -> None:
        self._chunks: List[Chunk] = []

    def load(self) -> bool:
        if not os.path.exists(config.CHUNKS_PATH):
            return False
        with open(config.CHUNKS_PATH, "rb") as f:
            self._chunks = pickle.load(f)
        return True

    def save_all(self, chunks: List[Chunk]) -> None:
        os.makedirs(os.path.dirname(config.CHUNKS_PATH) or ".", exist_ok=True)
        with open(config.CHUNKS_PATH, "wb") as f:
            pickle.dump(chunks, f)
        self._chunks = chunks

    def all(self) -> List[Chunk]:
        return list(self._chunks)

    def by_id(self, chunk_id: str) -> Optional[Chunk]:
        for c in self._chunks:
            if c.chunk_id == chunk_id:
                return c
        return None


def _extract_text(pdf_bytes: bytes) -> str:
    import io
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages)
        if text.strip():
            return text
    except Exception as e:
        logger.warning("pdfplumber failed: %s — trying pypdf", e)

    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as e:
        raise RuntimeError(f"PDF text extraction failed: {e}") from e


def _merge_graphs(base, new):
    import networkx as nx
    G = nx.compose(base, new)
    # Sum edge weights for overlapping edges
    for u, v, data in new.edges(data=True):
        if base.has_edge(u, v):
            G[u][v]["weight"] = base[u][v].get("weight", 0) + data.get("weight", 0)
            existing_edges = base[u][v].get("edges", [])
            new_edges = data.get("edges", [])
            G[u][v]["edges"] = list(set(existing_edges + new_edges))
    return G
