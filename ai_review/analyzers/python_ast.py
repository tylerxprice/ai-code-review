import ast
from typing import Dict, Any

from ai_review.config import ReviewConfig
from ai_review.analyzers.errors import AnalyzerError
from ai_review.analyzers.types import PythonSummary, PythonFunctionSummary, PythonClassSummary


class PythonAnalyzer:
    """Analyzes Python files using AST to extract structural information."""

    def analyze_content(self, content: str) -> PythonSummary:
        """Extract classes, functions, and docstrings from Python source."""
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError) as exc:
            raise AnalyzerError("Failed to parse AST") from exc

        summary: PythonSummary = {
            "classes": [],
            "functions": [],
            "docstring": ast.get_docstring(tree),
            "imports": [],
        }

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                summary["classes"].append(self._analyze_class(node))
            elif isinstance(node, ast.FunctionDef):
                summary["functions"].append(self._analyze_function(node))
            elif isinstance(node, ast.Import):
                for name in node.names:
                    summary["imports"].append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    summary["imports"].append(f"{module}.{name.name}")

        return summary

    def _analyze_class(self, node: ast.ClassDef) -> PythonClassSummary:
        return PythonClassSummary(
            name=node.name,
            docstring=ast.get_docstring(node),
            methods=[
                self._analyze_function(n)
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ],
        )

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> PythonFunctionSummary:
        args = [arg.arg for arg in node.args.args]
        return PythonFunctionSummary(
            name=node.name,
            args=args,
            docstring=ast.get_docstring(node),
        )

    def format_summary(self, summary: Dict[str, Any]) -> str:
        """Format the AST summary into a compressed markdown-like string."""
        lines = []
        imports = summary.get("imports", [])
        if imports:
            display_imports = imports[: ReviewConfig.MAX_IMPORTS_IN_SUMMARY]
            lines.append(f"imports: {', '.join(display_imports)}")
            if len(imports) > len(display_imports):
                lines.append(f"imports: ... (+{len(imports) - len(display_imports)} more)")

        if summary.get("docstring"):
            lines.append(f"\"\"\"{summary['docstring']}\"\"\"")

        for cls in summary["classes"]:
            lines.append(f"class {cls['name']}:")
            if cls["docstring"]:
                lines.append(f"    \"\"\"{cls['docstring']}\"\"\"")
            for method in cls["methods"]:
                lines.append(f"    def {method['name']}({', '.join(method['args'])}): ...")

        for func in summary["functions"]:
            lines.append(f"def {func['name']}({', '.join(func['args'])}): ...")

        return "\n".join(lines)
