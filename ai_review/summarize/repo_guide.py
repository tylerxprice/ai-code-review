import os
from typing import Dict, Any, List

from ai_review.repo_scan import RepoScanner
from ai_review.cache.store import CacheStore
from ai_review.analyzers.registry import AnalyzerRegistry
from ai_review.analyzers.errors import AnalyzerError

class RepoAnalyzer:
    """Orchestrates the analysis of the entire repository."""

    def __init__(self, repo_path: str, cache_enabled: bool = True, cache_dir: str | None = None):
        self.repo_path = repo_path
        self.scanner = RepoScanner(repo_path)
        self.cache = CacheStore(repo_path, enabled=cache_enabled, cache_dir=cache_dir)
        self.registry = AnalyzerRegistry()

    def analyze(self, full: bool = False) -> Dict[str, Any]:
        """Perform full or incremental analysis."""
        all_files = self.scanner.scan()
        hashes = self.scanner.get_file_hashes(all_files)
        cache_data = self.cache.load() if not full else {}
        
        new_cache = {}
        for file_path in all_files:
            current_hash = hashes.get(file_path)
            cached_entry = cache_data.get(file_path)
            
            if not full and cached_entry and cached_entry.get("hash") == current_hash:
                new_cache[file_path] = cached_entry
                continue
            
            # Analyze file
            full_path = os.path.join(self.repo_path, file_path)
            analyzer = self.registry.get(file_path)
            
            if analyzer:
                try:
                    with open(full_path, "r") as f:
                        content = f.read()
                    summary = analyzer.analyze_content(content)
                    new_cache[file_path] = {
                        "hash": current_hash,
                        "summary": summary,
                        "type": "structural"
                    }
                except (AnalyzerError, UnicodeDecodeError, SyntaxError, ValueError) as e:
                    new_cache[file_path] = {"hash": current_hash, "error": str(e)}
            else:
                new_cache[file_path] = {"hash": current_hash, "type": "generic"}

        self.cache.save(new_cache)
        return new_cache

    def generate_guide(self, analysis_data: Dict[str, Any]) -> str:
        """Generate a REPO_GUIDE.md string from analysis data."""
        lines = ["# Repository Structural Guide", ""]
        
        for file_path, data in sorted(analysis_data.items()):
            if "summary" in data:
                analyzer = self.registry.get(file_path)
                if analyzer:
                    lines.append(f"## File: `{file_path}`")
                    lines.append("```")
                    lines.append(analyzer.format_summary(data["summary"]))
                    lines.append("```")
                    lines.append("")
        
        return "\n".join(lines)
