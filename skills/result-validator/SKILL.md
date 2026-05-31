---
id: result-validator
name: result-validator
description: "Validates worker result files before synthesis. Checks required sections, severity count consistency, scope compliance, and actionability of recommendations. Returns a per-worker validation report and a go/no-go decision for synthesis."
category: parallel-execution
risk: safe
source: project
date_added: "2026-04-06"
---

## When to Use — MANDATORY

**This skill MUST be called after every parallel execution, before synthesis begins.** It is not optional.

Use after all workers have completed (status: "synthesis-ready" in `context/parallel-tasks.json`) and before the Conductor begins synthesis.

Do not synthesize on unvalidated results. A malformed or incomplete worker result corrupts the synthesis. Do not skip this step because "the results look fine" — that judgment is exactly what this validator exists to make systematically.

---

# Result Validator

## Purpose

Read every completed worker result file, run structured validation checks against each, and return a clear go/no-go decision for synthesis with specific issues flagged per worker.

This skill does NOT fix worker results. It reads, checks, and reports.

---

## Instructions

### Step 1: Get Worker List

Read `context/parallel-tasks.json`. Extract:
- All workers where `status` is "complete"
- Their `result_file` paths

Skip workers with status "failed" or "timed_out" — their files may not exist or may be incomplete. Note them as excluded in the report.

### Step 2: Validate Each Result File

For each completed worker's result file, run all checks below. Track passes and failures per check.

#### Check 1: File Exists and Is Non-Empty

```
PASS: File exists and has content
FAIL: File missing → worker_N_result.md not found
FAIL: File empty → worker_N_result.md is 0 bytes
```

If this check fails, skip remaining checks for this worker. Mark as INVALID.

#### Check 2: Required Sections Present

Every result must have all 5 sections in this order:
- `## Status`
- `## Findings`
- `## Summary`
- `## Recommendations`
- `## Confidence`

```
PASS: All 5 sections present
FAIL: Missing sections → [list which ones]
WARN: Sections present but out of order
```

#### Check 3: Status Section Has Real Timestamps

```
PASS: Started and Completed timestamps are ISO format (YYYY-MM-DDTHH:MM:SSZ)
FAIL: Timestamps are placeholders (contain "YYYY", "HH", "timestamp", or similar)
FAIL: Completed timestamp is before Started timestamp
WARN: Timestamps look unusual (started in the future, completed >2 hours ago)
```

#### Check 4: Summary Counts Match Findings

Count the actual occurrences of each severity in the Findings section by looking for `Severity: CRITICAL`, `Severity: HIGH`, etc. (or `CRITICAL.`, `HIGH.` inline in finding descriptions).

Compare to Summary section counts.

```
PASS: Summary counts match actual finding counts (±0 tolerance)
WARN: Counts differ by 1-2 (minor inconsistency, synthesis can proceed)
FAIL: Counts differ by 3+ (significant inconsistency, findings may be unreliable)
```

#### Check 5: Every Finding Has a Location Reference

Scan Findings section for location markers:
- `File: path/to/file.py:LINE` format, OR
- `file.py:LINE` inline reference, OR
- "No findings" / "None found" explicit statement

```
PASS: All findings have location OR result explicitly states no findings
WARN: 1-2 findings lack location (minor)
FAIL: Multiple findings lack location — result is not actionable
```

#### Check 6: Every Recommendation References a Finding

Check that each numbered recommendation either:
- Names a specific finding by title or location, OR
- Is clearly tied to a finding described in the body

```
PASS: All recommendations reference specific findings
WARN: 1 recommendation is general (minor)
FAIL: Multiple recommendations are generic ("fix this", "consider improving") — result is not actionable
```

#### Check 7: Confidence Section Is Honest

Check for:
- Confidence level stated (High / Medium / Low)
- One-sentence reason provided
- Reason is consistent with what the finding body shows (e.g., not "High" when only 1 of 4 files was mentioned)

```
PASS: Confidence stated with clear reason
WARN: Confidence level present but reason is vague
FAIL: Confidence section missing level or reason entirely
```

#### Check 8: Scope Compliance (Spot Check)

Read Findings section for any file paths or domain references. Cross-reference against the worker's assigned scope (read from parallel-tasks.json worker task description if available).

```
PASS: All referenced files are within assigned scope
WARN: 1 out-of-scope reference found in Out-of-Scope Observations section (acceptable)
FAIL: Out-of-scope findings appear in main Findings section (scope violation)
```

---

### Step 3: Generate Validation Report

For each worker:

```
## Worker N — [Task Name]
Result File: context/worker-results/worker_N_result.md
Overall: [VALID ✓ | VALID WITH WARNINGS ⚠ | INVALID ✗]

| Check | Result | Detail |
|-------|--------|--------|
| File exists | ✓ PASS | 2,847 bytes |
| Required sections | ✓ PASS | All 5 present |
| Timestamps | ✓ PASS | 4m 37s execution |
| Summary counts | ⚠ WARN | Summary says HIGH: 3, found HIGH: 2 |
| Finding locations | ✓ PASS | All 5 findings have file:line |
| Recommendation linkage | ✓ PASS | 4 recommendations, all specific |
| Confidence | ✓ PASS | High — "reviewed all 4 files" |
| Scope compliance | ✓ PASS | All references within backend/api/ |
```

### Step 4: Overall Decision

After checking all workers:

**GO — Proceed to synthesis**
All workers: VALID or VALID WITH WARNINGS (warnings only, no FAIL checks)
> "All N worker results validated. N have warnings (noted above). Synthesis can proceed."

**GO WITH CAUTION — Proceed with flagged results**
Some workers have FAIL checks but result is still usable
> "N of N workers validated. Worker [X] has quality issues: [specific issues]. Conductor should treat Worker X findings with lower confidence during synthesis."

**HOLD — Do not synthesize**
One or more workers have critical failures (file missing, all sections missing, summary completely wrong)
> "Worker [X] result is INVALID: [specific failure]. Synthesis would produce unreliable output. Recommend: [re-run worker X | skip worker X and note gap in synthesis]."

---

## Output Contract

Prints a validation report per worker and an overall go/no-go decision.

Does NOT modify any files.

Does NOT fix worker results.

Returns one of three decisions: GO | GO WITH CAUTION | HOLD

---

## Remediation Guide (for Conductor)

When a worker result fails validation:

| Failure Type | Recommended Action |
|-------------|-------------------|
| File missing | Re-run that worker with same prompt |
| Empty file | Re-run that worker — it likely crashed before writing |
| Missing required sections | Use available sections, note gap in synthesis |
| Timestamp placeholders | Treat timestamps as unknown, proceed |
| Summary counts off by 1-2 | Use actual finding count from body, ignore summary |
| Summary counts off by 3+ | Re-count manually from body, flag as "low reliability" |
| All findings lack locations | Treat as low-confidence analysis, note in synthesis |
| Generic recommendations only | Extract from findings, recommendations section unreliable |
| Scope violations in Findings | Quarantine out-of-scope findings, pass to relevant worker |
