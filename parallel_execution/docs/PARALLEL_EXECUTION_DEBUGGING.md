# Parallel Execution — Debugging Guide

*Last updated: 2026-04-06*

---

## How to Use This Guide

Something went wrong during a parallel execution. Start with **Symptom → Diagnosis** to identify what happened, then follow the linked fix. If you're not sure what went wrong, start with the **Diagnostic Checklist** at the bottom.

---

## Symptom → Diagnosis

### 1. Worker Never Completes

**What you see:** `/worker-monitor` shows a worker stuck in "running" for longer than expected. No completion notification arrives.

**Possible causes:**

| Cause | How to confirm | Fix |
|-------|---------------|-----|
| Worker is actually still running (large scope) | Check elapsed time vs expected. Large scopes (10+ files) can take 10-15 min on Haiku. | Wait. Check again after the timeout period. |
| Worker crashed silently | Elapsed time exceeds `taskTimeoutMs` (30 min default). No result file written. | Mark as `timed_out` in registry. Re-run with same prompt, or proceed without it. |
| Worker is stuck in a read loop | Worker is trying to read a file that doesn't exist or is extremely large, causing retries. | Check the [SCOPE] — did you list a file that doesn't exist? Fix the scope and re-run. |
| Prompt is too large | Worker's prompt exceeded context limits and the agent failed to start. | Shorten the prompt. Reduce [SCOPE] to fewer files. Trim the output format section. |

**Resolution pattern:**
```
1. Check context/parallel-tasks.json for the worker's started_at
2. If elapsed > 30 min → mark as timed_out
3. Check context/worker-results/worker_N_result.md — does it exist? Is it partial?
4. If partial result exists → use what's there, flag incomplete in synthesis
5. If no result → note gap, re-run or proceed without
```

---

### 2. Worker Produces Empty or Malformed Result

**What you see:** Result file exists but is empty, contains only headers, or is missing required sections.

**Possible causes:**

| Cause | How to confirm | Fix |
|-------|---------------|-----|
| Worker crashed mid-write | File has partial content — starts normally, cuts off mid-section | Re-run the worker. The partial output can hint at where it failed. |
| Output format wasn't included in prompt | Worker didn't know the expected format and improvised | Always inline the full output format in the worker prompt. Re-run with format included. |
| Worker scope was empty | All files in [SCOPE] were missing or empty — worker had nothing to analyze | Check the file paths in [SCOPE]. Are they correct? Do they exist? |
| Worker hit token limit | Worker started writing but ran out of output tokens before finishing | Reduce the scope (fewer files) or split into two workers. |

**Resolution pattern:**
```
1. Read the result file — how much is there?
2. If >50% complete → extract findings manually, use in synthesis with low confidence
3. If <50% or missing key sections → re-run the worker
4. Before re-running, check: was the output format in the prompt? Was the scope correct?
```

---

### 3. Summary Counts Don't Match Findings

**What you see:** `/result-validator` reports "Summary says HIGH: 3, found HIGH: 2" or similar mismatches.

**Why it happens:** The worker counted incorrectly, or added/removed findings after writing the summary without updating it.

**Severity:**
- Off by 1-2: Minor. Use the actual count from the findings body.
- Off by 3+: Significant. The worker may have lost track of its own findings. Treat as low reliability.

**Fix:**
```
1. Recount findings manually from the ## Findings section
2. Use the recount in synthesis — ignore the worker's Summary section
3. Note "counts recalibrated" in synthesis metadata
4. No need to re-run — the findings themselves are usually fine
```

---

### 4. Worker Analyzed Files Outside Its Scope

**What you see:** `/result-validator` reports scope violations — findings reference files not in [SCOPE].

**Why it happens:**
- The worker's [CONSTRAINTS] weren't specific enough
- The worker found something interesting in an import/dependency and followed it
- [SCOPE] listed a directory and the worker interpreted it broadly

**Fix:**
```
1. Check findings: are the out-of-scope findings in the main ## Findings section or in ## Out-of-Scope Observations?
2. If in Out-of-Scope → this is correct behavior, worker noted it properly
3. If in main Findings → quarantine them:
   a. Don't include in this worker's synthesis counts
   b. Check if another worker's scope covers those files
   c. If yes → pass the finding to that worker's section in synthesis
   d. If no → include as a separate "Additional Observations" section in synthesis
4. For next execution: tighten [SCOPE] to explicit file paths, not directories
```

---

### 5. Two Workers Produced Contradictory Findings

**What you see:** Worker 1 says function X is safe. Worker 3 says function X has a vulnerability.

**Why it happens:**
- Different analytical lenses see different things — security vs. quality may disagree on what's "safe"
- One worker misread the code
- The code is genuinely ambiguous (could be safe or unsafe depending on context)

**Resolution protocol:**
```
1. Read both findings carefully — what specific claims are they making?
2. Check: are they actually about the same thing? (Same file, same line, same concern?)
   - Often "contradictions" are about different aspects of the same code
3. If genuinely contradictory:
   a. Check evidence quality: finding with file:line + code snippet > general observation
   b. Check confidence: high-confidence worker > low-confidence worker
   c. Check domain match: security worker on security issue > quality worker on security issue
4. If still unresolved: present both in synthesis under ## Contradictions
   - Don't arbitrarily pick a winner
   - Recommend a follow-up investigation
```

---

### 6. Workers Produced Duplicate Findings

**What you see:** Worker 1 and Worker 2 both report the same issue on the same file:line.

**Why it happens:** Overlapping scopes. Both workers were given access to the same files without constraints preventing them from reporting the same type of issue.

**Fix for current execution:**
```
1. Deduplicate in synthesis — keep the finding with more detail/better evidence
2. Note: "Independently confirmed by Workers 1 and 2" — this actually increases confidence
```

**Fix for future executions:**
```
1. Review [SCOPE] assignments — do any files appear in multiple workers?
2. If shared files are intentional (dimensional analysis): add [CONSTRAINTS] like:
   "File X is shared with Worker 2. You analyze ONLY [your dimension]. Do NOT report [their dimension]."
3. If shared files are accidental: fix the scope partitioning
```

---

### 7. Synthesis Context Is Too Large

**What you see:** When reading all worker results for synthesis, the combined content exceeds comfortable context size (approaching 100k+ tokens).

**Why it happens:** Too many workers, or workers produced very detailed results (20+ findings each).

**Fix:**
```
1. Don't read full result files into synthesis context
2. Instead, for each worker:
   a. Read ## Summary (counts only)
   b. Read ## Findings for CRITICAL and HIGH only
   c. Read ## Recommendations (top 3 only)
   d. Skip LOW and INFO findings entirely
3. Write synthesis from this condensed view
4. Reference full worker files for anyone who wants detail:
   "For complete Worker 1 findings, see context/worker-results/worker_1_result.md"
```

**Prevention for future executions:**
```
- Limit workers to 3-4
- Add to [CONSTRAINTS]: "Report maximum 10 findings. Prioritize by severity."
- Use Domain Split pattern instead of Dimensional if you're getting 15+ findings per worker
```

---

### 8. All Workers Failed

**What you see:** Every worker either crashed, timed out, or produced invalid results.

**This is a decomposition problem, not an execution problem.** Don't retry the same decomposition.

**Diagnostic checklist:**
```
1. Were the [SCOPE] file paths correct? (Most common cause — typo in paths)
2. Were the [TASK] descriptions clear and achievable?
3. Was the output format included in every prompt?
4. Was the total prompt size reasonable? (Under 4k tokens per worker)
5. Did you verify files in scope actually exist before spawning?
```

**Recovery:**
```
1. Do NOT re-run the same decomposition
2. Read the error messages or partial outputs — what went wrong?
3. Fix the root cause (usually bad file paths or impossible task descriptions)
4. Re-decompose if needed
5. Re-run with corrected prompts
```

---

### 9. Execution Registry Is Corrupted or Out of Sync

**What you see:** `context/parallel-tasks.json` shows wrong status, missing workers, or stale data from a previous execution.

**Fix:**
```
1. Check: is there a currentExecution that should have been archived?
   - If status is "complete" or "failed" but still in currentExecution → move to executions array
2. Check: do worker statuses match reality?
   - Read each worker's result file to verify
   - Worker has result file → status should be "complete"
   - Worker has no result file → status should be "failed" or "timed_out"
3. Rebuild if necessary:
   a. List files in context/worker-results/
   b. For each worker_N_result.md that exists → status "complete"
   c. For missing files → status "failed"
   d. Update counts accordingly
```

**Prevention:**
```
- Always update registry immediately after each worker status change
- Don't modify registry in parallel (only Conductor writes to it)
- After synthesis, always archive currentExecution to executions array
```

---

### 10. Worker Produced Findings But Zero Recommendations

**What you see:** Worker has findings in the body but the Recommendations section says "No remediation needed" or is empty.

**Why it happens:**
- Worker found issues but wasn't sure how to fix them
- Worker confused INFO-level observations with findings that need fixes
- [TASK] description asked for analysis only, not remediation

**Fix:**
```
1. If findings are MEDIUM+ severity → they need recommendations
2. In synthesis, generate recommendations yourself based on the findings
3. Note: "Recommendations generated during synthesis — Worker N did not provide fixes"
4. For future executions: explicitly state in [TASK]:
   "For each finding, provide a specific fix with file:line and corrected code."
```

---

## Diagnostic Checklist

When something goes wrong and you're not sure which symptom above applies, run through this:

```
STEP 1: Check the registry
  → Read context/parallel-tasks.json
  → Is there a currentExecution? What's its status?
  → How many workers are complete/failed/running?

STEP 2: Check worker result files
  → ls context/worker-results/
  → For each expected worker: does the file exist? Is it non-empty?
  → Read first 20 lines of each file — does it have the right format?

STEP 3: Check for obvious prompt issues
  → Re-read each worker's task description (from your conversation history)
  → Are file paths in [SCOPE] correct?
  → Is the output format included inline?
  → Are [CONSTRAINTS] explicit enough to prevent overlap?

STEP 4: Check timing
  → When was the execution started? (parallel-tasks.json → started_at)
  → How long has it been running?
  → Are any workers past the timeout threshold?

STEP 5: Check for partial results
  → Even failed workers may have written partial results
  → Read any existing worker result files for clues about what went wrong
```

---

## Prevention Checklist

Run this before every execution to avoid the most common failures:

- [ ] All file paths in [SCOPE] verified to exist (`ls` or `Glob` before spawning)
- [ ] Output format is inlined in every worker prompt (not just referenced)
- [ ] [CONSTRAINTS] explicitly prevent overlap between workers
- [ ] Worker count is 2-4 (not 5+)
- [ ] Each worker prompt is under 4k tokens
- [ ] `context/parallel-tasks.json` has no stale `currentExecution` from a previous run
- [ ] `context/worker-results/` directory exists and is writable

---

## Recovery Recipes

### Recipe: Re-run a single failed worker

```
1. Read the failed worker's entry from parallel-tasks.json
2. Get its original prompt from conversation history
3. Fix any issues in the prompt (bad file paths, missing format, etc.)
4. Spawn:
   Agent(model="haiku", prompt="[fixed prompt]", run_in_background=true)
5. Update registry with new task_id
6. Wait for completion
7. Validate result
8. Continue to synthesis
```

### Recipe: Abandon and restart entire execution

```
1. In parallel-tasks.json:
   - Set currentExecution.status to "abandoned"
   - Move to executions array
   - Set currentExecution to null
2. Delete all files in context/worker-results/
3. Re-decompose the task (fix whatever caused the failure)
4. Start fresh from Phase 2 of the runbook
```

### Recipe: Manual synthesis from partial results

When some workers succeeded and some failed, and re-running isn't worth it:

```
1. Read all available worker result files
2. Note which workers are missing and what they would have covered
3. Write synthesis from available results
4. Add explicit section:
   ## Coverage Gaps
   - Worker N ([task]) — failed/timed out. [Domain] was not analyzed.
   - Recommend: [standalone follow-up | accept the gap | manual review]
5. Lower overall confidence level to Medium or Low
6. Log metrics with outcome: "partial"
```

### Recipe: Post-mortem after a bad execution

After a failed or degraded execution, log what happened for future improvement:

```
1. In docs/TASK_DECOMPOSITION.md → Failed Decompositions table:
   | Date | Task | Problem | Fix Applied |
   | YYYY-MM-DD | [task] | [what went wrong] | [what you'll do differently] |

2. In context/parallel-execution-metrics.md:
   - Log the execution with outcome: "failed" or "degraded"
   - Note the specific failure mode in the Notes section

3. If the failure reveals a pattern:
   - Add it to this debugging guide under the appropriate symptom
   - Update the Prevention Checklist if a new pre-check would have caught it
```
