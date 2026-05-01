"""Main orchestrator: repo path → KnowledgeGraph.

Usage:
    graph = await CodeAnalyzer(repo_path, repo_id).analyze()
    graph.save("/tmp/jarvis-repos/myrepo/graph.json")
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from app.core.knowledge_graph import KnowledgeGraph
from app.core.phases.scan import scan_files
from app.core.phases.parse import parse_files
from app.core.phases.cross_file import resolve_references

logger = logging.getLogger(__name__)

# Global in-memory cache: repo_id → KnowledgeGraph
# Avoids re-parsing on repeated tool calls within the same process.
_GRAPH_CACHE: Dict[str, KnowledgeGraph] = {}
_GRAPH_CACHE_PATH: Dict[str, Path] = {}


def get_cached_graph(repo_id: str) -> Optional[KnowledgeGraph]:
    return _GRAPH_CACHE.get(repo_id)


def _cache_path(repo_id: str) -> Path:
    from app.config import config
    p = Path(config.REPO_CACHE_DIR) / repo_id / "graph.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


async def analyze_repo(repo_path: str, repo_id: str) -> KnowledgeGraph:
    """Parse a repository and return a populated KnowledgeGraph.

    Results are cached in-memory and persisted to disk so subsequent calls
    with the same repo_id return immediately without re-parsing.
    """
    # 1. Check in-memory cache
    if repo_id in _GRAPH_CACHE:
        logger.info("Graph cache hit for '%s'", repo_id)
        return _GRAPH_CACHE[repo_id]

    # 2. Check disk cache
    disk = _cache_path(repo_id)
    if disk.exists():
        logger.info("Loading graph from disk cache: %s", disk)
        try:
            graph = KnowledgeGraph.load(disk)
            _GRAPH_CACHE[repo_id] = graph
            return graph
        except Exception as e:
            logger.warning("Failed to load disk cache (%s), re-parsing: %s", disk, e)

    # 3. Full analysis
    t0 = time.monotonic()
    graph = KnowledgeGraph()

    logger.info("Starting analysis for '%s' at %s", repo_id, repo_path)

    # Run CPU-bound phases in a thread to avoid blocking the event loop
    await asyncio.get_event_loop().run_in_executor(None, _run_pipeline, repo_path, graph)

    elapsed = time.monotonic() - t0
    logger.info(
        "Analysis complete for '%s': %d nodes, %d edges in %.1fs",
        repo_id, graph.node_count, graph.edge_count, elapsed,
    )

    # Persist
    try:
        graph.save(disk)
        logger.info("Graph saved to %s", disk)
    except Exception as e:
        logger.warning("Could not save graph to disk: %s", e)

    _GRAPH_CACHE[repo_id] = graph
    return graph


def _run_pipeline(repo_path: str, graph: KnowledgeGraph) -> None:
    """Synchronous pipeline — called in a thread pool."""
    # Phase 1: Scan
    files = scan_files(repo_path)
    if not files:
        logger.warning("No parseable files found in %s", repo_path)
        return

    # Phase 2: Parse
    def _progress(done: int, total: int) -> None:
        if done % 50 == 0 or done == total:
            logger.info("  Parsed %d/%d files...", done, total)

    parse_files(files, repo_path, graph, on_progress=_progress)

    # Phase 3: Cross-file resolution
    resolve_references(graph)
