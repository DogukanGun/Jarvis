"""TypeScript / JavaScript language provider."""

from __future__ import annotations

from typing import List

from tree_sitter import Language, Tree

from .base import CallInfo, ImportInfo, LanguageProvider, RouteInfo, SymbolInfo

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "all", "use"}


class TypeScriptProvider(LanguageProvider):
    def __init__(self, tsx: bool = False):
        self._tsx = tsx

    @property
    def file_extensions(self) -> List[str]:
        return [".ts", ".tsx"] if self._tsx else [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]

    @property
    def language_object(self) -> Language:
        import tree_sitter_typescript as tsts
        return Language(tsts.language_tsx() if self._tsx else tsts.language_typescript())

    def extract_symbols(self, tree: Tree, code: bytes, file_path: str) -> List[SymbolInfo]:
        results: List[SymbolInfo] = []

        def walk(node):
            if node.type in ("function_declaration", "function_expression"):
                name_node = node.child_by_field_name("name")
                name = self.node_text(name_node, code) if name_node else "<anonymous>"
                results.append(SymbolInfo(
                    name=name,
                    node_type="Function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                ))
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = self.node_text(name_node, code) if name_node else "<anonymous>"
                bases: List[str] = []
                heritage = node.child_by_field_name("class_heritage") or node.child_by_field_name("heritage_clause")
                if heritage:
                    for child in heritage.children:
                        if child.type in ("type_identifier", "identifier"):
                            bases.append(self.node_text(child, code))
                results.append(SymbolInfo(
                    name=name,
                    node_type="Class",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    bases=bases,
                ))
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self.node_text(name_node, code)
                    results.append(SymbolInfo(
                        name=name,
                        node_type="Method",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    ))
            elif node.type == "lexical_declaration":
                # const myFunc = (...) => { ... }
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if name_node and value_node and value_node.type in ("arrow_function", "function_expression"):
                            results.append(SymbolInfo(
                                name=self.node_text(name_node, code),
                                node_type="Function",
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
                    if func.type == "identifier":
                        name = self.node_text(func, code)
                    elif func.type == "member_expression":
                        prop = func.child_by_field_name("property")
                        name = self.node_text(prop, code) if prop else ""
                    else:
                        name = ""
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
            if node.type == "import_statement":
                source = node.child_by_field_name("source")
                module = self.node_text(source, code).strip("'\"") if source else ""
                names: List[str] = []
                clause = node.child_by_field_name("import")
                if clause:
                    for child in clause.children:
                        if child.type == "identifier":
                            names.append(self.node_text(child, code))
                        elif child.type == "named_imports":
                            for spec in child.children:
                                if spec.type == "import_specifier":
                                    name_node = spec.child_by_field_name("name")
                                    if name_node:
                                        names.append(self.node_text(name_node, code))
                if module:
                    results.append(ImportInfo(module=module, names=names, line=node.start_point[0] + 1))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return results

    def extract_routes(self, tree: Tree, code: bytes, file_path: str) -> List[RouteInfo]:
        """Detect Express/Fastify/Hono route registrations: app.get('/path', handler)."""
        results: List[RouteInfo] = []

        def walk(node):
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                if func and func.type == "member_expression":
                    prop = func.child_by_field_name("property")
                    if prop and self.node_text(prop, code).lower() in _HTTP_METHODS:
                        method = self.node_text(prop, code).upper()
                        args = node.child_by_field_name("arguments")
                        if args:
                            children = [c for c in args.children if c.type not in (",", "(", ")")]
                            if children and children[0].type in ("string", "template_string"):
                                path = self.node_text(children[0], code).strip("'\"` ")
                                handler = ""
                                if len(children) > 1:
                                    last = children[-1]
                                    if last.type == "identifier":
                                        handler = self.node_text(last, code)
                                    elif last.type in ("arrow_function", "function_expression"):
                                        handler = "<inline>"
                                results.append(RouteInfo(
                                    method=method,
                                    path=path,
                                    handler=handler,
                                    line=node.start_point[0] + 1,
                                ))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return results


class JavaScriptProvider(TypeScriptProvider):
    def __init__(self):
        super().__init__(tsx=False)

    @property
    def file_extensions(self) -> List[str]:
        return [".js", ".jsx", ".mjs", ".cjs"]

    @property
    def language_object(self) -> Language:
        import tree_sitter_javascript as tsjs
        return Language(tsjs.language())
