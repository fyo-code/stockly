
# CLAUDE.md — Supply Chain Decision Engine

## What This Project Is

This is the core codebase for a supply chain decision engine built for Eastern European mid-market retail and agriculture. The first client is Mobexpert, one of Romania's largest furniture retailers.

Read these files before doing anything else:

- `docs/PROJECT_CONTEXT.md` — full business context, the problem, Mobexpert situation, who V is, what we're building and why
- `docs/MVP_SPEC.md` — exact features to build for MVP, blueprints, data requirements, calculations
- `docs/AGENT_RULES.md` — how you must behave, respond, and work on this project

Do not write a single line of code before reading all three.

---

## Project Structure

```
/
├── CLAUDE.md                  ← you are here
├── docs/
│   ├── PROJECT_CONTEXT.md     ← business context, problem, vision
│   ├── MVP_SPEC.md            ← exact MVP features and blueprints
│   └── AGENT_RULES.md        ← how to behave and work
├── backend/
│   ├── main.py                ← FastAPI entry point
│   ├── data/                  ← data ingestion and processing
│   ├── engines/               ← core calculation engines
│   │   ├── demand.py          ← real demand + trend detection
│   │   ├── dead_stock.py      ← dead stock detection + scoring
│   │   ├── supplier.py        ← supplier reliability scoring
│   │   └── scenario.py        ← scenario simulation
│   ├── agents/                ← AI reasoning layer
│   └── api/                   ← API routes
├── frontend/
│   ├── app/                   ← Next.js app directory
│   ├── components/            ← reusable UI components
│   └── lib/                   ← utilities and API calls
└── data_samples/              ← synthetic data for development
```

---

## Tech Stack

**Backend:** Python, FastAPI, PostgreSQL, pandas for data processing, APScheduler for nightly jobs

**Frontend:** Next.js 14, Tailwind CSS, shadcn/ui components, Recharts for data visualization

**AI Layer:** Anthropic Claude API for natural language reasoning on recommendations

**Data:** CSV/Excel ingestion for now — no direct Pentaho connection at MVP stage. Data arrives as exports.

---

## Current Status

**Mobexpert is the target first client — not yet confirmed.** The goal is to demo the product to the owner's son, get a pilot approved, and make Mobexpert the first paying client. Do not assume the relationship is confirmed. Build as if you need to earn it.

No Pentaho access yet. Building on synthetic data structured to match Pentaho export format. One real dataset available: gift category sales export from Mobexpert. Use this for testing and demonstration.

When Pentaho access arrives: plug real exports into the existing data pipeline. Architecture must support this without rebuilding.

---

## How This File System Stays Current

This project uses a simple update protocol. When business context, product decisions, or technical direction changes:

1. The relevant doc gets updated directly — PROJECT_CONTEXT.md for business/strategic changes, MVP_SPEC.md for feature changes, AGENT_RULES.md for working style changes
2. CLAUDE.md gets a one-line entry in the CHANGELOG section below noting what changed and when
3. The agent reads CLAUDE.md at the start of every session — the changelog tells it what to re-read

If you are the agent and the changelog shows a file was updated more recently than your last session, re-read that file before proceeding.

---

## CHANGELOG

| Date | File Updated | What Changed |
|------|-------------|--------------|
| March 2026 | CLAUDE.md | Initial setup |
| March 2026 | CLAUDE.md | Corrected Mobexpert status to target not confirmed client. Removed premature agriculture references. Added update protocol. |
| 2026-03-28 | VISION.md | Created — full startup vision, data moat thesis, product roadmap V1→V4, competitive context |
| 2026-03-28 | CLAUDE.md | Added mandatory progress tracking rule — mark steps done after every action |
| 2026-03-28 | PREFERENCES.md | Added vision summary, corrected model selection preference, added errors/patterns section |
| 2026-04-06 | CLAUDE.md | Added parallel execution system — conductor/worker infrastructure, skills, and runbook |
| 2026-04-06 | Parallel execution system | Fixed: synthesis made MANDATORY (was optional), added Pattern 6 (Independent Implementation), added enforcement language across all docs |

---

## Mandatory Progress Tracking — Non-Negotiable

After completing ANY step, edit, or build — before responding to the user — do this:

1. **Mark the step done in PROGRESS.md** — change `- [ ]` to `- [x]`, add a one-line note if something unexpected happened
2. **If a preference, correction, or decision was expressed** — append it to PREFERENCES.md immediately
3. **If architecture or direction changed** — add a one-line entry to the CHANGELOG table in this file

This is not optional. The system learns by capturing what was done. Without this, every new session starts blind.

---

## Parallel Execution System

This project has parallel multi-agent execution infrastructure. For complex tasks, use the Conductor pattern — one Opus orchestrator decomposes the task, spawns multiple Haiku workers simultaneously, then synthesizes their results.

**When to use it:** Any task with 3+ independent subtasks — analysis OR implementation. Works for code reviews, multi-file builds, multi-perspective decisions, etc.

**How to trigger it:** Begin your prompt with "Use parallel execution to..." or ask the Conductor to decompose the task. The Conductor will handle everything.

**MANDATORY SYNTHESIS RULE:** After workers complete, you MUST run: `/result-validator` → Opus synthesis report → `/metrics-tracker`. NEVER skip synthesis. NEVER manually integrate worker outputs. NEVER deliver raw worker results to the user. The execution is incomplete until all three post-worker phases run.

**Key files:**
- `docs/PARALLEL_EXECUTION.md` — system overview and concepts
- `docs/PARALLEL_EXECUTION_RUNBOOK.md` — step-by-step execution guide
- `docs/TASK_DECOMPOSITION.md` — how to decompose tasks correctly
- `context/parallel-tasks.json` — live execution registry
- `context/worker-results/` — where worker outputs land
- `context/parallel-execution-metrics.md` — performance log

**Skills (call with `/skill-name`):**
- `/worker-monitor` — check live status of running workers
- `/result-validator` — validate outputs before synthesis
- `/metrics-tracker` — log performance after synthesis

**Model assignment:**
- Conductor (orchestration, synthesis): Opus 4.6
- Workers (analysis subtasks): Haiku 4.5
- Complex analysis subtasks: Sonnet 4.6

**Performance targets (3 workers):** ~67% faster wall time, ~62% fewer tokens vs sequential Opus.

---

## The One Rule That Overrides Everything

Build for real value on real data, not for impressive demos on fake data. Every feature must work correctly on messy, incomplete, real-world CSV exports — not just on clean synthetic data.
