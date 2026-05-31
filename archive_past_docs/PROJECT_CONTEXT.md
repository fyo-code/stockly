# PROJECT_CONTEXT.md — Full Business Context

## What We Are Building And Why

A supply chain decision engine for Eastern European mid-market retail and agriculture.

The core problem: Romanian businesses — retailers, agricultural firms, distributors — are making inventory decisions blind. They look at what sold last year in the same month and order roughly the same amount. They do not know which products are secretly unprofitable because returns are not being subtracted from demand. They do not know which suppliers are quietly stretching delivery times and causing stockouts. They do not know how much capital is sitting dead in their warehouses. They do not know demand is shifting until it is already too late.

The result: dead stock accumulating in warehouses for years. Stockouts on fast-moving products that should never run out. Over-ordering on high-return SKUs that inflate apparent demand. Supplier lead time drift that nobody tracks until a crisis hits.

The people making these decisions are not incompetent. They are working with incomplete, unprocessed information using tools that look backwards not forwards.

---

## The First Client — Mobexpert

Mobexpert is one of Romania's largest furniture retailers. Multiple stores across Romania. 200,000+ SKUs across stores and warehouses. The founder has a direct relationship with the owner's son — this is the path to the first pilot.

### How Mobexpert Currently Orders Inventory

A product manager opens Pentaho — their internal database and BI tool — and pulls last year's data for the same month. They look at what was ordered in March 2025 and reorder a similar quantity for March 2026. Communication with suppliers happens by phone and email. Dedicated employees speak Italian, Romanian, and English negotiating and confirming orders manually.

There is no system that accounts for demand trends, return rates, supplier reliability, product profitability, or opportunity cost between competing SKUs.

### The V Tool — Critical Context

V is an internal digitalization lead at Mobexpert. He prototyped an ordering tool and worked with the IT team to implement it directly inside Pentaho. This tool is currently live and being used.

**What V's tool does:**
- Calculates how many units to order based on same-month-last-year data
- Factors in supplier lead times as static inputs — the lead time the supplier promised, not what they actually deliver
- Flags SKUs as urgent or non-urgent based on current stock versus reorder trigger
- Allows buyers to place reorder requests directly from the interface
- Demand estimate based on last four months sales divided by days, or previous year same month — basic calculation

**What V's tool cannot do — this is where we build:**
- Does not subtract returns from demand signals — gross sales overstate real demand
- Uses promised lead times not actual lead times — causes predictable stockouts when suppliers drift
- Has no dead stock detection — capital accumulates silently with no flag
- Has no supplier reliability tracking — no awareness of delivery performance history
- Makes no financial impact calculations — everything is quantities not money
- Has no trend detection — blind to whether demand is growing or declining

**Critical rule:** Do NOT build features that overlap with V's tool. Do not replicate reorder triggers, lead time calculation, or basic demand estimation. Build what V's tool cannot do. Our product extends V's tool, it does not compete with it. This is politically important — V is an internal ally and champion.

### The Business System Context

**Pentaho:** Internal database and BI tool. All sales data, purchase orders, delivery records live here. Clean and trusted — employees make decisions from it daily. No direct API access at MVP stage — data arrives as CSV or Excel exports.

**CROSweb:** Internal order management system. 1990s UI. Orders flow through here after being initiated in Pentaho.

**Supplier relationships:** Many Italian suppliers. Communication in Italian, Romanian, English. One dedicated employee spends half her working day on the phone managing supplier relationships manually.

---

## The Vision — Where This Goes

### The Core Insight

The software is the entry point. The data is the asset. The trained model is the moat.

Every transaction processed, every recommendation made, every human approval or override becomes labeled training data. Over 24 to 36 months of real Romanian retail data, the model gets fine-tuned on patterns that do not exist in any Western-trained model — Romanian seasonal demand cycles, Italian supplier behavior patterns, Romanian consumer return behavior, furniture demand correlation with construction activity.

A competitor entering this market two years later cannot replicate two years of Romanian retail training data. That is the moat.

### The Two-Phase Platform

**Phase 1 — Business Decision Engine:** Sits on top of existing databases. Converts raw transaction data into specific, reasoned, executable business decisions with financial impact in lei attached to every recommendation.

**Phase 2 — Supplier Communication Platform:** Replaces phone and email chaos with structured digital workflows. Structured reorder requests flow to suppliers, suppliers confirm delivery windows, performance is scored automatically. Network effect: once Mobexpert's suppliers are on the platform, approaching Dedeman becomes "your suppliers are already here."

### Target Market Progression

1. Mobexpert — Romanian furniture retail. Insider access, validated problem, direct path to decision maker.
2. Romanian agricultural firms — personal network connection to top-10 agricultural firms. Zero competitor presence. 2% margins mean ordering decisions have immediate existential impact.
3. Romanian retail broadly — Dedeman, food chains, FMCG distributors.
4. Eastern European retail — Bulgaria, Hungary, Poland, Czech Republic.
5. European mid-market supply chain platform.

### Competitive Position

RELEX Solutions ($2B+ Finnish platform) entered Romania through re:innovation, first client Carturesti (bookstore chain). Enterprise only. Too expensive, too slow for mid-market.

invent.ai — fashion-focused, enterprise pricing, no Romanian presence confirmed.

The mid-market gap is real, confirmed, and uncontested. RELEX in Romania proves the market exists. Their enterprise positioning proves the mid-market is open.

---

## The Architecture Philosophy

The product does not replace Pentaho, CROSweb, or any legacy infrastructure. It sits on top, reads from them, and adds the intelligence layer they do not have.

From a16z research: "the systems of record endure; the interface, automation, and extension layer becomes the new software frontier."

From Sequoia research: "a copilot sells the tool, an autopilot sells the work." MVP is copilot — humans approve every recommendation. Long-term destination is autopilot — routine SKUs ordered autonomously, humans handle exceptions only.

From invent.ai research: multi-agent architecture where specialized agents run simultaneously per domain, coordinated by a central agent that synthesizes outputs. Build toward this architecture from day one even if early versions are simpler.

---

## What Success Looks Like

**MVP success:** Owner's son opens the app, sees the dead stock number in lei, sees one supplier whose lead time drift is causing stockouts V's tool is blind to, says "I want to run this as a pilot."

**Pilot success:** One store, four weeks, running alongside V's tool. System catches three real anomalies with quantified financial impact. Pilot becomes formal contract.

**Year 1 success:** Mobexpert as paying client, one agricultural firm through personal network, product running on real data improving every month.
