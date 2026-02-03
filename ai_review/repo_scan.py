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
        for root, dirs, files in os.walk(self.repo_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']]
            
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                if not ReviewConfig.should_exclude(rel_path):
                    repo_files.append(rel_path)
        
        return repo_files

    def get_file_hashes(self, files: List[str]) -> Dict[str, str]:
        """Get git blob hashes for a list of files."""
        # Using git rev-parse to get hashes is efficient
        hashes = {}
        for f in files:
            try:
                # This is a bit slow in a loop, ideal would be a batch command
                h = self.git._run(["rev-parse", f":{f}"])
                hashes[f] = h
            except Exception:
                # If not in git yet (untracked), use a placeholder or skip
                hashes[f] = "untracked"
        return hashes
