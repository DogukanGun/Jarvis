"""Python language provider — extracts symbols, calls, imports, and routes."""

from __future__ import annotations

from typing import List

from tree_sitter import Language, Tree

from .base import CallInfo, ImportInfo, LanguageProvider, RouteInfo, SymbolInfo

_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "route", "add_url_rule"}


class PythonProvider(LanguageProvider):
    @property
    def file_extensions(self) -> List[str]:
        return [".py"]

    @property
    def language_object(self) -> Language:
        import tree_sitter_python as tspython
        return Language(tspython.language())

    def extract_symbols(self, tree: Tree, code: bytes, file_path: str) -> List[SymbolInfo]:
        results: List[SymbolInfo] = []
        lang = self.language_object

        # Functions
        fn_query = lang.query("""
            (function_definition
              name: (identifier) @name
            ) @func
        """)
        for node, alias in fn_query.captures(tree.root_node):
            if alias == "func":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self.node_text(name_node, code)
                    results.append(SymbolInfo(
                        name=name,
                        node_type="Function",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    ))

        # Classes
        cls_query = lang.query("""
            (class_definition
              name: (identifier) @name
            ) @cls
        """)
        for node, alias in cls_query.captures(tree.root_node):
            if alias == "cls":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self.node_text(name_node, code)
                    bases: List[str] = []
                    args_node = node.child_by_field_name("superclasses")
                    if args_node:
                        for child in args_node.children:
                            if child.type in ("identifier", "attribute"):
                                bases.append(self.node_text(child, code))
                    results.append(SymbolInfo(
                        name=name,
                        node_type="Class",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        bases=bases,
                    ))

        return results

    def extract_calls(self, tree: Tree, code: bytes, file_path: str) -> List[CallInfo]:
        results: List[CallInfo] = []
        lang = self.language_object

        q = lang.query("""
            (call
              function: [
                (identifier) @callee
                (attribute attribute: (identifier) @callee)
              ]
            ) @call
        """)
        seen: set = set()
        for node, alias in q.captures(tree.root_node):
            if alias == "callee":
                name = self.node_text(node, code)
                line = node.start_point[0] + 1
                key = (name, line)
                if key not in seen:
                    seen.add(key)
                    results.append(CallInfo(callee=name, line=line))

        return results

    def extract_imports(self, tree: Tree, code: bytes, file_path: str) -> List[ImportInfo]:
        results: List[ImportInfo] = []
        lang = self.language_object

        q = lang.query("""
            [
              (import_statement) @import
              (import_from_statement) @from_import
            ]
        """)
        for node, _ in q.captures(tree.root_node):
            if node.type == "import_statement":
                for child in node.children:
                    if child.type in ("dotted_name", "aliased_import"):
                        module = self.node_text(child, code).split(" as ")[0].strip()
                        results.append(ImportInfo(module=module, names=[], line=node.start_point[0] + 1))
            elif node.type == "import_from_statement":
                mod_node = node.child_by_field_name("module_name")
                module = self.node_text(mod_node, code) if mod_node else ""
                names: List[str] = []
                for child in node.children:
                    if child.type in ("dotted_name", "aliased_import") and child != mod_node:
                        names.append(self.node_text(child, code).split(" as ")[0].strip())
                results.append(ImportInfo(module=module, names=names, line=node.start_point[0] + 1))

        return results

    def extract_routes(self, tree: Tree, code: bytes, file_path: str) -> List[RouteInfo]:
        """Detect Flask/FastAPI route decorators."""
        results: List[RouteInfo] = []
        lang = self.language_object

        # Match: @app.get("/path") or @router.post("/path")
        q = lang.query("""
            (decorated_definition
              (decorator
                (call
                  function: (attribute
                    attribute: (identifier) @method)
                  arguments: (argument_list (string) @path)
                )
              )
              definition: (function_definition name: (identifier) @handler)
            ) @route
        """)
        for node, alias in q.captures(tree.root_node):
            pass  # collect captures per match below

        # Simpler approach: walk all decorators manually
        def walk(n):
            if n.type == "decorated_definition":
                _process_decorated(n)
            for child in n.children:
                walk(child)

        def _process_decorated(node):
            handler_name = ""
            method = ""
            path = ""
            for child in node.children:
                if child.type == "function_definition":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        handler_name = self.node_text(name_node, code)
                elif child.type == "decorator":
                    call_node = child.child_count and child.children[-1]
                    if call_node and call_node.type == "call":
                        func = call_node.child_by_field_name("function")
                        if func and func.type == "attribute":
                            attr = func.child_by_field_name("attribute")
                            if attr:
                                m = self.node_text(attr, code).lower()
                                if m in _ROUTE_METHODS:
                                    method = m.upper()
                        args = call_node.child_by_field_name("arguments")
                        if args:
                            for a in args.children:
                                if a.type == "string":
                                    path = self.node_text(a, code).strip("\"'")
                                    break
            if handler_name and method and path:
                results.append(RouteInfo(
                    method=method,
                    path=path,
                    handler=handler_name,
                    line=node.start_point[0] + 1,
                ))

        walk(tree.root_node)
        return results
