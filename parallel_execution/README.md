# Parallel Execution Framework

A complete, battle-tested infrastructure for orchestrating multiple independent Claude agents in parallel to solve complex tasks faster and more efficiently.

## What This Is

This framework enables you to:
- **Decompose complex tasks** into independent subtasks
- **Spawn multiple agents** to work on those subtasks simultaneously
- **Monitor progress** in real-time across all workers
- **Validate results** before synthesis
- **Synthesize findings** from all workers into a coherent report
- **Track metrics** and token efficiency for continuous improvement

**Token savings:** 10-15% for 3+ workers vs sequential execution
**Wall-clock time savings:** ~67% faster (workers run in parallel, not sequentially)

---

## Directory Structure

```
_parallel-execution-framework/
├── README.md                                 ← You are here
├── docs/
│   ├── PARALLEL_EXECUTION.md                ← Conceptual overview & design
│   ├── TASK_DECOMPOSITION.md                ← How to decompose tasks correctly
│   ├── PARALLEL_EXECUTION_RUNBOOK.md        ← Step-by-step operational guide
│   └── PARALLEL_EXECUTION_DEBUGGING.md      ← Troubleshooting & recovery recipes
├── context/
│   ├── agent-spawner-config.json            ← (Template) Spawner configuration
│   ├── parallel-tasks.json                  ← (Template) Execution registry
│   └── parallel-execution-metrics.md        ← (Template) Metrics log
├── skills/
│   ├── worker-monitor-SKILL.md              ← Monitor live worker status
│   ├── result-validator-SKILL.md            ← Validate worker outputs
│   └── metrics-tracker-SKILL.md             ← Log execution metrics
└── agents/
    ├── conductor.md                         ← Orchestrator agent (Opus 4.6)
    └── worker-template.md                   ← Worker agent template
```

---

## Quick Start (5 Minutes)

### 1. Copy Framework to Your Project

```bash
# From your project root:
cp -r _parallel-execution-framework framework/
# Or symlink it if you want to share across projects:
ln -s /path/to/_parallel-execution-framework framework/
```

### 2. Create Infrastructure Files

Create these three files in your project's `context/` directory (copy from `framework/context/`):

- `context/parallel-tasks.json` — execution registry
- `context/agent-spawner-config.json` — spawner config
- `context/parallel-execution-metrics.md` — metrics log

Create `context/worker-results/` directory:
```bash
mkdir -p context/worker-results/
```

### 3. Install Agents Globally (One-time)

Copy agent templates to your local Claude Code agents directory:

```bash
cp framework/agents/conductor.md ~/.claude/agents/
cp framework/agents/worker-template.md ~/.claude/agents/
```

### 4. Install Skills Globally (One-time)

Copy skills to your Claude Code skills directory. Create subdirectories for each:

```bash
mkdir -p ~/.claude/skills/worker-monitor
mkdir -p ~/.claude/skills/result-validator
mkdir -p ~/.claude/skills/metrics-tracker

# Then copy the skill files from framework/skills/
```

### 5. Read the Runbook

Before your first execution, read:
- `framework/docs/PARALLEL_EXECUTION_RUNBOOK.md` (10 min)
- `framework/docs/PARALLEL_EXECUTION.md` (conceptual overview, 5 min)

---

## When to Use Parallelization

**Use parallel agents when ALL of these are true:**
- Task has 3+ independent subtasks
- Each subtask takes >5k tokens (non-trivial)
- Subtask B doesn't depend on subtask A's results (independent)
- Results can be combined into a coherent output

**Stick with sequential when:**
- Task has only 1-2 subtasks
- Subtasks are dependent (B needs A's output)
- Total task is simple (<2k tokens)
- You're under time pressure

---

## The 7-Phase Workflow

1. **Pre-Flight** — Verify infrastructure exists
2. **Decompose** — Break task into independent subtasks
3. **Spawn** — Launch all workers simultaneously in background
4. **Monitor** — Check progress with `/worker-monitor` skill
5. **Validate** — Run `/result-validator` before synthesis — **MANDATORY**
6. **Synthesize** — Read all results, combine into final report — **MANDATORY**
7. **Track** — Log metrics with `/metrics-tracker` skill — **MANDATORY**

**Phases 5-7 are non-negotiable. NEVER skip synthesis and deliver raw worker outputs.**

**Time for 3 workers:** ~15-20 minutes wall-clock
**Phases 3-4 run in parallel** — workers execute while you wait

---

## Key Concepts

### Decomposition Patterns (5 strategies)

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Dimensional Analysis** | Same subject from multiple angles | Security review + performance review + code quality |
| **Multi-Perspective Decision** | One decision from multiple views | Should we migrate to X? (Engineer view + DevOps view + Security view) |
| **Domain Split** | Large codebase by directory/module | `backend/api/` (Worker 1) + `backend/data/` (Worker 2) |
| **Research & Synthesis** | Topic from multiple sources | Research library A + research library B + research library C |
| **Validation & Cross-Check** | Design/spec from multiple angles | Correctness review + feasibility review + completeness review |
| **Independent Implementation** | Build independent modules in parallel | `ingestion.py` (W1) + `cleaning.py` (W2) + `data_models.py` (W3) |

### Output Format (Standardized)

Every worker produces:
```
# Worker N — [Task Name]

## Status
- Current: Complete | Running | Failed

## Findings
[Organized by type/severity with file:line + Severity level]

## Summary
- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N
- INFO: N

## Recommendations
[Actionable fixes for each finding]

## Confidence
[High | Medium | Low] — [what was covered, what might be missed]
```

### Token Efficiency

**Sequential baseline:** N workers × 15k tokens/worker + 5k synthesis = (N × 15k) + 5k

**Parallel actual:** N × 10k (Haiku workers) + 15k (Opus synthesis) = (N × 10k) + 15k

**Example (3 workers):**
- Sequential: (3 × 15k) + 5k = 50k tokens
- Parallel: (3 × 10k) + 15k = 45k tokens
- **Savings: 10% fewer tokens**

Plus 67% faster wall-clock time since workers run simultaneously.

---

## Typical Execution Timeline

```
T+0:00    Spawn 3 workers in background (5 min to all spawned)
T+0:05    Workers 1, 2, 3 start running
T+0:10    Check progress with /worker-monitor
T+0:15    Worker 1 completes (5 min)
T+0:20    All workers complete (longest duration)
T+0:21    Run /result-validator (1 min)
T+0:22    Start synthesis — read all 3 result files (5 min)
T+0:27    Write synthesis report (5 min)
T+0:32    Run /metrics-tracker to log metrics (1 min)
T+0:33    Complete

Total: ~33 minutes wall-clock (vs ~80 minutes if sequential)
```

---

## Monitoring & Troubleshooting

### Live Monitoring
Use the `/worker-monitor` skill to see real-time status:
- Which workers are running/complete/failed
- How long each has been running
- When workers are expected to finish

### Result Validation
Use the `/result-validator` skill before synthesis:
- Checks 8 criteria (file exists, format correct, sections present, etc.)
- Returns GO / GO WITH CAUTION / HOLD
- Prevents invalid results from flowing into synthesis

### Troubleshooting
See `framework/docs/PARALLEL_EXECUTION_DEBUGGING.md` for:
- 10 specific failure scenarios with diagnosis and fixes
- Recovery recipes (re-run single worker, abandon, manual synthesis)
- Prevention checklist (to avoid future failures)

---

## Skills Reference

### `/worker-monitor`
**When:** Periodically during Phase 4 (monitoring)
**What it does:** Polls TaskOutput for each worker, shows live status table, estimates completion time
**Returns:** Simple status summary you can act on

### `/result-validator`
**When:** Before synthesis (Phase 5)
**What it does:** Checks each worker's output file against 8-point criteria
**Returns:** GO / GO WITH CAUTION / HOLD decision

### `/metrics-tracker`
**When:** After synthesis (Phase 7)
**What it does:** Logs execution metadata, calculates token savings, appends to metrics log
**Returns:** Confirmation + updated summary table

---

## Configuration Files

### `parallel-tasks.json` (Execution Registry)

Tracks all worker status in real-time:
```json
{
  "currentExecution": {
    "execution_id": "parallel_20260406_001",
    "task_description": "Security analysis of backend APIs",
    "started_at": "2026-04-06T10:30:00Z",
    "status": "running",
    "workers": [
      {
        "worker_id": 1,
        "task_id": "agent_xyz123",
        "status": "complete",
        "started_at": "2026-04-06T10:30:15Z",
        "completed_at": "2026-04-06T10:35:00Z"
      }
    ]
  }
}
```

**When to update:**
- After spawning each worker (record task_id)
- When a worker completes (record completed_at)
- After synthesis (set status to "complete" and archive to executions array)

### `agent-spawner-config.json` (Configuration)

Default configuration for spawner:
```json
{
  "models": {
    "conductor": "claude-opus-4-6",
    "worker_default": "claude-haiku-4-5",
    "worker_complex": "claude-sonnet-4-6"
  },
  "timeout": {
    "taskTimeoutMs": 1800000,
    "maxWorkers": 4
  }
}
```

**Adjust based on:**
- Task complexity (change worker model for individual workers)
- Time constraints (lower taskTimeoutMs if you need faster feedback)
- Parallelism degree (keep maxWorkers at 2-4 to avoid token saturation)

---

## Global Implementation (For Multiple Projects)

To use this framework across all your projects:

1. **Install globally** (do once):
   ```bash
   # Copy framework to a shared location:
   cp -r _parallel-execution-framework ~/projects/shared/frameworks/parallel-execution

   # Install agents globally:
   cp ~/projects/shared/frameworks/parallel-execution/agents/* ~/.claude/agents/

   # Install skills globally:
   # (Create subdirectories and copy .md files as described above)
   ```

2. **Reference from projects** (per project):
   - Copy `context/parallel-tasks.json` template to your project's `context/`
   - Copy `context/agent-spawner-config.json` template to your project's `context/`
   - Create `context/worker-results/` directory
   - Create `context/parallel-execution-metrics.md` (or symlink the global one)

3. **Document in project CLAUDE.md**:
   ```markdown
   ## Parallel Execution System

   This project uses the parallel execution framework for complex multi-task problems.

   - **Infrastructure:** See `context/` for execution registry and config
   - **Documentation:** `~/projects/shared/frameworks/parallel-execution/docs/`
   - **Agents:** `~/.claude/agents/conductor.md`, `worker-template.md`
   - **Skills:** `/worker-monitor`, `/result-validator`, `/metrics-tracker`

   Before first use, read: `PARALLEL_EXECUTION_RUNBOOK.md`
   ```

---

## Performance Targets

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Token savings % | 15%+ | 5-15% | <5% |
| Worker success rate | 100% | 75-99% | <75% |
| Wall-clock time | N min / (longest worker) | Within 20% | >30% variance |
| Findings per worker | 1-10 | 0 or 11-20 | >20 |

---

## Common Mistakes (Learn From Them)

1. **Not inlining output format** — Workers don't have access to templates. Always inline the format in the prompt. `result-validator` catches this.

2. **Spawning sequentially** — All workers must be spawned in ONE message with `run_in_background: true`. Spawning in separate messages makes them sequential.

3. **Starting synthesis early** — Wait for `/worker-monitor` to confirm all workers are done. Partial synthesis = incomplete report.

4. **Overlapping scopes** — If Worker 1 covers `backend/` and Worker 2 covers `backend/api`, they'll duplicate findings. Use non-overlapping scopes.

5. **Missing independence test** — If Worker B needs Worker A's output, run them sequentially. Parallel with hidden dependencies breaks causality.

---

## Next Steps

1. **Read the runbook:** `framework/docs/PARALLEL_EXECUTION_RUNBOOK.md`
2. **Copy infrastructure files** to your project's `context/`
3. **Install agents & skills** globally (one-time setup)
4. **Pick a complex task** with 3+ independent subtasks
5. **Decompose it** using one of the 5 patterns
6. **Run Phase 0** (should-you-parallelize decision)
7. **Execute** following the 7-phase workflow

---

## Feedback & Improvement

This framework is designed to improve over time. As you run parallel executions:
- Log metrics with `/metrics-tracker` after each execution
- Update `PARALLEL_EXECUTION_DEBUGGING.md` with new failure modes you discover
- Record successful decomposition patterns
- Track token savings and wall-clock improvements

Over time, the framework will give you increasingly accurate estimates and patterns for future tasks.

---

**Version:** 1.0 (2026-04-06)
**Status:** Stable, ready for production use
**Built for:** Claude Code, all projects
