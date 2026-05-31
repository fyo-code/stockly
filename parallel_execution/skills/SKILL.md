---
id: metrics-tracker
name: metrics-tracker
description: "Tracks performance metrics for parallel executions. Logs execution time, worker count, findings, token efficiency, and outcome to context/parallel-execution-metrics.md. Calculates token savings vs sequential baseline."
category: parallel-execution
risk: safe
source: project
date_added: "2026-04-06"
---

## When to Use

Use this skill after synthesis is complete. It captures execution metrics and logs them to `context/parallel-execution-metrics.md` for future reference and performance tracking.

Call once per execution, after the Conductor's synthesis report is finalized.

---

# Metrics Tracker

## Purpose

Record execution metadata and performance data to build a historical log of parallel execution efficiency. Track total duration, worker count, findings, token usage patterns, and overall outcome.

This enables future sessions to:
- See which decomposition patterns work best
- Estimate token savings
- Identify failing patterns
- Improve decomposition strategy over time

---

## Instructions

### Step 1: Gather Execution Data

From `context/parallel-tasks.json`:
- `execution_id`
- `task_description`
- `decomposition_pattern`
- `started_at`
- For each completed worker:
  - `worker_id`
  - `task`
  - `status` (complete or failed)
  - `started_at`
  - `completed_at`

From the Conductor's synthesis report:
- Total findings count (sum of CRITICAL + HIGH + MEDIUM + LOW + INFO)
- Count by severity (N_critical, N_high, etc.)
- Number of cross-worker patterns identified
- Number of conflicts resolved
- Overall outcome (success / partial / degraded)

### Step 2: Calculate Metrics

**Total Duration:**
```
total_duration = max(worker.completed_at) - execution.started_at
```

**Per-Worker Duration:**
```
worker_duration = worker.completed_at - worker.started_at
```

**Worker Success Rate:**
```
success_rate = completed_workers / total_workers
```

**Estimated Token Efficiency** (for future reference):

Use this formula as a rough baseline:
- **Sequential estimate:** N workers × 15k tokens/worker = baseline
  - Add 5k for synthesis overhead
  - Total sequential ≈ (N × 15k) + 5k

- **Parallel actual:**
  - Sum actual workers' token usage (if available) OR
  - Estimate: (N × 10k for Haiku) + (15k for Opus synthesis)
  - Total parallel ≈ (N × 10k) + 15k

- **Savings:**
  ```
  token_savings_pct = (baseline - actual) / baseline × 100%
  ```

Example:
- 3 workers, sequential baseline = (3 × 15k) + 5k = 50k tokens
- 3 Haiku workers + Opus synthesis = (3 × 10k) + 15k = 45k tokens
- Savings = (50k - 45k) / 50k × 100% = 10% token savings

### Step 3: Format and Append

Append the following to `context/parallel-execution-metrics.md`:

```markdown
## Execution: [execution_id]

**Date:** YYYY-MM-DD HH:MM:SS UTC
**Task:** [brief description, max 100 chars]
**Pattern:** [dimensional | multi-perspective | domain-split | research | validation]
**Outcome:** [success | partial | degraded | failed]

### Workers
| ID | Task | Status | Duration | Findings |
|----|------|--------|----------|----------|
| 1 | Security Analysis | ✓ | 4m 37s | 3 (1C, 2H) |
| 2 | Performance Review | ✓ | 6m 12s | 5 (2H, 3M) |
| 3 | Code Quality | ✓ | 5m 44s | 7 (1H, 4M, 2L) |

**Success Rate:** 3/3 (100%)
**Total Duration:** 16m 34s (wall-clock time, not sum)

### Findings Summary
- Total: 15 findings
- CRITICAL: 1
- HIGH: 5
- MEDIUM: 7
- LOW: 0
- INFO: 2

### Efficiency
- Cross-worker patterns identified: 2
- Conflicts resolved: 0
- Gaps in coverage: None

**Estimated Token Usage:**
- Sequential baseline: ~50k tokens
- Parallel actual: ~45k tokens
- Savings: ~10% fewer tokens

### Notes
[Optional: any notable observations about this execution, e.g., "Worker 2 timed out but Worker 1+3 filled the gap", "Conflict between Workers 1&2 on X — resolved through Y"]

---
```

### Step 4: Update Summary Section (if exists)

At the top of `context/parallel-execution-metrics.md`, maintain a summary table of the last 10 executions (or all if <10):

```markdown
# Parallel Execution Metrics Log

## Recent Executions (Last 10)

| Date | Pattern | Workers | Success Rate | Duration | Token Est. Savings | Outcome |
|------|---------|---------|--------------|----------|-------------------|---------|
| 2026-04-06 | dimensional | 3 | 100% | 16m 34s | ~10% | success |
| ... | ... | ... | ... | ... | ... | ... |

---
```

If the file doesn't exist yet, create it with the summary header and the first execution entry.

---

## Output Contract

Appends one execution record to `context/parallel-execution-metrics.md`.

Creates the file if it doesn't exist.

Does NOT modify any other files.

Returns confirmation message: "Metrics logged: [execution_id] — [outcome] — [X workers, Y findings]"

---

## Interpretation Guide

**Token Savings %:**
- 15%+ savings — parallelization was highly efficient for this task
- 5-15% savings — parallelization was worthwhile
- <5% savings — marginal benefit; sequential might have been better

**Success Rate:**
- 100% — ideal
- 75-99% — acceptable; synthesis proceeded with degraded coverage
- <75% — decomposition may have been flawed; consider re-evaluating pattern

**Duration:**
- Expected wall-clock time ≈ longest worker duration (not sum of workers)
- If reported duration is close to sum, workers didn't actually run in parallel (investigate)

**Findings per Worker:**
- 0 findings — worker was well-scoped or found nothing (valid)
- 1-10 findings — typical range
- >20 findings — worker may have over-included or expanded scope (review)
