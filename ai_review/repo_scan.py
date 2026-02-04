import os
from typing import List, Set, Dict
from ai_review.git_ops import GitOps
from ai_review.config import ReviewConfig

class RepoScanner:
    """Scanner for repository file discovery and classification."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.git = GitOps(repo_path)

    def scan(self) -> List[str]:
        """List all files in the repository that are not excluded."""
        repo_files = []
        try:
            tracked = self.git._run(["ls-files"])
            for line in tracked.splitlines():
                if not line:
                    continue
                if not ReviewConfig.should_exclude(line):
                    repo_files.append(line)
            return repo_files
        except Exception:
            # Fallback to filesystem walk for non-git repos
            for root, dirs, files in os.walk(self.repo_path):
                # Prune ignored directories
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith('.') and d not in ReviewConfig.EXCLUDED_DIR_NAMES
                ]

                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                    if not ReviewConfig.should_exclude(rel_path):
                        repo_files.append(rel_path)

            return repo_files

    def get_file_hashes(self, files: List[str]) -> Dict[str, str]:
        """Get git blob hashes for a list of files."""
        hashes = {f: "untracked" for f in files}
        try:
            output = self.git._run(["ls-files", "-s"])
        except Exception:
            return hashes

        for line in output.splitlines():
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            _, file_hash, _, path = parts
            if path in hashes:
                hashes[path] = file_hash

        return hashes
