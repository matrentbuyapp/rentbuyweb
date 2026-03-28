export function formatCurrency(n: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatCompact(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

export function formatPercent(n: number): string {
  return `${(n * 100).toFixed(2)}%`;
}

export function formatMonth(m: number): string {
  const yr = Math.floor(m / 12) + 1;
  const mo = (m % 12) + 1;
  return `Year ${yr}, Month ${mo}`;
}

export function yearLabel(m: number): string {
  const yr = Math.floor(m / 12) + 1;
  return `Yr ${yr}`;
}
