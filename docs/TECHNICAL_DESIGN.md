# Technical Design Document: AI-Powered Code Review Generator

| **Document Version** | 1.0 |
|---------------------|-----|
| **Status** | Draft |
| **Author** | Josh English |
| **Target Audience** | Engineering Leads, AI Agent Developers |
| **Primary Goal** | Enable AI coding agents to produce world-class code reviews with full architectural context |

---

## 1. Executive Summary

This document describes a Python-based system that enables AI coding agents (Claude Code, Gemini CLI, Codex, etc.) to produce high-quality, insightful code reviews by constructing a **Review Packet**—a structured assembly of repository architecture, change analysis, and impact surface that mirrors what a senior engineer would prepare before reviewing code.

The tool generates a complete review prompt and outputs it to stdout, allowing users to pipe directly to their preferred agent:

```bash
ai_review prompt --base main | claude -p > CODE_REVIEW.md
```

The core insight: most AI-assisted code reviews fail because they operate on diffs in isolation. By providing the agent with comprehensive architectural context compressed to fit within token budgets, we enable reviews that catch architectural violations, identify blast radius, and provide mentorship-quality feedback.

### Key Differentiators

**System Awareness.** The AI understands where changed code fits within the broader architecture, enabling detection of pattern violations and missed reuse opportunities.

**Evidence-Based Review.** The prompt architecture enforces citation of specific files and diff hunks, eliminating hallucinated feedback.

**Token-Optimized Context.** AST-based compression reduces unchanged code to lightweight signatures, preserving budget for the actual changes under review.

**Agent Agnostic.** Pipe to Claude Code, Gemini CLI, Codex, or any compatible agent—no API configuration required.

**Dual-Mode Operation.** Supports both work-in-progress (uncommitted changes) and pull request (branch comparison) workflows.

---

## 2. Design Philosophy

The system operates on three principles that distinguish world-class reviews from superficial feedback.

**Principle 1: Give the Agent What a Senior Engineer Would Assemble.** Before reviewing a PR, experienced engineers don't just read the diff—they understand the affected modules, trace import relationships, identify downstream consumers, and consider the blast radius. This tool assembles that context automatically.

**Principle 2: Compress Context, Not Understanding.** Large codebases exceed context windows. Rather than truncating arbitrarily, we use AST parsing to preserve the semantic skeleton of unchanged files (class hierarchies, function signatures, docstrings) while discarding implementation bodies. The agent retains architectural understanding without consuming tokens on code that hasn't changed.

**Principle 3: Constrain the Model to Prevent Invention.** The prompt architecture explicitly forbids the model from referencing code not present in the packet. Every criticism must cite a file path and line reference. This eliminates the most common failure mode of AI code review: confident feedback about nonexistent issues.

---

## 3. System Architecture

### 3.1 Component Overview

The system comprises four modules orchestrated by a central CLI controller, with output piped to the user's preferred AI agent.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI Controller                              │
│   ai_review analyze | changes | packet | prompt                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│  Repo Analyzer  │    │  Change Collector   │    │  Packet Builder │
│                 │    │                     │    │                 │
│ • File tree     │    │ • git diff parsing  │    │ • Context merge │
│ • AST parsing   │    │ • Symbol detection  │    │ • Token budget  │
│ • Import graph  │    │ • Hunk extraction   │    │ • Risk flagging │
│ • Caching       │    │                     │    │                 │
└────────┬────────┘    └──────────┬──────────┘    └────────┬────────┘
         │                        │                        │
         ▼                        ▼                        ▼
    REPO_GUIDE.md            CHANGES.md             REVIEW_PACKET.md
                                                           │
                                                           ▼
                                               ┌─────────────────────┐
                                               │   Prompt Composer   │
                                               │                     │
                                               │ • System context    │
                                               │ • Review rubric     │
                                               │ • Citation rules    │
                                               └──────────┬──────────┘
                                                          │
                                                          ▼
                                                       stdout
                                                          │
                                          ┌───────────────┼───────────────┐
                                          ▼               ▼               ▼
                                    ┌──────────┐   ┌──────────┐   ┌──────────┐
                                    │  claude  │   │  gemini  │   │  codex   │
                                    │    -p    │   │    -p    │   │   cli    │
                                    └────┬─────┘   └────┬─────┘   └────┬─────┘
                                         │              │              │
                                         └──────────────┼──────────────┘
                                                        ▼
                                                 CODE_REVIEW.md
```

### 3.2 Module Responsibilities

**Repo Analyzer** walks the repository, extracts structure and relationships using language-aware parsing, and produces `REPO_GUIDE.md`—a compressed architectural map suitable for LLM consumption.

**Change Collector** gathers diffs for uncommitted changes or branch comparisons, parses them into structured per-file summaries with symbol-level change detection where possible, and produces `CHANGES.md`.

**Packet Builder** combines the repo guide with the change summary, applies tiered context selection based on token budget, adds risk heuristics and impact analysis, and produces `REVIEW_PACKET.md`.

**Prompt Composer** constructs the complete review prompt with system instructions, review rubric, citation rules, and the review packet. Output goes to stdout for piping to the user's preferred AI agent.

---

## 4. Data Flow

### 4.1 Standard Review Flow

The user invokes one of two review modes:

```bash
# Review uncommitted work, pipe to Claude Code
ai_review prompt --mode working | claude -p

# Review branch against main, pipe to Gemini
ai_review prompt --base main --head feature/new-auth | gemini -p
```

The tool executes the following sequence:

1. **Update Repo Analysis.** Check cache validity against git blob hashes. Re-analyze only changed files. Rebuild import graph if dependencies changed.

2. **Collect Changes.** For working mode, combine staged (`git diff --cached`) and unstaged (`git diff`) changes. For branch mode, compute merge-base and extract divergent commits.

3. **Build Review Packet.** Select relevant sections of repo guide based on affected paths. Apply tiered context compression. Flag risk areas. Merge into single packet.

4. **Compose Prompt.** Insert packet into prompt template with system instructions and rubric.

5. **Output to stdout.** The complete prompt streams to stdout, ready for piping to any compatible agent.

### 4.2 Packet-Only Mode

For debugging or use with external agents, the tool can emit the review packet without calling an LLM:

```bash
ai_review packet --base main --head feature/new-auth --output REVIEW_PACKET.md
```

This is the recommended development workflow: perfect the packet generation before tuning the prompt.

---

## 5. Repository Analysis

### 5.1 Output Structure

`REPO_GUIDE.md` provides a compressed architectural map with the following sections:

**Repository Summary** includes primary languages, detected frameworks, and a directory tree (depth-limited, excluding noise directories).

**Key Entry Points** lists executables, main modules, CLI scripts, and service definitions—the "front doors" of the codebase.

**Module Breakdown** provides per-package summaries including purpose (from docstrings/READMEs), important files, and public API surface.

**Dependency Graph** shows import relationships at the module/package level, with optional file-level adjacency for high-coupling areas.

**Core Abstractions** identifies the top classes, interfaces, and types by fan-in (how many other modules depend on them).

**Hotspots** flags the largest files and highest-coupling modules—areas where changes have elevated risk.

**Testing Layout** describes test directories, frameworks, and conventions detected.

**Build and Deploy** captures CI configs, Dockerfiles, and infrastructure definitions.

### 5.2 Extraction Strategy

The analyzer uses a tiered approach based on language support and available tooling.

**Tier 1: AST Parsing (Python).** Uses the `ast` module to extract imports, class definitions, function signatures, and docstrings. Discards function bodies entirely. A 500-line module compresses to perhaps 30 lines of structural summary.

```python
# Input: 500 lines of implementation
class AuthenticationService:
    """Handles user authentication and session management."""
    
    def __init__(self, db: Database, cache: RedisClient): ...
    def authenticate(self, username: str, password: str) -> Session: ...
    def validate_token(self, token: str) -> Optional[User]: ...
    def revoke_session(self, session_id: str) -> bool: ...

# Output: Structural skeleton only
```

**Tier 2: Heuristic Parsing (JS/TS/Go/Java).** For languages without convenient AST access, uses regex-based extraction of import statements, export declarations, class/function definitions, and type annotations. Less precise but still valuable.

**Tier 3: File Headers (Fallback).** For unsupported languages or binary-adjacent files, includes only the first 10 lines and any detected documentation comments.

### 5.3 Import Graph Construction

The analyzer builds a directed graph of module dependencies:

```python
# Adjacency list representation
{
    "auth/service.py": ["db/client.py", "cache/redis.py", "models/user.py"],
    "api/routes.py": ["auth/service.py", "api/middleware.py"],
    ...
}
```

This graph enables two critical capabilities. First, **impact analysis**: given a set of changed files, identify all downstream consumers. Second, **context selection**: when building the review packet, prioritize summaries for modules that import or are imported by changed files.

### 5.4 Caching Strategy

Analysis results are cached in `.ai_review/cache/` with entries keyed by file path and git blob hash:

```json
{
    "auth/service.py": {
        "blob_hash": "a1b2c3d4",
        "summary": "...",
        "imports": ["db.client", "cache.redis"],
        "exports": ["AuthenticationService"],
        "analyzed_at": "2024-01-15T10:30:00Z"
    }
}
```

Incremental updates re-analyze only files whose blob hash has changed since last run. The import graph is rebuilt if any dependency relationships changed.

---

## 6. Change Collection

### 6.1 Operating Modes

**Working Tree Mode** captures uncommitted changes by combining three sources:

- Staged changes: `git diff --cached`
- Unstaged changes: `git diff`  
- Untracked files: `git ls-files --others --exclude-standard`

For untracked files, the tool includes full contents (bounded by `--max-file-bytes`).

**Branch Comparison Mode** captures the divergence between two refs:

```bash
# Compute the point where branches diverged
merge_base=$(git merge-base main feature/new-auth)

# Get only the changes introduced on the feature branch
git diff ${merge_base}..feature/new-auth
```

This is critical: a naive `git diff main feature/new-auth` includes changes from main that aren't in the feature branch, polluting the review context.

### 6.2 Change Summary Structure

`CHANGES.md` provides structured change information at multiple granularities:

**Overview** includes aggregate statistics (files changed, insertions, deletions), top-level directories affected, and commit list (for branch mode).

**Per-File Detail** for each changed file includes the change type (added/modified/deleted/renamed), size delta, key hunks (bounded by `--max-diff-lines`), and symbol-level changes where detectable.

### 6.3 Symbol-Level Change Detection

For Python files, the collector can identify which functions and classes were modified by parsing the diff for definition patterns:

```
Modified: auth/service.py
  Changed functions: authenticate(), validate_token()
  Changed classes: AuthenticationService (method: __init__)
  Unchanged: revoke_session()
```

This enables the review prompt to reference specific functions rather than just file names, producing more actionable feedback.

### 6.4 Diff Parsing

The collector parses unified diff format into structured hunks:

```python
@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str          # The @@ line
    content: str         # The actual diff lines
    context_before: str  # Lines preceding the hunk
    context_after: str   # Lines following the hunk
```

Hunks are grouped by file and annotated with detected symbol associations.

---

## 7. Review Packet Construction

### 7.1 Tiered Context Strategy

Large repositories and diffs will exceed context limits. The packet builder implements a tiered strategy that preserves the most valuable context:

**Tier 1: The Diff (Highest Priority).** Full diff content for all changed files. This is non-negotiable—the agent cannot review what it cannot see.

**Tier 2: Direct Dependencies.** For files imported by or importing changed files, include either full content (if token budget allows) or AST summaries.

**Tier 3: System Map.** For the rest of the repository, include only the structural skeleton from `REPO_GUIDE.md`.

Token allocation follows this heuristic:

| Tier 1 Size | Tier 2 Treatment | Tier 3 Treatment |
|-------------|------------------|------------------|
| < 30% budget | Full source | Full summaries |
| 30-60% budget | AST summaries | Directory tree only |
| > 60% budget | AST summaries | Omit entirely |

### 7.2 Risk Heuristics

The packet builder flags changes in sensitive areas:

**Security-Critical Paths**: auth/, crypto/, secrets/, permissions/, payment/

**Concurrency-Sensitive**: Files importing threading, multiprocessing, asyncio, or containing lock/mutex patterns

**Data-Critical**: migrations/, schemas/, models with persistence annotations

**Infrastructure**: CI/CD configs, Dockerfiles, Kubernetes manifests, terraform/

Flagged areas receive a risk annotation in the packet that prompts the reviewer to apply extra scrutiny.

### 7.3 Impact Surface Analysis

Using the import graph, the builder identifies downstream consumers of changed code:

```markdown
## Impact Analysis

### Direct Consumers of `auth/service.py`
- `api/routes.py` (imports AuthenticationService)
- `workers/session_cleanup.py` (imports validate_token)

### Transitive Consumers (2 hops)
- `api/middleware.py` (via api/routes.py)
- `tests/integration/test_auth.py` (via auth/service.py)
```

This enables the reviewer to assess blast radius and identify missing test coverage.

### 7.4 Packet Format

The final `REVIEW_PACKET.md` follows this structure:

```markdown
# Code Review Packet

## Metadata
- Repository: josh-english-terminal
- Review Mode: Branch Comparison
- Base: main (abc1234)
- Head: feature/new-auth (def5678)
- Generated: 2024-01-15T10:30:00Z

## Change Summary
[Contents of CHANGES.md, possibly condensed]

## Impact Analysis
[Downstream consumers, blast radius]

## Risk Flags
[Security/concurrency/data/infra warnings]

## Repository Context
[Relevant sections of REPO_GUIDE.md, filtered to affected packages]

## Full File Contents
[For new files and heavily-modified files, bounded]
```

---

## 8. Prompt Architecture

### 8.1 Design Goals

The prompt architecture serves three goals. First, **elicit structured output** that's easy to parse and act upon. Second, **enforce evidence-based feedback** by requiring citations. Third, **prevent hallucination** by explicitly forbidding invention.

### 8.2 System Prompt

```markdown
You are a Principal Software Engineer conducting a code review. Your role is to:

1. Ensure correctness, security, and maintainability
2. Identify architectural violations and missed opportunities
3. Mentor the author toward better practices
4. Protect the codebase from regression

## Critical Rules

**Evidence Requirement**: Every piece of feedback MUST cite specific evidence from the provided packet. Use the format `[File: path/to/file.py:L42-L47]` for line references or quote the relevant diff hunk header (`@@ -12,7 +12,10 @@`).

**No Invention**: You may only reference code that appears in the review packet. If you cannot find evidence for a concern, state "Unable to verify without seeing [specific file/function]" rather than assuming.

**Uncertainty Protocol**: When uncertain about intent or context, ask a clarifying question rather than making assumptions. Frame questions as "Question for author: ..."

**Proportional Response**: Match feedback intensity to issue severity. Blocking issues get detailed explanation. Minor style suggestions get brief mention.
```

### 8.3 Review Rubric

The prompt includes a structured rubric that ensures comprehensive coverage:

```markdown
## Review Rubric

Evaluate the changes against each dimension. Skip dimensions that don't apply.

### Correctness
- Logic errors, off-by-one, null handling
- Edge cases and boundary conditions
- Error handling completeness

### Security
- Input validation and sanitization
- Authentication/authorization gaps
- Secrets handling, injection risks

### Design & Architecture
- Pattern consistency with existing code
- Abstraction appropriateness
- Coupling and cohesion
- SOLID principle adherence

### Performance
- Algorithmic complexity
- Resource usage (memory, connections, handles)
- N+1 queries, unnecessary computation

### Maintainability
- Code clarity and self-documentation
- Test coverage for new/changed behavior
- Error messages and logging
- Documentation updates needed

### API & Contracts
- Backward compatibility
- Interface stability
- Schema/migration safety
```

### 8.4 Output Format

The prompt specifies the expected output structure:

```markdown
## Required Output Format

### Summary
[2-3 sentences: what this change does and why]

### Verdict
[APPROVE | REQUEST_CHANGES | COMMENT]
[One sentence justification]

### Blocking Issues
[Issues that must be addressed before merge. If none, state "None identified."]

### Recommendations  
[Non-blocking suggestions for improvement]

### Questions for Author
[Clarifying questions about intent or context]

### Testing Notes
[Suggested test cases or coverage gaps]
```

---

## 9. Agent Integration (Pipe-Based Architecture)

### 9.1 Design Philosophy

Rather than implementing LLM adapters, this tool generates a complete review prompt and pipes it to the user's preferred AI coding agent. This approach provides several advantages:

**Zero Configuration.** Users have already authenticated and configured their preferred agent (Claude Code, Gemini CLI, Codex). No additional API keys or setup required.

**Agent Capabilities Preserved.** Piping to the full agent means access to tool use, web search, and other capabilities the agent provides—not just raw completion.

**Single Responsibility.** The tool focuses exclusively on what it does best: assembling high-quality context. The agent handles everything else.

**Future-Proof.** New agents and capabilities require no tool updates.

### 9.2 Supported Agents

| Agent | Pipe Syntax | Notes |
|-------|-------------|-------|
| Claude Code | `echo "prompt" \| claude -p` | `-p` for print mode (non-interactive) |
| Gemini CLI | `gemini -p "prompt"` | `-p` for headless agent mode |
| Codex CLI | `echo "prompt" \| codex-cli` | Standard pipe input |

### 9.3 Output Modes

The tool supports two output modes for agent integration:

**Prompt Mode (Default).** Outputs the complete review prompt (system instructions + rubric + packet) ready for piping:

```bash
ai_review prompt --base main --head feature/auth | claude -p
```

**Packet Mode.** Outputs only the review packet (no prompt wrapper) for users who want to customize the prompt or use the context for other purposes:

```bash
ai_review packet --base main --head feature/auth > context.md
```

### 9.4 Shell Integration Examples

**One-liner review with Claude Code:**
```bash
ai_review prompt --mode working | claude -p > CODE_REVIEW.md
```

**Review with Gemini CLI:**
```bash
ai_review prompt --base main --head $(git branch --show-current) | gemini -p
```

**Save packet for inspection, then review:**
```bash
ai_review packet --mode working -o /tmp/packet.md
cat /tmp/packet.md | claude -p
```

**Pipe to clipboard for paste into web UI:**
```bash
ai_review prompt --mode working | pbcopy  # macOS
ai_review prompt --mode working | xclip   # Linux
```

### 9.5 Large Changeset Strategy

For changesets that may exceed agent context limits, the tool provides a chunked output mode:

```bash
ai_review prompt --mode working --chunked
```

This generates multiple prompts—one per file or logical group—that can be run sequentially:

```bash
ai_review prompt --mode working --chunked | while read -r prompt; do
    echo "$prompt" | claude -p >> CODE_REVIEW.md
    echo "---" >> CODE_REVIEW.md
done
```

Alternatively, users can run the synthesis pass manually after per-file reviews:

```bash
# Generate per-file reviews
for file in $(ai_review list-changed --mode working); do
    ai_review prompt --mode working --focus "$file" | claude -p >> reviews/
done

# Synthesize
ai_review synthesize-prompt reviews/ | claude -p > CODE_REVIEW.md
```

---

## 10. CLI Design

### 10.1 Commands

```bash
# Analyze repository and build/update REPO_GUIDE.md
ai_review analyze [--full | --incremental] [--output PATH]

# Collect changes and build CHANGES.md
ai_review changes (--mode working | --base REF --head REF) [--output PATH]

# Build review packet only (context without prompt wrapper)
ai_review packet (...) [--output PATH]

# Build complete review prompt (ready to pipe to agent)
ai_review prompt (...) [--chunked] [--output PATH]

# List changed files (useful for scripting)
ai_review list-changed (--mode working | --base REF --head REF)

# Generate synthesis prompt from multiple review files
ai_review synthesize-prompt REVIEWS_DIR [--output PATH]
```

### 10.2 Common Options

```
--mode working        Review uncommitted changes (staged + unstaged)
--base REF            Base ref for branch comparison
--head REF            Head ref for branch comparison (default: current branch)
--exclude PATTERN     Glob patterns to exclude (repeatable)
--max-file-bytes N    Skip files larger than N bytes
--max-diff-lines N    Truncate hunks beyond N lines  
--depth LEVEL         Analysis depth: shallow|standard|deep
--focus PATH          Limit review to subtree
--output PATH         Write to file instead of stdout
--verbose             Detailed progress to stderr
--chunked             Split output for large changesets
```

### 10.3 Default Exclusions

```
.git/
node_modules/
__pycache__/
*.pyc
.venv/
venv/
dist/
build/
*.egg-info/
.ai_review/cache/
```

---

## 11. Security Considerations

### 11.1 Secret Redaction

Before transmitting any content to an LLM, the packet builder scans for high-entropy strings and known secret patterns:

```python
SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w-]{20,}',
    r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?[\w-]{8,}',
    r'(?i)(token|bearer)\s*[=:]\s*["\']?[\w-]{20,}',
    r'-----BEGIN [A-Z]+ PRIVATE KEY-----',
    r'(?i)aws[_-]?(access[_-]?key|secret)',
]
```

Matched content is replaced with `[REDACTED: possible secret]`.

### 11.2 File Exclusions

By default, the following files are never transmitted:

```
.env
.env.*
*.pem
*.key
*credentials*
*secrets*
```

### 11.3 Audit Logging

Each review run logs (locally, never transmitted):
- Files included in packet
- Total tokens transmitted
- Model endpoint used
- Timestamp and user

---

## 12. Implementation Plan

### 12.1 Package Structure

```
ai_review/
├── __init__.py
├── cli.py                 # Click-based CLI
├── config.py              # Configuration loading
├── git_ops.py             # Git subprocess wrappers
├── repo_scan.py           # File discovery and classification
├── analyzers/
│   ├── __init__.py
│   ├── base.py            # Analyzer protocol
│   ├── python_ast.py      # Python AST extraction
│   ├── js_heuristic.py    # JS/TS heuristic extraction
│   └── generic.py         # Fallback extraction
├── summarize/
│   ├── __init__.py
│   ├── repo_guide.py      # REPO_GUIDE.md generation
│   ├── changes.py         # CHANGES.md generation
│   └── packet.py          # REVIEW_PACKET.md assembly
├── prompt/
│   ├── __init__.py
│   ├── composer.py        # Prompt assembly logic
│   ├── templates/
│   │   ├── system.md      # System prompt template
│   │   ├── rubric.md      # Review rubric template
│   │   └── synthesis.md   # Multi-review synthesis template
│   └── chunker.py         # Large changeset splitting
├── cache/
│   └── store.py           # Cache management
└── security/
    └── redact.py          # Secret detection and redaction
```

### 12.2 Development Phases

**Phase 1: Foundation (Days 1-2).** Implement git operations, file scanning, and basic diff collection. Produce working `CHANGES.md` generation. Goal: `ai_review changes` functional.

**Phase 2: Analysis (Days 3-4).** Implement Python AST analyzer. Build import graph construction. Produce working `REPO_GUIDE.md` generation with caching. Goal: `ai_review analyze` functional.

**Phase 3: Packet Assembly (Day 5).** Implement tiered context selection. Add risk heuristics. Produce complete `REVIEW_PACKET.md`. Goal: `ai_review packet` functional.

**Phase 4: Prompt Composition (Day 6).** Implement prompt templates and composer. Output complete prompts to stdout. Goal: `ai_review prompt | claude -p` works end-to-end.

**Phase 5: Polish (Days 7-8).** Add chunked output mode for large diffs. Implement additional language analyzers. Add synthesis prompt generation. Write documentation and examples.

### 12.3 Testing Strategy

**Unit Tests** cover diff parsing (various change types, renames, binary files), AST extraction accuracy, cache invalidation correctness, secret pattern detection, and token counting accuracy.

**Integration Tests** use fixture repositories with known structures to verify end-to-end packet generation, cache behavior across incremental changes, and branch vs. working mode equivalence.

**Golden File Tests** compare `REPO_GUIDE.md` and `CHANGES.md` output against known-good baselines to catch regressions in output formatting.

---

## 13. Usage Examples

### 13.1 Quick Review of Uncommitted Work

```bash
# One-liner: generate prompt, pipe to Claude Code, save output
ai_review prompt --mode working | claude -p > CODE_REVIEW.md

# Same with Gemini CLI
ai_review prompt --mode working | gemini -p > CODE_REVIEW.md

# Review and display in terminal
ai_review prompt --mode working | claude -p
```

### 13.2 Review Pull Request

```bash
# Compare feature branch to main
ai_review prompt --base main --head feature/new-auth | claude -p

# Review specific subdirectory only
ai_review prompt --base main --head feature/new-auth --focus src/auth/ | claude -p

# Default head is current branch, so this works:
ai_review prompt --base main | claude -p
```

### 13.3 Inspect Before Piping

```bash
# Generate packet for inspection
ai_review packet --mode working > /tmp/packet.md
less /tmp/packet.md

# If it looks good, generate full prompt and pipe
ai_review prompt --mode working | claude -p
```

### 13.4 Large Changesets

```bash
# Chunked mode for big PRs
ai_review prompt --base main --chunked | while IFS= read -r -d '' prompt; do
    echo "$prompt" | claude -p
    echo -e "\n---\n"
done > reviews.md

# Or manually review high-priority files first
ai_review prompt --base main --focus src/auth/ | claude -p > auth_review.md
ai_review prompt --base main --focus src/api/ | claude -p > api_review.md
```

### 13.5 Maintain Repository Analysis

```bash
# Full analysis (first run or after major refactor)  
ai_review analyze --full

# Incremental update (routine maintenance)
ai_review analyze --incremental

# Check what would be analyzed
ai_review analyze --incremental --verbose 2>&1 | head -20
```

### 13.6 Copy to Clipboard for Web UI

```bash
# macOS
ai_review prompt --mode working | pbcopy

# Linux (X11)
ai_review prompt --mode working | xclip -selection clipboard

# Linux (Wayland)
ai_review prompt --mode working | wl-copy
```

### 13.7 Integration with Git Hooks

```bash
# .git/hooks/pre-push (make executable)
#!/bin/bash
echo "Generating code review..."
ai_review prompt --base origin/main --head HEAD | claude -p > /tmp/review.md
echo "Review saved to /tmp/review.md"
cat /tmp/review.md
```

### 13.8 CI Pipeline Integration

```yaml
# GitHub Actions example
- name: Generate Review Context
  run: |
    ai_review packet --base origin/main --head ${{ github.sha }} > review_packet.md
    
- name: Post Review Packet as Comment
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const packet = fs.readFileSync('review_packet.md', 'utf8');
      // Post as PR comment or artifact
```

---

## 14. Success Metrics

The system achieves its goals when reviews demonstrate:

**Architectural Awareness**: Feedback references module relationships and patterns defined in `REPO_GUIDE.md`.

**Evidence-Based Criticism**: Every issue includes a file:line citation or diff hunk reference.

**Zero Hallucination**: No feedback references code that doesn't exist in the packet.

**Actionable Output**: The author can address each item without requesting clarification.

**Fast Context Generation**: Prompt generation completes in under 5 seconds for typical repos (< 100K lines), enabling rapid iteration.

**Reasonable Token Footprint**: The compressed packet fits within 32K tokens for typical PRs, leaving headroom for agent response.

---

## 15. Future Enhancements

**Shell Aliases & Functions.** Provide ready-to-use shell functions for common workflows (e.g., `review-pr`, `review-wip`).

**IDE Integration.** VS Code extension that generates packet on demand or on branch push.

**CI Pipeline Hook.** GitHub Action that posts the review packet (or a summary) as a PR comment for agent-assisted review.

**Historical Context.** Include summaries of recent commits to the same files, helping the agent understand ongoing work patterns.

**Custom Rubrics.** Per-repository review criteria configuration (e.g., stricter security review for auth modules).

**Multi-Language AST.** Tree-sitter integration for consistent, high-quality parsing across all languages.

**Token Estimation.** Built-in token counting to warn when packets exceed typical context limits.

---

## Appendix A: Quick Reference

### Minimal Usage

```bash
# Install
pip install ai-review

# Review current work
ai_review prompt --mode working | claude -p

# Review branch
ai_review prompt --base main | claude -p
```

### Full Command Reference

```bash
ai_review analyze [--full|--incremental] [--output PATH]
ai_review changes (--mode working | --base REF [--head REF]) [--output PATH]
ai_review packet (--mode working | --base REF [--head REF]) [--output PATH]
ai_review prompt (--mode working | --base REF [--head REF]) [--chunked] [--output PATH]
ai_review list-changed (--mode working | --base REF [--head REF])
```

### Agent Pipe Syntax

```bash
# Claude Code
ai_review prompt ... | claude -p

# Gemini CLI  
ai_review prompt ... | gemini -p

# Codex CLI
ai_review prompt ... | codex-cli

# Copy to clipboard (macOS)
ai_review prompt ... | pbcopy
```

---

## Appendix B: Sample Review Packet

```markdown
# Code Review Packet

## Metadata
- Repository: josh-english-terminal
- Review Mode: Branch Comparison  
- Base: main (a1b2c3d)
- Head: feature/rctr-calculation (e4f5g6h)
- Generated: 2024-01-15T14:30:00Z

## Change Summary

### Overview
- Files changed: 4
- Insertions: 127
- Deletions: 23
- Areas touched: analytics/, tests/

### Modified Files

#### analytics/metrics.py
Change type: Modified (+89, -12)
Symbol changes: 
  - Added: calculate_rctr()
  - Modified: MetricsCalculator.__init__()

```diff
@@ -45,6 +45,28 @@ class MetricsCalculator:
+    def calculate_rctr(self, video_id: str, period: DateRange) -> float:
+        """Calculate Relative Click-Through Rate for a video.
+        
+        RCTR = (video CTR) / (channel average CTR for period)
+        """
+        video_ctr = self._get_video_ctr(video_id, period)
+        channel_avg = self._get_channel_average_ctr(period)
+        
+        if channel_avg == 0:
+            return 0.0
+        
+        return video_ctr / channel_avg
```

[Additional files truncated for example]

## Impact Analysis

### Direct Consumers of `analytics/metrics.py`
- api/routes/analytics.py (imports MetricsCalculator)
- workers/daily_rollup.py (imports calculate_rctr)

## Risk Flags
- None identified

## Repository Context

### Module: analytics/
Purpose: Core analytics calculations for YouTube metrics.

Key classes:
- MetricsCalculator: Central calculation engine
- DateRange: Time period abstraction  
- VideoMetrics: Data container for per-video stats

Dependencies: db.client, cache.redis, models.video
```

---

## Appendix C: Sample Review Output

```markdown
### Summary
This change adds RCTR (Relative Click-Through Rate) calculation to the MetricsCalculator class, enabling comparison of individual video CTR against channel averages. The implementation follows existing patterns in the metrics module.

### Verdict
**APPROVE** with minor suggestions

### Blocking Issues
None identified.

### Recommendations

1. **Division safety** [File: analytics/metrics.py:L56-L58]
   The zero-check handles `channel_avg == 0`, but consider whether negative values are possible from `_get_channel_average_ctr()`. If CTR data can be corrupted, a `channel_avg <= 0` check would be more defensive.

2. **Missing type hint** [File: analytics/metrics.py:L45]
   The `period` parameter uses `DateRange` but this import isn't visible in the diff. Verify the import exists at file top.

3. **Test coverage** [File: tests/test_metrics.py:L78-L95]
   Tests cover the happy path but consider adding:
   - Test for zero channel average (division edge case)
   - Test for period with no data

### Questions for Author
- Is RCTR intended to be exposed via the API immediately, or is this groundwork for a future endpoint?
- Should RCTR calculation be cached given it depends on channel-wide aggregation?

### Testing Notes
Consider adding a property-based test that verifies RCTR is always non-negative when inputs are valid.
```
