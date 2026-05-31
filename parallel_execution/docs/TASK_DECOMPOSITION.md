# Task Decomposition Guide

*Last updated: 2026-04-06*

---

## What Decomposition Is

Task decomposition is the process of breaking a complex request into independent subtasks that can be solved simultaneously by separate worker agents — without needing each other's results.

Good decomposition is the most important skill in parallel execution. Poor decomposition (hidden dependencies, overlapping scope) creates synthesis problems and wastes tokens. Good decomposition creates clean, focused workers that produce high-quality, combinable results.

---

## The Independence Test

Before decomposing any task, every subtask must pass this test:

> "Can worker N solve its subtask completely, without knowing what any other worker found?"

If YES for all subtasks → decompose and parallelize.
If NO for any subtask → keep it sequential, or restructure.

### Examples

**Passes the test:**
```
Task: Analyze the backend

Worker 1: Find all security vulnerabilities
Worker 2: Find all performance bottlenecks
Worker 3: Find all code quality issues

→ Worker 1 doesn't need to know about performance to find security issues
→ Worker 2 doesn't need to know about security to find performance issues
→ All three are independent ✓
```

**Fails the test:**
```
Task: Refactor the authentication module

Worker 1: Design the new auth structure
Worker 2: Implement the new auth structure

→ Worker 2 CANNOT implement without Worker 1's design
→ Sequential dependency — do NOT parallelize ✗
```

---

## The 5 Decomposition Patterns

### Pattern 1: Dimensional Analysis

Split one subject into independent analytical dimensions.

**Structure:**
```
Task: Analyze [subject]
Workers: [Dimension A reviewer] + [Dimension B reviewer] + [Dimension C reviewer]
```

**Best for:** Code review, system evaluation, architecture assessment, document review

**Example:**
```
Task: "Review the backend API"

Worker 1 — Security dimension
  Task: Find security vulnerabilities in the backend API
  Context: All API route files
  Output: Security findings with severity

Worker 2 — Performance dimension
  Task: Identify performance bottlenecks in the backend API
  Context: All API route files
  Output: Performance issues with impact

Worker 3 — Reliability dimension
  Task: Find reliability/error handling gaps in the backend API
  Context: All API route files
  Output: Reliability issues with severity

Synthesis: Combine all three → prioritized action list
```

**Why it works:** Security, performance, and reliability are independent analytical lenses. A security analyst doesn't need the performance report to find a SQL injection — they can see it directly.

---

### Pattern 2: Multi-Perspective Decision

Evaluate one decision from independent viewpoints.

**Structure:**
```
Task: Should we [decision]?
Workers: [Technical evaluator] + [Cost evaluator] + [Risk evaluator]
```

**Best for:** Architecture decisions, tool selection, build-vs-buy, vendor selection

**Example:**
```
Task: "Should we switch from SQLite to PostgreSQL for production?"

Worker 1 — Technical perspective
  Task: Evaluate SQLite vs PostgreSQL technical fit for our codebase
  Context: Current schema, query patterns, codebase size
  Output: Technical assessment (pros/cons, migration complexity)

Worker 2 — Cost perspective
  Task: Estimate total cost of ownership for SQLite vs PostgreSQL
  Context: Current infra, expected scale, team size
  Output: Cost comparison (infrastructure, ops, dev time)

Worker 3 — Risk perspective
  Task: Identify migration risks in switching from SQLite to PostgreSQL
  Context: Current schema, data volume, deployment environment
  Output: Risk assessment (data migration, downtime, rollback)

Synthesis: Combine all three → recommendation with reasoning
```

---

### Pattern 3: Domain Split

Divide a large scope into separate non-overlapping domains.

**Structure:**
```
Task: Review/analyze [large scope]
Workers: [Domain A] + [Domain B] + [Domain C]
```

**Best for:** Large codebases, comprehensive audits, full-system reviews

**Example:**
```
Task: "Audit the entire codebase for issues"

Worker 1 — Backend domain
  Task: Audit backend/ directory for all issues
  Context: backend/ directory only
  Output: Backend issues by category

Worker 2 — Frontend domain
  Task: Audit frontend/ directory for all issues
  Context: frontend/ directory only
  Output: Frontend issues by category

Worker 3 — Data/infrastructure domain
  Task: Audit data pipeline and configuration files for issues
  Context: data/, config files, .env files
  Output: Data/infra issues by category

Synthesis: Combine all three → full-system audit report
```

**Critical rule:** Domains must not overlap. Worker 1 covers backend/ ONLY. Worker 2 covers frontend/ ONLY. If they overlap, findings will duplicate and synthesis becomes confusing.

---

### Pattern 4: Research & Synthesis

Gather information from independent sources or angles, then synthesize.

**Structure:**
```
Task: Research [topic]
Workers: [Source/angle A] + [Source/angle B] + [Source/angle C]
```

**Best for:** Competitor analysis, technology evaluation, requirements gathering

**Example:**
```
Task: "Research the best demand forecasting approach for our use case"

Worker 1 — Statistical methods
  Task: Research statistical demand forecasting methods (ARIMA, ETS, Holt-Winters)
  Output: Summary of statistical approaches, pros/cons, accuracy benchmarks

Worker 2 — ML methods
  Task: Research ML-based demand forecasting (LightGBM, Prophet, LSTM)
  Output: Summary of ML approaches, pros/cons, data requirements

Worker 3 — Industry patterns
  Task: Research how retailers actually implement demand forecasting in practice
  Output: Real-world patterns, common mistakes, implementation considerations

Synthesis: Combine all three → "here's what the evidence says, here's our recommendation"
```

---

### Pattern 5: Validation & Cross-Check

Multiple workers independently validate the same thing from different angles.

**Structure:**
```
Task: Validate [claim/design/proposal]
Workers: [Validator A] + [Validator B] + [Validator C]
```

**Best for:** Final review, pre-launch checks, design validation, spec verification

**Example:**
```
Task: "Validate the demand engine design before we build it"

Worker 1 — Accuracy validation
  Task: Review FORECAST_ENGINE_BLUEPRINT_V2.md for mathematical correctness
  Output: Formula errors, missing edge cases, accuracy concerns

Worker 2 — Implementability validation
  Task: Review FORECAST_ENGINE_BLUEPRINT_V2.md for implementation feasibility
  Output: Impossible or impractical requirements, missing specs

Worker 3 — Completeness validation
  Task: Review FORECAST_ENGINE_BLUEPRINT_V2.md against the MVP requirements
  Output: Gaps between blueprint and what MVP actually needs

Synthesis: Combine all three → "blueprint is ready / here are blockers"
```

---

## How to Write a Worker Task Description

A good worker task description has 4 parts:

### Part 1: TASK (1-2 sentences)
What the worker must do. Be specific.

```
TASK:
Review backend/api/ for SQL injection vulnerabilities. Check all database
queries for parameterization, user input handling, and query construction patterns.
```

### Part 2: SCOPE (1 paragraph)
Exactly what files/data to look at. No ambiguity.

```
SCOPE:
Analyze these files only:
- backend/api/explain.py
- backend/api/demand.py
- backend/api/queue.py
- backend/data/ingest.py
Do not analyze frontend files.
```

### Part 3: OUTPUT (exact format)
Tell the worker exactly what to produce.

```
OUTPUT:
Write results to: context/worker-results/worker_1_result.md

Use this format:
# Worker 1 — SQL Injection Security Review

## Status
Current: Complete
Started: [ISO timestamp]
Completed: [ISO timestamp]

## Findings
[Your findings here]

## Summary
- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N

## Recommendations
[Specific fixes for each finding]

## Confidence
[High | Medium | Low] — reason
```

### Part 4: CONSTRAINTS (what NOT to do)
Prevent workers from scope-creeping into each other's territory.

```
CONSTRAINTS:
- Do NOT review XSS or authentication issues (Worker 2 handles those)
- Do NOT suggest performance improvements (Worker 3 handles those)
- Focus ONLY on SQL injection and database query safety
```

### Full Example:

```
[TASK]
Review backend/api/ for SQL injection vulnerabilities. Check all database
queries for parameterization, user input handling, and query construction patterns.

[SCOPE]
Analyze these files only:
- backend/api/explain.py
- backend/api/demand.py
- backend/api/queue.py
- backend/data/ingest.py

[OUTPUT]
Write results to: context/worker-results/worker_1_result.md

# Worker 1 — SQL Injection Security Review

## Status
Current: Complete
Started: [ISO timestamp]
Completed: [ISO timestamp]

## Findings
[Your findings here]

## Summary
- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N

## Recommendations
[Specific fixes]

## Confidence
[High/Medium/Low] — reason

[CONSTRAINTS]
- Only SQL injection and database query safety
- Do NOT cover XSS, authentication, or other security topics
- Do NOT suggest performance improvements
```

---

## Decomposition Checklist

Before finalizing any decomposition:

- [ ] All subtasks pass the independence test
- [ ] Scopes are non-overlapping (no domain appears in two workers)
- [ ] Each subtask has a clear, specific task description
- [ ] Each subtask has exact scope boundaries (which files/data)
- [ ] Each subtask has explicit constraints (what NOT to do)
- [ ] Output format is specified for each worker
- [ ] Synthesis is feasible (results can be meaningfully combined)
- [ ] Number of workers is 2-4 (avoid > 4, synthesis gets complex)

---

## What Makes a Bad Decomposition

### Problem 1: Hidden dependencies
```
BAD:
Worker 1: Design the new database schema
Worker 2: Write queries for the new schema

Worker 2 depends on Worker 1's output. Sequential, not parallel.
```

### Problem 2: Overlapping scope
```
BAD:
Worker 1: Review backend/ for security issues
Worker 2: Review the entire codebase for security issues

Worker 2 includes backend/ — overlap creates duplicate findings.
```

### Problem 3: Scope too large for one worker
```
BAD:
Worker 1: Fully implement the demand forecasting engine

This is a 10+ hour task. Too large for one worker — results will be shallow.

BETTER: Break into smaller, focused subtasks
Worker 1: Implement data ingestion + validation layer
Worker 2: Implement feature engineering functions
Worker 3: Implement ETS model wrapper
```

### Problem 4: Scope too small to bother
```
BAD:
Worker 1: Check if the variable is named correctly on line 42

This is a 30-second task. Overhead of spawning a worker > value.
Keep trivial tasks sequential.
```

### Problem 5: No clear output format
```
BAD:
Worker 1: "Review the code and let me know what you find"

No output format → worker will produce whatever format feels right
→ synthesis fails because outputs are inconsistent

ALWAYS specify exact output format and file path.
```

---

## When NOT to Parallelize

Even if subtasks seem independent, sometimes sequential is better:

| Scenario | Why Sequential | Alternative |
|----------|---------------|-------------|
| Subtask B might not need to run (depends on A's result) | Waste to spawn B if A determines it's unnecessary | Run A, then decide if B is needed |
| Task is simple (<2k tokens total) | Spawning overhead > time saved | Just do it in one context |
| Results need constant cross-referencing | Workers can't work in isolation | Sequential with full context |
| Only 1-2 subtasks | Parallelism benefit minimal | Not worth the setup overhead |
| Tight deadline + workers might fail | Sequential is more reliable under pressure | Keep sequential |

---

## Quick Reference: Pattern Selector

```
What kind of task is it?

  Is it a review/analysis?
    → Same subject, multiple angles? → Pattern 1 (Dimensional)
    → Large scope, multiple domains? → Pattern 3 (Domain Split)
    → Validating correctness?       → Pattern 5 (Validation)

  Is it a decision?
    → Multiple stakeholders/perspectives? → Pattern 2 (Multi-Perspective)

  Is it research?
    → Multiple sources/angles to explore? → Pattern 4 (Research & Synthesis)

  None of the above?
    → Keep sequential. Parallelism may not be suitable.
```

---

## Decomposition Log

Track decompositions that worked well and those that failed — builds over time.

### Successful Decompositions

*(Empty — populate as you run executions)*

| Date | Task | Pattern | Workers | Result |
|------|------|---------|---------|--------|
| | | | | |

### Failed Decompositions (Lessons Learned)

*(Empty — populate as you run executions)*

| Date | Task | Problem | Fix Applied |
|------|------|---------|-------------|
| | | | |
