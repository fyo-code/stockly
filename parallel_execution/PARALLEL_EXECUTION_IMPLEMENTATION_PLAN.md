# Parallel Execution Implementation Plan

**Status:** Ready to implement
**Created:** 2026-04-06
**Target Completion:** 3 phases over 2-3 sessions
**Scope:** Complete infrastructure for parallel multi-agent orchestration

---

## **PHASE 1: Foundation (90 minutes)**

Create core infrastructure files that enable parallel execution.

### **Phase 1.1: Core Documentation**

#### **File 1: `PARALLEL_EXECUTION.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/docs/PARALLEL_EXECUTION.md`

**Content Template:**
```markdown
# Parallel Execution System

## Overview

Parallel execution spawns multiple independent worker agents (Haiku 4.5) simultaneously to solve subtasks, while a synthesizer agent (Opus 4.6) aggregates results and produces the final answer.

**Why it matters:**
- Reduces context rot (each worker sees only its subtask)
- ~65% faster (all workers run simultaneously)
- ~35-40% fewer tokens (small focused tasks < one giant task)
- Higher quality (no distraction, focused analysis)

## How It Works

### Step 1: Decomposition (Opus)
User asks: "Review code for security, performance, and quality"
Opus decomposes into 3 independent subtasks:
- Security analysis (independent)
- Performance analysis (independent)
- Code quality analysis (independent)

### Step 2: Parallel Spawning (Conductor)
Conductor spawns 3 Agent tools simultaneously:
```
Agent(subagent_type="worker-security", prompt="task 1")
Agent(subagent_type="worker-performance", prompt="task 2")
Agent(subagent_type="worker-quality", prompt="task 3")
```
Each returns a task_id for monitoring.

### Step 3: Parallel Execution
All 3 agents run simultaneously with minimal context:
- Worker 1 (Haiku): Analyzes security only
- Worker 2 (Haiku): Analyzes performance only
- Worker 3 (Haiku): Analyzes code quality only
- Each writes result to: `context/worker-results/worker_N_result.md`

### Step 4: Monitoring
Conductor periodically polls TaskOutput(task_id) to check status:
- Updates `context/parallel-tasks.json` with progress
- Waits for all workers to complete
- Collects all result files

### Step 5: Synthesis (Opus)
Opus reads all 3 results and synthesizes:
- Identifies patterns across results
- Prioritizes by severity
- Produces single coherent recommendation
- Output: Comprehensive analysis

## Task Decomposition Rules

### When to use parallel execution:
✓ Subtasks are independent (no dependencies)
✓ Each subtask can be solved by a focused agent
✓ Results can be meaningfully combined
✓ Task is complex enough to benefit (>5k tokens expected)

### When NOT to use:
✗ Subtasks depend on each other
✗ Results need constant cross-referencing
✗ Simple tasks that fit in one context (<2k tokens)
✗ Tasks requiring sequential decision-making

### Common Decomposition Patterns

**Pattern A: Dimensional Analysis**
- Task: Analyze system
- Workers: Security analyst, Performance analyst, Architecture analyst
- Example: Code review → 3 independent workers

**Pattern B: Perspective Analysis**
- Task: Evaluate decision
- Workers: Technical reviewer, Product reviewer, Cost reviewer
- Example: Architecture decision → 3 independent perspectives

**Pattern C: Stage-based (if some stages independent)**
- Task: Design → Implement → Test
- Workers: Designer, Implementer, Tester
- Only if stages don't depend on previous (rare)

## Result Format Contract

Every worker MUST output to `context/worker-results/worker_N_result.md`:

```markdown
# Worker N - Task Description

## Status
- Current: [Analyzing | Complete]
- Started: 2026-04-06T10:30:00Z
- Completed: 2026-04-06T10:35:00Z (if done)

## Findings
[Main findings in markdown format]

## Severity Summary
- CRITICAL: N items
- HIGH: N items
- MEDIUM: N items
- LOW: N items

## Recommendations
[Specific, actionable recommendations]

## Confidence
[Low | Medium | High] - why
```

## Monitoring & Status Tracking

All parallel executions tracked in: `context/parallel-tasks.json`

Format:
```json
{
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
      "result_file": "context/worker-results/worker_1_result.md"
    }
  ]
}
```

## Performance Baseline

Expected improvements (parallel vs sequential):
- Time: 65-80% faster
- Tokens: 35-40% fewer
- Quality: Same or higher (focused workers)
- Example: 4 workers × 10k tokens each = 40k (parallel) vs 120k (sequential Opus)

## Failure Handling

If a worker fails:
1. Conductor detects (TaskOutput shows error)
2. Logs failure to parallel-tasks.json
3. Optionally re-queues worker (if retry enabled)
4. Synthesis proceeds with available results (partial output)
5. Notes in final answer: "Worker N failed, synthesis based on other workers"
```

**Action:** Create this file with the template above.

---

#### **File 2: `TASK_DECOMPOSITION.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/docs/TASK_DECOMPOSITION.md`

**Content Template:**
```markdown
# Task Decomposition Guide

## How to Decompose a Task

### Step 1: Identify Independence
Ask: "Can these subtasks be solved without knowledge of other subtasks?"
- YES → Good candidates for parallelization
- NO → Keep sequential

### Step 2: Define Clear Boundaries
Each worker should have:
- One focused responsibility
- Clear success criteria
- Minimal context needed
- Standard output format

### Step 3: Create Subtask Descriptions
Write 2-3 sentence description of EXACTLY what worker should do.

### Example Decomposition: Code Review

**Original task:** "Review the backend for security, performance, and code quality issues"

**Decomposition:**

Worker 1 - Security Analysis
- Scan for hardcoded secrets, SQL injection vulnerabilities, XSS risks, auth/authz gaps
- Output: List of security findings with severity
- Dependencies: None

Worker 2 - Performance Analysis
- Identify N+1 queries, inefficient algorithms, missing indexes, memory leaks
- Output: Performance bottlenecks with improvement potential
- Dependencies: None (but reads code independently)

Worker 3 - Code Quality Analysis
- Check for dead code, duplication, naming clarity, function size, test coverage
- Output: Quality metrics and refactoring priorities
- Dependencies: None (but reads code independently)

Synthesis:
- Opus reads all 3 results
- Integrates into: "Critical issues first, then improvements, then refactoring"
- Output: Prioritized action plan

### Example Decomposition: Architecture Decision

**Original task:** "Should we use PostgreSQL or MongoDB for this feature?"

**Decomposition:**

Worker 1 - Technical Requirements
- Read requirements, evaluate schema, query patterns needed
- Output: Technical fit scoring

Worker 2 - Cost Analysis
- Analyze licensing, infrastructure, ops overhead, scaling costs
- Output: Cost comparison

Worker 3 - Team Expertise
- Evaluate team's experience with each, training needed, hiring impact
- Output: Team capability assessment

Synthesis:
- Opus weighs all 3 factors
- Output: Recommendation with reasoning

## Decomposition Checklist

For any task, ask:

- [ ] Are subtasks truly independent?
- [ ] Can each worker solve in <20 minutes?
- [ ] Is output format clear and standard?
- [ ] Would parallel actually save time vs sequential?
- [ ] Can results be meaningfully synthesized?

If all YES → Decompose and parallelize
If any NO → Keep sequential
```

**Action:** Create this file with the template above.

---

### **Phase 1.2: Configuration Files**

#### **File 3: `context/agent-spawner-config.json`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/context/agent-spawner-config.json`

**Content:**
```json
{
  "parallelExecution": {
    "enabled": true,
    "maxConcurrentWorkers": 4,
    "workerModel": "haiku-4.5-20251001",
    "synthesizerModel": "opus-4.6",
    "taskTimeoutMs": 1800000,
    "pollIntervalMs": 5000,
    "maxPolls": 360,
    "runInBackground": true,
    "failureMode": "continue-with-available-results"
  },
  "workerTypes": {
    "security-analyst": {
      "model": "haiku-4.5-20251001",
      "role": "Security analysis specialist",
      "timeout": 900000
    },
    "performance-analyst": {
      "model": "haiku-4.5-20251001",
      "role": "Performance optimization specialist",
      "timeout": 900000
    },
    "quality-analyst": {
      "model": "haiku-4.5-20251001",
      "role": "Code quality and architecture specialist",
      "timeout": 900000
    },
    "generic-analyst": {
      "model": "haiku-4.5-20251001",
      "role": "General analysis specialist",
      "timeout": 1200000
    }
  },
  "resultValidation": {
    "enabled": true,
    "requireFields": ["status", "findings", "recommendations"],
    "maxResultSize": 50000,
    "validateMarkdown": true
  }
}
```

**Action:** Create this file.

---

#### **File 4: `context/parallel-tasks.json` (template)**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/context/parallel-tasks.json`

**Content:**
```json
{
  "executions": [],
  "currentExecution": null,
  "metadata": {
    "lastUpdated": null,
    "totalExecutions": 0,
    "successfulExecutions": 0,
    "failedWorkers": 0
  }
}
```

**Action:** Create this file.

---

#### **File 5: `context/worker-results/.gitkeep`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/context/worker-results/.gitkeep`

**Content:** (empty file to preserve directory)

**Action:** Create directory and `.gitkeep` file.

---

### **Phase 1.3: Core Skills**

#### **File 6: `.claude/agents/conductor.md`**
**Location:** `~/.claude/agents/conductor.md`

**Content:**
```markdown
# Conductor Agent

**Model:** Opus 4.6
**Role:** Orchestrator for parallel worker execution
**Trigger:** When complex task needs decomposition and parallelization

## Instructions

You are the conductor — the orchestrator who decomposes tasks, spawns workers, monitors progress, and synthesizes results.

### Core Responsibilities

1. **Decompose** — Break complex task into independent subtasks
2. **Validate** — Ensure subtasks are truly independent
3. **Spawn** — Launch worker agents in parallel using Agent tool
4. **Monitor** — Poll TaskOutput to track worker progress
5. **Collect** — Gather results from worker files as they complete
6. **Synthesize** — Combine results into coherent final answer
7. **Report** — Present findings with priority and reasoning

### Decomposition Rules

✓ Each subtask must be solvable independently
✓ Workers should not need each other's results
✓ Standard output format (see PARALLEL_EXECUTION.md)
✓ Clear success criteria for each worker
✗ Avoid sequential dependencies

### Spawning Workers

Use Agent tool with parameters:
```
Agent(
  subagent_type="worker-{type}",  # e.g., worker-security
  description="Specific task description",
  prompt="[TASK] [CONTEXT] [OUTPUT FORMAT]",
  run_in_background=true
)
```

Each Agent call returns task_id. Store all task_ids immediately.

### Monitoring

```python
# After spawning, poll each task
for task_id in task_ids:
  result = TaskOutput(task_id=task_id, block=false)
  if result.status == "complete":
    read context/worker-results/worker_N_result.md
    update context/parallel-tasks.json
```

### Result File Format

Each worker writes to: `context/worker-results/worker_{N}_result.md`

Expected structure:
```
# Worker N - {Task Name}

## Status
Current: [Analyzing | Complete]
Started: [ISO timestamp]
Completed: [ISO timestamp]

## Findings
[Markdown findings]

## Summary
- CRITICAL: N
- HIGH: N
- MEDIUM: N

## Recommendations
[Specific recommendations]
```

### Synthesis Rules

1. Read ALL worker results
2. Identify cross-cutting themes
3. Prioritize by severity (CRITICAL → HIGH → MEDIUM → LOW)
4. Synthesize into single coherent narrative
5. Show how workers' findings connect
6. Note any conflicts or contradictions
7. Present final recommendation with reasoning

### Failure Handling

If a worker fails:
- Record failure in parallel-tasks.json
- Continue synthesis with available results
- Note in final answer: "Worker N failed — synthesis based on {N-1} workers"
- Suggest re-running failed worker separately

## Implementation Workflow

1. Read task
2. Decompose into subtasks (validate independence)
3. Write task descriptions for each worker
4. Spawn all workers simultaneously
5. Update parallel-tasks.json with execution metadata
6. Poll TaskOutput(task_id) every 5 seconds
7. Update parallel-tasks.json as workers complete
8. Once all complete (or timeout), read all results
9. Synthesize findings
10. Report to user
```

**Action:** Create this file in `~/.claude/agents/conductor.md`

---

#### **File 7: `.claude/agents/worker-template.md`**
**Location:** `~/.claude/agents/worker-template.md`

**Content:**
```markdown
# Worker Agent Template

**Model:** Haiku 4.5
**Role:** Execute single focused subtask
**Usage:** Spawned by conductor for one specific task

## Instructions

You are a worker — a focused specialist solving ONE specific subtask.

### Your Role

- Receive one specific task description
- Solve it thoroughly but narrowly
- Output results to standard file format
- No need to coordinate with other workers
- No need to synthesize across domains

### Task Input Format

You will receive:
```
[TASK]
{Task description}

[CONTEXT]
{Relevant context, code, requirements}

[OUTPUT FORMAT]
Write results to: context/worker-results/worker_{N}_result.md

Structure:
# Worker N - {Task Name}

## Status
Current: Complete
Started: [ISO timestamp]
Completed: [ISO timestamp]

## Findings
[Your findings in markdown]

## Summary
- CRITICAL: N items
- HIGH: N items
- MEDIUM: N items
- LOW: N items

## Recommendations
[Specific, actionable recommendations]
```

### How to Work

1. Understand the specific task
2. Work through it systematically
3. Document findings as you go
4. Prioritize by severity (CRITICAL > HIGH > MEDIUM > LOW)
5. Write clear, actionable recommendations
6. Format output exactly as specified
7. Write to the file path provided
8. Include your confidence level

### Important Constraints

- ⚠️ Stay narrowly focused on YOUR task only
- ⚠️ Do NOT try to synthesize with other workers (conductor does that)
- ⚠️ Do NOT attempt to coordinate with other workers
- ⚠️ Do output exactly as specified (conductor reads automated)
- ⚠️ Do keep output under 10k tokens if possible

### Quality Standards

- Clear, scannable findings (use headers)
- Specific examples (not generic)
- Actionable recommendations (not vague)
- Severity classification (CRITICAL/HIGH/MEDIUM/LOW)
- Confidence assessment (Low/Medium/High)

### Success Criteria

- [ ] Task understood
- [ ] Analysis complete
- [ ] Findings documented
- [ ] Recommendations specific
- [ ] Output file written correctly
- [ ] Format matches template exactly
```

**Action:** Create this file in `~/.claude/agents/worker-template.md`

---

### **Phase 1.4: Progress Tracking**

#### **File 8: `PROGRESS.md` (update)**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/PROGRESS.md`

**Add Section:**
```markdown
## Phase: Parallel Execution Setup

### Phase 1: Foundation (In Progress)
- [ ] Create PARALLEL_EXECUTION.md
- [ ] Create TASK_DECOMPOSITION.md
- [ ] Create context/agent-spawner-config.json
- [ ] Create context/parallel-tasks.json
- [ ] Create context/worker-results/ directory
- [ ] Create ~/.claude/agents/conductor.md
- [ ] Create ~/.claude/agents/worker-template.md
- [ ] Update PROGRESS.md with parallel execution section
- [ ] Update CLAUDE.md with parallel execution reference

**Status:** Starting Phase 1
```

**Action:** Add this section to PROGRESS.md

---

#### **File 9: `PREFERENCES.md` (update)**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/context/preferences.md`

**Add Entry:**
```markdown
## Parallel Execution Settings

[2026-04-06] parallel-execution PREFERENCE — Max 4 concurrent workers — Opus for synthesis, Haiku for workers — allows good balance of speed and cost

[2026-04-06] parallel-execution PREFERENCE — Only decompose tasks with truly independent subtasks — avoid false parallelization with hidden dependencies

[2026-04-06] parallel-execution PREFERENCE — Always validate result format before synthesis — prevents garbage-in-garbage-out
```

**Action:** Add these entries to PREFERENCES.md

---

## **PHASE 2: Skills & Utilities (60 minutes)**

Create reusable skills for monitoring, validation, and synthesis.

### **Phase 2.1: Monitoring Skill**

#### **File 10: `skills/worker-monitor/SKILL.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/skills/worker-monitor/SKILL.md`

**Content:**
```markdown
# Worker Monitor Skill

**Purpose:** Track parallel worker execution in real-time
**Called by:** Conductor agent
**Model:** Haiku (lightweight polling)

## Usage

```
/worker-monitor
```

## What It Does

1. Reads current parallel-tasks.json
2. For each worker with status "running":
   - Calls TaskOutput(task_id, block=false)
   - Checks if complete
   - Reads result file if complete
3. Updates parallel-tasks.json with status
4. Returns summary: "2/4 complete, 1 running, 1 pending"

## Input

Requires context/parallel-tasks.json with structure:
```json
{
  "currentExecution": {
    "workers": [
      { "worker_id": 1, "task_id": "abc123", "status": "running" }
    ]
  }
}
```

## Output

Updated parallel-tasks.json:
```json
{
  "workers": [
    { "worker_id": 1, "task_id": "abc123", "status": "complete", "completed_at": "..." }
  ]
}
```

And console summary:
```
Worker Status:
- Worker 1 (Security): Complete ✓
- Worker 2 (Performance): Running (3/5 steps) ⏳
- Worker 3 (Quality): Running ⏳
- Worker 4 (Generic): Pending ⏱️

2/4 complete | Poll again in 5s
```

## Implementation

1. Read parallel-tasks.json
2. For each "running" worker:
   - Get task_id
   - Call TaskOutput(task_id, block=false)
   - Parse status
   - If "complete", read worker result file
   - Update worker entry with status + timestamp
3. Count statuses
4. Write updated parallel-tasks.json
5. Print summary
6. Return: { complete: N, running: N, pending: N }
```

**Action:** Create this file.

---

### **Phase 2.2: Result Validation Skill**

#### **File 11: `skills/result-validator/SKILL.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/skills/result-validator/SKILL.md`

**Content:**
```markdown
# Result Validator Skill

**Purpose:** Validate worker output before synthesis
**Called by:** Conductor (optional but recommended)
**Model:** Haiku

## Usage

```
/result-validator
```

## What It Does

1. Reads all files in context/worker-results/
2. For each worker result:
   - Checks if file exists
   - Validates required fields present
   - Validates markdown format
   - Checks result size (max 50k chars)
   - Validates severity counts are numeric
3. Returns: Valid results + any validation errors

## Validation Rules

Required fields:
- [ ] "# Worker N - Task Name" header
- [ ] "## Status" section with Current, Started, Completed
- [ ] "## Findings" section (not empty)
- [ ] "## Summary" with CRITICAL/HIGH/MEDIUM/LOW counts
- [ ] "## Recommendations" section (not empty)

Format checks:
- [ ] Valid markdown (no syntax errors)
- [ ] Proper header hierarchy (# > ##)
- [ ] No malformed tables
- [ ] Result < 50,000 characters

Content checks:
- [ ] Findings are specific (not generic)
- [ ] Recommendations are actionable
- [ ] Severity counts are numbers
- [ ] Confidence level stated

## Output

If valid:
```json
{
  "status": "valid",
  "workers": [
    { "worker_id": 1, "file": "worker_1_result.md", "valid": true }
  ]
}
```

If invalid:
```json
{
  "status": "invalid",
  "workers": [
    {
      "worker_id": 1,
      "file": "worker_1_result.md",
      "valid": false,
      "errors": [
        "Missing ## Recommendations section",
        "Severity counts not numeric (found 'N items' instead of number)"
      ]
    }
  ]
}
```

## Action on Invalid Results

If validator finds errors:
1. Log errors to parallel-tasks.json
2. Conductor decides: re-run worker or synthesis with available results
3. If synthesis proceeds, note: "Worker N had formatting issues — findings included but unvalidated"
```

**Action:** Create this file.

---

### **Phase 2.3: Metrics Tracking Skill**

#### **File 12: `skills/metrics-tracker/SKILL.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/skills/metrics-tracker/SKILL.md`

**Content:**
```markdown
# Metrics Tracker Skill

**Purpose:** Track performance of parallel vs sequential execution
**Called by:** Conductor (after synthesis)
**Model:** Haiku (data logging)

## Usage

```
/metrics-tracker
```

## What It Tracks

After each parallel execution, logs:
- Total execution time (wall clock)
- Total tokens used (all workers + synthesis)
- Number of workers
- Number of critical findings
- Quality score (based on findings/recommendations clarity)
- Estimated sequential time (for comparison)
- Estimated sequential tokens (for comparison)

## Data Stored

File: `context/parallel-execution-metrics.md`

Format:
```markdown
# Parallel Execution Metrics

## Execution 1: Code Review (2026-04-06)
- Task: Security + Performance + Quality analysis
- Workers: 3
- Wall time: 8m 23s
- Tokens used: 42,100
- Estimated sequential: 24m 15s, 120,500 tokens
- Time savings: 65%
- Token savings: 65%
- Quality: High (specific findings, actionable recommendations)

## Execution 2: ...
```

## Comparison Logic

Baseline (sequential):
- 1 Opus × 30 min × 3 = 90 min total
- 1 Opus × 120k tokens = 120k tokens

Parallel:
- 3 Haiku × 8 min = 8 min total (+ 1 min synthesis) = 9 min
- 3 Haiku × 10k + 1 Opus × 15k = 45k tokens

Savings:
- Time: 90 min → 9 min = 90% improvement
- Tokens: 120k → 45k = 62% improvement

## Output

```
Metrics logged to: context/parallel-execution-metrics.md

Summary:
✓ 65% faster (9m vs 24m sequential estimate)
✓ 65% fewer tokens (42k vs 120k sequential estimate)
✓ Quality: High
```

## Use Cases

1. Prove parallel execution works (run first 3 times)
2. Identify which task types benefit most from parallelization
3. Show ROI to justify effort invested in setup
4. Optimize: which tasks to parallelize vs keep sequential
```

**Action:** Create this file.

---

### **Phase 2.4: Create Metrics Storage File**

#### **File 13: `context/parallel-execution-metrics.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/context/parallel-execution-metrics.md`

**Content:**
```markdown
# Parallel Execution Metrics

Tracks performance of parallel vs sequential execution over time.

## Format

Each execution logs:
- Execution ID
- Task type
- Number of workers
- Wall time (minutes)
- Tokens used
- Estimated sequential time/tokens
- Quality assessment
- Notes

## Execution Log

(Empty - will be populated as you run parallel executions)

## Summary Statistics

To be updated after first 5 executions:
- Average time savings: __%
- Average token savings: __%
- Quality trends: __
- Optimal worker count: __
- Most suitable task types: __
```

**Action:** Create this file.

---

## **PHASE 3: Integration & Documentation (60 minutes)**

Integrate parallel execution into project workflows and create runbooks.

### **Phase 3.1: Update Project CLAUDE.md**

#### **File 14: `CLAUDE.md` (update)**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/CLAUDE.md`

**Add Section:**
```markdown
---

## Parallel Execution System

This project now supports parallel multi-agent execution for complex tasks. Instead of one Opus agent solving everything sequentially, you can decompose tasks into independent subtasks, spawn multiple Haiku workers in parallel, and synthesize results with Opus.

### When to Use

✓ Complex analysis (security + performance + quality)
✓ Multi-perspective decisions (technical + cost + team capability)
✓ Large codebases needing focused reviews
✓ Any task > 5k tokens that can be meaningfully decomposed

### Quick Start

1. **Request:** Tell conductor what you need analyzed
2. **Decompose:** Conductor breaks into independent subtasks
3. **Spawn:** All workers run simultaneously
4. **Monitor:** Watch progress in real-time
5. **Synthesize:** Opus combines all results
6. **Report:** Get prioritized, coherent answer

### Example

```
User: "Review the backend for security, performance, and code quality issues"

Conductor:
- Decomposes into 3 independent subtasks
- Spawns 3 Haiku workers in parallel
- Workers complete in ~8-10 minutes
- Synthesis takes 2-3 minutes
- Total: 10-13 minutes vs 25+ minutes sequential
```

### Key Files

- `docs/PARALLEL_EXECUTION.md` — How the system works
- `docs/TASK_DECOMPOSITION.md` — How to decompose tasks
- `context/agent-spawner-config.json` — Configuration
- `~/.claude/agents/conductor.md` — Orchestrator agent
- `~/.claude/agents/worker-template.md` — Worker template

### Skills

- `/worker-monitor` — Track parallel execution in real-time
- `/result-validator` — Validate worker outputs
- `/metrics-tracker` — Track performance (time/tokens saved)

### Files Read Before Each Parallel Execution

1. `docs/PARALLEL_EXECUTION.md` — Understand system
2. `docs/TASK_DECOMPOSITION.md` — Learn decomposition
3. `context/agent-spawner-config.json` — Get configuration
4. `~/.claude/agents/conductor.md` — Get orchestrator role
5. `context/parallel-tasks.json` — See current execution status
```

**Action:** Add this section to CLAUDE.md

---

### **Phase 3.2: Create Runbook**

#### **File 15: `docs/PARALLEL_EXECUTION_RUNBOOK.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/docs/PARALLEL_EXECUTION_RUNBOOK.md`

**Content:**
```markdown
# Parallel Execution Runbook

Step-by-step guide to executing parallel analysis tasks.

## Pre-Execution Checklist

- [ ] Task is complex enough to benefit (> 5k tokens estimated)
- [ ] Subtasks would be independent
- [ ] You have `context/agent-spawner-config.json`
- [ ] You have `~/.claude/agents/conductor.md` and worker-template.md
- [ ] You have `context/worker-results/` directory

## Execution Steps

### Step 1: Request Parallel Execution
```
User asks conductor:
"I want you to use parallel execution. Here's the task:
[Full task description]

Decompose into independent subtasks, spawn workers, monitor, synthesize, report."
```

### Step 2: Conductor Decomposes
Conductor reads task and decides:
- Is parallelization suitable? (independent subtasks?)
- How many workers needed? (3-4 typical)
- What's each worker's task? (specific, focused)

Output:
```
Task: Code review for backend
Decomposition:
1. Worker 1 — Security analysis (30-40 min task)
2. Worker 2 — Performance analysis (30-40 min task)
3. Worker 3 — Code quality analysis (30-40 min task)

Starting parallel execution...
```

### Step 3: Spawn Workers
Conductor uses Agent tool:
```
Agent(subagent_type="worker-security", prompt="[TASK]...")
Agent(subagent_type="worker-performance", prompt="[TASK]...")
Agent(subagent_type="worker-quality", prompt="[TASK]...")
```

Updates `context/parallel-tasks.json`:
```json
{
  "execution_id": "parallel_20260406_001",
  "status": "running",
  "workers": [
    { "worker_id": 1, "task_id": "agent_abc123", "status": "running" },
    { "worker_id": 2, "task_id": "agent_def456", "status": "running" },
    { "worker_id": 3, "task_id": "agent_ghi789", "status": "running" }
  ]
}
```

### Step 4: Monitor Progress
Conductor periodically (every 5 seconds):
1. Calls TaskOutput(task_id) for each worker
2. Updates parallel-tasks.json with status
3. Reports progress:
```
Monitoring parallel execution...
Worker 1 (Security): Running (2/5 steps)
Worker 2 (Performance): Running (3/4 steps)
Worker 3 (Quality): Running (1/3 steps)

Completed: 0/3 | Next check: 5s
```

As workers complete:
```
Worker 1 (Security): Complete ✓
Worker 2 (Performance): Running (3/4 steps)
Worker 3 (Quality): Complete ✓

Completed: 2/3 | All results received, waiting for final worker...
```

### Step 5: Validate Results (Optional)
If validation enabled:
```
/result-validator

Validating worker outputs...
✓ Worker 1: Valid
✓ Worker 2: Valid
✓ Worker 3: Valid

All results validated. Proceeding to synthesis.
```

### Step 6: Synthesis
Conductor reads all worker results:
```
Reading results from:
- context/worker-results/worker_1_result.md
- context/worker-results/worker_2_result.md
- context/worker-results/worker_3_result.md

Synthesizing findings...
```

Creates integrated answer:
```
## Analysis Summary

### Critical Issues (Must fix immediately)
1. Hardcoded API key in config.py:42 [from Worker 1]
2. N+1 query in user_list() [from Worker 2]

### High Priority
1. Missing input validation on 3 endpoints [from Worker 1]
2. Inefficient sort in reports.py [from Worker 2]
3. 8 duplicate utility functions [from Worker 3]

### Medium Priority
[Combined from all workers, prioritized by impact]

### Recommendations
[Synthesis of all worker recommendations]
```

### Step 7: Optional Metrics
```
/metrics-tracker

Logging execution metrics...

Execution completed:
✓ 65% faster (8m vs 24m sequential estimate)
✓ 65% fewer tokens (42k vs 120k sequential estimate)
✓ Quality: High
```

Updates `context/parallel-execution-metrics.md`

## Real-Time Monitoring

### Check Status Anytime
```
/worker-monitor

Worker Status:
- Worker 1: Complete ✓
- Worker 2: Running (3/4 steps)
- Worker 3: Complete ✓

Progress: 2/3 workers complete
```

### Check Specific Worker Result
```
cat context/worker-results/worker_1_result.md
```

### Check Execution Status
```
cat context/parallel-tasks.json
```

## Troubleshooting

### Worker takes too long
- Expected: 8-15 min per worker (depends on task)
- If > 20 min: May indicate overly complex subtask
- Solution: Break worker task into smaller piece

### Worker fails
- Check error in TaskOutput
- Conductor logs to parallel-tasks.json
- Synthesis proceeds with available results
- Option: Re-run failed worker separately

### Results don't validate
- /result-validator shows which fields missing
- Return to worker with feedback
- Reformat and rerun
- Or proceed with unvalidated results

### Synthesis unclear
- Conductor unable to find connections
- May indicate subtasks weren't truly independent
- Review decomposition, try again with clearer boundaries

## Performance Expectations

### Execution Time
- Spawning: 5-10 seconds
- Worker execution: 8-15 minutes (typically)
- Monitoring polls: 5-second intervals
- Synthesis: 2-3 minutes
- Total: 10-20 minutes

### Token Usage
- Each Haiku worker: 8-12k tokens
- 3 workers: 24-36k tokens
- Opus synthesis: 10-15k tokens
- Total: 34-51k tokens (vs 100-150k sequential)

### Quality vs Sequential
- Same or higher quality
- Results more focused (workers don't distract each other)
- Synthesis integrates perspectives coherently

## Example: Full Execution

```
User: "Review the backend for security issues, performance bottlenecks, and code quality problems. Use parallel execution."

Conductor reads and decomposes into 3 workers.

10:30:05 — Spawning workers...
          Worker 1 (Security): agent_abc123
          Worker 2 (Performance): agent_def456
          Worker 3 (Quality): agent_ghi789

10:30:10 — All workers spawned. Monitoring...

10:35:00 — Worker 1 (Security) complete!
          Findings: 2 CRITICAL, 3 HIGH, 5 MEDIUM

10:38:45 — Worker 2 (Performance) complete!
          Findings: 1 HIGH, 4 MEDIUM

10:41:20 — Worker 3 (Quality) complete!
          Findings: 3 HIGH, 8 MEDIUM

10:42:00 — All workers complete. Validating results...
          ✓ All results valid

10:44:30 — Synthesis complete.

Final Report:
=============
CRITICAL Issues: 2
HIGH Issues: 8
MEDIUM Issues: 17

Top Priority:
1. Hardcoded API key [Security]
2. N+1 queries [Performance]
3. Missing input validation [Security]

Detailed recommendations for each.

Metrics:
- Time: 14 min (vs 35 min sequential) = 60% faster
- Tokens: 48k (vs 140k sequential) = 65% savings
```

## When to Escalate

Contact if:
- Multiple workers fail (> 1)
- Synthesis unable to integrate results
- Results contradict each other significantly
- Task timing >> expected (> 30 minutes)
```

**Action:** Create this file.

---

### **Phase 3.3: Create Debugging Guide**

#### **File 16: `docs/PARALLEL_EXECUTION_DEBUGGING.md`**
**Location:** `/Users/fyodorgolovin/Downloads/Supply-Inventory v1.0/docs/PARALLEL_EXECUTION_DEBUGGING.md`

**Content:**
```markdown
# Parallel Execution Debugging Guide

Troubleshooting parallel execution issues.

## Issue 1: Worker Takes Too Long (> 20 min)

### Symptoms
```
Worker 2 (Performance): Running (2/5 steps) ⏳
[5 minutes later]
Worker 2 (Performance): Running (2/5 steps) ⏳
```

Worker appears stuck on same step.

### Causes
1. Subtask too complex for one worker
2. Worker confused by ambiguous instructions
3. Task requires more context than provided
4. Worker trying to solve more than one subtask

### Solutions
1. Check `context/parallel-tasks.json` for worker task description
2. Re-evaluate: Can this subtask be split further?
3. Increase timeout in `context/agent-spawner-config.json`
4. Re-run worker with clearer instructions

### How to Check
```
cat context/parallel-tasks.json | grep worker_2
```

Look for: task description, started_at, last_poll_time

---

## Issue 2: Worker Fails

### Symptoms
```
Worker 1: Error (agent_abc123)
TaskOutput shows: [error message]
```

### Causes
1. Worker received malformed input
2. Context too large for Haiku
3. Task description ambiguous
4. Worker ran out of context (very rare)

### Solutions
1. Read error in TaskOutput
2. Check worker task description clarity
3. Simplify if possible
4. Re-spawn worker with corrected task

### How to Check
```
TaskOutput(task_id="agent_abc123", block=false)
```

Look for: error message, partial output

---

## Issue 3: Result File Missing or Malformed

### Symptoms
```
Trying to read: context/worker-results/worker_1_result.md
File not found or empty
```

### Causes
1. Worker crashed before writing file
2. Worker wrote to wrong path
3. File permissions issue
4. Conductor didn't wait long enough

### Solutions
1. Check if worker completed (TaskOutput)
2. If completed, manually run worker again
3. Verify file path matches expectation
4. Check file permissions: `ls -la context/worker-results/`

---

## Issue 4: Validation Fails

### Symptoms
```
/result-validator
Worker 1: INVALID
- Missing ## Recommendations section
- Severity counts not numeric
```

### Causes
1. Worker output doesn't match expected format
2. Markdown syntax error
3. Missing required section

### Solutions
1. View actual file: `cat context/worker-results/worker_1_result.md`
2. Compare against template in docs/PARALLEL_EXECUTION.md
3. Identify missing or malformed sections
4. Re-run worker with format template

### Expected Format (Quick Check)
```
# Worker N - Task Name          ← Required
## Status                        ← Required
## Findings                      ← Required
## Summary                       ← Required (with CRITICAL/HIGH/MEDIUM/LOW)
## Recommendations              ← Required
```

---

## Issue 5: Synthesis Unclear or Missing Connections

### Symptoms
```
Synthesis output is disjointed:
- Lists findings from each worker separately
- Doesn't show how they relate
- No integrated recommendations
```

### Causes
1. Subtasks weren't truly independent (hidden dependencies)
2. Conductor confused about relationships
3. Too many workers (> 5) for synthesis to integrate

### Solutions
1. Review decomposition (was it truly independent?)
2. Reduce to 3-4 workers max
3. Provide clearer synthesis instructions
4. Manually integrate if needed

---

## Issue 6: Context Rot / Conductor Loses Track

### Symptoms
```
Conductor asks: "Which worker results do I have?"
[No clear tracking in parallel-tasks.json]
```

### Causes
1. parallel-tasks.json not updated during execution
2. Worker-monitor skill didn't run
3. Conductor didn't call TaskOutput regularly

### Solutions
1. Run /worker-monitor to refresh status
2. Manually update parallel-tasks.json
3. Conductor should poll every 5 seconds (check config)

---

## Debug Checklist

When something fails:

- [ ] Check `context/parallel-tasks.json` for execution status
- [ ] Check `context/worker-results/` directory for output files
- [ ] Run `/worker-monitor` to get current status
- [ ] View specific worker result: `cat context/worker-results/worker_N_result.md`
- [ ] Check TaskOutput for error: `TaskOutput(task_id="...", block=false)`
- [ ] Review worker task description: Is it clear? Is it one task or multiple?
- [ ] Check agent config: `context/agent-spawner-config.json`
- [ ] Review decomposition: Are subtasks truly independent?
- [ ] Optional: Run `/result-validator` to check format

## Common Error Messages

### "task_id not found"
Worker never started or task_id incorrect. Check parallel-tasks.json.

### "agent returned error"
Worker failed. Check TaskOutput for error message. Re-run.

### "timeout waiting for workers"
Worker took > 30 min. May be too complex. Break into smaller subtasks.

### "result file empty"
Worker didn't write output. Likely crashed. Re-run with same task.

### "validation failed: missing field X"
Worker output doesn't match format. Re-run with format template.

## Manual Recovery Steps

If parallel execution gets stuck:

1. Stop waiting (kill any polling)
2. Check current state: `cat context/parallel-tasks.json`
3. Identify which workers incomplete
4. For each incomplete worker:
   - Note its task description
   - Spawn new Agent with same task
   - Get new task_id
   - Update parallel-tasks.json manually
5. Once all results available, synthesize manually
6. Update metrics

## Prevention Tips

- Start small: first attempt with 2-3 workers
- Test decomposition: confirm subtasks are independent
- Use clear, specific task descriptions
- Monitor actively (don't go idle for > 10 min)
- Review first execution's metrics (did it work?)
```

**Action:** Create this file.

---

### **Phase 3.4: Update Existing Documentation**

#### **File 17: `CLAUDE.md` Section 2 (update)**

Already added in Phase 3.1 above.

---

#### **File 18: `PROGRESS.md` Final Update**

**Action:** Update Phase 1 section:
```
- [x] Create PARALLEL_EXECUTION.md
- [x] Create TASK_DECOMPOSITION.md
- [x] Create context/agent-spawner-config.json
- [x] Create context/parallel-tasks.json
- [x] Create context/worker-results/ directory
- [x] Create ~/.claude/agents/conductor.md
- [x] Create ~/.claude/agents/worker-template.md
- [x] Update PROGRESS.md with parallel execution section
- [x] Update CLAUDE.md with parallel execution reference

**Status:** Phase 1 Complete — Foundation Ready
```

---

## **VERIFICATION CHECKLIST**

After completing all phases, verify:

### **Phase 1 Files Exist**
- [ ] `docs/PARALLEL_EXECUTION.md` — system documentation
- [ ] `docs/TASK_DECOMPOSITION.md` — decomposition guide
- [ ] `context/agent-spawner-config.json` — configuration
- [ ] `context/parallel-tasks.json` — execution tracking
- [ ] `context/worker-results/` — result directory
- [ ] `~/.claude/agents/conductor.md` — orchestrator
- [ ] `~/.claude/agents/worker-template.md` — worker template

### **Phase 2 Skills Exist**
- [ ] `skills/worker-monitor/SKILL.md` — monitor skill
- [ ] `skills/result-validator/SKILL.md` — validation skill
- [ ] `skills/metrics-tracker/SKILL.md` — metrics skill
- [ ] `context/parallel-execution-metrics.md` — metrics storage

### **Phase 3 Documentation**
- [ ] `docs/PARALLEL_EXECUTION_RUNBOOK.md` — execution steps
- [ ] `docs/PARALLEL_EXECUTION_DEBUGGING.md` — troubleshooting
- [ ] `CLAUDE.md` updated with parallel execution section
- [ ] `PROGRESS.md` updated with parallel execution tracking

### **Configuration Verified**
- [ ] `context/agent-spawner-config.json` has valid JSON
- [ ] `~/.claude/agents/conductor.md` exists and readable
- [ ] `context/worker-results/` directory is writable

---

## **NEXT STEPS**

### After Implementation:

1. **Run Test Execution** — Small task with 2-3 workers to validate system
2. **Measure Performance** — Use metrics-tracker to see real time/token savings
3. **Refine Decomposition** — Based on first execution, improve task breakdown
4. **Document Patterns** — Add successful decomposition patterns to TASK_DECOMPOSITION.md
5. **Train Team** — Share runbook and examples with anyone using the system

### Test Execution Example:
```
"Review the API endpoints for security and performance. Use parallel execution with 2 workers."

Expected:
- Execution time: 8-10 minutes
- Tokens: 18-25k
- Quality: Clear findings + recommendations
```

---

## **FILE SUMMARY**

**Total Files to Create: 18**

| Phase | File | Type | Purpose |
|-------|------|------|---------|
| 1 | PARALLEL_EXECUTION.md | Doc | System overview |
| 1 | TASK_DECOMPOSITION.md | Doc | Decomposition guide |
| 1 | agent-spawner-config.json | Config | Spawn configuration |
| 1 | parallel-tasks.json | Data | Execution tracking |
| 1 | worker-results/.gitkeep | Dir | Result storage |
| 1 | conductor.md | Agent | Orchestrator |
| 1 | worker-template.md | Agent | Worker template |
| 2 | worker-monitor/SKILL.md | Skill | Monitor execution |
| 2 | result-validator/SKILL.md | Skill | Validate results |
| 2 | metrics-tracker/SKILL.md | Skill | Track performance |
| 2 | parallel-execution-metrics.md | Doc | Metrics log |
| 3 | PARALLEL_EXECUTION_RUNBOOK.md | Doc | Execution steps |
| 3 | PARALLEL_EXECUTION_DEBUGGING.md | Doc | Troubleshooting |
| 3 | CLAUDE.md (update) | Update | Add parallel section |
| 3 | PREFERENCES.md (update) | Update | Add preferences |
| 3 | PROGRESS.md (update) | Update | Add tracking |
| 1 | .claude/agents/conductor.md | Agent | Global conductor |
| 1 | .claude/agents/worker-template.md | Agent | Global template |

**Total Time Estimate:** 3-4 hours for experienced developer, 5-6 for first-time

---

## **READY TO IMPLEMENT?**

This plan is complete, specific, and executable. Every file has:
- ✓ Exact location
- ✓ Content template or structure
- ✓ Purpose and usage
- ✓ Dependencies and integration points

**Next action:** Start Phase 1, Step 1. Create PARALLEL_EXECUTION.md.

