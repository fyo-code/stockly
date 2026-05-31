# Parallel Execution Runbook

*Last updated: 2026-04-06*

---

## Purpose

This is the operational guide for running parallel agent executions. Read this once before your first execution. After that, use the Quick Reference at the bottom.

For concepts and design rationale, see `docs/PARALLEL_EXECUTION.md`.
For how to decompose tasks correctly, see `docs/TASK_DECOMPOSITION.md`.

---

## Phase 0: Should You Parallelize?

Run this decision check before doing anything else.

**Parallelize if ALL of these are true:**
- [ ] The task has 3 or more independent subtasks
- [ ] Each subtask would take > 5k tokens on its own
- [ ] Each subtask can be solved without knowing what the other workers find
- [ ] The results can be meaningfully combined into a single output

**Keep it sequential if ANY of these are true:**
- [ ] Subtask B depends on subtask A's results
- [ ] Task is simple enough for one focused context (<2k tokens total)
- [ ] Only 1-2 subtasks (parallelism overhead isn't worth it)
- [ ] Total target scope is < 1000 lines AND < 5 files (worker context overhead dominates the actual work)
- [ ] You're under time pressure and can't afford worker failures

If you're not sure: start sequential. Parallelize when you see the context getting bloated.

---

## Phase 1: Pre-Flight Checklist

Before spawning workers, verify infrastructure is ready:

```
context/
  ├── agent-spawner-config.json   ← exists?
  ├── parallel-tasks.json         ← exists?
  └── worker-results/             ← directory exists?

~/.claude/agents/
  ├── conductor.md                ← exists?
  └── worker-template.md          ← exists?
```

If any file is missing, check `PROGRESS.md` Phase 1 and Phase 2 to see if setup was completed.

---

## Phase 2: Decompose the Task

### Step 2.1 — Identify the decomposition pattern

| Task type | Use pattern |
|-----------|-------------|
| Review/analyze same subject from multiple angles | Dimensional Analysis |
| Evaluate one decision from multiple stakeholder views | Multi-Perspective Decision |
| Analyze a large codebase split by directory | Domain Split |
| Research a topic from multiple sources | Research & Synthesis |
| Validate a design or spec for correctness, feasibility, completeness | Validation & Cross-Check |

See `docs/TASK_DECOMPOSITION.md` for full pattern descriptions.

### Step 2.2 — Write worker task descriptions

For each worker, write out all 4 required parts:

```
[TASK]
One or two sentences. Specific verb, specific subject, specific output type.
"Review backend/api/*.py for SQL injection vulnerabilities."

[SCOPE]
Exact files or directories. This is the whitelist.
- backend/api/explain.py
- backend/api/demand.py
- backend/api/queue.py

[OUTPUT]
File path + exact format the worker must use.
Write to: context/worker-results/worker_1_result.md

# Worker 1 — [Name]
## Status
## Findings
## Summary
## Recommendations
## Confidence

[CONSTRAINTS]
What NOT to analyze — prevents overlap with other workers.
- Do NOT review authentication issues (Worker 2 handles those)
- SQL injection only
```

### Step 2.3 — Independence test

For each pair of workers, ask: "Does Worker B need Worker A's findings to do its job?"

If YES to any pair → restructure before proceeding.

### Step 2.4 — Update `context/parallel-tasks.json`

Before spawning, write the execution record to the registry:

```json
{
  "currentExecution": {
    "execution_id": "parallel_YYYYMMDD_NNN",
    "task_description": "Short description of what this execution does",
    "decomposition_pattern": "dimensional",
    "started_at": "ISO_TIMESTAMP",
    "status": "running",
    "total_workers": 3,
    "workers_complete": 0,
    "workers_failed": 0,
    "workers": [
      {
        "worker_id": 1,
        "task_id": null,
        "task": "Security analysis — backend/api/",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "result_file": "context/worker-results/worker_1_result.md"
      }
    ]
  }
}
```

---

## Phase 3: Spawn Workers

### Step 3.1 — Spawn all workers simultaneously

Use the Agent tool with `run_in_background: true`. Spawn all workers in one message — this is what makes them run in parallel.

```
Agent(
  subagent_type="general-purpose",
  model="haiku",
  prompt="[TASK]...[SCOPE]...[OUTPUT]...[CONSTRAINTS]...",
  run_in_background=true
) → task_id_1

Agent(
  subagent_type="general-purpose",
  model="haiku",
  prompt="[TASK]...[SCOPE]...[OUTPUT]...[CONSTRAINTS]...",
  run_in_background=true
) → task_id_2

Agent(
  subagent_type="general-purpose",
  model="haiku",
  prompt="[TASK]...[SCOPE]...[OUTPUT]...[CONSTRAINTS]...",
  run_in_background=true
) → task_id_3
```

**Model selection:**
- Standard analysis subtasks → Haiku 4.5 (default, cheapest)
- Reasoning-heavy subtasks (complex math, architectural decision) → Sonnet 4.6

### Step 3.2 — Record task IDs in registry

After spawning, update `context/parallel-tasks.json` with the task_ids returned by each Agent call:

```json
{
  "worker_id": 1,
  "task_id": "agent_abc123",
  "status": "running",
  "started_at": "ISO_TIMESTAMP"
}
```

---

## Phase 4: Monitor Workers

**Key design:** Workers return their analysis as response text, not as written files. When each worker completes, the Conductor must use TaskOutput to read the response and write the result file. This avoids the Write-permission issue in background mode.

### Step 4.1 — Check progress periodically

Run the `/worker-monitor` skill to get a live status table:

```
## Execution: parallel_20260406_001
Started: 2026-04-06T10:30:00Z
Elapsed: 00:08:30

| Worker | Task                | Status     | Duration |
|--------|---------------------|------------|----------|
| 1      | Security analysis   | ✓ Complete | 4m 37s   |
| 2      | Performance review  | ⟳ Running  | 8m 30s   |
| 3      | Code quality        | ✓ Complete | 5m 44s   |

Progress: 2/3 complete, 1 running, 0 failed

Next action: Waiting for Worker 2 to complete.
```

### Step 4.2 — Handle worker failure

If a worker shows as `failed`:

1. Note the failure in `context/parallel-tasks.json` (status: "failed")
2. Decide: is this worker's coverage critical?
   - **Critical** → re-run the worker with same prompt before synthesis
   - **Not critical** → proceed to synthesis, note the gap in the final report

Re-running a failed worker:
```
Agent(prompt="[same prompt as original]", run_in_background=true) → new_task_id
```
Update registry with new task_id and reset status to "running".

### Step 4.3 — Write result files as workers complete

When each worker notification arrives:
1. Call `TaskOutput(task_id)` to read the worker's response text
2. Write it to `context/worker-results/worker_N_result.md` using the Write tool
3. Update registry status for that worker

The Conductor owns all file I/O. Workers only return text.

### Step 4.4 — Wait for all workers

Do not proceed to synthesis until all workers are either "complete" or "failed".

The `/worker-monitor` skill will report: **"All workers finished. Synthesis can proceed."**

---

## MANDATORY GATE — Phases 5, 6, and 7 Are Non-Negotiable

**CRITICAL RULE: You MUST complete Phases 5 (Validate), 6 (Synthesis), and 7 (Metrics) for EVERY parallel execution. These are not optional capabilities — they are mandatory gates. Skipping synthesis and manually integrating worker outputs defeats the entire purpose of the system.**

**If you are tempted to skip synthesis because "the worker outputs look good enough" — STOP. That is the exact failure mode this system is designed to prevent. Individual worker outputs are fragments. Only synthesis produces an integrated, cross-validated, conflict-resolved deliverable.**

**The execution is NOT complete until `/metrics-tracker` has been called. Do not report results to the user before that.**

---

## Phase 5: Validate Before Synthesis

### Step 5.1 — Run result validation

Before synthesis, run `/result-validator`. It checks each worker's output file against 8 criteria:

| Check | What it verifies |
|-------|-----------------|
| File exists | Result file was actually written |
| Required sections | Status, Findings, Summary, Recommendations, Confidence all present |
| Real timestamps | No placeholder "YYYY-MM-DD" values |
| Summary counts match | Summary CRITICAL: N matches actual CRITICAL findings in body |
| Finding locations | Every finding has a file:line reference |
| Recommendation linkage | Each recommendation points to a specific finding |
| Confidence is honest | High confidence only when all files were actually read |
| Scope compliance | No out-of-scope findings in main Findings section |

### Step 5.2 — Interpret the validator's decision

| Decision | Meaning | Action |
|----------|---------|--------|
| **GO** | All workers valid or have minor warnings | Proceed to synthesis |
| **GO WITH CAUTION** | Some workers have quality issues, still usable | Proceed — treat flagged workers as lower confidence |
| **HOLD** | One or more workers have critical failures | Fix failures before synthesis (see below) |

**If HOLD:** Check what failed. Common fixes:

| Failure | Fix |
|---------|-----|
| File missing | Re-run that worker |
| File empty | Re-run that worker — likely crashed before writing |
| Summary counts off by 3+ | Re-count manually from body, flag as "low reliability" in synthesis |
| All findings lack locations | Treat as low-confidence, note in synthesis |

---

## Phase 6: Synthesis

### Step 6.1 — Read all worker result files

The Conductor reads every completed worker's result file in `context/worker-results/`.

Order doesn't matter — read all, understand all before writing.

### Step 6.2 — Synthesis structure

The synthesis report must follow this structure:

```markdown
# Synthesis Report — [Task Description]

## Execution Summary
- Execution ID: [id]
- Date: [ISO date]
- Workers: N/N completed, N failed
- Pattern: [dimensional | multi-perspective | domain-split | research | validation]

## Cross-Worker Patterns

[Findings that appear across multiple workers — these are the most important]

**Pattern 1: [Name]**
- Worker 1 flagged: [brief]
- Worker 3 flagged: [brief]
→ Conclusion: [why this matters, combined interpretation]

## Prioritized Findings

### CRITICAL

[List all critical findings from all workers, merged and deduplicated]

**[Finding name]** — [Worker N]
- Description: [what it is]
- Location: file:line
- Recommendation: [specific action]

### HIGH

[...]

### MEDIUM, LOW, INFO
[...]

## Conflicts & Resolutions

[Any case where two workers gave contradictory findings on the same thing]

**Conflict:** Worker 1 says X, Worker 3 says Y
**Resolution:** [How it was resolved and why]

## Coverage Gaps

[Areas that weren't covered, either because a worker failed or scope was limited]

- Worker 2 failed — [its scope] not analyzed
- [Any explicitly excluded areas]

## Summary Statistics
- Total findings: N
- CRITICAL: N, HIGH: N, MEDIUM: N, LOW: N, INFO: N
- Cross-worker patterns identified: N
- Conflicts resolved: N

## Top 5 Actions

Prioritized, specific, actionable. These are what the person reading this should do first.

1. [Action] — [Why it's #1] — Location: file:line
2. ...
```

### Step 6.3 — Update execution registry

After synthesis, update `context/parallel-tasks.json`:

```json
{
  "currentExecution": {
    "status": "complete"
  }
}
```

Move the completed execution to the `executions` archive array.

---

## Phase 7: Post-Execution

### Step 7.1 — Log metrics

Run `/metrics-tracker` after synthesis. It will:
- Calculate total wall-clock duration
- Estimate token savings vs sequential baseline
- Append the record to `context/parallel-execution-metrics.md`
- Update the summary table of recent executions

### Step 7.2 — Clean up worker result files

Worker result files in `context/worker-results/` are transient — they exist for one execution.

After synthesis and metrics are logged, you may delete them to keep the directory clean. Or leave them for 24 hours in case you need to re-read them.

**Never** commit worker result files to git — they are ephemeral execution outputs.

---

## Quick Reference

### Execution Sequence

```
1. Pre-flight check (infrastructure exists + scope ≥ 1000 lines OR ≥ 5 files)
2. Decompose → write [TASK][SCOPE][OUTPUT][CONSTRAINTS] for each worker
3. Independence test — all workers independent?
4. Update parallel-tasks.json with execution record
5. Spawn ALL workers in one message (run_in_background: true)
   └─ Worker prompts must say "return text" NOT "write file"
6. Record task_ids in registry
7. As each worker completes: TaskOutput → write result file (Conductor owns file I/O)
8. /worker-monitor → confirm all workers complete
9. /result-validator → GO or fix failures              ← MANDATORY
10. Read all result files → write synthesis report      ← MANDATORY (Opus)
11. /metrics-tracker → log performance                  ← MANDATORY

⛔ NEVER deliver worker outputs directly to the user.
⛔ NEVER tell workers to Write files — they'll block in background mode.
⛔ NEVER skip steps 9-11 because "results look fine."
⛔ The execution is INCOMPLETE until step 11 finishes.
```

### Worker Prompt Template

```
You are Worker N in a parallel execution. Your task is strictly scoped — do not read or analyze anything outside your assigned scope.

[TASK]
[one or two sentences: what to do, what to find]

[SCOPE]
[exact file list or directory — your whitelist]

[OUTPUT]
Return your complete analysis as your final response text. Do NOT use the Write tool.
The Conductor reads your response via TaskOutput and handles all file writing.

Use this EXACT format:
# Worker N — [Task Name]

## Status
- Current: Complete
- Started: [ISO timestamp]
- Completed: [ISO timestamp]

## Findings

[Your findings here. Group by type. Every finding must include File: path:line and Severity: CRITICAL/HIGH/MEDIUM/LOW/INFO]

## Summary
- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N
- INFO: N

## Recommendations
[One numbered item per finding. Each recommendation names the finding and gives a specific fix.]

## Confidence
[High | Medium | Low] — [one sentence: what you read, what you might have missed]

[CONSTRAINTS]
[what NOT to analyze — prevents overlap with other workers]
```

### Decision Table: When Things Go Wrong

| Problem | Symptom | Action |
|---------|---------|--------|
| Worker timed out | task_id status never changes | Re-run worker with same prompt |
| Worker produced wrong format | validator returns HOLD — missing sections | Re-run worker or synthesize without it (note gap) |
| Workers' findings contradict each other | Conflict on same file/line | Note in synthesis conflict section, explain resolution |
| All workers failed | validator returns HOLD for all | Stop. Re-examine task descriptions. Re-run decomposition. |
| Synthesis context too long | 3+ workers × detailed results = huge context | Summarize each worker's findings to top 5 before synthesis |
| Can't tell if workers are running | No output visible | Use `/worker-monitor` — it calls TaskOutput for you |

### Model Selection Reference

| Role | Model | Why |
|------|-------|-----|
| Conductor (decompose, synthesize) | Opus 4.6 | Deep reasoning, complex synthesis |
| Standard worker (analysis, review) | Haiku 4.5 | Fast, cheap, focused |
| Complex worker (architecture, math) | Sonnet 4.6 | More reasoning than Haiku, less expensive than Opus |

### Token Estimation

| N workers | Sequential baseline | Parallel actual | Savings |
|-----------|---------------------|-----------------|---------|
| 2 | (2 × 15k) + 5k = 35k | (2 × 10k) + 15k = 35k | ~0% |
| 3 | (3 × 15k) + 5k = 50k | (3 × 10k) + 15k = 45k | ~10% |
| 4 | (4 × 15k) + 5k = 65k | (4 × 10k) + 15k = 55k | ~15% |

*Note: Token savings are modest for small N. The larger benefit is faster wall time (~67% faster) and better quality synthesis from isolated, focused workers.*

---

## Common Mistakes

**Mistake 1: Not including the output format in the worker prompt.**
Workers don't have access to `worker-template.md`. They need the format inlined in the prompt. The result-validator will catch this, but it means a re-run.

**Mistake 2: Spawning workers sequentially (one at a time).**
All workers must be spawned in a single message to run in parallel. Spawning them in separate messages makes them sequential.

**Mistake 3: Starting synthesis before all workers finish.**
Partial synthesis = partial report. Always wait for `/worker-monitor` to confirm all workers are done.

**Mistake 4: Overlapping scopes between workers.**
If Worker 1 covers "all backend" and Worker 2 covers "backend/api", they'll produce duplicate findings on the same files. Scopes must be non-overlapping.

**Mistake 5: Skipping the independence test.**
If one worker's output feeds another, run them sequentially. Parallel with hidden dependencies produces wrong results.

**Mistake 6: Skipping synthesis and manually integrating worker outputs.**
This is the most dangerous mistake because it looks like it works. You read the worker outputs, combine them yourself, and deliver to the user. But you've bypassed validation, cross-pattern detection, conflict resolution, and metrics tracking. The result is fragmented, unvalidated, and the system learns nothing. ALWAYS run Phases 5-7. No exceptions.

**Mistake 7: Using this system only for analysis tasks.**
The parallel execution system works for implementation (code-writing) tasks too, not just reviews. Use the "Independent Implementation" decomposition pattern (Pattern 6) when building multiple independent modules. Workers write code; synthesis validates integration, resolves conflicts, and ensures consistency across modules.

**Mistake 8: Parallelizing tasks that are too small.**
Each worker loads the full system context (~80k tokens). If the actual target code is < 1000 lines / < 5 files, the overhead completely dominates — you're burning tokens for zero benefit. Hard rule: if total scope is < 1000 lines AND < 5 files, solve it directly. Only parallelize when the task is large enough that isolated, focused workers produce meaningfully better analysis than one thorough sequential pass.

**Mistake 9: Telling workers to write files instead of returning text.**
Background agents in Claude Code cannot get Write permission approved — they run silently and the user isn't prompted. Workers that try to Write will block and their analysis is lost. Always instruct workers to return their full analysis as response text. The Conductor reads it via TaskOutput and writes the result files itself.
