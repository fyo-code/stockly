---
id: worker-monitor
name: worker-monitor
description: "Monitors active parallel agent workers. Reads current execution from parallel-tasks.json, checks each worker's TaskOutput status, updates the registry, and returns a live status summary."
category: parallel-execution
risk: safe
source: project
date_added: "2026-04-06"
---

## When to Use

Use this skill when a parallel execution is running (status: "running" in `context/parallel-tasks.json`) and you need to check how many workers have completed, which are still running, and whether any have failed.

Call this after receiving a background agent completion notification to update the registry and check if all workers are done.

---

# Worker Monitor

## Purpose

Poll all active background workers for their current status, update `context/parallel-tasks.json` to reflect current state, and return a clear summary of execution progress.

This skill does NOT synthesize results. It only tracks status.

---

## Instructions

### Step 1: Read Current Execution State

Read `context/parallel-tasks.json`. Extract:
- `currentExecution.execution_id`
- `currentExecution.total_workers`
- `currentExecution.workers_complete`
- `currentExecution.workers` — array of worker objects with `task_id` and `status`

If `currentExecution` is null, report: "No active execution found. Nothing to monitor."

### Step 2: Check Each Worker

For every worker in `currentExecution.workers` where status is NOT "complete" or "failed":

Use `TaskOutput` to check current status. The tool returns the agent's completion status.

Map TaskOutput results to worker statuses:
- Agent returned output → status: "complete"
- Agent still running → status: "running"
- Agent errored → status: "failed", log error message

### Step 3: Update Registry

After checking all workers, update `context/parallel-tasks.json`:

For each worker that changed status:
```json
{
  "worker_id": N,
  "status": "complete",
  "completed_at": "ISO_TIMESTAMP"
}
```

Update top-level counters:
- `workers_complete` — count of workers with status "complete"
- `workers_failed` — count of workers with status "failed"
- `metadata.lastUpdated` — current timestamp

If all workers are complete or failed, update execution status:
```json
"status": "synthesis-ready"
```

### Step 4: Report Status

Output a status table:

```
## Execution: [execution_id]
Started: [started_at]
Elapsed: [HH:MM:SS since started_at]

| Worker | Task | Status | Duration |
|--------|------|--------|----------|
| 1 | Security Analysis | ✓ Complete | 4m 37s |
| 2 | Performance Review | ⟳ Running | 6m 12s |
| 3 | Code Quality | ✗ Failed | — |

Progress: 1/3 complete, 1 running, 1 failed

Next action: [one of]
  - "Waiting for N workers to complete."
  - "All workers complete. Ready for synthesis."
  - "All workers finished (N failed). Synthesis will cover N-1 dimensions."
```

---

## Output Contract

- Updates `context/parallel-tasks.json` with current statuses
- Prints a status table to the conversation
- Returns one of three next-action states:
  - WAITING — some workers still running
  - READY — all workers complete or failed, proceed to synthesis
  - EMPTY — no active execution found

---

## Error Handling

**Worker task_id not found:** Mark status as "failed", note: "task_id [id] not found — worker may have been terminated externally."

**parallel-tasks.json missing or malformed:** Report the error and stop. Do not attempt to continue without registry state.

**All workers failed:** Report this explicitly. Do not proceed to synthesis. Return: "All N workers failed. Recommend re-examining task descriptions and re-running decomposition."
