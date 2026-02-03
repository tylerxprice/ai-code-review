from typing import List, Dict, Any
import re

class ChangeCollector:
    """Collects and structures changes from git diffs."""

    def __init__(self, diff_text: str):
        self.diff_text = diff_text

    def parse_diff(self) -> Dict[str, Any]:
        """Parse unified diff into a structured format."""
        # Simple implementation for Phase 1
        summary = {
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
            "file_details": []
        }
        
        if not self.diff_text:
            return summary

        # Extract basic stats using diff --stat if needed, 
        # but here we parse the unified diff manually for more detail later.
        
        current_file = None
        for line in self.diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
                summary["files_changed"] += 1
                summary["file_details"].append({"path": current_file, "additions": 0, "deletions": 0})
            elif line.startswith("+") and not line.startswith("+++"):
                summary["insertions"] += 1
                if current_file:
                    summary["file_details"][-1]["additions"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                summary["deletions"] += 1
                if current_file:
                    summary["file_details"][-1]["deletions"] += 1

        return summary

    def get_markdown_summary(self) -> str:
        """Generate a markdown summary of the changes including diff hunks."""
        data = self.parse_diff()
        if not data["files_changed"]:
            return "No changes detected."

        md = [
            "### Change Overview",
            f"- **Files changed**: {data['files_changed']}",
            f"- **Insertions**: {data['insertions']}",
            f"- **Deletions**: {data['deletions']}",
            "",
            "## Changes",
            ""
        ]
        
        # In a more advanced version, we would parse hunks. 
        # For now, we'll provide the raw diff per file.
        md.append("```diff")
        md.append(self.diff_text)
        md.append("```")
            
        return "\n".join(md)
