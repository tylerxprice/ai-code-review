from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re

from ai_review.config import ReviewConfig

@dataclass
class DiffHunk:
    header: str
    old_start: Optional[int] = None
    new_start: Optional[int] = None
    lines: List[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0

@dataclass
class DiffFile:
    path: str
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    status: str = "M"
    hunks: List[DiffHunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    is_binary: bool = False
    rename_from: Optional[str] = None
    rename_to: Optional[str] = None

class ChangeCollector:
    """Collects and structures changes from git diffs."""

    def __init__(
        self,
        diff_text: str,
        file_statuses: Optional[Dict[str, Dict[str, Any]]] = None,
        numstat: Optional[Dict[str, Dict[str, Any]]] = None,
        max_diff_lines: Optional[int] = None,
        annotate_line_numbers: bool = True,
    ):
        self.diff_text = diff_text
        self.file_statuses = file_statuses or {}
        self.numstat = numstat or {}
        self.max_diff_lines = max_diff_lines or ReviewConfig.MAX_DIFF_LINES
        self.annotate_line_numbers = annotate_line_numbers
        self._files: List[DiffFile] = []
        self._annotated_diff: Optional[str] = None
        self._truncated_lines: int = 0

    def parse_diff(self) -> List[DiffFile]:
        """Parse unified diff into structured file/hunk objects."""
        if self._files:
            return self._files

        current: Optional[DiffFile] = None
        current_hunk: Optional[DiffHunk] = None

        for line in self.diff_text.splitlines():
            if line.startswith("diff --git "):
                if current:
                    self._files.append(current)
                current_hunk = None
                match = re.match(r"diff --git a/(.+) b/(.+)", line)
                if match:
                    old_path, new_path = match.group(1), match.group(2)
                    current = DiffFile(path=new_path, old_path=old_path, new_path=new_path)
                else:
                    current = DiffFile(path="unknown")
                continue

            if not current:
                continue

            if line.startswith("new file mode"):
                current.status = "A"
            elif line.startswith("deleted file mode"):
                current.status = "D"
                current.path = current.old_path or current.path
            elif line.startswith("rename from "):
                current.status = "R"
                current.rename_from = line.replace("rename from ", "").strip()
            elif line.startswith("rename to "):
                current.rename_to = line.replace("rename to ", "").strip()
                if current.rename_to:
                    current.path = current.rename_to
            elif line.startswith("Binary files "):
                current.is_binary = True
            elif line.startswith("@@ "):
                old_start, new_start = self._parse_hunk_header(line)
                current_hunk = DiffHunk(header=line, old_start=old_start, new_start=new_start)
                current.hunks.append(current_hunk)
            elif line.startswith("+") and not line.startswith("+++"):
                current.additions += 1
                if current_hunk:
                    current_hunk.additions += 1
                    current_hunk.lines.append(line)
            elif line.startswith("-") and not line.startswith("---"):
                current.deletions += 1
                if current_hunk:
                    current_hunk.deletions += 1
                    current_hunk.lines.append(line)
            else:
                if current_hunk:
                    current_hunk.lines.append(line)

        if current:
            self._files.append(current)

        self._apply_statuses()
        self._apply_numstat()
        self._add_missing_from_statuses()
        return self._files

    def _apply_statuses(self):
        if not self.file_statuses:
            return
        for diff_file in self._files:
            status = self.file_statuses.get(diff_file.path)
            if not status:
                continue
            diff_file.status = status.get("status", diff_file.status)
            diff_file.rename_from = status.get("old_path", diff_file.rename_from)
            diff_file.rename_to = status.get("new_path", diff_file.rename_to)

    def _apply_numstat(self):
        if not self.numstat:
            return
        for diff_file in self._files:
            stats = self.numstat.get(diff_file.path)
            if not stats:
                continue
            diff_file.additions = stats.get("additions", diff_file.additions)
            diff_file.deletions = stats.get("deletions", diff_file.deletions)
            diff_file.is_binary = stats.get("is_binary", diff_file.is_binary)

    def _add_missing_from_statuses(self):
        for path, status in self.file_statuses.items():
            if any(df.path == path for df in self._files):
                continue
            diff_file = DiffFile(path=path, status=status.get("status", "M"))
            diff_file.rename_from = status.get("old_path")
            diff_file.rename_to = status.get("new_path")
            stats = self.numstat.get(path)
            if stats:
                diff_file.additions = stats.get("additions", 0)
                diff_file.deletions = stats.get("deletions", 0)
                diff_file.is_binary = stats.get("is_binary", False)
            self._files.append(diff_file)

    def get_markdown_summary(self) -> str:
        """Generate a markdown summary of the changes including diff hunks."""
        files = self.parse_diff()
        summary = self.get_summary()
        if not summary["files_changed"]:
            return "No changes detected."

        md = [
            "## Change Overview",
            f"- **Files changed**: {summary['files_changed']}",
            f"- **Insertions**: {summary['insertions']}",
            f"- **Deletions**: {summary['deletions']}",
        ]

        if self.annotate_line_numbers:
            md.append("- **Line numbers**: additions `(+Lx)`, deletions `(-Lx)`, context `(Lx)`")

        if summary["binary_files"]:
            md.append(f"- **Binary files**: {len(summary['binary_files'])}")
        if self._truncated_lines:
            md.append(f"- **Diff truncated**: {self._truncated_lines} lines omitted")

        md.extend([
            "",
            "## File Summary",
            "",
            "| Status | File | + | - |",
            "| --- | --- | --- | --- |",
        ])

        for f in summary["files"]:
            status = f["status"]
            path = f["path"]
            if f.get("rename_from"):
                path = f"{f['rename_from']} → {path}"
            additions = f["additions"] if f["additions"] is not None else "-"
            deletions = f["deletions"] if f["deletions"] is not None else "-"
            md.append(f"| {status} | `{path}` | {additions} | {deletions} |")

        hunk_rows = self._hunk_rows(files)
        if hunk_rows:
            md.extend([
                "",
                "## Hunk Index",
                "",
                "| File | Hunk Header |",
                "| --- | --- |",
            ])
            md.extend([f"| `{row[0]}` | `{row[1]}` |" for row in hunk_rows])

        md.extend([
            "",
            "## Changes",
            "",
        ])

        diff_block = self._truncate_diff(self.get_annotated_diff())
        md.append("```diff")
        md.append(diff_block)
        md.append("```")

        return "\n".join(md)

    def _truncate_diff(self, diff_text: str) -> str:
        lines = diff_text.splitlines()
        if len(lines) <= self.max_diff_lines:
            return diff_text
        truncated = lines[: self.max_diff_lines]
        self._truncated_lines = len(lines) - self.max_diff_lines
        truncated.append(f"... [diff truncated, {self._truncated_lines} lines omitted]")
        return "\n".join(truncated)

    def _hunk_rows(self, files: List[DiffFile]) -> List[Tuple[str, str]]:
        rows = []
        for diff_file in files:
            for hunk in diff_file.hunks:
                rows.append((diff_file.path, hunk.header))
        return rows

    def get_summary(self) -> Dict[str, Any]:
        files = self.parse_diff()
        total_additions = 0
        total_deletions = 0
        file_rows = []
        binary_files = []

        for diff_file in files:
            additions = diff_file.additions
            deletions = diff_file.deletions
            if diff_file.is_binary:
                additions = None
                deletions = None
                binary_files.append(diff_file.path)
            else:
                total_additions += diff_file.additions
                total_deletions += diff_file.deletions

            file_rows.append({
                "path": diff_file.path,
                "status": diff_file.status,
                "additions": additions,
                "deletions": deletions,
                "is_binary": diff_file.is_binary,
                "rename_from": diff_file.rename_from,
                "rename_to": diff_file.rename_to,
            })

        return {
            "files_changed": len(files),
            "insertions": total_additions,
            "deletions": total_deletions,
            "files": sorted(file_rows, key=lambda row: row["path"]),
            "binary_files": binary_files,
        }

    def get_annotated_diff(self) -> str:
        if self._annotated_diff is not None:
            return self._annotated_diff
        if not self.annotate_line_numbers or not self.diff_text:
            self._annotated_diff = self.diff_text
            return self._annotated_diff

        lines = []
        old_line = None
        new_line = None
        for line in self.diff_text.splitlines():
            if line.startswith("@@ "):
                old_line, new_line = self._parse_hunk_header(line)
                lines.append(line)
                continue
            if line.startswith("diff --git ") or line.startswith("index "):
                lines.append(line)
                continue
            if line.startswith("---") or line.startswith("+++"):
                lines.append(line)
                continue

            if line.startswith("+") and not line.startswith("+++"):
                if new_line is None:
                    lines.append(line)
                else:
                    lines.append(f"{line}  (+L{new_line})")
                    new_line += 1
                continue
            if line.startswith("-") and not line.startswith("---"):
                if old_line is None:
                    lines.append(line)
                else:
                    lines.append(f"{line}  (-L{old_line})")
                    old_line += 1
                continue
            if line.startswith(" "):
                if old_line is None or new_line is None:
                    lines.append(line)
                else:
                    lines.append(f"{line}  (L{new_line})")
                    old_line += 1
                    new_line += 1
                continue

            lines.append(line)

        self._annotated_diff = "\n".join(lines)
        return self._annotated_diff

    def _parse_hunk_header(self, header: str) -> Tuple[Optional[int], Optional[int]]:
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
        if not match:
            return None, None
        old_start = int(match.group(1))
        new_start = int(match.group(3))
        return old_start, new_start
