import os
from typing import Optional

class PromptComposer:
    """Assembles the final review prompt using templates and context."""

    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir

    def _read_template(self, name: str) -> str:
        with open(os.path.join(self.templates_dir, f"{name}.md"), "r") as f:
            return f.read()

    def compose(
        self,
        packet_md: str,
        chunk_info: Optional[str] = None,
        final_instruction: Optional[str] = None
    ) -> str:
        """Combine system instructions, rubric, and review packet into a single prompt."""
        system = self._read_template("system")
        rubric = self._read_template("rubric")
        final_text = final_instruction or (
            "Return only the professional-quality review in Markdown."
        )
        
        prompt = [
            "# SYSTEM INSTRUCTIONS",
            system,
            "",
            "# REVIEW RUBRIC",
            rubric,
        ]

        if chunk_info:
            prompt.extend([
                "",
                "# CHUNK CONTEXT",
                chunk_info,
            ])

        prompt.extend([
            "",
            "# REVIEW PACKET",
            packet_md,
            "",
            "# FINAL INSTRUCTION",
            final_text,
        ])
        
        return "\n".join(prompt)
