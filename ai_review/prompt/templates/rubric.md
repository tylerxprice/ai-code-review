
## Instructions

- Evaluate only applicable dimensions.
- Score each applicable dimension **0–5** (0 = unacceptable, 5 = excellent).
- For each dimension: list the most important findings with evidence citations.
- If evidence is missing, do not guess—either inspect the repo (if allowed) or ask **Questions for Author**.

### Format per dimension

- **Score:**
- **What looks good:**
- **Issues / Risks (prioritized):**
- **Evidence:**
- **Recommended action:**

## 1) Correctness & Functional Behavior

Look for:
- Logic errors, edge cases, off-by-one, null/None handling
- Error propagation and fallback behavior
- State transitions, concurrency hazards, ordering assumptions
- Data invariants and contract violations (types, schemas, API expectations)
- Backward compatibility of behavior (silent changes are risky)

Verify (when possible):
- Trace call sites and data flow through modified interfaces
- Check boundary conditions and failure paths
- Confirm behavior matches tests or add missing tests

Evidence required:
- Cite diff lines/hunks for changes; cite repo anchors for invariants/tests you inspected

## 2) Security & Privacy

Look for:
- Input validation, sanitization, encoding, injection risks (SQL/NoSQL, command, template, path, header)
- AuthN/AuthZ regressions, privilege escalation paths, missing checks
- Secrets handling: logging, error messages, config exposure, token forwarding
- Unsafe deserialization, SSRF, open redirects, insecure default config
- Supply chain risk if deps changed (new libs, version bumps)

Verify (when possible):
- Inspect auth middleware/policies for affected routes and call paths
- Inspect config defaults and environment variable handling
- Confirm sensitive values are redacted and never logged

Evidence required:
- Every security claim needs explicit evidence. If unsure, label as **Potential risk** and ask for confirmation/tests.

## 3) Reliability, Resilience & Operational Safety

Look for:
- Timeouts, retries, backoff, circuit breaking (for network/IO)
- Resource handling: file descriptors, sockets, threads, connection pools
- Crash safety, partial failures, rollback/compensation
- Idempotency and re-entrancy where relevant
- Migration/rollout safety: feature flags, staged deployments, safe defaults

Verify (when possible):
- Identify critical paths and ensure defensive handling exists
- Check for deadlocks, race conditions, and blocking IO in async paths
- Confirm observability exists for failure modes

Evidence required:
- Cite concrete code paths and config defaults.

## 4) Design & Architecture

Look for:
- Consistency with existing patterns and boundaries
- Clear ownership of responsibilities; cohesion and coupling
- Appropriateness of abstractions (not too leaky, not over-engineered)
- Dependency direction (avoid layering violations)
- API ergonomics and long-term maintainability

Verify (when possible):
- Inspect adjacent modules and how the changed API is used
- Ensure changes don’t duplicate existing utilities or violate conventions

Evidence required:
- Cite specific modules/interfaces and how they interact.

## 5) Performance & Efficiency

Look for:
- Big-O regressions, unbounded loops, accidental N+1 patterns
- Excessive allocations, serialization overhead, unnecessary copying
- Hot-path logging, per-request expensive computation
- Caching correctness and invalidation (correctness beats caching)
- Latency and throughput implications; memory growth

Verify (when possible):
- Identify hot paths by usage patterns; check where this code runs (startup vs per-request)
- Inspect batching, pagination, limits, and streaming behavior

Evidence required:
- Provide evidence; if performance impact is hypothetical, label as such and propose measurement.

## 6) Maintainability & Clarity

Look for:
- Readability, naming, modularity, and principled error messages
- Complexity: cyclomatic complexity, nested conditionals, unclear invariants
- Documentation updates (README, inline docs, ADRs, comments)
- Consistent style and lint alignment (but do not nitpick)

Verify (when possible):
- Check whether the code is understandable without tribal knowledge
- Ensure public APIs have docstrings/typing/contracts

Evidence required:
- Cite where clarity breaks down and propose a concrete improvement.

## 7) Testing & Observability

Look for:
- Adequate unit/integration coverage for new/changed behavior
- Tests for negative paths and boundary conditions
- Determinism and flake risk (time, randomness, concurrency)
- Logging/metrics/tracing coverage for critical paths
- Backward compatibility tests or migration tests when relevant

Verify (when possible):
- Locate existing tests and ensure they reflect new behavior
- Inspect CI to confirm tests actually run in required environments
- Confirm observability patterns match the codebase conventions

Evidence required:
- Cite added/updated tests, or cite absence/gaps with evidence.

## 8) Delivery & Compatibility (Build/CI/CD/Runtime Environment)

Look for:
- Breaking changes in public interfaces, CLI flags, configs, env vars
- Changes to deployment manifests, containerization, OS assumptions
- Python version constraints, platform-specific paths, file permissions
- Compatibility with supported runtimes (prod vs dev differences)

Verify (when possible):
- Inspect build scripts, Dockerfiles, workflows, and config templates
- Confirm new settings have safe defaults and clear docs

Evidence required:
- Cite the exact change and where it is configured/consumed.

# Rubric Summary (Required)

At the end, include:

- **Dimension scores** (only applicable ones)
- **Top 3 risks** (with evidence)
- **Top 3 improvements** (with evidence)
- **Confidence**
  - **High**: sufficient evidence + tests/config reviewed
  - **Medium**: some missing context but no major red flags
  - **Low**: chunked/truncated diff or missing repo access prevents verification
