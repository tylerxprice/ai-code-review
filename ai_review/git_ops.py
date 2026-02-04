import subprocess
import os
from typing import List, Optional, Dict, Any

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

    def _run_optional(self, cmd: List[str]) -> str:
        try:
            return self._run(cmd)
        except RuntimeError:
            return ""

    def has_head(self) -> bool:
        try:
            self._run(["rev-parse", "--verify", "HEAD"])
            return True
        except RuntimeError:
            return False

    def get_diff(self, base: Optional[str] = None, head: Optional[str] = None, working: bool = False) -> str:
        """Get the diff for the specified range or working tree."""
        if working:
            # Combined staged and unstaged changes relative to HEAD
            if self.has_head():
                return self._run_optional(["diff", "--no-color", "HEAD"]).strip()
            staged = self._run_optional(["diff", "--cached", "--no-color"])
            unstaged = self._run_optional(["diff", "--no-color"])
            return f"{staged}\n{unstaged}".strip()
        
        if base:
            head = head or "HEAD"
            # Use merge-base to find where branches diverged
            merge_base = self._run(["merge-base", base, head])
            return self._run(["diff", "--no-color", f"{merge_base}..{head}"])
        
        return ""

    def get_untracked_files(self) -> List[str]:
        """List untracked files that are not gitignored."""
        files = self._run(["ls-files", "--others", "--exclude-standard"])
        return files.splitlines() if files else []

    def get_merge_base(self, base: str, head: str) -> str:
        """Find the common ancestor of two refs."""
        return self._run(["merge-base", base, head])

    def list_changed_files_with_status(
        self,
        base: Optional[str] = None,
        head: Optional[str] = None,
        working: bool = False
    ) -> List[str]:
        """List files with git change status."""
        if working:
            if self.has_head():
                status = self._run_optional(["diff", "--name-status", "HEAD", "--"])
            else:
                status = self._run_optional(["diff", "--name-status", "--"])
            return status.splitlines() if status else []

        if base:
            head = head or "HEAD"
            merge_base = self.get_merge_base(base, head)
            status = self._run_optional(["diff", "--name-status", f"{merge_base}..{head}", "--"])
            return status.splitlines() if status else []

        return []

    def get_name_status_entries(
        self,
        base: Optional[str] = None,
        head: Optional[str] = None,
        working: bool = False
    ) -> List[Dict[str, Any]]:
        if working:
            if self.has_head():
                output = self._run_optional(["diff", "--name-status", "-z", "HEAD", "--"])
            else:
                output = self._run_optional(["diff", "--name-status", "-z", "--"])
        else:
            if not base:
                return []
            head = head or "HEAD"
            merge_base = self.get_merge_base(base, head)
            output = self._run_optional(["diff", "--name-status", "-z", f"{merge_base}..{head}", "--"])
        return self._parse_name_status_z(output)

    def get_numstat(
        self,
        base: Optional[str] = None,
        head: Optional[str] = None,
        working: bool = False
    ) -> List[str]:
        """Return numstat lines for changes."""
        if working:
            if self.has_head():
                output = self._run_optional(["diff", "--numstat", "HEAD", "--"])
            else:
                output = self._run_optional(["diff", "--numstat", "--"])
            return output.splitlines() if output else []

        if base:
            head = head or "HEAD"
            merge_base = self.get_merge_base(base, head)
            output = self._run_optional(["diff", "--numstat", f"{merge_base}..{head}", "--"])
            return output.splitlines() if output else []

        return []

    def get_numstat_entries(
        self,
        base: Optional[str] = None,
        head: Optional[str] = None,
        working: bool = False
    ) -> List[Dict[str, Any]]:
        if working:
            if self.has_head():
                output = self._run_optional(["diff", "--numstat", "HEAD", "--"])
            else:
                output = self._run_optional(["diff", "--numstat", "--"])
        else:
            if not base:
                return []
            head = head or "HEAD"
            merge_base = self.get_merge_base(base, head)
            output = self._run_optional(["diff", "--numstat", f"{merge_base}..{head}", "--"])
        return self._parse_numstat_lines(output)

    def _parse_name_status_z(self, output: str) -> List[Dict[str, Any]]:
        if not output:
            return []
        parts = output.split("\0")
        entries = []
        i = 0
        while i < len(parts) and parts[i]:
            status = parts[i]
            i += 1
            if status.startswith(("R", "C")):
                if i + 1 >= len(parts):
                    break
                old_path = parts[i]
                new_path = parts[i + 1]
                entries.append({"status": status[0], "old_path": old_path, "path": new_path})
                i += 2
            else:
                if i >= len(parts):
                    break
                path = parts[i]
                entries.append({"status": status, "path": path})
                i += 1
        return entries

    def _parse_numstat_lines(self, output: str) -> List[Dict[str, Any]]:
        if not output:
            return []
        entries = []
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            additions, deletions, path = parts[0], parts[1], parts[2]
            normalized = _normalize_rename_path(path)
            entries.append({
                "additions": additions,
                "deletions": deletions,
                "path": normalized,
                "old_path": None,
            })
        return entries

    def list_changed_files(self, base: Optional[str] = None, head: Optional[str] = None, working: bool = False) -> List[str]:
        """List names of files changed in the specified range."""
        if working:
            if self.has_head():
                combined = self._run_optional(["diff", "--name-only", "HEAD", "--"]).splitlines()
                staged = combined
                unstaged = []
            else:
                staged = self._run_optional(["diff", "--cached", "--name-only", "--"]).splitlines()
                unstaged = self._run_optional(["diff", "--name-only", "--"]).splitlines()
            others = self.get_untracked_files()
            return list(set(staged + unstaged + others))
        
        if base:
            head = head or "HEAD"
            merge_base = self.get_merge_base(base, head)
            return self._run(["diff", "--name-only", f"{merge_base}..{head}", "--"]).splitlines()
        
        return []


def _normalize_rename_path(path: str) -> str:
    if "=>" not in path:
        return path
    if "{" in path and "}" in path:
        prefix, rest = path.split("{", 1)
        middle, suffix = rest.split("}", 1)
        _, new = middle.split("=>", 1)
        return f"{prefix}{new.strip()}{suffix}"
    return path.split("=>", 1)[1].strip()
