# Model Strategy for Parallel Execution Setup

**Decision Rule:** Switch based on task complexity, not category.
- **Haiku 4.5** — Simple, structural work (low complexity, high repetition)
- **Sonnet 4.6** — Medium complexity (requires judgment, integration points)
- **Opus 4.6** — High complexity (architectural decisions, synthesis, design tradeoffs)

---

## **PHASE 1: Foundation (90 min)**

### **Phase 1.1: Documentation Files**

#### **PARALLEL_EXECUTION.md**
- **Task:** Write system overview, explain concepts, provide templates
- **Complexity:** Medium (needs clarity, examples, good structure)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Needs clear explanations, good examples, must be reference material others read. Sonnet balances clarity + conciseness.
- **Cost:** ~8-12k tokens
- **Skip Haiku because:** Documentation quality matters — misexplanations propagate. Worth the extra cost.

#### **TASK_DECOMPOSITION.md**
- **Task:** Write decomposition guide, patterns, examples
- **Complexity:** Medium-High (needs concrete examples, pattern recognition)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Must provide worked examples that actually work. Haiku might skip edge cases.
- **Cost:** ~6-10k tokens
- **Skip Haiku because:** Poor examples = poor decomposition later. Sonnet ensures quality.

### **Phase 1.2: Configuration Files**

#### **agent-spawner-config.json**
- **Task:** Create JSON configuration file with settings
- **Complexity:** Low (structural, straightforward)
- **Recommendation:** **Haiku 4.5**
- **Why:** Simple JSON structure, no judgment needed. Haiku handles perfectly.
- **Cost:** ~1-2k tokens
- **Fine to use Haiku because:** Config is config — no ambiguity.

#### **parallel-tasks.json** (template)
- **Task:** Create empty JSON template
- **Complexity:** Low (trivial)
- **Recommendation:** **Haiku 4.5**
- **Why:** Just an empty template structure
- **Cost:** <500 tokens
- **Fine to use Haiku because:** Cannot be simpler.

#### **worker-results/.gitkeep**
- **Task:** Create directory and .gitkeep file
- **Complexity:** None (just filesystem)
- **Recommendation:** **You do this manually (CLI)**
- **Why:** No AI needed, 10 seconds with bash

### **Phase 1.3: Core Skills**

#### **conductor.md** (Agent definition)
- **Task:** Write detailed orchestrator agent instructions
- **Complexity:** High (complex logic, decision-making, monitoring strategy)
- **Recommendation:** **Opus 4.6**
- **Why:** Conductor has to:
  - Decompose tasks intelligently
  - Spawn agents correctly
  - Monitor and handle failures
  - Synthesize complex results
  - This is architectural work — needs Opus reasoning
- **Cost:** ~15-20k tokens
- **Must use Opus because:** Conductor is the critical component. Bad conductor = system fails.

#### **worker-template.md** (Agent definition)
- **Task:** Write worker agent instructions
- **Complexity:** Medium (needs clarity, constraints, quality standards)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Workers need clear instructions but it's simpler than conductor. Sonnet is good fit.
- **Cost:** ~8-12k tokens
- **Sonnet vs Haiku:** Haiku might be too minimal. Sonnet ensures workers understand role clearly.

### **Phase 1.4: Progress Tracking**

#### **Update PROGRESS.md + PREFERENCES.md**
- **Task:** Add tracking sections
- **Complexity:** Low (templated updates)
- **Recommendation:** **Haiku 4.5**
- **Why:** Simple additions, no synthesis needed
- **Cost:** ~2-3k tokens
- **Fine to use Haiku because:** Just appending structured sections.

---

## **PHASE 2: Skills & Utilities (60 min)**

### **Phase 2.1: Monitoring Skill**

#### **worker-monitor/SKILL.md**
- **Task:** Write skill for monitoring parallel workers
- **Complexity:** Medium (needs polling logic, status tracking, updates)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Not trivial — needs clear logic for:
  - When/how to poll
  - How to update status
  - How to handle partial results
- **Cost:** ~8-10k tokens
- **Haiku risk:** Might oversimplify polling strategy or miss edge cases.

### **Phase 2.2: Validation Skill**

#### **result-validator/SKILL.md**
- **Task:** Write skill for validating worker outputs
- **Complexity:** Medium (needs format rules, validation logic, error reporting)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Validation logic needs to be comprehensive and clear. Sonnet handles this well.
- **Cost:** ~8-10k tokens

### **Phase 2.3: Metrics Skill**

#### **metrics-tracker/SKILL.md**
- **Task:** Write skill for tracking execution metrics
- **Complexity:** Low-Medium (straightforward logging, some math)
- **Recommendation:** **Haiku 4.5**
- **Why:** Mostly logging + basic calculations. Haiku is sufficient.
- **Cost:** ~5-7k tokens
- **Can use Haiku because:** Metrics is relatively simple — log, compare, report.

### **Phase 2.4: Metrics Storage**

#### **parallel-execution-metrics.md**
- **Task:** Create metrics template file
- **Complexity:** Low (templating)
- **Recommendation:** **Haiku 4.5**
- **Why:** Just a file template with examples
- **Cost:** ~2-3k tokens

---

## **PHASE 3: Integration & Documentation (60 min)**

### **Phase 3.1: Update CLAUDE.md**

#### **Add Parallel Execution Section**
- **Task:** Write new section explaining parallel execution
- **Complexity:** Medium (needs to integrate with existing docs, clear positioning)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Must integrate smoothly with existing CLAUDE.md style and substance.
- **Cost:** ~6-8k tokens
- **Why not Haiku:** Tone/integration consistency matters.

### **Phase 3.2: Create Runbook**

#### **PARALLEL_EXECUTION_RUNBOOK.md**
- **Task:** Write step-by-step execution guide with examples
- **Complexity:** Medium-High (needs clarity, examples, troubleshooting paths)
- **Recommendation:** **Sonnet 4.6**
- **Why:** Runbook is critical — unclear steps = failed executions. Needs Sonnet clarity.
- **Cost:** ~12-15k tokens
- **Must not use Haiku:** Runbooks need precision.

### **Phase 3.3: Create Debugging Guide**

#### **PARALLEL_EXECUTION_DEBUGGING.md**
- **Task:** Write troubleshooting guide with diagnostic steps
- **Complexity:** High (needs to anticipate problems, provide diagnostic logic, solution reasoning)
- **Recommendation:** **Opus 4.6**
- **Why:** Good debugging guide requires:
  - Anticipating what can go wrong
  - Logical diagnostic flowcharts
  - Multiple solution paths
  - This is reasoning work — needs Opus
- **Cost:** ~18-25k tokens
- **Why Opus:** Debugging quality directly impacts whether users can fix problems themselves. Worth the cost.

---

## **SUMMARY TABLE**

| Phase | File | Complexity | Model | Cost | Reasoning |
|-------|------|-----------|-------|------|-----------|
| 1.1 | PARALLEL_EXECUTION.md | Medium | **Sonnet** | 10k | Reference docs need clarity |
| 1.1 | TASK_DECOMPOSITION.md | Med-High | **Sonnet** | 8k | Examples must be correct |
| 1.2 | agent-spawner-config.json | Low | **Haiku** | 2k | Pure structure |
| 1.2 | parallel-tasks.json | Low | **Haiku** | 1k | Simple template |
| 1.3 | conductor.md | **High** | **Opus** | 18k | Architectural component |
| 1.3 | worker-template.md | Medium | **Sonnet** | 10k | Workers need clarity |
| 2.1 | worker-monitor/SKILL.md | Medium | **Sonnet** | 9k | Monitoring logic |
| 2.2 | result-validator/SKILL.md | Medium | **Sonnet** | 9k | Validation rules |
| 2.3 | metrics-tracker/SKILL.md | Low-Med | **Haiku** | 6k | Simple logging |
| 3.1 | CLAUDE.md update | Medium | **Sonnet** | 7k | Integration consistency |
| 3.2 | PARALLEL_EXECUTION_RUNBOOK.md | Med-High | **Sonnet** | 13k | Steps must be clear |
| 3.3 | PARALLEL_EXECUTION_DEBUGGING.md | **High** | **Opus** | 22k | Diagnostic reasoning |
| Config/Templates | (misc) | Low | **Haiku** | 5k | Structural |

**Total Token Budget by Model:**
- **Haiku 4.5:** ~15k tokens (miscellaneous, templating)
- **Sonnet 4.6:** ~75k tokens (medium complexity, documentation, examples)
- **Opus 4.6:** ~40k tokens (architectural, reasoning, debugging)

**Total: ~130k tokens**

---

## **EXECUTION ORDER WITH MODELS**

### **Recommended Sequence:**

**Day 1 — Foundation + Architecture**
1. **Opus** — Create conductor.md (18k) — most critical component
2. **Sonnet** — Create PARALLEL_EXECUTION.md (10k) — understand system
3. **Sonnet** — Create TASK_DECOMPOSITION.md (8k) — understand decomposition
4. **Sonnet** — Create worker-template.md (10k) — understand workers
5. **Haiku** — Create configs + templates (8k) — quick structural work

**Day 2 — Skills**
6. **Sonnet** — Create worker-monitor SKILL (9k) — monitoring strategy
7. **Sonnet** — Create result-validator SKILL (9k) — validation rules
8. **Haiku** — Create metrics-tracker SKILL (6k) — simple logging

**Day 3 — Documentation & Integration**
9. **Sonnet** — Update CLAUDE.md (7k) — integration
10. **Sonnet** — Create RUNBOOK (13k) — execution guide
11. **Opus** — Create DEBUGGING guide (22k) — reasoning for diagnostics

---

## **COST OPTIMIZATION OPPORTUNITIES**

If you want to reduce costs (while maintaining quality):

### **Can downgrade to Haiku:**
- ✗ agent-spawner-config.json, parallel-tasks.json, metrics-tracker SKILL
- **Savings:** ~9k tokens, negligible quality loss

### **Can downgrade to Haiku (risky):**
- ⚠️ worker-monitor SKILL, result-validator SKILL
- **Savings:** ~18k tokens, moderate quality risk
- **Recommendation:** Keep at Sonnet (risk not worth 18k savings)

### **Must keep Opus:**
- ✓ conductor.md — orchestrator can't fail
- ✓ PARALLEL_EXECUTION_DEBUGGING.md — bad debugging = user frustration

### **Must keep Sonnet:**
- ✓ Documentation (PARALLEL_EXECUTION.md, TASK_DECOMPOSITION.md)
- ✓ Skills requiring logic (worker-monitor, result-validator)
- ✓ Runbook (execution guide must be clear)

---

## **QUALITY vs COST TRADEOFF**

| Strategy | Total Tokens | Quality | Risk | Recommendation |
|----------|-------------|---------|------|-----------------|
| **All Haiku** | 50k | Poor | High | ✗ Don't do |
| **Haiku + Sonnet** | 90k | Good | Low | ✓ Balanced |
| **Sonnet + Opus** | 130k | Excellent | Very Low | ✓ Recommended |
| **All Opus** | 150k | Perfect | None | ✗ Overkill (3x cost) |

**Recommended:** Sonnet + Opus (130k tokens)
- Haiku for trivial work (5k tokens)
- Sonnet for medium complexity docs/skills (75k tokens)
- Opus for critical architecture (40k tokens)

---

## **YOUR PREFERENCE NOTE**

From earlier feedback: *"I don't prefer Sonnet for engine logic and Haiku for frontend — I switch them up whenever I feel like the task is harder."*

This strategy follows that exactly:
- Task complexity drives model choice
- Not predefined by category
- If something feels harder mid-execution, can upgrade
- Examples: conductor.md needs Opus because it's architectural, not because it's "backend"

---

## **FINAL RECOMMENDATION**

**Use this execution order:**

```
[2026-04-06 10:00] Switch to Opus
  → Create conductor.md (18k) — critical component
  → Create PARALLEL_EXECUTION_DEBUGGING.md (22k) — complex reasoning

[2026-04-06 11:00] Switch to Sonnet
  → Create PARALLEL_EXECUTION.md (10k)
  → Create TASK_DECOMPOSITION.md (8k)
  → Create worker-template.md (10k)
  → Create worker-monitor SKILL (9k)
  → Create result-validator SKILL (9k)
  → Create RUNBOOK (13k)
  → Update CLAUDE.md (7k)

[2026-04-06 13:00] Switch to Haiku
  → Create all configs/templates (15k)
  → Create metrics-tracker SKILL (6k)
```

**Total:** 3 hours, 130k tokens, excellent quality, balanced cost.

Ready to start?
