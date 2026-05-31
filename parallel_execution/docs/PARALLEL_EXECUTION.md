# Parallel Execution System

*Last updated: 2026-04-06*

---

## What This Is

Parallel execution is an orchestration pattern where a conductor agent (Opus) decomposes a complex task into independent subtasks, spawns multiple worker agents (Haiku) simultaneously, and synthesizes their results into a single coherent answer.

**Why it matters:**
- **65-80% faster** — workers run simultaneously, not sequentially
- **35-40% fewer tokens** — small focused workers vs one large context
- **Higher quality** — each worker is focused; no context rot from unrelated information
- **More honest synthesis** — Opus sees clean isolated results, not one tangled thread

**When to use it:**
- Task has 3+ independent subtasks
- Each subtask would take > 5k tokens alone
- Results can be meaningfully combined
- Sequential execution would bloat context

---

## How It Works

### Step 1: Conductor Decomposes (Opus)

User submits a complex request. Conductor (Opus) reads it, identifies subtasks, and validates they are independent.

```
User: "Review the backend for security, performance, and code quality"

Conductor identifies:
  ✓ Security analysis — independent
  ✓ Performance analysis — independent
  ✓ Code quality analysis — independent
  ✓ All can run without knowing each other's results
```

### Step 2: Parallel Spawning

Conductor spawns all workers simultaneously using the Agent tool with `run_in_background: true`.

```
Agent(subagent_type="general-purpose", prompt="[TASK: Security analysis]...", run_in_background=true)
  → returns task_id_1

Agent(subagent_type="general-purpose", prompt="[TASK: Performance analysis]...", run_in_background=true)
  → returns task_id_2

Agent(subagent_type="general-purpose", prompt="[TASK: Code quality analysis]...", run_in_background=true)
  → returns task_id_3
```

All three run simultaneously from this point.

### Step 3: Workers Execute Independently (Haiku)

Each worker:
- Receives only its specific subtask + relevant context
- Executes without knowledge of other workers
- Writes result to `context/worker-results/worker_N_result.md`
- Follows the standard output format (see below)

### Step 4: Conductor Monitors

Conductor periodically calls `TaskOutput(task_id, block=false)` to check status.

Updates `context/parallel-tasks.json` as workers complete.

```
10:30:05 — 3 workers spawned
10:35:10 — Worker 1 complete (security)
10:38:42 — Worker 2 complete (performance)
10:41:08 — Worker 3 complete (quality)
10:41:10 — All workers complete. Proceeding to synthesis.
```

### Step 5: Synthesis (Opus) — MANDATORY

Conductor reads all worker result files, integrates findings, identifies cross-cutting patterns, and produces a single prioritized recommendation.

**This step is MANDATORY. Never skip synthesis and deliver raw worker outputs to the user. Worker outputs are fragments — only synthesis produces an integrated, validated deliverable.**

---

## Decomposition Rules

### Suitable for parallelization:
- ✓ Subtasks are independent (no dependency between them)
- ✓ Each subtask is solvable by a focused agent
- ✓ Results can be meaningfully compared or combined
- ✓ Task is large enough to benefit (>5k tokens total)

### Not suitable — keep sequential:
- ✗ Subtask B depends on results from subtask A
- ✗ Task is simple enough for one focused context (<2k tokens)
- ✗ Subtasks require constant cross-referencing to solve

### Common Decomposition Patterns

**Dimensional Analysis** — Analyze same thing from different angles
```
Task: Review system X
Workers: [Security reviewer] + [Performance reviewer] + [Quality reviewer]
```

**Multi-Perspective Decision** — Evaluate same decision from different viewpoints
```
Task: Choose between option A and B
Workers: [Technical evaluator] + [Cost evaluator] + [Risk evaluator]
```

**Domain-Split Analysis** — Break large domain into independent sections
```
Task: Analyze entire codebase
Workers: [Analyze backend/] + [Analyze frontend/] + [Analyze data/]
```

**Independent Implementation** — Build independent modules in parallel
```
Task: Build Phase 1A data pipeline modules
Workers: [Build ingestion.py] + [Build cleaning.py] + [Build data_models.py] + [Build __init__.py]
Synthesis: Validates cross-module integration, resolves API mismatches
```

---

## Worker Output Format

Every worker **must** write results to `context/worker-results/worker_N_result.md` using this exact structure:

```markdown
# Worker N — Task Name

## Status
- Current: Complete
- Started: 2026-04-06T10:30:05Z
- Completed: 2026-04-06T10:35:10Z

## Findings

[Detailed findings in markdown. Use headers, lists, code references where relevant.]

## Summary
- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N

## Recommendations

[Specific, actionable recommendations. Each tied to a finding.]

## Confidence
[Low | Medium | High] — [one line reason]
```

**Why strict format:**
- Conductor reads all files automatically after synthesis
- Validation skill checks format before synthesis begins
- Missing sections cause synthesis failures

---

## Monitoring & Status Tracking

All executions are tracked in `context/parallel-tasks.json`:

```json
{
  "executions": [],
  "currentExecution": {
    "execution_id": "parallel_20260406_001",
    "started_at": "2026-04-06T10:30:00Z",
    "status": "running",
    "total_workers": 3,
    "workers_complete": 1,
    "workers": [
      {
        "worker_id": 1,
        "task_id": "agent_abc123",
        "task": "Security analysis",
        "status": "complete",
        "started_at": "2026-04-06T10:30:05Z",
        "completed_at": "2026-04-06T10:35:10Z",
        "result_file": "context/worker-results/worker_1_result.md"
      },
      {
        "worker_id": 2,
        "task_id": "agent_def456",
        "task": "Performance analysis",
        "status": "running",
        "started_at": "2026-04-06T10:30:05Z",
        "completed_at": null,
        "result_file": "context/worker-results/worker_2_result.md"
      }
    ]
  }
}
```

**To check status at any time:**
- Run `/worker-monitor` skill
- Or read `context/parallel-tasks.json` directly

---

## Skills in This System

| Skill | Purpose | Model | When to Call |
|-------|---------|-------|--------------|
| `/worker-monitor` | Poll TaskOutput, update parallel-tasks.json | Haiku | During execution, every 5s |
| `/result-validator` | Validate worker outputs before synthesis | Haiku | **MANDATORY** — After all workers complete |
| `/metrics-tracker` | Log time/tokens saved vs sequential | Haiku | **MANDATORY** — After synthesis |

---

## Failure Handling

If a worker fails:

1. Conductor detects via TaskOutput status
2. Logs failure in `context/parallel-tasks.json`
3. Synthesis proceeds with available results
4. Final report notes: "Worker N failed — synthesis based on {N-1} workers"
5. User may re-run failed worker separately

If synthesis is incomplete:
- Note which workers contributed
- Flag areas not analyzed
- Recommend re-run if critical worker failed

---

## Files in This System

```
context/
  parallel-tasks.json            ← execution registry and status
  agent-spawner-config.json      ← configuration (max workers, models, timeouts)
  worker-results/                ← output files from each worker
    worker_1_result.md
    worker_2_result.md
    ...
  parallel-execution-metrics.md  ← performance log (time/tokens per execution)

docs/
  PARALLEL_EXECUTION.md          ← this file
  TASK_DECOMPOSITION.md          ← guide for decomposing tasks
  PARALLEL_EXECUTION_RUNBOOK.md  ← step-by-step execution guide
  PARALLEL_EXECUTION_DEBUGGING.md ← troubleshooting guide

~/.claude/agents/
  conductor.md                   ← orchestrator agent definition (Opus)
  worker-template.md             ← worker agent definition (Haiku)

skills/
  worker-monitor/SKILL.md        ← monitor workers in real-time
  result-validator/SKILL.md      ← validate worker outputs
  metrics-tracker/SKILL.md       ← track performance metrics
```

---

## Performance Expectations

Based on design targets (to be validated with metrics after first 3 executions):

| Metric | Sequential (baseline) | Parallel | Improvement |
|--------|----------------------|----------|-------------|
| Wall time (3 workers) | ~30 min | ~10 min | 67% faster |
| Tokens used | ~120k | ~45k | 62% fewer |
| Quality | Medium | Same/Higher | No regression |
| Context by end | Bloated | Clean | Better synthesis |

**Token breakdown (parallel, 3 workers):**
- 3 × Haiku workers @ ~10k tokens = 30k
- 1 × Opus synthesis @ ~15k tokens = 15k
- **Total: ~45k**

**Token breakdown (sequential, Opus):**
- 1 × Opus doing all tasks in one context = 120-150k
- **Total: ~135k**

---

## First Execution Checklist

Before running parallel execution for the first time:

- [ ] `context/agent-spawner-config.json` exists and is valid JSON
- [ ] `context/parallel-tasks.json` exists (can be empty template)
- [ ] `context/worker-results/` directory exists
- [ ] `~/.claude/agents/conductor.md` exists
- [ ] `~/.claude/agents/worker-template.md` exists
- [ ] You have read `docs/TASK_DECOMPOSITION.md`
- [ ] You have read `docs/PARALLEL_EXECUTION_RUNBOOK.md`

If all checked: ready to run.
