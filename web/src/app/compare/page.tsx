"use client";

import { useEffect } from "react";
import { usePremium } from "@/hooks/usePremium";
import { useScenarios } from "@/hooks/useScenarios";
import { Scenario } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import Link from "next/link";

function MetricRow({ label, values, format = "currency", highlight = "high" }: {
  label: string;
  values: (number | null)[];
  format?: "currency" | "percent" | "month" | "number";
  highlight?: "high" | "low" | "none";
}) {
  const formatted = values.map((v) => {
    if (v == null) return "—";
    switch (format) {
      case "currency": return formatCurrency(v);
      case "percent": return formatPercent(v);
      case "month": return v >= 0 ? `Yr ${Math.floor(v / 12) + 1}, Mo ${(v % 12) + 1}` : "Never";
      case "number": return String(v);
    }
  });

  // Find best value index
  const numericValues = values.filter((v): v is number => v != null);
  let bestIdx = -1;
  if (highlight !== "none" && numericValues.length > 1) {
    const target = highlight === "high" ? Math.max(...numericValues) : Math.min(...numericValues);
    bestIdx = values.indexOf(target);
  }

  return (
    <tr className="border-b border-gray-50 last:border-0">
      <td className="py-2 pr-3 text-[11px] text-gray-500 whitespace-nowrap">{label}</td>
      {formatted.map((v, i) => (
        <td key={i} className={`py-2 px-2 text-xs text-center ${i === bestIdx ? "font-semibold text-emerald-600" : "text-gray-700"}`}>
          {v}
        </td>
      ))}
    </tr>
  );
}

function ScenarioColumn({ scenario }: { scenario: Scenario }) {
  const r = scenario.response;
  if (!r) return null;

  const diff = r.avg_buyer_net_worth - r.avg_renter_net_worth;
  const buyerWins = diff > 0;

  return (
    <th className="px-2 pb-3 text-left align-bottom min-w-[140px]">
      <p className="text-xs font-semibold text-gray-700 truncate">{scenario.name}</p>
      <p className={`text-[10px] font-medium mt-0.5 ${buyerWins ? "text-emerald-600" : "text-rose-500"}`}>
        {buyerWins ? "Buy" : "Rent"} +{formatCurrency(Math.abs(diff))}
      </p>
      {scenario.data_vintage && (
        <p className="text-[9px] text-gray-400">Data: {scenario.data_vintage}</p>
      )}
    </th>
  );
}

export default function ComparePage() {
  const { isPro } = usePremium();
  const scenarioCtx = useScenarios(isPro);
  const scenarios = scenarioCtx.scenarios.filter((s) => s.response != null);

  if (!isPro) {
    return (
      <main className="min-h-screen">
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-12 text-center">
          <p className="text-sm text-gray-500">Scenario comparison is a Pro feature.</p>
        </div>
      </main>
    );
  }

  if (scenarios.length === 0) {
    return (
      <main className="min-h-screen">
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-12 text-center">
          <p className="text-sm text-gray-500">No saved scenarios to compare.</p>
          <p className="text-xs text-gray-400 mt-1">
            <Link href="/" className="underline hover:text-gray-600">Run a simulation</Link> and save it first.
          </p>
        </div>
      </main>
    );
  }

  if (scenarios.length === 1) {
    return (
      <main className="min-h-screen">
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-12 text-center">
          <p className="text-sm text-gray-500">You need at least 2 saved scenarios to compare.</p>
          <p className="text-xs text-gray-400 mt-1">
            You have 1 saved. <Link href="/" className="underline hover:text-gray-600">Run another</Link> with different settings.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen pb-10">
      <Header />

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-gray-800">Compare Scenarios</h2>
          <p className="text-xs text-gray-400 mt-1">Side-by-side comparison of your {scenarios.length} saved scenarios</p>
        </div>

        <div className="overflow-x-auto -mx-4 px-4">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="pb-3 pr-3" />
                {scenarios.map((s) => (
                  <ScenarioColumn key={s.id} scenario={s} />
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Property */}
              <tr><td colSpan={scenarios.length + 1} className="pt-4 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Property</td></tr>
              <MetricRow label="Home Price" values={scenarios.map((s) => s.response!.house_price)} highlight="low" />
              <MetricRow label="Mortgage Rate" values={scenarios.map((s) => s.response!.mortgage_rate)} format="percent" highlight="low" />
              <MetricRow label="Property Tax" values={scenarios.map((s) => s.response!.property_tax_rate)} format="percent" highlight="low" />
              <MetricRow label="Down Payment" values={scenarios.map((s) => (s.inputs.down_payment_pct ?? 0.1) * 100)} format="number" highlight="none" />

              {/* Results */}
              <tr><td colSpan={scenarios.length + 1} className="pt-4 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Results</td></tr>
              <MetricRow label="Buy Score" values={scenarios.map((s) => s.response!.buy_score)} highlight="high" />
              <MetricRow label="Verdict" values={scenarios.map((s) => null)} highlight="none" />
              <MetricRow label="Net Worth Diff" values={scenarios.map((s) => s.response!.avg_buyer_net_worth - s.response!.avg_renter_net_worth)} highlight="high" />
              <MetricRow label="Breakeven" values={scenarios.map((s) => s.response!.breakeven_month)} format="month" highlight="low" />

              {/* End State */}
              <tr><td colSpan={scenarios.length + 1} className="pt-4 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">After {scenarios[0].inputs.years ?? 10} Years</td></tr>
              <MetricRow label="Home Value" values={scenarios.map((s) => s.response!.monthly[s.response!.monthly.length - 1].home_value)} highlight="high" />
              <MetricRow label="Equity Built" values={scenarios.map((s) => s.response!.monthly[s.response!.monthly.length - 1].buyer_equity)} highlight="high" />
              <MetricRow label="Buyer Net Worth" values={scenarios.map((s) => s.response!.monthly[s.response!.monthly.length - 1].buyer_net_worth)} highlight="high" />
              <MetricRow label="Renter Net Worth" values={scenarios.map((s) => s.response!.monthly[s.response!.monthly.length - 1].renter_net_worth)} highlight="high" />

              {/* Monthly Costs */}
              <tr><td colSpan={scenarios.length + 1} className="pt-4 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Monthly (Month 1)</td></tr>
              <MetricRow label="Mortgage Payment" values={scenarios.map((s) => s.response!.monthly[0].mortgage_payment)} highlight="low" />
              <MetricRow label="Total Housing Cost" values={scenarios.map((s) => s.response!.monthly[0].total_housing_cost)} highlight="low" />
              <MetricRow label="Rent" values={scenarios.map((s) => s.response!.monthly[0].rent)} highlight="low" />
              <MetricRow label="Tax Savings" values={scenarios.map((s) => s.response!.monthly[0].tax_savings)} highlight="high" />

              {/* Settings */}
              <tr><td colSpan={scenarios.length + 1} className="pt-4 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Settings</td></tr>
              <MetricRow label="ZIP Code" values={scenarios.map(() => null)} highlight="none" />
              <MetricRow label="Horizon" values={scenarios.map((s) => s.inputs.years ?? 10)} format="number" highlight="none" />
              <MetricRow label="Outlook" values={scenarios.map(() => null)} highlight="none" />
            </tbody>
          </table>

          {/* Verdict row (special — text not numbers) */}
        </div>

        {/* Text rows that MetricRow can't handle */}
        <div className="overflow-x-auto -mx-4 px-4">
          <div className="flex gap-3">
            {scenarios.map((s) => (
              <div key={s.id} className="flex-1 min-w-[140px] rounded-xl border border-gray-100 bg-white/60 p-3 text-center">
                <p className="text-[10px] text-gray-400">{s.name}</p>
                <p className="text-sm font-semibold text-gray-700 mt-1">{s.response!.verdict}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">
                  {s.inputs.zip_code ? `ZIP ${s.inputs.zip_code}` : "National avg"} · {s.inputs.outlook_preset ?? "historical"}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

function Header() {
  return (
    <header className="bg-white/70 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-400 to-violet-400 flex items-center justify-center">
            <span className="text-white text-sm font-bold">R</span>
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-800 leading-tight">Compare Scenarios</h1>
            <p className="text-[10px] text-gray-400 leading-tight">Side-by-side analysis</p>
          </div>
        </Link>
        <Link href="/#results" className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to results
        </Link>
      </div>
    </header>
  );
}
