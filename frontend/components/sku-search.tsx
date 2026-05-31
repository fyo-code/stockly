"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SearchResult {
  sku_id: string;
  sku_name: string;
  category: string;
}

export function SkuSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      return;
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/api/sku/search?q=${encodeURIComponent(query)}`);
        if (res.ok) {
          const data = await res.json();
          setResults(data.results ?? []);
          setOpen(true);
          setActiveIndex(-1);
        }
      } catch {
        // backend unreachable — silent fail
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function select(sku: SearchResult) {
    setQuery("");
    setResults([]);
    setOpen(false);
    router.push(`/sku/${sku.sku_id}`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      select(results[activeIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapperRef} className="relative w-56">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          const nextQuery = e.target.value;
          setQuery(nextQuery);
          if (nextQuery.trim().length < 2) {
            setResults([]);
            setOpen(false);
          }
        }}
        onKeyDown={handleKeyDown}
        placeholder="Search SKU…"
        className="w-full text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent transition-colors"
      />

      {open && results.length > 0 && (
        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white rounded-xl border border-gray-200 shadow-lg max-h-72 overflow-y-auto">
          {results.map((r, i) => (
            <button
              key={r.sku_id}
              onClick={() => select(r)}
              className={`w-full text-left px-4 py-2.5 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0 ${
                i === activeIndex ? "bg-blue-50" : ""
              }`}
            >
              <p className="text-sm font-medium text-gray-900 truncate">{r.sku_name}</p>
              <p className="text-xs text-gray-400">
                {r.category} · {r.sku_id}
              </p>
            </button>
          ))}
        </div>
      )}

      {open && query.trim().length >= 2 && results.length === 0 && (
        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white rounded-xl border border-gray-200 shadow-lg px-4 py-3">
          <p className="text-xs text-gray-400">No SKUs found for &quot;{query}&quot;</p>
        </div>
      )}
    </div>
  );
}
