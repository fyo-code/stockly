# Parallel Execution Metrics Log

## Recent Executions (Last 10)

| Date | Pattern | Workers | Success Rate | Duration | Token Est. Savings | Outcome |
|------|---------|---------|--------------|----------|-------------------|------------|
| — | — | — | — | — | — | — |

---

## Execution Records

*Execution entries will be appended here in chronological order. Each entry documents a complete parallel execution cycle: worker performance, findings aggregation, token efficiency, and synthesis outcome.*

---

### Format Reference

Each execution record follows this structure:

```markdown
## Execution: [execution_id]

**Date:** YYYY-MM-DD HH:MM:SS UTC
**Task:** [brief description, max 100 chars]
**Pattern:** [dimensional | multi-perspective | domain-split | research | validation]
**Outcome:** [success | partial | degraded | failed]

### Workers
| ID | Task | Status | Duration | Findings |
|----|------|--------|----------|----------|
| 1 | [Task] | ✓ | HHm SSs | N (levels) |

**Success Rate:** N/N (%)
**Total Duration:** HHm SSs (wall-clock time, not sum)

### Findings Summary
- Total: N findings
- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N
- INFO: N

### Efficiency
- Cross-worker patterns identified: N
- Conflicts resolved: N
- Gaps in coverage: [None | description]

**Estimated Token Usage:**
- Sequential baseline: ~Nk tokens
- Parallel actual: ~Nk tokens
- Savings: ~N% fewer tokens

### Notes
[Optional observations about this execution]

---
```

Use the `metrics-tracker` skill to populate entries after synthesis is complete.
