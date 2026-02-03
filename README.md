<div align="center">
  <img src="logo.png" alt="AI Review Logo" width="200"/>
  <h1>AI Code Review</h1>
  <p><b>Precision AI-Powered Code Reviews with Deep Architectural Awareness</b></p>
  
  [![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Security: Redacted](https://img.shields.io/badge/Security-Redacted-green.svg)](#security--redaction)
  [![AI: Agent--Ready](https://img.shields.io/badge/AI-Agent--Ready-blueviolet.svg)](#prompt-engineering)
</div>

---

## 🚀 Overview

**AI Code Review** is a high-fidelity code review orchestration tool designed for AI-assisted workflows in the modern DevOps era. Unlike basic diff scripts, it assembles **Review Packets**—rich context containers that combine raw code changes with deep architectural awareness.

It provides AI agents (like Claude, Gemini, or ChatGPT) with the same "system awareness" a Senior Engineer has, leading to higher-quality, evidence-based feedback.

---

## ✨ Key Features

### 🧠 Structural Context Analysis
*   **Python AST Compression**: Extracts class/function signatures and docstrings without wasting tokens on implementation bodies.
*   **JS/TS Heuristics**: Multi-language support for Javascript and Typescript (JSX/TSX) using intelligent heuristic parsing.

### 🛡️ Security & Privacy First
*   **Automated Redaction**: Scans and masks high-entropy secrets (API keys, tokens, auth headers) before they ever leave your machine.
*   **Risk Path Flagging**: Automatically identifies and highlights changes in sensitive areas like `auth/`, `security/`, or infrastructure configs.
*   **Strict Exclusions**: Hardwired protection against accidentally sharing `.env`, `.pem`, or other sensitive assets.

### 🧩 Enterprise Scalability
*   **Prompt Chunking**: Automatically fragments large changesets into sequential AI-readable parts when token limits are exceeded.
*   **Review Rubric**: Includes a professional 5-dimension rubric (Correctness, Security, Design, Performance, Maintainability).

---

## 🛠️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/josh-english/ai-code-review.git
cd ai-code-review

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install in editable mode
pip install -e . --user

# 4. Add to your PATH (recommended)
export PATH="$PATH:$(python3 -m site --user-base)/bin"
```

---

## 📖 Usage

### Generate an AI Review Prompt
The core command that builds the final, pipeable prompt for your AI agent.

```bash
# Review uncommitted (working) changes
ai_review prompt --mode working

# Support for large PRs via chunking
ai_review prompt . --mode working --chunked

# Compare branches
ai_review prompt --base main --head feature-branch
```

### Analyze Repository Structure
Generate a structural guide (REPO_GUIDE.md) that summarizes the entire repository.

```bash
ai_review analyze . --full
```

### Synthesize Multiple Reviews
Consolidate feedback from multiple AI agents into a single report.

```bash
ai_review synthesize-prompt ./reviews --output final_review_prompt.md
```
```

### Inspect Changes Only
Get a clean markdown summary of the diff.

```bash
ai_review changes --mode working
```

### Build a Context Packet
Generate the raw structural context without the prompt instructions.

```bash
ai_review packet .
```

---

## 🧬 Project Structure

```text
ai_review/
├── analyzers/    # AST and Heuristic structural analyzers
├── prompt/       # Templates and chunking logic
├── security/     # Redaction and masking utilities
├── summarize/    # Packet and Change collection logic
├── cli.py        # Click-based interface
└── git_ops.py    # Robust Git integration layer
```

---

<div align="center">
  <p>Built with ❤️ by Josh English</p>
</div>
