import click
import os
import sys
from pathlib import Path
from rich.console import Console

from ai_review.config import ReviewConfig

console = Console()

def _print_payload(payload: str):
    sys.stdout.write(payload)
    if not payload.endswith("\n"):
        sys.stdout.write("\n")

def _status_map_from_entries(entries):
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


def _numstat_map_from_entries(entries):
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

@click.group()
def main():
    """AI-Powered Code Review Generator.
    
    This tool assembles architectural context and code changes into a 'Review Packet'
    suitable for piping to AI agents like Claude or Gemini.
    """
    pass

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--full', is_flag=True, help='Perform a full repository analysis.')
@click.option('--incremental', is_flag=True, default=True, help='Update existing analysis.')
@click.option('--output', type=click.Path(), help='Write guide to file instead of stdout.')
@click.option('--read-only', is_flag=True, help='Do not write cache or files into the repo.')
def analyze(path, full, incremental, output, read_only):
    """Analyze repository and build/update structural summaries."""
    from ai_review.summarize.repo_guide import RepoAnalyzer

    console.print(f"[bold blue]Analyzing repository at: {path}[/bold blue]")
    
    analyzer = RepoAnalyzer(path, cache_enabled=not read_only)
    try:
        analysis_data = analyzer.analyze(full=full)
        guide_md = analyzer.generate_guide(analysis_data)

        if output:
            with open(output, "w") as f:
                f.write(guide_md)
            console.print(f"[bold green]Structural guide written to: {output}[/bold green]")
        elif read_only:
            _print_payload(guide_md)
        else:
            guide_path = os.path.join(path, "REPO_GUIDE.md")
            with open(guide_path, "w") as f:
                f.write(guide_md)
            console.print(f"[bold green]Successfully generated structural guide at: {guide_path}[/bold green]")

        console.print(f"Analyzed {len(analysis_data)} files.")
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['working']), default='working', help='Review uncommitted changes.')
@click.option('--base', help='Base ref for branch comparison.')
@click.option('--head', help='Head ref for branch comparison.')
@click.option('--max-diff-lines', type=int, default=ReviewConfig.MAX_DIFF_LINES, help='Limit diff size in output.')
@click.option('--line-numbers/--no-line-numbers', default=True, help='Annotate diff lines with line numbers.')
def changes(path, mode, base, head, max_diff_lines, line_numbers):
    """Collect changes and build structured diff summary."""
    from ai_review.git_ops import GitOps
    from ai_review.summarize.changes import ChangeCollector

    git = GitOps(repo_path=path)
    try:
        is_working = (mode == 'working' and not base and not head)
        diff_text = git.get_diff(base=base, head=head, working=is_working)
        
        file_statuses = _status_map_from_entries(
            git.get_name_status_entries(base=base, head=head, working=is_working)
        )
        numstat = _numstat_map_from_entries(
            git.get_numstat_entries(base=base, head=head, working=is_working)
        )
        collector = ChangeCollector(
            diff_text,
            file_statuses=file_statuses,
            numstat=numstat,
            max_diff_lines=max_diff_lines,
            annotate_line_numbers=line_numbers,
        )
        summary_md = collector.get_markdown_summary()

        _print_payload(summary_md)
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['working']), default='working', help='Review uncommitted changes.')
@click.option('--base', help='Base ref for branch comparison.')
@click.option('--head', help='Head ref for branch comparison.')
@click.option('--max-diff-lines', type=int, default=ReviewConfig.MAX_DIFF_LINES, help='Limit diff size in output.')
@click.option('--include-untracked/--no-include-untracked', default=True, help='Include untracked files in diff.')
@click.option('--line-numbers/--no-line-numbers', default=True, help='Annotate diff lines with line numbers.')
@click.option('--read-only', is_flag=True, help='Do not write cache or files into the repo.')
def packet(path, mode, base, head, max_diff_lines, include_untracked, line_numbers, read_only):
    """Build review packet (structured context without prompt wrapper)."""
    from ai_review.summarize.packet import PacketBuilder
    
    builder = PacketBuilder(path, cache_enabled=not read_only)
    try:
        packet_md = builder.build_packet(
            mode=mode,
            base=base,
            head=head,
            max_diff_lines=max_diff_lines,
            include_untracked=include_untracked,
            annotate_line_numbers=line_numbers,
        )
        _print_payload(packet_md)
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['working']), default='working', help='Review uncommitted changes.')
@click.option('--base', help='Base ref for branch comparison.')
@click.option('--head', help='Head ref for branch comparison.')
@click.option('--chunked', is_flag=True, help='Split output for large changesets.')
@click.option('--chunk-separator', type=click.Choice(['divider', 'nul']), default='divider', help='Chunk separator for output.')
@click.option('--output', type=click.Path(), help='Write prompt to file (or directory when chunked).')
@click.option('--max-diff-lines', type=int, default=ReviewConfig.MAX_DIFF_LINES, help='Limit diff size in output.')
@click.option('--include-untracked/--no-include-untracked', default=True, help='Include untracked files in diff.')
@click.option('--line-numbers/--no-line-numbers', default=True, help='Annotate diff lines with line numbers.')
@click.option('--read-only', is_flag=True, help='Do not write cache or files into the repo.')
def prompt(path, mode, base, head, chunked, chunk_separator, output, max_diff_lines, include_untracked, line_numbers, read_only):
    """Build complete review prompt ready for piping to an agent."""
    from ai_review.summarize.packet import PacketBuilder
    from ai_review.prompt.composer import PromptComposer
    from ai_review.prompt.chunker import PromptChunker

    builder = PacketBuilder(path, cache_enabled=not read_only)
    
    # Get the templates directory relative to this file
    templates_dir = os.path.join(os.path.dirname(__file__), "prompt", "templates")
    composer = PromptComposer(templates_dir)
    
    try:
        packet_md = builder.build_packet(
            mode=mode,
            base=base,
            head=head,
            max_diff_lines=max_diff_lines,
            include_untracked=include_untracked,
            annotate_line_numbers=line_numbers,
        )

        if chunked:
            chunker = PromptChunker()
            packet_chunks = chunker.chunk_packet(packet_md)
            total = len(packet_chunks)
            chunk_info_template = "This is chunk {i} of {total}. Provide review for only the visible content."
            final_instruction = (
                "Return a PARTIAL review for this chunk in Markdown. "
                "Do not assume missing context. End with a short 'Needs More Context' "
                "line if additional chunks are required."
            )

            if output:
                output_path = Path(output)
                if output_path.suffix:
                    base_name = output_path.stem
                    output_dir = output_path.parent
                else:
                    base_name = "chunk"
                    output_dir = output_path
                output_dir.mkdir(parents=True, exist_ok=True)
                for i, packet_chunk in enumerate(packet_chunks, 1):
                    chunk_info = chunk_info_template.format(i=i, total=total)
                    full_prompt = composer.compose(
                        packet_chunk,
                        chunk_info=chunk_info,
                        final_instruction=final_instruction,
                    )
                    chunk_path = output_dir / f"{base_name}.{i:02d}.md"
                    with open(chunk_path, "w") as f:
                        f.write(full_prompt)
                console.print(f"[bold green]Chunked prompts written to: {output_dir}[/bold green]")
                return

            for i, packet_chunk in enumerate(packet_chunks, 1):
                chunk_info = chunk_info_template.format(i=i, total=total)
                full_prompt = composer.compose(
                    packet_chunk,
                    chunk_info=chunk_info,
                    final_instruction=final_instruction,
                )
                if chunk_separator == "nul":
                    sys.stdout.write(full_prompt + "\0")
                else:
                    _print_payload(full_prompt)
                    _print_payload("\n" + "="*40 + "\n")
            if chunk_separator == "nul":
                sys.stdout.flush()
        else:
            full_prompt = composer.compose(packet_md)
            if output:
                with open(output, "w") as f:
                    f.write(full_prompt)
                console.print(f"[bold green]Prompt written to: {output}[/bold green]")
            else:
                _print_payload(full_prompt)
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('reviews_dir', type=click.Path(exists=True))
@click.option('--output', type=click.Path(), help='Write to file instead of stdout.')
def synthesize_prompt(reviews_dir, output):
    """Generate a synthesis prompt from multiple review files."""
    
    reviews = []
    for f in os.listdir(reviews_dir):
        if f.endswith(".md"):
            with open(os.path.join(reviews_dir, f), "r") as r:
                reviews.append(f"### Review from {f}\n\n{r.read()}")
    
    if not reviews:
        console.print("[yellow]No markdown reviews found in directory.[/yellow]")
        return

    synthesis_template = """
# Review Synthesis Task

You have been provided with several partial code reviews for a large changeset.
Your task is to synthesize these into a single, cohesive, and professional Final Code Review Report.

## Input Reviews
{reviews}

## Requirements
1.  **Deduplicate**: If multiple reviews point out the same issue, consolidate them.
2.  **Prioritize**: Highlight blocking issues clearly.
3.  **Consistency Check**: Resolve any conflicting feedback between different reviews.
4.  **Final Verdict**: Provide a single final verdict (APPROVE, REQUEST_CHANGES, or COMMENT).
5.  **Professional Tone**: Maintain a mentorship-quality, professional tone throughout.

## Output Format
Follow the standard Review Rubric structure (Summary, Verdict, Blocking Issues, Recommendations, etc.).
"""
    full_prompt = synthesis_template.format(reviews="\n\n---\n\n".join(reviews))
    
    if output:
        with open(output, "w") as f:
            f.write(full_prompt)
        console.print(f"[bold green]Synthesis prompt written to: {output}[/bold green]")
    else:
        _print_payload(full_prompt)

if __name__ == '__main__':
    main()
# Modifying existing file
