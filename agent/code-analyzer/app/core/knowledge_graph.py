"""In-memory knowledge graph built from source code.

Nodes: File, Function, Class, Method, Route
Edges: CALLS, IMPORTS, EXTENDS, CONTAINS, HAS_METHOD, HANDLES_ROUTE

Backed by networkx MultiDiGraph. Serializes to/from JSON for caching.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import networkx as nx


class NodeType(str, Enum):
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    METHOD = "Method"
    ROUTE = "Route"


class EdgeType(str, Enum):
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    EXTENDS = "EXTENDS"
    CONTAINS = "CONTAINS"
    HAS_METHOD = "HAS_METHOD"
    HANDLES_ROUTE = "HANDLES_ROUTE"


class KnowledgeGraph:
    def __init__(self) -> None:
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()

    # ── Mutations ──────────────────────────────────────────────────────────

    def add_node(self, node_id: str, node_type: NodeType, **props: Any) -> None:
        self._g.add_node(node_id, type=node_type.value, **props)

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: EdgeType,
        confidence: float = 1.0,
        **props: Any,
    ) -> None:
        if from_id not in self._g or to_id not in self._g:
            return
        self._g.add_edge(from_id, to_id, type=edge_type.value, confidence=confidence, **props)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._g

    # ── Stats ──────────────────────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    # ── Queries ────────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Text search over node names and file paths."""
        q = query.lower()
        results = []
        for node_id, data in self._g.nodes(data=True):
            name = str(data.get("name", "")).lower()
            path = str(data.get("file_path", "")).lower()
            if q in name or q in path or q in node_id.lower():
                results.append({"id": node_id, **data})
        results.sort(key=lambda n: (0 if query.lower() in str(n.get("name", "")).lower() else 1))
        return results[:limit]

    def get_context(self, symbol: str) -> Dict[str, Any]:
        """360° view of a symbol: its definition, callers, callees, and containing file."""
        matches = [
            (nid, data)
            for nid, data in self._g.nodes(data=True)
            if str(data.get("name", "")).lower() == symbol.lower()
            or nid.lower().endswith(f":{symbol.lower()}")
        ]
        if not matches:
            return {"error": f"Symbol '{symbol}' not found in the knowledge graph."}

        node_id, node_data = matches[0]

        callers = [
            {"id": src, "name": self._g.nodes[src].get("name", src), "file": self._g.nodes[src].get("file_path", "")}
            for src, _, d in self._g.in_edges(node_id, data=True)
            if d.get("type") == EdgeType.CALLS.value
        ]
        callees = [
            {"id": tgt, "name": self._g.nodes[tgt].get("name", tgt), "file": self._g.nodes[tgt].get("file_path", "")}
            for _, tgt, d in self._g.out_edges(node_id, data=True)
            if d.get("type") == EdgeType.CALLS.value
        ]
        imports = [
            {"id": tgt, "name": self._g.nodes[tgt].get("name", tgt)}
            for _, tgt, d in self._g.out_edges(node_id, data=True)
            if d.get("type") == EdgeType.IMPORTS.value
        ]

        return {
            "symbol": node_id,
            "type": node_data.get("type"),
            "name": node_data.get("name", symbol),
            "file_path": node_data.get("file_path", ""),
            "start_line": node_data.get("start_line"),
            "end_line": node_data.get("end_line"),
            "callers": callers,
            "callees": callees,
            "imports": imports,
        }

    def get_impact(self, symbol: str, direction: str = "upstream", max_depth: int = 4) -> Dict[str, Any]:
        """Blast radius: upstream = who calls this; downstream = what this calls."""
        matches = [
            nid for nid, data in self._g.nodes(data=True)
            if str(data.get("name", "")).lower() == symbol.lower()
            or nid.lower().endswith(f":{symbol.lower()}")
        ]
        if not matches:
            return {"error": f"Symbol '{symbol}' not found."}

        node_id = matches[0]
        affected: List[Dict[str, Any]] = []

        if direction == "upstream":
            # BFS over reversed graph (who calls this symbol?)
            view = self._g.reverse(copy=False)
        else:
            view = self._g

        visited = set()
        queue = [(node_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for neighbor in view.successors(current):
                edge_data = list(view.get_edge_data(current, neighbor).values())[0]
                if edge_data.get("type") == EdgeType.CALLS.value and neighbor not in visited:
                    node = self._g.nodes[neighbor]
                    affected.append({
                        "id": neighbor,
                        "name": node.get("name", neighbor),
                        "type": node.get("type"),
                        "file_path": node.get("file_path", ""),
                        "depth": depth + 1,
                    })
                    queue.append((neighbor, depth + 1))

        return {
            "symbol": node_id,
            "direction": direction,
            "affected_count": len(affected),
            "affected": affected,
        }

    def get_routes(self) -> List[Dict[str, Any]]:
        """Return all HTTP route nodes."""
        return [
            {"id": nid, **data}
            for nid, data in self._g.nodes(data=True)
            if data.get("type") == NodeType.ROUTE.value
        ]

    def get_files(self) -> List[str]:
        return [
            data.get("file_path", nid)
            for nid, data in self._g.nodes(data=True)
            if data.get("type") == NodeType.FILE.value
        ]

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [{"id": nid, **data} for nid, data in self._g.nodes(data=True)],
            "edges": [
                {"from": u, "to": v, **d}
                for u, v, d in self._g.edges(data=True)
            ],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeGraph":
        data = json.loads(Path(path).read_text())
        g = cls()
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            g._g.add_node(node_id, **node)
        for edge in data.get("edges", []):
            u = edge.pop("from")
            v = edge.pop("to")
            g._g.add_edge(u, v, **edge)
        return g
