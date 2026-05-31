export function formatLei(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M lei`;
  if (n >= 1_000) return `${Math.round(n / 1_000).toLocaleString("ro-RO")}K lei`;
  return `${Math.round(n).toLocaleString("ro-RO")} lei`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ro-RO", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
