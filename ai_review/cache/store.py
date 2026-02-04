import json
import os
from typing import Dict, Any, Optional

class CacheStore:
    """Manages persistent caching for repository analysis results."""

    def __init__(self, repo_path: str, enabled: bool = True, cache_dir: str | None = None):
        self.enabled = enabled
        self.cache_dir = cache_dir or os.path.join(repo_path, ".ai_review", "cache")
        self.cache_file = os.path.join(self.cache_dir, "analysis.json")
        if self.enabled:
            self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self.cache_dir, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if not self.enabled:
            return {}
        if not os.path.exists(self.cache_file):
            return {}
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self, data: Dict[str, Any]):
        """Save cache to disk."""
        if not self.enabled:
            return
        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_entry(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get a specific file's cache entry."""
        cache = self.load()
        return cache.get(file_path)

    def update_entry(self, file_path: str, data: Dict[str, Any]):
        """Update or create a cache entry for a file."""
        cache = self.load()
        cache[file_path] = data
        self.save(cache)
