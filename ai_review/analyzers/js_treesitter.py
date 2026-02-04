from __future__ import annotations

from typing import Optional

from ai_review.analyzers.errors import AnalyzerError
from ai_review.analyzers.types import JSSummary, JSFunctionSummary

try:
    from tree_sitter_languages import get_parser  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    get_parser = None


class TreeSitterJSAnalyzer:
    """Uses tree-sitter to extract structure from JS/TS files."""

    def __init__(self, language: str = "javascript"):
        if get_parser is None:
            raise AnalyzerError("tree_sitter_languages is not installed")
        self.language = language
        self.parser = get_parser(language)

    def analyze_content(self, content: str) -> JSSummary:
        try:
            tree = self.parser.parse(content.encode("utf8"))
        except Exception as exc:
            raise AnalyzerError("Failed to parse JS/TS content") from exc

        summary: JSSummary = {
            "classes": [],
            "functions": [],
            "interfaces": [],
            "types": [],
            "enums": [],
            "imports": [],
            "exports": [],
        }

        root = tree.root_node

        for node in root.children:
            if node.type == "class_declaration":
                name = _child_text(content, node.child_by_field_name("name"))
                if name:
                    summary["classes"].append(name)
            elif node.type == "function_declaration":
                summary["functions"].append(_function_summary(content, node))
            elif node.type in ("lexical_declaration", "variable_declaration"):
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        func = _variable_function(content, declarator)
                        if func:
                            summary["functions"].append(func)
            elif node.type == "interface_declaration":
                name = _child_text(content, node.child_by_field_name("name"))
                if name:
                    summary["interfaces"].append(name)
            elif node.type == "type_alias_declaration":
                name = _child_text(content, node.child_by_field_name("name"))
                if name:
                    summary["types"].append(name)
            elif node.type == "enum_declaration":
                name = _child_text(content, node.child_by_field_name("name"))
                if name:
                    summary["enums"].append(name)

        # Imports/exports are still best-effort via simple scanning.
        summary["imports"] = _scan_imports(content)
        summary["exports"] = _scan_exports(content)
        return summary


def _child_text(content: str, node) -> Optional[str]:
    if node is None:
        return None
    return content[node.start_byte:node.end_byte]


def _function_summary(content: str, node) -> JSFunctionSummary:
    name = _child_text(content, node.child_by_field_name("name")) or "<anonymous>"
    params = node.child_by_field_name("parameters")
    args = _child_text(content, params) or "()"
    return JSFunctionSummary(name=name, args=args.strip("()"))


def _variable_function(content: str, declarator) -> Optional[JSFunctionSummary]:
    name_node = declarator.child_by_field_name("name")
    value_node = declarator.child_by_field_name("value")
    if name_node is None or value_node is None:
        return None
    if value_node.type not in ("arrow_function", "function"):
        return None
    name = _child_text(content, name_node) or "<anonymous>"
    params = value_node.child_by_field_name("parameters")
    args = _child_text(content, params) or "()"
    return JSFunctionSummary(name=name, args=args.strip("()"))


def _scan_imports(content: str) -> list[str]:
    imports = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("import ") or line.startswith("export "):
            if " from " in line:
                parts = line.split(" from ")
                if len(parts) > 1:
                    target = parts[-1].strip().strip(";").strip("\"' ")
                    imports.append(target)
            elif line.startswith("import "):
                target = line.replace("import", "").strip().strip(";").strip("\"' ")
                if target:
                    imports.append(target)
    return imports


def _scan_exports(content: str) -> list[str]:
    exports = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("export "):
            exports.append(line)
    return exports
