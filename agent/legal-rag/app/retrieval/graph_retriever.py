"""Graph-augmented retrieval: entity lookup, neighbor expansion, PageRank boost, Dijkstra paths."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from app.config import config
from app.ingest.orchestrator import ChunkStore
from app.retrieval.retriever import ScoredChunk

logger = logging.getLogger(__name__)


@dataclass
class AugmentedResult:
    augmented_chunks: List[ScoredChunk]
    graph_triplets: List[Dict[str, Any]] = field(default_factory=list)
    paths_found: List[List[str]] = field(default_factory=list)


class GraphRetriever:
    def __init__(self, graph: Optional[nx.Graph], chunk_store: ChunkStore) -> None:
        self.graph = graph
        self.chunk_store = chunk_store

    def augment(self, query: str, base_chunks: List[ScoredChunk]) -> AugmentedResult:
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return AugmentedResult(augmented_chunks=base_chunks)

        # Normalize base scores to [0, 1] so they're comparable to graph extras.
        # RRF produces tiny absolute values (~0.01), so without normalization the
        # hardcoded 0.3 score on graph neighbours would always outrank real hits.
        if base_chunks:
            max_base = max(sc.score for sc in base_chunks) or 1.0
            for sc in base_chunks:
                sc.score = sc.score / max_base

        G = self.graph
        query_entities = _extract_query_entities(query, G)
        extra_chunks: List[ScoredChunk] = []
        triplets: List[Dict[str, Any]] = []
        paths_found: List[List[str]] = []

        # 1. Neighbor expansion
        neighbor_chunk_ids: Set[str] = set()
        for entity in query_entities:
            if entity not in G:
                continue
            for nbr in G.neighbors(entity):
                edge_data = G[entity][nbr]
                if edge_data.get("weight", 0) >= config.GRAPH_MIN_EDGE_WEIGHT_FOR_EXPANSION:
                    for cid in G.nodes[nbr].get("chunk_ids", []):
                        neighbor_chunk_ids.add(cid)
                    triplets.append({
                        "node1": entity,
                        "edge": edge_data.get("edges", ["related"])[0] if edge_data.get("edges") else "related",
                        "node2": nbr,
                        "weight": edge_data.get("weight", 0),
                        "sem_type": edge_data.get("sem_type", "general"),
                    })

        # Graph-neighbour chunks score below normalized base top-k by design:
        # they enrich context but should never displace a chunk the retriever
        # actually matched against the query.
        existing_ids = {sc.chunk.chunk_id for sc in base_chunks}
        for cid in neighbor_chunk_ids:
            if cid in existing_ids:
                continue
            chunk = self.chunk_store.by_id(cid)
            if chunk:
                extra_chunks.append(ScoredChunk(chunk=chunk, score=0.5))

        # 2. PageRank boost on base chunks
        for sc in base_chunks:
            best_pr = 0.0
            for n, data in G.nodes(data=True):
                if sc.chunk.chunk_id in data.get("chunk_ids", []):
                    best_pr = max(best_pr, data.get("pagerank", 0.0))
            sc.score = sc.score * (1.0 + best_pr * config.PAGERANK_BOOST)

        # 3. Dijkstra path-finding between entity pairs
        for i, e1 in enumerate(query_entities):
            for e2 in query_entities[i + 1:]:
                if e1 not in G or e2 not in G:
                    continue
                try:
                    inv_weight = lambda u, v, d: 1.0 / (d.get("weight", 1.0) + 1e-9)
                    path = nx.dijkstra_path(G, e1, e2, weight=inv_weight)
                    paths_found.append(path)
                    # Collect chunks along the path
                    for node in path:
                        for cid in G.nodes[node].get("chunk_ids", []):
                            if cid not in existing_ids and cid not in neighbor_chunk_ids:
                                chunk = self.chunk_store.by_id(cid)
                                if chunk:
                                    extra_chunks.append(ScoredChunk(chunk=chunk, score=0.35))
                    # Add path triplets
                    for j in range(len(path) - 1):
                        u, v = path[j], path[j + 1]
                        ed = G[u][v]
                        triplets.append({
                            "node1": u,
                            "edge": ed.get("edges", ["—"])[0] if ed.get("edges") else "—",
                            "node2": v,
                            "weight": ed.get("weight", 0),
                            "sem_type": ed.get("sem_type", "general"),
                        })
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass

        # Merge and re-sort
        all_chunks = base_chunks + extra_chunks
        all_chunks.sort(key=lambda x: x.score, reverse=True)

        # Deduplicate triplets
        seen_triplets: Set[Tuple[str, str, str]] = set()
        unique_triplets = []
        for t in triplets:
            key = (t["node1"], t["edge"], t["node2"])
            if key not in seen_triplets:
                seen_triplets.add(key)
                unique_triplets.append(t)

        return AugmentedResult(
            augmented_chunks=all_chunks[:config.TOP_K_RERANKED + 5],
            graph_triplets=unique_triplets[:20],
            paths_found=paths_found,
        )


def _extract_query_entities(query: str, G: nx.Graph) -> List[str]:
    """Find graph nodes that appear in the query (exact + fuzzy)."""
    q_lower = query.lower()
    matched: List[str] = []
    for node in G.nodes():
        if node.lower() in q_lower:
            matched.append(node)
    return matched[:10]
