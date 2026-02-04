import os
import datetime
import re
from typing import Dict, Any, List
from ai_review.git_ops import GitOps
from ai_review.summarize.changes import ChangeCollector
from ai_review.analyzers.registry import AnalyzerRegistry
from ai_review.analyzers.errors import AnalyzerError
from ai_review.security.redact import Redactor
from ai_review.config import ReviewConfig
from ai_review.cache.store import CacheStore
from ai_review.analyzers.graph import GraphService
from ai_review.summarize.repo_guide import RepoAnalyzer

class PacketBuilder:
    """Orchestrates different summaries into a comprehensive Review Packet."""

    def __init__(self, repo_path: str, cache_enabled: bool = True, cache_dir: str | None = None):
        self.repo_path = repo_path
        self.git = GitOps(repo_path)
        self.registry = AnalyzerRegistry()
        self.redactor = Redactor()
        self.cache = CacheStore(repo_path, enabled=cache_enabled, cache_dir=cache_dir)
        self.graph = GraphService()
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir

    def build_packet(
        self,
        mode: str = 'working',
        base: str = None,
        head: str = None,
        max_diff_lines: int | None = None,
        include_untracked: bool = True,
        annotate_line_numbers: bool = True,
    ) -> str:
        """Generate the full packet markdown."""
        is_working = (mode == 'working' and not base and not head)
        diff_text = self.git.get_diff(base=base, head=head, working=is_working)
        changed_files = [
            f for f in self.git.list_changed_files(base=base, head=head, working=is_working)
            if not ReviewConfig.should_exclude(f)
        ]

        file_statuses = self._status_map_from_entries(
            self.git.get_name_status_entries(base=base, head=head, working=is_working)
        )
        numstat = self._numstat_map_from_entries(
            self.git.get_numstat_entries(base=base, head=head, working=is_working)
        )
        file_statuses = {k: v for k, v in file_statuses.items() if not ReviewConfig.should_exclude(k)}
        numstat = {k: v for k, v in numstat.items() if not ReviewConfig.should_exclude(k)}

        if is_working and include_untracked:
            untracked_files = [f for f in self.git.get_untracked_files() if not ReviewConfig.should_exclude(f)]
            for rel_path in untracked_files:
                file_statuses.setdefault(rel_path, {"status": "??"})
            diff_text = self._append_untracked_diff(diff_text, untracked_files)
        else:
            untracked_files = []

        diff_text = self._filter_excluded_diffs(diff_text)
        
        # Redact secrets from diff
        diff_text, redaction_count = self.redactor.redact(diff_text)
        
        collector = ChangeCollector(
            diff_text,
            file_statuses=file_statuses,
            numstat=numstat,
            max_diff_lines=max_diff_lines or ReviewConfig.MAX_DIFF_LINES,
            annotate_line_numbers=annotate_line_numbers,
        )
        changes_md = collector.get_markdown_summary()
        summary = collector.get_summary()
        
        # Load analysis for impact and context
        analysis_data = self.cache.load()
        analysis_source = "cache"
        if not analysis_data:
            try:
                analysis_data = RepoAnalyzer(
                    self.repo_path,
                    cache_enabled=self.cache_enabled,
                    cache_dir=self.cache_dir
                ).analyze(full=False)
                analysis_source = "fresh analysis"
            except Exception:
                analysis_data = {}
                analysis_source = "unavailable"

        if analysis_data:
            self.graph.build_from_analysis(analysis_data)
        
        # Identify risk areas
        risk_flags = []
        for file_path in changed_files:
            if ReviewConfig.is_risk_path(file_path):
                risk_flags.append(f"- **High Risk**: `{file_path}` is in a sensitive area (CI/CD, Auth, Schema, etc.)")

        for pattern, description in ReviewConfig.RISKY_DIFF_PATTERNS:
            if re.search(pattern, diff_text, re.IGNORECASE):
                risk_flags.append(f"- **Pattern Match**: {description}")

        if risk_flags:
            risk_flags = list(dict.fromkeys(risk_flags))
        
        # Impact Analysis
        impact_md = ["## Downstream Impact Analysis", ""]
        impacted_files = {}
        if analysis_data:
            impacted_files = self.graph.get_impacted_files(changed_files, depth=2)
        if impacted_files:
            for source, targets in impacted_files.items():
                limit = ReviewConfig.MAX_IMPACT_PER_FILE
                display_targets = targets[:limit]
                line = f"- Changes to `{source}` may affect: " + ", ".join([f"`{t}`" for t in display_targets])
                if len(targets) > limit:
                    line += f" ... (+{len(targets) - limit} more)"
                impact_md.append(line)
        else:
            impact_md.append("No direct downstream consumers identified in the repository.")

        risk_md = "## Risk Flags\n" + ("\n".join(risk_flags) if risk_flags else "None identified.")

        # Test & documentation signals
        tests_changed = [f for f in changed_files if ReviewConfig.is_test_path(f)]
        docs_changed = [f for f in changed_files if ReviewConfig.is_doc_path(f)]
        code_changed = [
            f for f in changed_files
            if f not in tests_changed and f not in docs_changed and not ReviewConfig.is_binary_path(f)
        ]
        test_md = [
            "## Test Signals",
            f"- **Tests changed**: {len(tests_changed)}",
            f"- **Docs changed**: {len(docs_changed)}",
        ]
        if code_changed and not tests_changed:
            test_md.append("- **Note**: Code changed without test updates. Confirm coverage or add tests.")

        # Add architectural context for changed files and their direct dependencies
        context_md = ["## Architectural Context", ""]
        
        # Tiered Selection: Changed files + Direct impacted files
        context_files = set(changed_files)
        for targets in impacted_files.values():
            context_files.update(targets)

        context_files = [f for f in sorted(context_files) if not ReviewConfig.should_exclude(f)]
        if len(context_files) > ReviewConfig.MAX_CONTEXT_FILES:
            context_files = context_files[: ReviewConfig.MAX_CONTEXT_FILES]
            context_md.append(f"_Context truncated to {ReviewConfig.MAX_CONTEXT_FILES} files._")
            context_md.append("")

        for file_path in context_files:
            if ReviewConfig.should_exclude(file_path):
                continue
            
            # Use cached summary if available, otherwise analyze
            file_data = analysis_data.get(file_path)
            file_summary = file_data.get("summary") if file_data else None
            
            analyzer = self.registry.get(file_path)
            if not file_summary and analyzer:
                full_path = os.path.join(self.repo_path, file_path)
                if os.path.exists(full_path):
                    if not self._is_binary_file(full_path):
                        with open(full_path, "r") as f:
                            content = f.read()
                        try:
                            file_summary = analyzer.analyze_content(content)
                        except AnalyzerError:
                            file_summary = None

            if file_summary and analyzer:
                context_md.append(f"### Structure: `{file_path}`")
                context_md.append("```")
                context_md.append(analyzer.format_summary(file_summary))
                context_md.append("```")
                context_md.append("")

        repo_name = os.path.basename(os.path.abspath(self.repo_path))
        mode_label = "working" if is_working else "compare"
        metadata_md = [
            "## Review Metadata",
            f"- Repository: {repo_name}",
            f"- Mode: {mode_label}",
            f"- Base: {base or 'HEAD'}",
            f"- Head: {head or 'working tree'}",
            f"- Generated: {datetime.datetime.utcnow().isoformat()}Z",
            f"- Files changed: {summary['files_changed']} (+{summary['insertions']} / -{summary['deletions']})",
            f"- Untracked files: {len(untracked_files)}",
            f"- Structural analysis: {analysis_source} ({len(analysis_data)} files)",
            f"- Redactions applied: {redaction_count}",
            f"- Line numbers: {'enabled' if annotate_line_numbers else 'disabled'}",
        ]

        packet = [
            "# Code Review Packet",
            "",
            "\n".join(metadata_md),
            "",
            risk_md,
            "",
            "\n".join(test_md),
            "",
            "\n".join(impact_md),
            "",
            changes_md,
            "",
            "\n".join(context_md)
        ]
        
        return "\n".join(packet)

    def _status_map_from_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        results = {}
        for entry in entries:
            path = entry.get("path")
            if not path:
                continue
            results[path] = {
                "status": entry.get("status", "M"),
                "old_path": entry.get("old_path"),
                "new_path": entry.get("path"),
            }
        return results

    def _numstat_map_from_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        stats = {}
        for entry in entries:
            path = entry.get("path")
            if not path:
                continue
            additions = entry.get("additions", "0")
            deletions = entry.get("deletions", "0")
            is_binary = additions == "-" or deletions == "-"
            stats[path] = {
                "additions": None if is_binary else int(additions),
                "deletions": None if is_binary else int(deletions),
                "is_binary": is_binary,
            }
        return stats

    def _append_untracked_diff(self, diff_text: str, untracked_files: List[str]) -> str:
        blocks = [diff_text] if diff_text else []
        for rel_path in untracked_files:
            if ReviewConfig.should_exclude(rel_path):
                continue
            full_path = os.path.join(self.repo_path, rel_path)
            if not os.path.exists(full_path):
                continue
            if self._is_binary_file(full_path) or ReviewConfig.is_binary_path(rel_path):
                blocks.append(self._binary_diff_block(rel_path))
                continue
            with open(full_path, "r") as f:
                lines = f.read().splitlines()
            truncated = lines[: ReviewConfig.MAX_UNTRACKED_LINES]
            if len(lines) > len(truncated):
                truncated.append(f"... [file truncated, {len(lines) - len(truncated)} lines omitted]")
            block = [
                f"diff --git a/{rel_path} b/{rel_path}",
                "new file mode 100644",
                "--- /dev/null",
                f"+++ b/{rel_path}",
                f"@@ -0,0 +1,{len(truncated)} @@",
            ]
            block.extend([f"+{line}" for line in truncated])
            blocks.append("\n".join(block))
        return "\n\n".join([b for b in blocks if b])

    def _filter_excluded_diffs(self, diff_text: str) -> str:
        if not diff_text:
            return diff_text
        blocks = []
        current = []
        keep = True
        for line in diff_text.splitlines():
            if line.startswith("diff --git "):
                if current and keep:
                    blocks.append("\n".join(current))
                current = [line]
                match = re.match(r"diff --git a/(.+) b/(.+)", line)
                if match:
                    _, new_path = match.group(1), match.group(2)
                    keep = not ReviewConfig.should_exclude(new_path)
                else:
                    keep = True
                continue
            if current is not None:
                current.append(line)
        if current and keep:
            blocks.append("\n".join(current))
        return "\n\n".join(blocks)

    def _binary_diff_block(self, rel_path: str) -> str:
        return "\n".join([
            f"diff --git a/{rel_path} b/{rel_path}",
            "new file mode 100644",
            f"Binary files /dev/null and b/{rel_path} differ",
        ])

    def _is_binary_file(self, path: str) -> bool:
        try:
            if ReviewConfig.is_binary_path(path):
                return True
            with open(path, "rb") as f:
                chunk = f.read(2048)
                return b"\0" in chunk
        except OSError:
            return False
