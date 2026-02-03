import os
from typing import Dict, Any

class PromptComposer:
    """Assembles the final review prompt using templates and context."""

    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir

    def _read_template(self, name: str) -> str:
        with open(os.path.join(self.templates_dir, f"{name}.md"), "r") as f:
            return f.read()

    def compose(self, packet_md: str) -> str:
        """Combine system instructions, rubric, and review packet into a single prompt."""
        system = self._read_template("system")
        rubric = self._read_template("rubric")
        
        prompt = [
            "# SYSTEM INSTRUCTIONS",
            system,
            "",
            "# REVIEW RUBRIC",
            rubric,
            "",
            "# REVIEW PACKET",
            packet_md,
            "",
            "# FINAL INSTRUCTION",
            "Write all findings in a sophisticated, professional-quality markdown, persisted to `CODE_REVIEW.md`."
        ]
        
        return "\n".join(prompt)
