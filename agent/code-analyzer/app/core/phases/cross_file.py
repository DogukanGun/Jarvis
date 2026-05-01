"""Phase 3: resolve cross-file call and import edges.

After Phase 2 every symbol is a node. This phase walks through the raw
call/import data stored on file nodes and wires up CALLS/IMPORTS edges.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from app.core.knowledge_graph import EdgeType, KnowledgeGraph, NodeType

logger = logging.getLogger(__name__)


def resolve_references(graph: KnowledgeGraph) -> None:
    """Add CALLS and IMPORTS edges across the whole graph."""
    # Build name → node_id index for fast lookup
    name_index: Dict[str, List[str]] = {}
    for node_id, data in graph._g.nodes(data=True):
        name = data.get("name", "")
        if name:
            name_index.setdefault(name, []).append(node_id)

    call_edges = 0
    import_edges = 0

    for file_node_id, file_data in list(graph._g.nodes(data=True)):
        if file_data.get("type") != NodeType.FILE.value:
            continue

        # ── CALLS ──────────────────────────────────────────────────────────
        # For each function/method in this file, find callee nodes by name
        raw_calls: List[Tuple[str, int]] = file_data.get("_raw_calls", [])
        if raw_calls:
            # Collect all symbol nodes defined in this file
            file_symbols = [
                nid for nid, d in graph._g.nodes(data=True)
                if d.get("file_path") == file_data.get("file_path")
                and d.get("type") in (NodeType.FUNCTION.value, NodeType.METHOD.value)
            ]
            # Use the file node as the caller if no specific function found
            caller = file_symbols[0] if len(file_symbols) == 1 else file_node_id

            for callee_name, line in raw_calls:
                if callee_name in name_index:
                    for target_id in name_index[callee_name]:
                        if target_id != caller:
                            graph.add_edge(caller, target_id, EdgeType.CALLS, line=line)
                            call_edges += 1

        # ── IMPORTS ────────────────────────────────────────────────────────
        raw_imports: List[Tuple[str, List[str], int]] = file_data.get("_raw_imports", [])
        for module_name, names, line in raw_imports:
            # Try to match module to a File node
            candidates = [
                nid for nid, d in graph._g.nodes(data=True)
                if d.get("type") == NodeType.FILE.value
                and (
                    _module_matches_path(module_name, d.get("file_path", ""))
                )
            ]
            for target_id in candidates:
                graph.add_edge(file_node_id, target_id, EdgeType.IMPORTS, line=line)
                import_edges += 1

    # ── EXTENDS (class inheritance) ────────────────────────────────────────
    extends_edges = 0
    for node_id, data in graph._g.nodes(data=True):
        if data.get("type") == NodeType.CLASS.value:
            for base_name in data.get("bases", []):
                if base_name in name_index:
                    for target_id in name_index[base_name]:
                        graph.add_edge(node_id, target_id, EdgeType.EXTENDS)
                        extends_edges += 1

    # Clean up temporary raw data
    for _, data in graph._g.nodes(data=True):
        data.pop("_raw_calls", None)
        data.pop("_raw_imports", None)

    logger.info(
        "Cross-file resolution: %d CALLS, %d IMPORTS, %d EXTENDS edges",
        call_edges, import_edges, extends_edges,
    )


def _module_matches_path(module: str, file_path: str) -> bool:
    """Heuristic: does an import module string refer to a given file path?"""
    # Normalize both to forward slashes
    fp = file_path.replace("\\", "/")
    mod = module.replace(".", "/").replace("\\", "/").lstrip("./")

    # Strip common source prefixes
    for prefix in ("src/", "lib/", "app/", "pkg/"):
        if fp.startswith(prefix):
            fp_stripped = fp[len(prefix):]
        else:
            fp_stripped = fp

    # Remove extension from file path for comparison
    fp_no_ext = fp.rsplit(".", 1)[0]
    fp_stripped_no_ext = fp_stripped.rsplit(".", 1)[0]

    return (
        fp_no_ext.endswith(mod)
        or fp_stripped_no_ext.endswith(mod)
        or fp_no_ext == mod
        or fp_stripped_no_ext == mod
    )
