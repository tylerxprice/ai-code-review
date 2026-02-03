import os
from ai_review.git_ops import GitOps
from ai_review.summarize.changes import ChangeCollector
from ai_review.analyzers.python_ast import PythonAnalyzer
from ai_review.analyzers.js_heuristic import JSHeuristicAnalyzer
from ai_review.security.redact import Redactor
from ai_review.config import ReviewConfig
from ai_review.cache.store import CacheStore
from ai_review.analyzers.graph import GraphService

class PacketBuilder:
    """Orchestrates different summaries into a comprehensive Review Packet."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.git = GitOps(repo_path)
        self.py_analyzer = PythonAnalyzer()
        self.js_analyzer = JSHeuristicAnalyzer()
        self.redactor = Redactor()
        self.cache = CacheStore(repo_path)
        self.graph = GraphService()

    def build_packet(self, mode: str = 'working', base: str = None, head: str = None) -> str:
        """Generate the full packet markdown."""
        is_working = (mode == 'working')
        diff_text = self.git.get_diff(base=base, head=head, working=is_working)
        changed_files = self.git.list_changed_files(base=base, head=head, working=is_working)
        
        # Redact secrets from diff
        diff_text = self.redactor.redact(diff_text)
        
        collector = ChangeCollector(diff_text)
        changes_md = collector.get_markdown_summary()
        
        # Load analysis for impact and context
        analysis_data = self.cache.load()
        self.graph.build_from_analysis(analysis_data)
        
        # Identify risk areas
        risk_flags = []
        for file_path in changed_files:
            if ReviewConfig.is_risk_path(file_path):
                risk_flags.append(f"- **High Risk**: `{file_path}` is in a sensitive area (CI/CD, Auth, Schema, etc.)")
        
        # Impact Analysis
        impact_md = ["## Downstream Impact Analysis", ""]
        impacted_files = self.graph.get_impacted_files(changed_files, depth=2)
        if impacted_files:
            for source, targets in impacted_files.items():
                impact_md.append(f"- Changes to `{source}` may affect: " + ", ".join([f"`{t}`" for t in targets]))
        else:
            impact_md.append("No direct downstream consumers identified in the repository.")

        risk_md = "## Risk Flags\n" + ("\n".join(risk_flags) if risk_flags else "None identified.")

        # Add architectural context for changed files and their direct dependencies
        context_md = ["## Architectural Context", ""]
        
        # Tiered Selection: Changed files + Direct impacted files
        context_files = set(changed_files)
        for targets in impacted_files.values():
            context_files.update(targets)

        for file_path in sorted(context_files):
            if ReviewConfig.should_exclude(file_path):
                continue
            
            # Use cached summary if available, otherwise analyze
            file_data = analysis_data.get(file_path)
            summary = file_data.get("summary") if file_data else None
            
            analyzer = self._get_analyzer(file_path)
            if not summary and analyzer:
                full_path = os.path.join(self.repo_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, "r") as f:
                        content = f.read()
                    summary = analyzer.analyze_content(content)

            if summary and analyzer:
                context_md.append(f"### Structure: `{file_path}`")
                context_md.append("```")
                context_md.append(analyzer.format_summary(summary))
                context_md.append("```")
                context_md.append("")

        packet = [
            "# Code Review Packet",
            "",
            risk_md,
            "",
            "\n".join(impact_md),
            "",
            changes_md,
            "",
            "\n".join(context_md)
        ]
        
        return "\n".join(packet)

    def _get_analyzer(self, file_path: str):
        if file_path.endswith(".py"):
            return self.py_analyzer
        if file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            return self.js_analyzer
        return None

        packet = [
            "# Code Review Packet",
            "",
            f"- Repository: {os.path.basename(self.repo_path)}",
            f"- Mode: {mode}",
            "",
            changes_md,
            "",
            risk_md,
            "",
            "\n".join(context_md)
        ]
        
        return "\n".join(packet)
