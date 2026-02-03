from typing import Dict, List, Set, Any
import os

class GraphService:
    """Manages the directed graph of module dependencies."""

    def __init__(self):
        self.adj_list: Dict[str, List[str]] = {}
        self.reverse_adj_list: Dict[str, List[str]] = {}

    def build_from_analysis(self, analysis_data: Dict[str, Any]):
        """Build the graph from repository analysis data."""
        self.adj_list = {}
        self.reverse_adj_list = {}
        
        for file_path, data in analysis_data.items():
            imports = data.get("summary", {}).get("imports", [])
            # Resolve imports to file paths (simplified for now)
            resolved_imports = self._resolve_imports(file_path, imports, analysis_data.keys())
            self.adj_list[file_path] = resolved_imports
            
            for imp in resolved_imports:
                if imp not in self.reverse_adj_list:
                    self.reverse_adj_list[imp] = []
                self.reverse_adj_list[imp].append(file_path)

    def get_impacted_files(self, changed_files: List[str], depth: int = 1) -> Dict[str, List[str]]:
        """Identify downstream files impacted by changes in specified files."""
        impact = {}
        for f in changed_files:
            impacted = self._bfs_reachable(f, depth)
            if impacted:
                impact[f] = impacted
        return impact

    def _resolve_imports(self, current_file: str, imports: List[str], all_files: Set[str]) -> List[str]:
        """Maps import symbols/strings back to repository file paths."""
        resolved = []
        for imp in imports:
            # Heuristic resolution: check if any file path contains the import string
            # e.g., 'auth.service' -> 'auth/service.py'
            imp_path = imp.replace(".", "/")
            for f in all_files:
                if imp_path in f:
                    resolved.append(f)
                    break
        return list(set(resolved))

    def _bfs_reachable(self, start_node: str, max_depth: int) -> List[str]:
        """Find nodes reachable in reverse graph (downstream consumers) up to max_depth."""
        if start_node not in self.reverse_adj_list:
            return []
            
        visited = {start_node}
        queue = [(start_node, 0)]
        reachable = []
        
        while queue:
            node, depth = queue.pop(0)
            if depth >= max_depth:
                continue
                
            for neighbor in self.reverse_adj_list.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    reachable.append(neighbor)
                    queue.append((neighbor, depth + 1))
        
        return reachable
