# VISION.md — Supply Chain Decision Engine
*Finalised: March 2026*

---

## The Core Problem

Retail businesses have one fundamental goal: sell exactly what customers want — no more, no less. In reality, this means:

- Buy 100 units → customers want 100 → sell 100 → zero waste, zero stockout
- Every unit over that 100 is capital sitting dead in a warehouse
- Every unit under that 100 is revenue lost and a customer who leaves empty-handed

The entire industry fails at this because nobody has an accurate answer to the one question that matters: **how many units will customers want next month?**

Romanian mid-market retailers (Mobexpert and others) currently solve this by looking backward — what sold last year same month — and ordering roughly the same. This produces:
- Dead stock accumulating silently for years
- Stockouts on fast-moving products that should never run out
- Over-ordering on high-return SKUs that inflate apparent demand
- Supplier lead time drift that nobody tracks until a crisis hits

---

## The Core Insight

**Demand forecasting is the foundation. Everything else is a layer on top of it.**

If you know accurately what demand will be next month:
- You know what to order (and how much)
- You know which products are over-stocked relative to forecast (dead stock)
- You know which suppliers need to deliver in time to meet that forecast (lead time matters)
- You can simulate the financial consequence of getting the order quantity wrong (scenario planning)

Without accurate demand forecasting, every other feature is guesswork dressed up as analysis.

---

## The Data Moat — The Real Business

The software is the means of collecting data. The data is the asset. The trained model is the moat.

**What accumulates over time:**
- Romanian consumer demand patterns per SKU category
- Italian and Romanian supplier behavior — actual performance vs promises
- Seasonality specific to Romanian retail (not German, not American)
- Return behavior by product type, store location, price point
- What correlates with demand shifts — construction activity, salary cycles, holidays, economic conditions
- Buyer decision patterns — when they approve recommendations, when they override, and why

**Why this is defensible:**
No Western AI company has 3 years of Romanian furniture retail data. No competitor entering this market in 2027 can buy or replicate 3 years of labeled training data from Mobexpert, Romanian agricultural firms, and Romanian retail chains. The data gap is the moat.

**What the data enables long-term:**
A specialized forecasting model — not a general LLM, but a domain-specific model trained on tabular retail time-series data — that predicts Romanian retail demand with accuracy no generic model can match. Think Chronos, TimeGPT, or a fine-tuned foundation model trained entirely on Eastern European retail patterns.

This is an 18-36 month horizon. The architecture being built now must feed it.

---

## The Decision Engine Layer

Data alone is useless. Data X must produce decision Y.

The product must not say: "Demand forecast is 140 units."
The product must say: "Order 140 units of SKU X by Friday. Confidence: high. Risk: Supplier B is running 14 days late — order now or you'll stockout."

Every recommendation must carry:
- A specific action
- A financial consequence of doing it vs not doing it
- A confidence level
- The risks that could invalidate it

The buyer's job is to approve, skip, or override — not to interpret raw numbers.

**Critical long-term feature: Decision Logging**
Every buyer action (approve / skip / override + reason) is stored as labeled training data. This is how the system learns what humans do when given a specific recommendation. This is what closes the feedback loop between the forecasting model and real-world outcomes. Without logging decisions, the data moat is only half built.

---

## The Network Effect Play

Once multiple stores are connected to the platform:

1. **Demand signals from one store inform forecasts for another** — if Store A in Bucharest sees a demand spike for a SKU, the system can predict it will arrive at Store B in Cluj within 2-3 weeks
2. **Cross-store distribution optimization** — instead of ordering new stock for Store B, transfer surplus from Store A. The system calculates whether transfer or reorder is more cost-efficient
3. **Every store added increases forecast accuracy for all stores** — the model gets smarter with more data

This is the Phase 2 platform play. The architecture must support multi-store from day one even if MVP is single-store.

---

## Product Roadmap

### MVP (Now — 2026 Q2)
- Demand forecasting visible and central
- Decision queue with approve/skip/override logging
- Dead stock surfacing with financial impact
- Supplier reliability scoring vs actual performance
- Scenario simulation with financial consequences
- SKU deep dive — full picture for any product

### V2 (2026 Q3-Q4)
- Automated reorder suggestions (human-approved, not autonomous)
- Multi-store inventory view
- Buyer performance tracking (are their overrides making things better or worse?)
- Real Pentaho data integration (replace synthetic data)

### V3 (2027)
- Cross-store distribution optimization
- Supplier communication platform (structured reorder requests, not phone/email)
- Network effect: once Mobexpert's suppliers are on the platform, approaching Dedeman becomes "your suppliers are already here"

### V4+ (2027-2028)
- Autonomous reordering for routine SKUs (copilot → autopilot)
- Custom forecasting model trained on accumulated Romanian retail data
- Expansion to Romanian agricultural firms, then Eastern European retail broadly

---

## Target Market Progression

1. **Mobexpert** — Romanian furniture retail. Insider access via V (internal champion), direct path to owner's son
2. **Romanian agricultural firms** — personal network connection. Zero competitor presence. 2% margins mean ordering decisions have immediate existential impact
3. **Romanian retail broadly** — Dedeman, food chains, FMCG distributors
4. **Eastern European retail** — Bulgaria, Hungary, Poland, Czech Republic
5. **European mid-market supply chain platform**

**Competitive position:** RELEX Solutions ($2B+ Finnish platform) entered Romania through enterprise channel (Carturesti). Too expensive, too slow for mid-market. The mid-market gap is real, confirmed, and uncontested.

---

## What "Done" Looks Like at Each Stage

**MVP done:** Owner's son opens the app, sees the demand forecast for next month, sees dead stock in lei, sees one supplier whose lead time drift is causing stockouts V's tool missed, says "I want to run this as a pilot."

**Pilot done:** One store, four weeks, running alongside V's tool. System catches three real anomalies with quantified financial impact. Pilot becomes formal contract.

**Year 1 done:** Mobexpert paying, one agricultural firm through personal network, product running on real data improving every month, decision logging accumulating labeled training data.

---

## The One Rule That Never Changes

Build for real value on real data, not for impressive demos on fake data. Every feature must work correctly on messy, incomplete, real-world CSV exports. Every recommendation must be defensible with a specific calculation, not a black box.
