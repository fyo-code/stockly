"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SkuSearch } from "@/components/sku-search";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/demand", label: "Demand Forecast" },
  { href: "/dead-stock", label: "Dead Stock" },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/queue", label: "Morning Queue" },
  { href: "/scenario", label: "Scenario" },
];

export function Nav() {
  const pathname = usePathname();
  const today = new Date().toLocaleDateString("ro-RO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  if (pathname === "/") {
    return null;
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <span className="font-semibold text-gray-900 text-sm">
            Supply Chain Engine
          </span>
          <nav className="flex gap-6">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <SkuSearch />
          <span className="text-xs text-gray-400 capitalize">{today}</span>
        </div>
      </div>
    </header>
  );
}
