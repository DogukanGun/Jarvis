"""Go language provider."""

from __future__ import annotations

from typing import List

from tree_sitter import Language, Tree

from .base import CallInfo, ImportInfo, LanguageProvider, RouteInfo, SymbolInfo

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "handle", "handlefunc"}


class GoProvider(LanguageProvider):
    @property
    def file_extensions(self) -> List[str]:
        return [".go"]

    @property
    def language_object(self) -> Language:
        import tree_sitter_go as tsgo
        return Language(tsgo.language())

    def extract_symbols(self, tree: Tree, code: bytes, file_path: str) -> List[SymbolInfo]:
        results: List[SymbolInfo] = []

        def walk(node):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    results.append(SymbolInfo(
                        name=self.node_text(name_node, code),
                        node_type="Function",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    ))
            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    results.append(SymbolInfo(
                        name=self.node_text(name_node, code),
                        node_type="Method",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    ))
            elif node.type == "type_declaration":
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        type_node = child.child_by_field_name("type")
                        if name_node and type_node and type_node.type == "struct_type":
                            results.append(SymbolInfo(
                                name=self.node_text(name_node, code),
                                node_type="Class",
                                start_line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                            ))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return results

    def extract_calls(self, tree: Tree, code: bytes, file_path: str) -> List[CallInfo]:
        results: List[CallInfo] = []
        seen: set = set()

        def walk(node):
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                if func:
                    name = ""
                    if func.type == "identifier":
                        name = self.node_text(func, code)
                    elif func.type == "selector_expression":
                        field = func.child_by_field_name("field")
                        name = self.node_text(field, code) if field else ""
                    if name:
                        line = node.start_point[0] + 1
                        key = (name, line)
                        if key not in seen:
                            seen.add(key)
                            results.append(CallInfo(callee=name, line=line))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return results

    def extract_imports(self, tree: Tree, code: bytes, file_path: str) -> List[ImportInfo]:
        results: List[ImportInfo] = []

        def walk(node):
            if node.type == "import_declaration":
                for child in node.children:
                    if child.type == "import_spec_list":
                        for spec in child.children:
                            if spec.type == "import_spec":
                                path_node = spec.child_by_field_name("path")
                                if path_node:
                                    module = self.node_text(path_node, code).strip('"')
                                    results.append(ImportInfo(module=module, names=[], line=spec.start_point[0] + 1))
                    elif child.type == "import_spec":
                        path_node = child.child_by_field_name("path")
                        if path_node:
                            module = self.node_text(path_node, code).strip('"')
                            results.append(ImportInfo(module=module, names=[], line=child.start_point[0] + 1))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return results

    def extract_routes(self, tree: Tree, code: bytes, file_path: str) -> List[RouteInfo]:
        """Detect net/http HandleFunc and common router patterns."""
        results: List[RouteInfo] = []

        def walk(node):
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                if func and func.type == "selector_expression":
                    field = func.child_by_field_name("field")
                    if field and self.node_text(field, code).lower() in _HTTP_METHODS:
                        args = node.child_by_field_name("arguments")
                        if args:
                            children = [c for c in args.children if c.type not in (",", "(", ")")]
                            if children and children[0].type == "interpreted_string_literal":
                                path = self.node_text(children[0], code).strip('"')
                                handler = ""
                                if len(children) > 1:
                                    last = children[-1]
                                    handler = self.node_text(last, code)
                                results.append(RouteInfo(
                                    method=self.node_text(field, code).upper(),
                                    path=path,
                                    handler=handler,
                                    line=node.start_point[0] + 1,
                                ))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return results
