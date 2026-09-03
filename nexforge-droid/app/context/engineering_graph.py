"""Multi-relational Engineering Graph & Code Intelligence Engine (Phase 6)."""

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.context.ast_parser import PythonASTParser
from app.context.base import EdgeType, EngineeringGraphEdge, EngineeringGraphNode, NodeType
from app.context.scanner import RepositoryScanner


class EngineeringGraph:
    """Multi-relational code graph storing symbols, containment, calls, imports, and tests."""

    def __init__(self) -> None:
        self.nodes: Dict[str, EngineeringGraphNode] = {}
        self.edges: List[EngineeringGraphEdge] = []
        
        # Indexes for O(1) lookups
        self._name_index: Dict[str, List[str]] = {}       # name -> list of node_ids
        self._file_index: Dict[str, List[str]] = {}       # file_path -> list of node_ids
        self._type_index: Dict[NodeType, List[str]] = {}  # node_type -> list of node_ids
        self._outgoing_edges: Dict[str, List[EngineeringGraphEdge]] = {}  # source_id -> edges
        self._incoming_edges: Dict[str, List[EngineeringGraphEdge]] = {}  # target_id -> edges

    def add_node(self, node: EngineeringGraphNode) -> None:
        """Adds or updates a node in the graph and updates all indices."""
        self.nodes[node.node_id] = node

        # Index by name
        self._name_index.setdefault(node.name.lower(), []).append(node.node_id)

        # Index by file
        self._file_index.setdefault(node.file_path, []).append(node.node_id)

        # Index by type
        self._type_index.setdefault(node.node_type, []).append(node.node_id)

    def add_edge(self, edge: EngineeringGraphEdge) -> None:
        """Adds a directed relationship edge to the graph."""
        self.edges.append(edge)
        self._outgoing_edges.setdefault(edge.source_id, []).append(edge)
        self._incoming_edges.setdefault(edge.target_id, []).append(edge)

    def build_from_repository(self, repo_root: str) -> None:
        """Scans the repository and parses all Python source files into the unified graph."""
        repo_root = os.path.abspath(repo_root)
        scanner = RepositoryScanner(repo_root)
        summary = scanner.scan()

        ast_parser = PythonASTParser(repo_root=repo_root)

        for file_metric in summary.files:
            if file_metric.language == "Python" and os.path.exists(file_metric.path):
                try:
                    nodes, edges = ast_parser.parse_file(file_metric.path)
                    for n in nodes:
                        self.add_node(n)
                    for e in edges:
                        self.add_edge(e)
                except Exception:
                    continue

        # Post-process: Cross-file edge resolution
        self._resolve_cross_file_relationships()

    def _resolve_cross_file_relationships(self) -> None:
        """Resolves unresolved call and test targets across the symbol graph."""
        resolved_edges: List[EngineeringGraphEdge] = []

        for edge in self.edges:
            if edge.edge_type == EdgeType.CALLS and edge.target_id.startswith("call:"):
                target_name = edge.target_id.split("call:")[-1]
                matches = self.find_symbols_by_name(target_name)
                for match in matches:
                    if match.node_type in (NodeType.FUNCTION, NodeType.METHOD, NodeType.CLASS):
                        resolved_edges.append(
                            EngineeringGraphEdge(
                                source_id=edge.source_id,
                                target_id=match.node_id,
                                edge_type=EdgeType.CALLS,
                                metadata={"target_name": target_name, "resolved": True},
                            )
                        )
            elif edge.edge_type == EdgeType.INHERITS and edge.target_id.startswith("type:"):
                base_name = edge.target_id.split("type:")[-1]
                matches = self.find_symbols_by_name(base_name, node_type=NodeType.CLASS)
                for match in matches:
                    resolved_edges.append(
                        EngineeringGraphEdge(
                            source_id=edge.source_id,
                            target_id=match.node_id,
                            edge_type=EdgeType.INHERITS,
                            metadata={"base_name": base_name, "resolved": True},
                        )
                    )

        for re_edge in resolved_edges:
            self.add_edge(re_edge)

        # Connect tests to their likely target symbols
        test_nodes = self.get_nodes_by_type(NodeType.TEST)
        for t_node in test_nodes:
            # test_read_file -> target read_file
            m = re.match(r"^test_(.+)$", t_node.name)
            if m:
                target_sym_name = m.group(1)
                targets = self.find_symbols_by_name(target_sym_name)
                for tgt in targets:
                    if tgt.node_type in (NodeType.FUNCTION, NodeType.METHOD, NodeType.CLASS):
                        self.add_edge(
                            EngineeringGraphEdge(
                                source_id=t_node.node_id,
                                target_id=tgt.node_id,
                                edge_type=EdgeType.TESTS,
                                metadata={"test_name": t_node.name},
                            )
                        )

    def get_node(self, node_id: str) -> Optional[EngineeringGraphNode]:
        """Retrieves a node by its unique identifier."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[EngineeringGraphNode]:
        """Returns all nodes matching a specific NodeType."""
        node_ids = self._type_index.get(node_type, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def find_symbols_by_name(self, name: str, node_type: Optional[NodeType] = None) -> List[EngineeringGraphNode]:
        """Finds symbols matching an exact name (case-insensitive)."""
        node_ids = self._name_index.get(name.lower(), [])
        res = [self.nodes[nid] for nid in node_ids if nid in self.nodes]
        if node_type is not None:
            res = [r for r in res if r.node_type == node_type]
        return res

    def search_symbols(self, query: str, limit: int = 25) -> List[EngineeringGraphNode]:
        """Searches symbols matching a query string across names, docstrings, and signatures."""
        q_lower = query.lower()
        scored_nodes: List[Tuple[float, EngineeringGraphNode]] = []

        for node in self.nodes.values():
            if node.node_type == NodeType.IMPORT:
                continue

            score = 0.0
            name_lower = node.name.lower()

            if name_lower == q_lower:
                score += 10.0
            elif name_lower.startswith(q_lower):
                score += 5.0
            elif q_lower in name_lower:
                score += 3.0

            if node.signature and q_lower in node.signature.lower():
                score += 2.0

            if node.docstring and q_lower in node.docstring.lower():
                score += 1.5

            if score > 0:
                scored_nodes.append((score, node))

        scored_nodes.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored_nodes[:limit]]

    def get_file_symbols(self, file_path: str) -> List[EngineeringGraphNode]:
        """Returns all symbols located in a specific file."""
        norm_path = file_path.replace("\\", "/")
        node_ids = self._file_index.get(norm_path, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_callers(self, symbol_name_or_id: str) -> List[EngineeringGraphNode]:
        """Finds all functions/methods calling the specified symbol."""
        target_ids: Set[str] = set()
        if symbol_name_or_id in self.nodes:
            target_ids.add(symbol_name_or_id)
        else:
            matches = self.find_symbols_by_name(symbol_name_or_id)
            target_ids.update(m.node_id for m in matches)
            target_ids.add(f"call:{symbol_name_or_id}")

        callers: List[EngineeringGraphNode] = []
        for tid in target_ids:
            in_edges = self._incoming_edges.get(tid, [])
            for edge in in_edges:
                if edge.edge_type == EdgeType.CALLS:
                    if edge.source_id in self.nodes:
                        callers.append(self.nodes[edge.source_id])
        return callers

    def get_callees(self, symbol_name_or_id: str) -> List[Dict[str, Any]]:
        """Finds all outgoing calls from the specified function/method."""
        node_id = symbol_name_or_id
        if node_id not in self.nodes:
            matches = self.find_symbols_by_name(symbol_name_or_id)
            if matches:
                node_id = matches[0].node_id

        out_edges = self._outgoing_edges.get(node_id, [])
        callees: List[Dict[str, Any]] = []
        for edge in out_edges:
            if edge.edge_type == EdgeType.CALLS:
                target_node = self.nodes.get(edge.target_id)
                callees.append({
                    "target_id": edge.target_id,
                    "target_name": target_node.name if target_node else edge.metadata.get("target_name", edge.target_id),
                    "target_node": target_node.to_dict() if target_node else None,
                    "resolved": target_node is not None,
                })
        return callees

    def get_dependencies(self, node_id: str) -> List[Dict[str, Any]]:
        """Returns outgoing dependency edges (imports, calls, containment, inheritance)."""
        edges = self._outgoing_edges.get(node_id, [])
        res: List[Dict[str, Any]] = []
        for e in edges:
            target_node = self.nodes.get(e.target_id)
            res.append({
                "edge_type": e.edge_type.value if isinstance(e.edge_type, EdgeType) else str(e.edge_type),
                "target_id": e.target_id,
                "target_name": target_node.name if target_node else e.metadata.get("target_name", e.target_id),
                "target_type": target_node.node_type.value if target_node else "UNKNOWN",
            })
        return res

    def get_stats(self) -> Dict[str, Any]:
        """Calculates graph metrics and distribution."""
        type_counts: Dict[str, int] = {}
        for n in self.nodes.values():
            t_val = n.node_type.value if isinstance(n.node_type, NodeType) else str(n.node_type)
            type_counts[t_val] = type_counts.get(t_val, 0) + 1

        edge_type_counts: Dict[str, int] = {}
        for e in self.edges:
            e_val = e.edge_type.value if isinstance(e.edge_type, EdgeType) else str(e.edge_type)
            edge_type_counts[e_val] = edge_type_counts.get(e_val, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_distribution": type_counts,
            "edge_distribution": edge_type_counts,
            "total_files": len(self._file_index),
        }

    def export_graph_data(self, max_nodes: int = 150) -> Dict[str, Any]:
        """Exports graph in a normalized format for visualization in the UI."""
        # Prioritize rich symbol nodes (Classes, Functions, Tests, Files)
        priority_order = [NodeType.CLASS, NodeType.FUNCTION, NodeType.TEST, NodeType.FILE, NodeType.METHOD]
        selected_nodes: List[EngineeringGraphNode] = []
        selected_ids: Set[str] = set()

        for p_type in priority_order:
            for n in self.get_nodes_by_type(p_type):
                if len(selected_nodes) >= max_nodes:
                    break
                selected_nodes.append(n)
                selected_ids.add(n.node_id)

        # Include valid edges between selected nodes
        selected_edges: List[Dict[str, Any]] = []
        for e in self.edges:
            if e.source_id in selected_ids and e.target_id in selected_ids:
                selected_edges.append(e.to_dict())

        return {
            "nodes": [n.to_dict() for n in selected_nodes],
            "links": selected_edges,
            "stats": self.get_stats(),
        }
