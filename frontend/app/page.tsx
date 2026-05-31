"use client";

import { useState } from "react";

const decisionQueue = [
  {
    id: "stockout",
    status: "Urgent",
    tone: "rose",
    title: "Store Alpha sofa line will run below safety stock",
    detail: "Synthetic forecast expects 184 units in 8 weeks. Current cover is 19 days.",
    impact: "€128k",
    action: "Prepare order for 96 units",
    sku: "SKU-A104",
  },
  {
    id: "supplier",
    status: "Review",
    tone: "amber",
    title: "Supplier Atlas delivery pattern is drifting",
    detail: "Planned 21 days, synthetic recent average is 34 days across 11 receipts.",
    impact: "€54k",
    action: "Move reorder date forward",
    sku: "SUP-042",
  },
  {
    id: "dead-stock",
    status: "Review",
    tone: "cyan",
    title: "Decor cluster has idle capital after promotion",
    detail: "38 demo SKUs have no meaningful movement and open supplier return windows.",
    impact: "€91k",
    action: "Recover budget window",
    sku: "CAT-D19",
  },
];

const forecastRows = [
  { category: "Seating", basic: "1,240", stockly: "1,118", signal: "High", trend: "+7.2%" },
  { category: "Lighting", basic: "520", stockly: "548", signal: "Medium", trend: "-4.1%" },
  { category: "Sleep", basic: "310", stockly: "286", signal: "High", trend: "+2.8%" },
  { category: "Decor", basic: "880", stockly: "612", signal: "Low", trend: "-18.4%" },
];

const suppliers = [
  { name: "Supplier Atlas", actual: "34d actual", drift: "+13d drift", status: "High risk", tone: "rose" },
  { name: "Supplier Nova", actual: "24d actual", drift: "+4d drift", status: "Watch", tone: "amber" },
  { name: "Supplier Meridian", actual: "28d actual", drift: "+7d drift", status: "Reorder early", tone: "cyan" },
];

const scenarios = [
  { label: "Lean", qty: "72 units", margin: "€28k", risk: "€16k shortage risk", tone: "cyan" },
  { label: "Balanced", qty: "96 units", margin: "€41k", risk: "lowest variance", tone: "emerald" },
  { label: "Heavy", qty: "118 units", margin: "€34k", risk: "€19k idle-stock risk", tone: "amber" },
];

const agents = [
  { name: "Forecast agent", body: "Demand ranges from sales, stock, returns, and campaign context.", tone: "emerald" },
  { name: "Supplier agent", body: "Promised windows compared with actual receipt behavior.", tone: "amber" },
  { name: "Inventory agent", body: "Dead stock, constrained demand, and transfer candidates.", tone: "cyan" },
  { name: "Decision agent", body: "Approvals, overrides, reasons, and downstream outcomes.", tone: "rose" },
];

const loopSteps = [
  ["1", "Forecast", "Demand, stock, returns, campaigns."],
  ["2", "Recommend", "Action, risk, confidence, impact."],
  ["3", "Decide", "Approve, skip, override, reason."],
  ["4", "Learn", "Outcome closes the training loop."],
];

export default function StocklyHomePage() {
  return (
    <div className="relative left-1/2 -mt-8 w-screen -translate-x-1/2 bg-slate-50 text-slate-950">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <a href="#top" className="flex items-center gap-3" aria-label="Stockly home">
          <LogoMark />
          <span className="font-serif text-2xl font-semibold text-slate-950">Stockly</span>
        </a>
        <nav className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
          <a className="hover:text-slate-950" href="#engine">Engine</a>
          <a className="hover:text-slate-950" href="#agents">Agent layer</a>
          <a className="hover:text-slate-950" href="#moat">Data moat</a>
          <a className="hover:text-slate-950" href="/dashboard">Live app</a>
        </nav>
        <a
          href="/dashboard"
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm hover:border-cyan-300 hover:text-cyan-800"
        >
          Open prototype
        </a>
      </header>

      <main id="top">
        <section className="mx-auto grid max-w-7xl gap-8 px-5 pb-14 pt-4 sm:px-8 lg:grid-cols-[0.82fr_1.18fr] lg:items-start lg:pb-20">
          <div className="pt-6">
            <p className="mb-4 inline-flex rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-sm font-medium text-cyan-900">
              Agentic inventory decisions, shown with synthetic data
            </p>
            <h1 className="max-w-3xl text-balance font-serif text-5xl font-semibold leading-none text-slate-950 sm:text-6xl lg:text-7xl">
              Forecast demand. Route the next decision.
            </h1>
            <p className="mt-6 max-w-2xl text-pretty text-lg leading-8 text-slate-600">
              Stockly turns messy retail exports into a ranked operating queue:
              what to order, what to recover, what to escalate, and why.
            </p>
            <div className="mt-8 grid max-w-2xl grid-cols-3 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
              <Metric label="Data" value="Synthetic demo" tone="cyan" />
              <Metric label="Loop" value="Approve / override" tone="emerald" />
              <Metric label="Impact" value="Euro modeled" tone="amber" />
            </div>
          </div>

          <ProductSurface />
        </section>

        <section id="engine" className="border-y border-slate-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.72fr_1.28fr]">
            <SectionIntro
              kicker="Forecast core"
              title="The forecast feeds every downstream action."
              body="Demand is the center. Supplier urgency, budget unlock, scenario planning, and agent routing all depend on the same forecast spine."
            />
            <div className="grid gap-4 lg:grid-cols-2">
              <ForecastPanel />
              <ScenarioPanel />
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-8 px-5 py-16 sm:px-8 lg:grid-cols-[0.9fr_1.1fr]">
          <DeadStockPanel />
          <SupplierPanel />
        </section>

        <section id="agents" className="border-y border-slate-200 bg-slate-100">
          <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
            <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
              <SectionIntro
                kicker="Agentic layer"
                title="Narrow agents. One operating queue."
                body="Not a chatbot wrapper. Specialized agents monitor the system and push only decision-ready exceptions to the buyer."
              />
              <AgentMap />
            </div>
          </div>
        </section>

        <section id="moat" className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
          <div className="grid gap-8 lg:grid-cols-[0.72fr_1.28fr]">
            <SectionIntro
              kicker="Learning loop"
              title="Every decision becomes operating data."
              body="The product starts human-approved. Over time, decision logs become the dataset for routine replenishment and exception handling."
            />
            <FeedbackLoop />
          </div>
        </section>

        <section className="border-t border-slate-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-5 px-5 py-14 sm:px-8 lg:grid-cols-4">
            <RoadmapItem stage="Now" title="Decision queue" body="Human-approved actions ranked by impact." tone="cyan" />
            <RoadmapItem stage="Next" title="Supplier workflow" body="Structured requests instead of phone/email drift." tone="amber" />
            <RoadmapItem stage="Platform" title="Inventory movement" body="Transfer surplus before buying more stock." tone="emerald" />
            <RoadmapItem stage="Later" title="Routine autopilot" body="Low-risk replenishment, exceptions escalated." tone="rose" />
          </div>
        </section>
      </main>
    </div>
  );
}

function ProductSurface() {
  const [active, setActive] = useState(decisionQueue[0]);
  const [decision, setDecision] = useState("Prepared");

  return (
    <MacWindow title="Stockly operating surface" subtitle="Demo queue" className="bg-slate-950">
      <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="border-b border-slate-200 lg:border-b-0 lg:border-r">
          {decisionQueue.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setActive(item);
                setDecision("Prepared");
              }}
              className={`block w-full cursor-pointer border-b border-slate-200 p-4 text-left transition last:border-b-0 ${
                active.id === item.id ? toneClass(item.tone, "soft") : "bg-white"
              } ${toneClass(item.tone, "hover")}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <span className={`rounded px-2 py-1 text-xs font-medium ${toneClass(item.tone, "badge")}`}>
                  {item.status}
                </span>
                <span className="text-sm font-semibold tabular-nums text-slate-950">{item.impact}</span>
              </div>
              <h2 className="mt-3 text-pretty text-base font-semibold text-slate-950">{item.title}</h2>
              <p className="mt-2 text-pretty text-sm leading-6 text-slate-600">{item.detail}</p>
              <p className="mt-3 text-sm font-medium text-slate-800">{item.action}</p>
            </button>
          ))}
        </div>
        <div className="bg-slate-50 p-4">
          <div className="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500">Selected item</p>
            <h3 className="mt-2 text-lg font-semibold text-slate-950">{active.sku}</h3>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <MiniStat label="8w forecast" value="184 units" tone="cyan" />
              <MiniStat label="On hand" value="41 units" tone="amber" />
              <MiniStat label="Confidence" value="High" tone="emerald" />
              <MiniStat label="Exposure" value={active.impact} tone={active.tone} />
            </dl>
            <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-medium text-slate-500">Recommended action</p>
              <p className="mt-1 text-pretty text-sm leading-6 text-slate-700">{active.action}. Final quantity remains buyer-approved.</p>
            </div>
          </div>
          <div className="mt-4 rounded-md border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500">Decision controls</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs font-medium">
              {["Approve", "Skip", "Override"].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setDecision(item)}
                  className={`cursor-pointer rounded border px-2 py-2 transition hover:border-slate-500 ${
                    decision === item ? "border-slate-950 bg-slate-950 text-white" : "border-slate-200 bg-white text-slate-700"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500">
              Current demo decision: <span className="font-semibold text-slate-800">{decision}</span>
            </p>
          </div>
        </div>
      </div>
    </MacWindow>
  );
}

function ForecastPanel() {
  const [selected, setSelected] = useState(forecastRows[0]);

  return (
    <Panel title="Forecast engine" note="click a category" tone="cyan">
      <div className="overflow-hidden rounded-md border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Category</th>
              <th className="px-3 py-2 font-medium">Basic</th>
              <th className="px-3 py-2 font-medium">Stockly</th>
              <th className="px-3 py-2 font-medium">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white tabular-nums">
            {forecastRows.map((row) => (
              <tr
                key={row.category}
                onClick={() => setSelected(row)}
                className={`cursor-pointer transition hover:bg-cyan-50 ${selected.category === row.category ? "bg-cyan-50" : ""}`}
              >
                <td className="px-3 py-3 font-medium text-slate-900">{row.category}</td>
                <td className="px-3 py-3 text-slate-600">{row.basic}</td>
                <td className="px-3 py-3 text-slate-950">{row.stockly}</td>
                <td className="px-3 py-3 text-slate-950">{row.trend}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-slate-600">
        Selected: <span className="font-semibold text-cyan-800">{selected.category}</span> with {selected.signal.toLowerCase()} signal quality.
      </p>
    </Panel>
  );
}

function ScenarioPanel() {
  const [selected, setSelected] = useState(scenarios[1]);

  return (
    <Panel title="Scenario simulation" note="select order posture" tone="emerald">
      <div className="space-y-3">
        {scenarios.map((scenario) => (
          <button
            key={scenario.label}
            type="button"
            onClick={() => setSelected(scenario)}
            className={`grid w-full cursor-pointer gap-2 rounded-md border p-3 text-left transition sm:grid-cols-[0.65fr_0.6fr_0.6fr_1fr] ${
              selected.label === scenario.label ? toneClass(scenario.tone, "outline") : "border-slate-200 bg-white hover:border-slate-400"
            }`}
          >
            <p className="text-sm font-semibold text-slate-950">{scenario.label}</p>
            <p className="text-sm tabular-nums text-slate-700">{scenario.qty}</p>
            <p className="text-sm tabular-nums text-slate-700">{scenario.margin}</p>
            <p className="text-sm text-slate-500">{scenario.risk}</p>
          </button>
        ))}
      </div>
      <p className="mt-4 text-sm text-slate-600">
        Active path: <span className="font-semibold text-emerald-800">{selected.label}</span>.
      </p>
    </Panel>
  );
}

function DeadStockPanel() {
  const [active, setActive] = useState("Recoverable");
  const values = [
    ["Idle capital", "€240k", "cyan"],
    ["Recoverable", "€86k", "emerald"],
    ["Affected SKUs", "38", "amber"],
    ["Closing windows", "9", "rose"],
  ];

  return (
    <Panel title="Dead stock as budget unlock" note="synthetic chain view" tone="amber">
      <div className="grid grid-cols-2 gap-3">
        {values.map(([label, value, tone]) => (
          <button
            key={label}
            type="button"
            onClick={() => setActive(label)}
            className={`cursor-pointer text-left transition ${active === label ? toneClass(tone, "outline") : "rounded-md border border-slate-200 bg-white p-3 hover:border-slate-400"}`}
          >
            <MiniStat label={label} value={value} tone={tone} />
          </button>
        ))}
      </div>
      <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm font-semibold text-slate-950">Selected signal: {active}</p>
        <p className="mt-2 text-pretty text-sm leading-6 text-slate-600">
          Recovered budget can be routed into higher-confidence reorder recommendations.
        </p>
      </div>
    </Panel>
  );
}

function SupplierPanel() {
  const [active, setActive] = useState(suppliers[0]);

  return (
    <MacWindow title="Supplier reliability" subtitle="dummy supplier names">
      <div className="space-y-3 p-4">
        {suppliers.map((supplier) => (
          <button
            key={supplier.name}
            type="button"
            onClick={() => setActive(supplier)}
            className={`grid w-full cursor-pointer grid-cols-[1fr_auto] gap-3 rounded-md border p-3 text-left transition ${
              active.name === supplier.name ? toneClass(supplier.tone, "outline") : "border-slate-200 bg-white hover:border-slate-400"
            }`}
          >
            <div>
              <p className="text-sm font-semibold text-slate-950">{supplier.name}</p>
              <p className="mt-1 text-xs text-slate-500">{supplier.actual} / {supplier.drift}</p>
            </div>
            <span className={`self-start rounded px-2 py-1 text-xs font-medium ${toneClass(supplier.tone, "badge")}`}>
              {supplier.status}
            </span>
          </button>
        ))}
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
          Active recommendation: adjust planning assumptions for <span className="font-semibold text-slate-900">{active.name}</span>.
        </div>
      </div>
    </MacWindow>
  );
}

function AgentMap() {
  const [active, setActive] = useState(agents[0]);

  return (
    <MacWindow title="Agent routing map" subtitle="interactive preview">
      <div className="grid gap-4 p-4 lg:grid-cols-[0.85fr_1.15fr]">
        <div className={`rounded-md border p-5 ${toneClass(active.tone, "outline")}`}>
          <p className="text-sm text-slate-500">Central synthesis</p>
          <h3 className="mt-3 text-balance font-serif text-3xl font-semibold text-slate-950">Decision queue conductor</h3>
          <p className="mt-4 text-pretty text-sm leading-6 text-slate-600">
            Routes findings from {active.name.toLowerCase()} into one ranked queue with action, confidence, and risk.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {agents.map((agent) => (
            <button
              key={agent.name}
              type="button"
              onClick={() => setActive(agent)}
              className={`cursor-pointer rounded-md border p-4 text-left transition ${
                active.name === agent.name ? toneClass(agent.tone, "outline") : "border-slate-200 bg-slate-50 hover:border-slate-400"
              }`}
            >
              <p className="text-sm font-semibold text-slate-950">{agent.name}</p>
              <p className="mt-2 text-pretty text-sm leading-6 text-slate-600">{agent.body}</p>
            </button>
          ))}
        </div>
      </div>
    </MacWindow>
  );
}

function FeedbackLoop() {
  const [active, setActive] = useState(loopSteps[0]);

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {loopSteps.map((step) => (
        <button
          key={step[0]}
          type="button"
          onClick={() => setActive(step)}
          className={`cursor-pointer rounded-lg border bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-cyan-300 ${
            active[0] === step[0] ? "border-cyan-300 shadow-md" : "border-slate-200"
          }`}
        >
          <div className="flex size-8 items-center justify-center rounded bg-slate-950 text-sm font-semibold text-white">
            {step[0]}
          </div>
          <h3 className="mt-4 text-lg font-semibold text-slate-950">{step[1]}</h3>
          <p className="mt-2 text-pretty text-sm leading-6 text-slate-600">{step[2]}</p>
        </button>
      ))}
    </div>
  );
}

function MacWindow({
  title,
  subtitle,
  className = "bg-white",
  children,
}: {
  title: string;
  subtitle: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`overflow-hidden rounded-xl border border-slate-300 shadow-xl ${className}`}>
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="size-3 rounded-full bg-rose-400" />
          <span className="size-3 rounded-full bg-amber-400" />
          <span className="size-3 rounded-full bg-emerald-400" />
        </div>
        <div className="text-center">
          <p className="text-xs font-semibold text-slate-700">{title}</p>
          <p className="text-[11px] text-slate-500">{subtitle}</p>
        </div>
        <span className="w-14 text-right text-[11px] text-slate-400">demo</span>
      </div>
      <div className="bg-white">{children}</div>
    </div>
  );
}

function SectionIntro({
  kicker,
  title,
  body,
}: {
  kicker: string;
  title: string;
  body: string;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-cyan-800">{kicker}</p>
      <h2 className="mt-3 text-balance font-serif text-4xl font-semibold leading-tight text-slate-950">
        {title}
      </h2>
      <p className="mt-5 text-pretty text-base leading-7 text-slate-600">{body}</p>
    </div>
  );
}

function Panel({
  title,
  note,
  tone,
  children,
}: {
  title: string;
  note: string;
  tone: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`rounded-xl border bg-white p-5 shadow-sm ${toneClass(tone, "ring")}`}>
      <div className="mb-5 flex items-start justify-between gap-4">
        <h3 className="text-lg font-semibold text-slate-950">{title}</h3>
        <p className="text-right text-xs text-slate-500">{note}</p>
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className={`p-4 ${toneClass(tone, "soft")}`}>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 text-pretty text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className={`rounded-md border p-3 ${toneClass(tone, "soft")}`}>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold tabular-nums text-slate-950">{value}</p>
    </div>
  );
}

function RoadmapItem({
  stage,
  title,
  body,
  tone,
}: {
  stage: string;
  title: string;
  body: string;
  tone: string;
}) {
  return (
    <div className={`rounded-xl border bg-white p-5 shadow-sm ${toneClass(tone, "ring")}`}>
      <p className="text-xs font-medium text-slate-500">{stage}</p>
      <h3 className="mt-2 text-lg font-semibold text-slate-950">{title}</h3>
      <p className="mt-2 text-pretty text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

function LogoMark() {
  return (
    <span className="grid size-9 place-items-center rounded-lg border border-slate-300 bg-white shadow-sm">
      <span className="grid size-5 grid-cols-2 gap-0.5">
        <span className="rounded-sm bg-cyan-500" />
        <span className="rounded-sm bg-emerald-500" />
        <span className="rounded-sm bg-amber-500" />
        <span className="rounded-sm bg-slate-950" />
      </span>
    </span>
  );
}

function toneClass(tone: string, variant: "soft" | "badge" | "outline" | "ring" | "hover") {
  const classes: Record<string, Record<string, string>> = {
    cyan: {
      soft: "border-cyan-100 bg-cyan-50",
      badge: "bg-cyan-100 text-cyan-800",
      outline: "border-cyan-300 bg-cyan-50 p-3",
      ring: "border-cyan-200",
      hover: "hover:bg-cyan-50",
    },
    emerald: {
      soft: "border-emerald-100 bg-emerald-50",
      badge: "bg-emerald-100 text-emerald-800",
      outline: "border-emerald-300 bg-emerald-50 p-3",
      ring: "border-emerald-200",
      hover: "hover:bg-emerald-50",
    },
    amber: {
      soft: "border-amber-100 bg-amber-50",
      badge: "bg-amber-100 text-amber-800",
      outline: "border-amber-300 bg-amber-50 p-3",
      ring: "border-amber-200",
      hover: "hover:bg-amber-50",
    },
    rose: {
      soft: "border-rose-100 bg-rose-50",
      badge: "bg-rose-100 text-rose-800",
      outline: "border-rose-300 bg-rose-50 p-3",
      ring: "border-rose-200",
      hover: "hover:bg-rose-50",
    },
  };

  return classes[tone]?.[variant] ?? classes.cyan[variant];
}
