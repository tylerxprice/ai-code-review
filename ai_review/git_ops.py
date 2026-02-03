import subprocess
import os
from typing import List, Optional

class GitOps:
    """Wrapper for Git operations required for code review analysis."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)

    def _run(self, cmd: List[str]) -> str:
        """Execute a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # Handle cases where git commands might fail
            stderr = e.stderr.strip()
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{stderr}")

    def get_diff(self, base: Optional[str] = None, head: Optional[str] = None, working: bool = False) -> str:
        """Get the diff for the specified range or working tree."""
        if working:
            # Combined staged and unstaged changes
            staged = self._run(["diff", "--cached"])
            unstaged = self._run(["diff"])
            return f"{staged}\n{unstaged}".strip()
        
        if base:
            head = head or "HEAD"
            # Use merge-base to find where branches diverged
            merge_base = self._run(["merge-base", base, head])
            return self._run(["diff", f"{merge_base}..{head}"])
        
        return ""

    def get_untracked_files(self) -> List[str]:
        """List untracked files that are not gitignored."""
        files = self._run(["ls-files", "--others", "--exclude-standard"])
        return files.splitlines() if files else []

    def get_merge_base(self, base: str, head: str) -> str:
        """Find the common ancestor of two refs."""
        return self._run(["merge-base", base, head])

    def list_changed_files(self, base: Optional[str] = None, head: Optional[str] = None, working: bool = False) -> List[str]:
        """List names of files changed in the specified range."""
        if working:
            staged = self._run(["diff", "--cached", "--name-only"]).splitlines()
            unstaged = self._run(["diff", "--name-only"]).splitlines()
            others = self.get_untracked_files()
            return list(set(staged + unstaged + others))
        
        if base:
            head = head or "HEAD"
            merge_base = self.get_merge_base(base, head)
            return self._run(["diff", "--name-only", f"{merge_base}..{head}"]).splitlines()
        
        return []
