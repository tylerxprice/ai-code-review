import ast
from typing import Dict, List, Any, Optional

class PythonAnalyzer:
    """Analyzes Python files using AST to extract structural information."""

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """Extract classes, functions, and docstrings from Python source."""
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            return {
                "classes": [],
                "functions": [],
                "docstring": None,
                "imports": [],
                "error": "Failed to parse AST"
            }

        summary = {
            "classes": [],
            "functions": [],
            "docstring": ast.get_docstring(tree),
            "imports": []
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # We only want top-level classes and functions for the structural summary
                # but we want all imports for the dependency graph.
                if node in tree.body:
                    summary["classes"].append(self._analyze_class(node))
            elif isinstance(node, ast.FunctionDef):
                if node in tree.body:
                    summary["functions"].append(self._analyze_function(node))
            elif isinstance(node, ast.Import):
                for name in node.names:
                    summary["imports"].append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    summary["imports"].append(f"{module}.{name.name}")

        return summary

    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        return {
            "name": node.name,
            "docstring": ast.get_docstring(node),
            "methods": [self._analyze_function(n) for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        }

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> Dict[str, Any]:
        args = [arg.arg for arg in node.args.args]
        return {
            "name": node.name,
            "args": args,
            "docstring": ast.get_docstring(node)
        }

    def format_summary(self, summary: Dict[str, Any]) -> str:
        """Format the AST summary into a compressed markdown-like string."""
        lines = []
        if summary.get("docstring"):
            lines.append(f"\"\"\"{summary['docstring']}\"\"\"")
        
        for cls in summary["classes"]:
            lines.append(f"class {cls['name']}:")
            if cls['docstring']:
                lines.append(f"    \"\"\"{cls['docstring']}\"\"\"")
            for method in cls["methods"]:
                lines.append(f"    def {method['name']}({', '.join(method['args'])}): ...")
        
        for func in summary["functions"]:
            lines.append(f"def {func['name']}({', '.join(func['args'])}): ...")
            
        return "\n".join(lines)
