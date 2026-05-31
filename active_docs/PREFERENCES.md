# PREFERENCES.md — Fyo's Preferences for This Project

All agents read this file before producing output. These override generic defaults.
Updated automatically when Fyo expresses a preference, dislike, or decision.

---

## UI / Design

- Light theme throughout — no dark backgrounds
- Lei amounts always formatted with thousand separators (e.g. 847,000 lei — not 847000)
- Financial impact must always be shown in lei, not just units
- URGENT status in red, REVIEW in amber, INFO in grey
- The "big number" (total dead stock in lei) must be front and center on the dashboard — large, impossible to ignore
- Dashboard must feel like a real daily tool, not a demo — no placeholder copy, no "lorem ipsum"

## Product

- Budget constraint is a first-class feature — every financial recommendation runs within the configured budget envelope per category
- Dead stock recovery = budget unlock — always frame it this way, not just as a loss
- Opportunity cost framing — when budget is constrained, show what could be bought with freed capital
- Morning Decision Queue is the primary UX — this is what the buyer sees first, everything else is secondary

## Code Style

- FastAPI routes: always include a docstring explaining what the endpoint does and what client uses it
- Python: use `logging` module, never `print()` for any server-side output
- Never hardcode Mobexpert-specific assumptions — the product must work for any retailer
- Calculation engines must be pure functions — input data in, results out, no DB calls inside engines
- Every function that divides must guard against zero-division explicitly

## Product Vision (Finalised 2026-03-28)

- Demand forecasting is the core engine — everything else is a layer on top of it
- The software is the means of collecting data; the data is the real asset; the trained model is the moat
- Decision engine framing: data X must always produce decision Y — raw numbers are not enough
- Buyer decisions (approve/skip/override) are labeled training data — must be captured from day one
- Multi-store distribution optimization is a planned Phase 3 network effect feature
- See VISION.md for full roadmap

## Model Selection

- No fixed rule on which model to use for which type of task
- Switch based on perceived difficulty of the specific step, not category of work
- Do not assume Sonnet = backend logic and Haiku = frontend — ask or use judgment per step

## Behaviour

- Do not ask for confirmation on routine technical decisions — just execute
- Do not ask multiple questions at once — one question at a time if needed
- After completing ANY step (not just phases): mark it [x] in PROGRESS.md immediately
- After completing a full feature: add a dated entry to the Completed section
- Update PREFERENCES.md whenever Fyo expresses a preference, dislike, correction, or decision
- Update CLAUDE.md CHANGELOG when architecture or project direction changes

## Parallel Execution (2026-04-06, updated 2026-04-09)

- Use parallel execution when: 3+ independent subtasks, >5k tokens total, results can be combined
- Do NOT parallelize: sequential dependencies, trivial tasks (<2k tokens), constant cross-referencing needed
- **Hard minimum: total scope must be ≥ 1000 lines OR ≥ 5 files** — below this, worker context overhead dominates
- Default to Conductor (Opus) for decomposition + 3-4 Haiku workers for execution
- Always spawn workers with `run_in_background=true` — conduct execution in parallel, not sequential
- **Workers return text as response — NEVER instruct workers to Write files** (background agents can't get Write permission approved)
- **Conductor owns all file I/O**: after each worker completes, call TaskOutput to read response, then Write the result file
- Validate all worker results against format spec before synthesis (Status + Findings + Summary + Recommendations + Confidence)
- Log all executions to `context/parallel-tasks.json` for future reference and metrics
- After synthesis, track time/tokens saved in `context/parallel-execution-metrics.md`

## Errors / Patterns to Avoid

- numpy.bool_ is not JSON-serializable by FastAPI — always cast with bool() on comparison results from pandas DataFrames
- Pyre2 flags round(sum(generator), 2) as error — false positive, safe to ignore at runtime
- Always test API endpoints with curl before building frontend against them

---

*Last updated: 2026-04-06*
