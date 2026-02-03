import re
from typing import Dict, List, Any

class JSHeuristicAnalyzer:
    """Uses regex-based heuristics to extract structure from JS/TS files."""

    # Patterns for common JS/TS constructs
    CLASS_PATTERN = re.compile(r'class\s+([A-Za-z0-9_$]+)')
    FUNCTION_PATTERN = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)')
    ARROW_FUNC_PATTERN = re.compile(r'(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>')
    INTERFACE_PATTERN = re.compile(r'interface\s+([A-Za-z0-9_$]+)')
    IMPORT_PATTERN = re.compile(r'(?:import|from)\s+[\'"](.+?)[\'"]')

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """Extract classes, functions, and interfaces using regex."""
        summary = {
            "classes": self.CLASS_PATTERN.findall(content),
            "functions": [],
            "interfaces": self.INTERFACE_PATTERN.findall(content),
            "imports": self.IMPORT_PATTERN.findall(content),
        }

        # Combine standard and arrow functions
        for name, args in self.FUNCTION_PATTERN.findall(content):
            summary["functions"].append({"name": name, "args": args.strip()})
        
        for name, args in self.ARROW_FUNC_PATTERN.findall(content):
            summary["functions"].append({"name": name, "args": args.strip()})

        return summary

    def format_summary(self, summary: Dict[str, Any]) -> str:
        """Format the JS/TS summary into a compressed markdown-like string."""
        lines = []
        
        for interface in summary.get("interfaces", []):
            lines.append(f"interface {interface} {{ ... }}")
        
        for cls in summary.get("classes", []):
            lines.append(f"class {cls} {{ ... }}")
        
        for func in summary.get("functions", []):
            lines.append(f"function {func['name']}({func['args']}): ...")
            
        return "\n".join(lines)
