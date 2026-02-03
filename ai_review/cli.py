import click
import os
from rich.console import Console

console = Console()

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
def analyze(path, full, incremental):
    """Analyze repository and build/update structural summaries."""
    from ai_review.summarize.repo_guide import RepoAnalyzer

    console.print(f"[bold blue]Analyzing repository at: {path}[/bold blue]")
    
    analyzer = RepoAnalyzer(path)
    try:
        analysis_data = analyzer.analyze(full=full)
        guide_md = analyzer.generate_guide(analysis_data)
        
        guide_path = os.path.join(path, "REPO_GUIDE.md")
        with open(guide_path, "w") as f:
            f.write(guide_md)
            
        console.print(f"[bold green]Successfully generated structural guide at: {guide_path}[/bold green]")
        console.print(f"Analyzed {len(analysis_data)} files.")
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['working']), help='Review uncommitted changes.')
@click.option('--base', help='Base ref for branch comparison.')
@click.option('--head', help='Head ref for branch comparison.')
def changes(path, mode, base, head):
    """Collect changes and build structured diff summary."""
    from ai_review.git_ops import GitOps
    from ai_review.summarize.changes import ChangeCollector

    git = GitOps(repo_path=path)
    try:
        is_working = (mode == 'working')
        diff_text = git.get_diff(base=base, head=head, working=is_working)
        
        collector = ChangeCollector(diff_text)
        summary_md = collector.get_markdown_summary()
        
        console.print(summary_md)
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['working']), default='working', help='Review uncommitted changes.')
@click.option('--base', help='Base ref for branch comparison.')
@click.option('--head', help='Head ref for branch comparison.')
def packet(path, mode, base, head):
    """Build review packet (structured context without prompt wrapper)."""
    from ai_review.summarize.packet import PacketBuilder
    
    builder = PacketBuilder(path)
    try:
        packet_md = builder.build_packet(mode=mode, base=base, head=head)
        console.print(packet_md)
    except Exception as e:
        console.print("[bold red]Error:[/bold red]", e)

@main.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['working']), default='working', help='Review uncommitted changes.')
@click.option('--base', help='Base ref for branch comparison.')
@click.option('--head', help='Head ref for branch comparison.')
@click.option('--chunked', is_flag=True, help='Split output for large changesets.')
def prompt(path, mode, base, head, chunked):
    """Build complete review prompt ready for piping to an agent."""
    from ai_review.summarize.packet import PacketBuilder
    from ai_review.prompt.composer import PromptComposer
    from ai_review.prompt.chunker import PromptChunker

    builder = PacketBuilder(path)
    
    # Get the templates directory relative to this file
    templates_dir = os.path.join(os.path.dirname(__file__), "prompt", "templates")
    composer = PromptComposer(templates_dir)
    
    try:
        packet_md = builder.build_packet(mode=mode, base=base, head=head)
        full_prompt = composer.compose(packet_md)
        
        if chunked:
            chunker = PromptChunker()
            chunks = chunker.chunk_packet(full_prompt)
            for chunk in chunks:
                console.print(chunk)
                console.print("\n" + "="*40 + "\n")
        else:
            console.print(full_prompt)
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
        console.print(full_prompt)

if __name__ == '__main__':
    main()
# Modifying existing file
