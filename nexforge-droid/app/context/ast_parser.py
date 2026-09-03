"""Python AST & Symbol Extraction Engine (Phase 6)."""

import ast
import os
from typing import Any, Dict, List, Optional, Set, Tuple

from app.context.base import EngineeringGraphEdge, EngineeringGraphNode, NodeType, EdgeType


class PythonASTParser:
    """Parses Python source files into rich symbols, hierarchies, call expressions, and inheritance."""

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.repo_root = os.path.abspath(repo_root) if repo_root else ""

    def parse_file(self, file_path: str, code_content: Optional[str] = None) -> Tuple[List[EngineeringGraphNode], List[EngineeringGraphEdge]]:
        """Parses a Python file and returns extracted graph nodes and intra-file edges."""
        nodes: List[EngineeringGraphNode] = []
        edges: List[EngineeringGraphEdge] = []

        rel_path = file_path
        if self.repo_root and os.path.isabs(file_path):
            rel_path = os.path.relpath(file_path, self.repo_root)
        rel_path = rel_path.replace("\\", "/")

        if code_content is None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    code_content = f.read()
            except Exception as e:
                # Return empty on read error
                return nodes, edges

        # Create File Root Node
        file_node_id = f"file:{rel_path}"
        line_count = len(code_content.splitlines())
        file_node = EngineeringGraphNode(
            node_id=file_node_id,
            node_type=NodeType.FILE,
            name=os.path.basename(rel_path),
            file_path=rel_path,
            line_start=1,
            line_end=max(1, line_count),
            metadata={"language": "Python", "lines": line_count},
        )
        nodes.append(file_node)

        try:
            tree = ast.parse(code_content, filename=rel_path)
        except SyntaxError as e:
            file_node.metadata["syntax_error"] = str(e)
            return nodes, edges

        visitor = _SymbolASTVisitor(file_node_id, rel_path, code_content)
        visitor.visit(tree)

        nodes.extend(visitor.extracted_nodes)
        edges.extend(visitor.extracted_edges)

        return nodes, edges


class _SymbolASTVisitor(ast.NodeVisitor):
    """AST visitor traversing Python module bodies and extracting code structures."""

    def __init__(self, file_node_id: str, file_path: str, source_code: str) -> None:
        self.file_node_id = file_node_id
        self.file_path = file_path
        self.source_lines = source_code.splitlines()
        self.extracted_nodes: List[EngineeringGraphNode] = []
        self.extracted_edges: List[EngineeringGraphEdge] = []
        self.current_class_id: Optional[str] = None
        self.current_scope_id: str = file_node_id

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        class_name = node.name
        class_id = f"class:{self.file_path}:{class_name}"
        docstring = ast.get_docstring(node)

        # Detect base classes
        bases: List[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{self._get_attribute_name(base.value)}.{base.attr}")

        # Decorators
        decorators = [self._format_decorator(dec) for dec in node.decorator_list]

        # Is test class?
        is_test = class_name.startswith("Test") or "TestCase" in bases

        class_node = EngineeringGraphNode(
            node_id=class_id,
            node_type=NodeType.TEST if is_test else NodeType.CLASS,
            name=class_name,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            dependencies=bases,
            docstring=docstring,
            decorators=decorators,
            parent_id=self.file_node_id,
            complexity_score=len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
            metadata={"bases": bases, "is_test": is_test},
        )
        self.extracted_nodes.append(class_node)

        # Edge: File contains Class
        self.extracted_edges.append(
            EngineeringGraphEdge(
                source_id=self.file_node_id,
                target_id=class_id,
                edge_type=EdgeType.CONTAINS,
            )
        )

        # Edges: Class inherits Bases
        for base_name in bases:
            self.extracted_edges.append(
                EngineeringGraphEdge(
                    source_id=class_id,
                    target_id=f"type:{base_name}",
                    edge_type=EdgeType.INHERITS,
                    metadata={"base_name": base_name},
                )
            )

        # Visit inner elements with class scope
        prev_class_id = self.current_class_id
        prev_scope_id = self.current_scope_id
        self.current_class_id = class_id
        self.current_scope_id = class_id

        self.generic_visit(node)

        self.current_class_id = prev_class_id
        self.current_scope_id = prev_scope_id

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._process_function(node, is_async=True)

    def _process_function(self, node: Any, is_async: bool) -> None:
        fn_name = node.name
        is_method = self.current_class_id is not None

        if is_method:
            node_id = f"method:{self.file_path}:{self.current_class_id.split(':')[-1]}.{fn_name}"
            node_type = NodeType.METHOD
            parent_id = self.current_class_id
        else:
            node_id = f"function:{self.file_path}:{fn_name}"
            node_type = NodeType.FUNCTION
            parent_id = self.file_node_id

        # Is test function?
        is_test = fn_name.startswith("test_") or fn_name.endswith("_test")
        if is_test:
            node_type = NodeType.TEST

        docstring = ast.get_docstring(node)
        decorators = [self._format_decorator(dec) for dec in node.decorator_list]
        signature = self._build_signature(node, is_async)

        # Extract calls made inside function
        calls_extractor = _CallExtractor()
        for stmt in node.body:
            calls_extractor.visit(stmt)

        fn_node = EngineeringGraphNode(
            node_id=node_id,
            node_type=node_type,
            name=fn_name,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            dependencies=list(calls_extractor.called_names),
            docstring=docstring,
            signature=signature,
            async_function=is_async,
            decorators=decorators,
            parent_id=parent_id,
            complexity_score=self._calculate_cyclomatic(node),
            metadata={"calls": list(calls_extractor.called_names), "is_test": is_test},
        )
        self.extracted_nodes.append(fn_node)

        # Edge: Parent (File or Class) contains Function/Method
        self.extracted_edges.append(
            EngineeringGraphEdge(
                source_id=parent_id or self.file_node_id,
                target_id=node_id,
                edge_type=EdgeType.CONTAINS,
            )
        )

        # Edges: Function calls target
        for called_name in calls_extractor.called_names:
            self.extracted_edges.append(
                EngineeringGraphEdge(
                    source_id=node_id,
                    target_id=f"call:{called_name}",
                    edge_type=EdgeType.CALLS,
                    metadata={"target_name": called_name},
                )
            )

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            import_id = f"import:{self.file_path}:{alias.name}"
            import_node = EngineeringGraphNode(
                node_id=import_id,
                node_type=NodeType.IMPORT,
                name=alias.name if not alias.asname else f"{alias.name} as {alias.asname}",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                metadata={"module": alias.name, "alias": alias.asname},
            )
            self.extracted_nodes.append(import_node)
            self.extracted_edges.append(
                EngineeringGraphEdge(
                    source_id=self.file_node_id,
                    target_id=import_id,
                    edge_type=EdgeType.IMPORTS,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = node.module or "." * node.level
        for alias in node.names:
            full_sym = f"{module}.{alias.name}"
            import_id = f"import:{self.file_path}:{full_sym}"
            import_node = EngineeringGraphNode(
                node_id=import_id,
                node_type=NodeType.IMPORT,
                name=full_sym if not alias.asname else f"{full_sym} as {alias.asname}",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                metadata={"module": module, "symbol": alias.name, "alias": alias.asname},
            )
            self.extracted_nodes.append(import_node)
            self.extracted_edges.append(
                EngineeringGraphEdge(
                    source_id=self.file_node_id,
                    target_id=import_id,
                    edge_type=EdgeType.IMPORTS,
                )
            )

    def _build_signature(self, node: Any, is_async: bool) -> str:
        """Constructs a clean human-readable function signature."""
        params: List[str] = []
        args = node.args

        # Positional arguments & defaults
        defaults_offset = len(args.args) - len(args.defaults)
        for idx, arg in enumerate(args.args):
            param_str = arg.arg
            if arg.annotation:
                param_str += f": {self._format_annotation(arg.annotation)}"
            if idx >= defaults_offset:
                def_idx = idx - defaults_offset
                param_str += f" = {self._format_node(args.defaults[def_idx])}"
            params.append(param_str)

        # *args
        if args.vararg:
            var_str = f"*{args.vararg.arg}"
            if args.vararg.annotation:
                var_str += f": {self._format_annotation(args.vararg.annotation)}"
            params.append(var_str)

        # **kwargs
        if args.kwarg:
            kw_str = f"**{args.kwarg.arg}"
            if args.kwarg.annotation:
                kw_str += f": {self._format_annotation(args.kwarg.annotation)}"
            params.append(kw_str)

        prefix = "async def " if is_async else "def "
        ret_annotation = f" -> {self._format_annotation(node.returns)}" if getattr(node, "returns", None) else ""
        return f"{prefix}{node.name}({', '.join(params)}){ret_annotation}"

    def _format_annotation(self, node: Any) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._format_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._format_annotation(node.value)}[{self._format_annotation(node.slice)}]"
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._format_annotation(e) for e in node.elts)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return f"{self._format_annotation(node.left)} | {self._format_annotation(node.right)}"
        return "Any"

    def _format_node(self, node: Any) -> str:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
            return "..."
        return "..."

    def _format_decorator(self, node: Any) -> str:
        if isinstance(node, ast.Name):
            return f"@{node.id}"
        elif isinstance(node, ast.Attribute):
            return f"@{self._get_attribute_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return f"@{self._format_decorator(node.func).lstrip('@')}(...)"
        return "@decorator"

    def _get_attribute_name(self, node: Any) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return "obj"

    def _calculate_cyclomatic(self, node: Any) -> int:
        """Estimates cyclomatic complexity score from branching AST nodes."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                    ast.comprehension,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity


class _CallExtractor(ast.NodeVisitor):
    """Extracts function and method names called inside a function body."""

    def __init__(self) -> None:
        self.called_names: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Name):
            self.called_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.called_names.add(node.func.attr)
        self.generic_visit(node)
