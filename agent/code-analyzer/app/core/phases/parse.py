"""Phase 2: parse each source file and add symbols/calls/imports to the graph."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from tree_sitter import Parser

from app.core.knowledge_graph import EdgeType, KnowledgeGraph, NodeType
from app.core.languages.base import LanguageProvider
from app.core.languages.registry import get_provider

logger = logging.getLogger(__name__)


def _make_node_id(file_path: str, name: str, node_type: str) -> str:
    rel = file_path.replace("\\", "/")
    return f"{node_type}:{rel}:{name}"


def parse_files(
    files: list[Path],
    repo_path: str,
    graph: KnowledgeGraph,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Parse all files and populate graph nodes (symbols, files).

    Edges between files are added in the cross_file phase.
    """
    root = Path(repo_path).resolve()
    total = len(files)

    # Parser instances are created per-language and reused
    parsers: dict[str, Parser] = {}

    for i, file_path in enumerate(files):
        provider = get_provider(file_path)
        if provider is None:
            continue

        # Add File node
        rel_path = str(file_path.relative_to(root)).replace("\\", "/")
        file_node_id = f"File:{rel_path}"
        if not graph.has_node(file_node_id):
            graph.add_node(file_node_id, NodeType.FILE, name=rel_path, file_path=rel_path)

        # Parse
        lang = provider.language_object
        lang_key = lang.__class__.__name__
        if lang_key not in parsers:
            parsers[lang_key] = Parser(lang)
        parser = parsers[lang_key]

        try:
            code = file_path.read_bytes()
        except OSError:
            continue

        try:
            tree = parser.parse(code)
        except Exception as e:
            logger.debug("Parse error %s: %s", rel_path, e)
            continue

        # Symbols → nodes
        for sym in provider.extract_symbols(tree, code, rel_path):
            node_id = _make_node_id(rel_path, sym.name, sym.node_type)
            nt = NodeType.FUNCTION if sym.node_type == "Function" else (
                NodeType.CLASS if sym.node_type == "Class" else NodeType.METHOD
            )
            graph.add_node(
                node_id, nt,
                name=sym.name,
                file_path=rel_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                **sym.extra,
            )
            # CONTAINS edge: File → Symbol
            graph.add_edge(file_node_id, node_id, EdgeType.CONTAINS)

        # Routes → nodes
        for route in provider.extract_routes(tree, code, rel_path):
            route_id = f"Route:{rel_path}:{route.method}:{route.path}"
            graph.add_node(
                route_id, NodeType.ROUTE,
                name=f"{route.method} {route.path}",
                file_path=rel_path,
                method=route.method,
                path=route.path,
                handler=route.handler,
                start_line=route.line,
            )
            graph.add_edge(file_node_id, route_id, EdgeType.HANDLES_ROUTE)

        # Store raw call/import info as node attributes for cross-file resolution
        raw_calls = [(c.callee, c.line) for c in provider.extract_calls(tree, code, rel_path)]
        raw_imports = [(im.module, im.names, im.line) for im in provider.extract_imports(tree, code, rel_path)]
        # Attach to file node for cross-file phase
        graph._g.nodes[file_node_id]["_raw_calls"] = raw_calls
        graph._g.nodes[file_node_id]["_raw_imports"] = raw_imports

        if on_progress:
            on_progress(i + 1, total)

    logger.info("Parsed %d files, graph has %d nodes", total, graph.node_count)
