"""Knowledge graph builder: entity extraction → NetworkX graph → semantic alignment → community detection → PageRank."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.config import config
from app.ingest.chunker import Chunk
from app.llm.prompts import (
    SEMANTIC_ALIGNMENT_SYSTEM,
    SEMANTIC_ALIGNMENT_USER,
    TRIPLET_EXTRACTION_SYSTEM,
    TRIPLET_EXTRACTION_USER,
)

logger = logging.getLogger(__name__)

_DIRECT_WEIGHT = 4.0
_COOCCUR_CHUNK_WEIGHT = 1.0
_COOCCUR_GLOBAL_WEIGHT = 0.5


@dataclass
class Triplet:
    node1: str
    edge: str
    node2: str
    weight: float = _DIRECT_WEIGHT
    chunk_id: str = ""


class KnowledgeGraphBuilder:
    def __init__(self, llm_client: Optional[object] = None) -> None:
        self._llm = llm_client

    # ── LLM extraction ────────────────────────────────────────────────────────

    async def extract_triplets(self, chunk: Chunk) -> List[Triplet]:
        if self._llm is None:
            return []
        prompt_user = TRIPLET_EXTRACTION_USER.format(text=chunk.text[:2000])
        try:
            raw = await self._llm.extract_json(TRIPLET_EXTRACTION_SYSTEM, prompt_user)  # type: ignore[union-attr]
            raw = _strip_fences(raw)
            items = json.loads(raw)
            triplets = []
            for it in items:
                n1 = str(it.get("node1", "")).strip()
                edge = str(it.get("edge", "")).strip()
                n2 = str(it.get("node2", "")).strip()
                if n1 and edge and n2:
                    triplets.append(Triplet(node1=n1, edge=edge, node2=n2, chunk_id=chunk.chunk_id))
            return triplets
        except Exception as e:
            logger.warning("Triplet extraction failed for chunk %s: %s", chunk.chunk_id, e)
            return []

    async def extract_triplets_batch(
        self, chunks: List[Chunk], semaphore: asyncio.Semaphore
    ) -> Dict[str, List[Triplet]]:
        results: Dict[str, List[Triplet]] = {}

        async def _extract(c: Chunk) -> None:
            async with semaphore:
                results[c.chunk_id] = await self.extract_triplets(c)

        await asyncio.gather(*[_extract(c) for c in chunks])
        return results

    # ── Graph construction ────────────────────────────────────────────────────

    def build_graph(
        self, chunks: List[Chunk], triplets_per_chunk: Dict[str, List[Triplet]]
    ) -> nx.Graph:
        G = nx.Graph()

        def _ensure_node(name: str) -> None:
            if name not in G:
                G.add_node(name, chunk_ids=[], pagerank=0.0, community=0, label=name)

        # 1. Add LLM-extracted triplets (weight=4)
        for chunk_id, triplets in triplets_per_chunk.items():
            for t in triplets:
                _ensure_node(t.node1)
                _ensure_node(t.node2)
                G.nodes[t.node1]["chunk_ids"].append(chunk_id)
                G.nodes[t.node2]["chunk_ids"].append(chunk_id)
                if G.has_edge(t.node1, t.node2):
                    G[t.node1][t.node2]["weight"] += _DIRECT_WEIGHT
                    G[t.node1][t.node2]["edges"].append(t.edge)
                else:
                    G.add_edge(t.node1, t.node2, weight=_DIRECT_WEIGHT, edges=[t.edge], sem_type="general")

        # 2. Co-occurrence within same chunk (weight += 1 per shared chunk)
        node_to_chunks: Dict[str, set] = defaultdict(set)
        for n, data in G.nodes(data=True):
            for cid in data.get("chunk_ids", []):
                node_to_chunks[n].add(cid)

        chunk_to_nodes: Dict[str, List[str]] = defaultdict(list)
        for n, cids in node_to_chunks.items():
            for cid in cids:
                chunk_to_nodes[cid].append(n)

        for cid, nodes in chunk_to_nodes.items():
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    n1, n2 = nodes[i], nodes[j]
                    if G.has_edge(n1, n2):
                        G[n1][n2]["weight"] += _COOCCUR_CHUNK_WEIGHT
                    else:
                        G.add_edge(n1, n2, weight=_COOCCUR_CHUNK_WEIGHT, edges=[], sem_type="general")

        # 3. Global co-occurrence across entire corpus (weight += 0.5)
        node_pair_corpus_count: Dict[Tuple[str, str], int] = defaultdict(int)
        all_nodes = list(G.nodes())
        for c in chunks:
            present = [n for n in all_nodes if n.lower() in c.text.lower()]
            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    n1, n2 = min(present[i], present[j]), max(present[i], present[j])
                    node_pair_corpus_count[(n1, n2)] += 1

        for (n1, n2), count in node_pair_corpus_count.items():
            if G.has_edge(n1, n2):
                G[n1][n2]["weight"] += _COOCCUR_GLOBAL_WEIGHT * count
            else:
                G.add_edge(n1, n2, weight=_COOCCUR_GLOBAL_WEIGHT * count, edges=[], sem_type="general")

        # Deduplicate chunk_ids per node
        for n in G.nodes():
            G.nodes[n]["chunk_ids"] = list(set(G.nodes[n]["chunk_ids"]))

        logger.info("Graph built: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
        return G

    # ── Semantic alignment ────────────────────────────────────────────────────

    async def tag_semantic_relations(self, G: nx.Graph) -> None:
        if self._llm is None or not config.ENABLE_SEMANTIC_ALIGNMENT:
            return
        sem = asyncio.Semaphore(config.LLM_EXTRACTION_CONCURRENCY)
        # Only align LLM-extracted edges (those with `edges` payload), and cap
        # to the top-N by weight so ingest stays within rate-limit budgets.
        candidates = [
            (u, v, d) for u, v, d in G.edges(data=True)
            if d.get("sem_type") == "general" and d.get("edges")
        ]
        candidates.sort(key=lambda x: x[2].get("weight", 0), reverse=True)
        edges_to_tag = candidates[: config.SEMANTIC_ALIGNMENT_MAX_EDGES]
        logger.info(
            "Semantic alignment: tagging %d / %d candidate edges",
            len(edges_to_tag), len(candidates),
        )

        async def _tag(u: str, v: str, d: dict) -> None:
            edge_label = d["edges"][0] if d["edges"] else "related to"
            prompt = SEMANTIC_ALIGNMENT_USER.format(c1=u, edge=edge_label, c2=v)
            async with sem:
                try:
                    raw = (await self._llm.generate(SEMANTIC_ALIGNMENT_SYSTEM, prompt)).strip().lower()  # type: ignore[union-attr]
                    valid = {"synonym", "hypernym", "ispartof", "belongto", "causes", "general"}
                    G[u][v]["sem_type"] = raw if raw in valid else "general"
                except Exception:
                    pass

        await asyncio.gather(*[_tag(u, v, d) for u, v, d in edges_to_tag])

    # ── Community detection ───────────────────────────────────────────────────

    def compute_communities(self, G: nx.Graph) -> None:
        if G.number_of_nodes() < 4:
            return
        try:
            from networkx.algorithms.community import girvan_newman  # type: ignore
            comp = girvan_newman(G)
            # Advance until we have ~8 communities or the graph is split enough
            communities = None
            for partition in comp:
                communities = list(partition)
                if len(communities) >= 8:
                    break
            if communities:
                for cid, community_set in enumerate(communities):
                    for node in community_set:
                        if node in G:
                            G.nodes[node]["community"] = cid
                logger.info("Communities detected: %d", len(communities))
        except Exception as e:
            logger.warning("Community detection failed: %s", e)

    # ── PageRank ──────────────────────────────────────────────────────────────

    def compute_pagerank(self, G: nx.Graph) -> None:
        if G.number_of_nodes() < 2:
            return
        try:
            pr = nx.pagerank(G, weight="weight", max_iter=100)
            for node, score in pr.items():
                G.nodes[node]["pagerank"] = score
            logger.info("PageRank computed for %d nodes", len(pr))
        except Exception as e:
            logger.warning("PageRank failed: %s", e)

    # ── Save / load ───────────────────────────────────────────────────────────

    def save(self, G: nx.Graph) -> None:
        import pickle
        os.makedirs(os.path.dirname(config.GRAPH_PATH) or ".", exist_ok=True)
        with open(config.GRAPH_PATH, "wb") as f:
            pickle.dump(G, f)
        logger.info("Graph saved to %s", config.GRAPH_PATH)

    def load(self) -> Optional[nx.Graph]:
        import pickle
        if not os.path.exists(config.GRAPH_PATH):
            return None
        with open(config.GRAPH_PATH, "rb") as f:
            G = pickle.load(f)
        logger.info("Graph loaded: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
        return G

    # ── Full ingest pipeline ──────────────────────────────────────────────────

    async def build_full(self, chunks: List[Chunk]) -> nx.Graph:
        sem = asyncio.Semaphore(config.LLM_EXTRACTION_CONCURRENCY)
        triplets_per_chunk = await self.extract_triplets_batch(chunks, sem)
        G = self.build_graph(chunks, triplets_per_chunk)
        await self.tag_semantic_relations(G)
        self.compute_communities(G)
        self.compute_pagerank(G)
        return G


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text.rstrip())
    return text.strip()
