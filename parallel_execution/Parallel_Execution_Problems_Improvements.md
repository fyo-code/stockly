### Improvements of the system

⏺ 1. Why agents couldn't return output

Each Haiku worker was instructed to write a file to context/worker-results/worker_N_result.md. But background agents run in a sandboxed permission context —
the user (you) wasn't prompted to approve the Write tool call because the agents run silently in the background. So all 4 workers:

- Read all the code files (Read tool was allowed)
- Did their full analysis
- Got blocked on Write tool → returned a message saying "I need permission"

I then had to read each worker's JSON transcript file, extract their analysis text, and write the result files myself as the Conductor.

Fix: Two options:

1. Change the worker prompt — Instead of "Write your results to file X", say "Return your complete analysis as your final response text." The Conductor then
reads the agent's return value (via TaskOutput) and writes the files itself. This is the simpler fix.
2. Pre-approve Write permissions — Configure allowedTools in settings to auto-approve Write for the context/worker-results/ path. Harder to set up, fragile.

Option 1 is better — it removes the file-writing dependency from workers entirely.

---

1. How the agent system is designed

Your system has 3 layers:

Layer 1: Agent definitions (~/.claude/agents/)

- [conductor.md](http://conductor.md/) — The orchestrator. Describes how Opus should decompose tasks, spawn workers, monitor, validate, synthesize. This is a behavioral instruction
file, not a skill.
- [worker-template.md](http://worker-template.md/) — The worker template. Describes how a worker should behave: stay in scope, use the output format, do self-checks. Also behavioral
instructions.

Layer 2: Skills (skills/ in project)

- worker-monitor/SKILL.md — Instructions for polling worker status and updating the registry
- result-validator/SKILL.md — Instructions for checking worker outputs against 8 criteria
- metrics-tracker/SKILL.md — Instructions for logging execution performance

These are instruction documents, not executable code. When I "run /result-validator", I'm reading that [SKILL.md](http://skill.md/) and following its instructions manually —
there's no actual skill invocation happening.

Layer 3: Infrastructure files (context/ in project)

- parallel-tasks.json — execution registry (tracks workers, statuses)
- agent-spawner-config.json — config (models, timeouts, max workers)
- worker-results/ — where worker output files land
- [parallel-execution-metrics.md](http://parallel-execution-metrics.md/) — performance log

How it flowed in this execution:

Me (Opus, acting as Conductor)
│
├─ Read [conductor.md](http://conductor.md/) → understood my role
├─ Phase 0: Decided to parallelize (4 independent subtasks)
├─ Phase 2: Wrote 4 worker prompts with [TASK][SCOPE][OUTPUT][CONSTRAINTS]
├─ Phase 3: Spawned 4 Agent(model="haiku", run_in_background=true)
│     ├─ Worker 1: Code quality    → read files → BLOCKED on Write
│     ├─ Worker 2: Architecture    → read files → BLOCKED on Write
│     ├─ Worker 3: Data pipeline   → read files → BLOCKED on Write
│     └─ Worker 4: System design   → read files → BLOCKED on Write
├─ Phase 4: Checked worker-results/ → empty → extracted from transcripts
├─ Phase 5: Ran validation logic from result-validator [SKILL.md](http://skill.md/)
├─ Phase 6: Wrote synthesis report (cross-worker patterns, prioritization)
└─ Phase 7: Logged metrics from metrics-tracker [SKILL.md](http://skill.md/)

Important: The workers are NOT using skill files. Each worker is a bare Agent(subagent_type="general-purpose", model="haiku") with everything it needs
inlined in the prompt. Workers don't have access to [conductor.md](http://conductor.md/), [worker-template.md](http://worker-template.md/), or any [SKILL.md](http://skill.md/) files. They only see their prompt.

---

1. What went wrong and how to fix it

Problem 1: Write permission wall

- Impact: All 4 workers wasted tokens doing analysis they couldn't save
- Fix: Change design so workers return text in response, not write files. Conductor writes files.

Problem 2: Task was too small (298 lines across 4 files)

- Impact: Each worker loaded ~80k tokens of system context to analyze ~75 lines of code. 99% overhead.
- Fix: Add a hard rule to the runbook: "Do NOT parallelize if total target code is <1000 lines or <5 files."

Problem 3: Skills are documents, not executable

- Impact: When the system says "run /result-validator", nothing actually executes. I just read the [SKILL.md](http://skill.md/) and follow instructions manually. This means the
"mandatory gate" depends entirely on the Conductor remembering to do it.
- Reality check: This isn't fixable without actual tooling. Your skills are instruction sets, not code. The enforcement comes from the MANDATORY language we
added — which did work this time.

Problem 4: 4 workers × full system prompt = massive duplication

- Impact: 320k tokens just loading [CLAUDE.md](http://claude.md/) + rules into 4 separate contexts
- Fix: This is inherent to the Claude Code Agent tool — each agent gets the full system context. No way around it currently. This is why the "minimum task
size" threshold matters so much.

Problem 5: No way to pre-verify worker capabilities

- Impact: We only discovered the Write permission issue after all 4 workers had already burned their tokens
- Fix: Before spawning workers, spawn a single test agent that tries to Write a dummy file to context/worker-results/test.md. If it fails, switch to the
"return text" approach. Or just always use the "return text" approach (simpler).

---

1. Structural improvements I'd recommend

┌──────────────────────────────────────────┬──────────────────────────────────────────────────────┬─────────────────────────────────────────────────────┐
│                  Change                  │                         Why                          │                       Effort                        │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ Workers return text, Conductor writes    │ Eliminates permission issue entirely                 │ Low — change worker prompt template                 │
│ files                                    │                                                      │                                                     │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ Minimum 1000 lines / 5 files threshold   │ Prevents overhead-dominated executions               │ Low — add to runbook Phase 0                        │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ Drop worker-results/ file system         │ Workers return via TaskOutput, Conductor holds in    │ Medium — redesign flow                              │
│ entirely                                 │ memory                                               │                                                     │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ Add "dry run" pre-spawn check            │ Catches permission/infra issues before burning       │ Low — one test agent                                │
│                                          │ tokens                                               │                                                     │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ Reduce worker system context             │ Workers don't need [CLAUDE.md](http://claude.md/) or rules — just their   │ Not possible currently (Agent tool inherits full    │
│                                          │ task                                                 │ context)                                            │
└──────────────────────────────────────────┴──────────────────────────────────────────────────────┴─────────────────────────────────────────────────────┘

The biggest structural insight: your system was designed for a world where agents can freely write files. They can't in background mode. Redesigning around
"workers return text, Conductor owns all file I/O" would fix the core issue and simplify the whole flow.