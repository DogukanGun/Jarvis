"""Abstract base for language-specific symbol/call/import extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from tree_sitter import Language, Node, Tree


class SymbolInfo:
    __slots__ = ("name", "node_type", "start_line", "end_line", "extra")

    def __init__(self, name: str, node_type: str, start_line: int, end_line: int, **extra: Any):
        self.name = name
        self.node_type = node_type
        self.start_line = start_line
        self.end_line = end_line
        self.extra = extra


class CallInfo:
    __slots__ = ("callee", "line")

    def __init__(self, callee: str, line: int):
        self.callee = callee
        self.line = line


class ImportInfo:
    __slots__ = ("module", "names", "line")

    def __init__(self, module: str, names: List[str], line: int):
        self.module = module
        self.names = names
        self.line = line


class RouteInfo:
    __slots__ = ("method", "path", "handler", "line")

    def __init__(self, method: str, path: str, handler: str, line: int):
        self.method = method
        self.path = path
        self.handler = handler
        self.line = line


class LanguageProvider(ABC):
    @property
    @abstractmethod
    def language_object(self) -> Language:
        """Return the tree-sitter Language object for this language."""
        ...

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Return file extensions handled by this provider, e.g. ['.py']."""
        ...

    def extract_symbols(self, tree: Tree, code: bytes, file_path: str) -> List[SymbolInfo]:
        return []

    def extract_calls(self, tree: Tree, code: bytes, file_path: str) -> List[CallInfo]:
        return []

    def extract_imports(self, tree: Tree, code: bytes, file_path: str) -> List[ImportInfo]:
        return []

    def extract_routes(self, tree: Tree, code: bytes, file_path: str) -> List[RouteInfo]:
        return []

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def node_text(node: Node, code: bytes) -> str:
        return code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def child_text(node: Node, field: str, code: bytes) -> Optional[str]:
        child = node.child_by_field_name(field)
        if child is None:
            return None
        return code[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
