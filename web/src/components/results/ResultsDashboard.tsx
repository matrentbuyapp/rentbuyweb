"use client";

import { SummaryResponse } from "@/lib/types";
import KeyMetrics from "./KeyMetrics";
import NetWorthChart from "./NetWorthChart";
import HomeValueChart from "./HomeValueChart";
import CostBreakdownChart from "./CostBreakdownChart";
import RentVsBuyChart from "./RentVsBuyChart";
import ProInsights from "./ProInsights";

interface Props {
  result: SummaryResponse | null;
  loading: boolean;
  error: string | null;
  isPro: boolean;
  sellMonth?: number | null;
}

export default function ResultsDashboard({ result, loading, error, isPro, sellMonth }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="relative w-12 h-12 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-indigo-100"></div>
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-400 animate-spin"></div>
          </div>
          <p className="text-sm text-gray-400">Running 500 simulations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const lines = error.split("\n");
    const isValidation = lines.length > 1 || error.includes("budget") || error.includes("savings");
    return (
      <div className="rounded-2xl border border-rose-100 bg-rose-50/50 p-6">
        <p className="font-semibold text-rose-700 text-sm">
          {isValidation ? "These numbers don\u2019t quite work" : "Something went wrong"}
        </p>
        <ul className="mt-2 space-y-1.5">
          {lines.map((line, i) => (
            <li key={i} className="text-xs text-rose-600 flex items-start gap-2">
              <span className="text-rose-300 mt-0.5 shrink-0">&bull;</span>
              {line}
            </li>
          ))}
        </ul>
        {isValidation && (
          <p className="text-[11px] text-rose-400 mt-3">
            Try adjusting your savings, budget, or down payment in Settings.
          </p>
        )}
      </div>
    );
  }

  if (!result) return null;

  const warnings = result.warnings ?? [];

  return (
    <div className="space-y-4">
      {warnings.length > 0 && (
        <div className="rounded-2xl border border-amber-100 bg-amber-50/50 p-4">
          <p className="font-semibold text-amber-700 text-sm mb-1.5">Heads up</p>
          <ul className="space-y-1">
            {warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-600 flex items-start gap-2">
                <span className="text-amber-300 mt-0.5 shrink-0">&bull;</span>
                {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      <KeyMetrics data={result} isPro={isPro} />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <NetWorthChart monthly={result.monthly} breakevenMonth={result.breakeven_month} sellMonth={sellMonth} />
        <RentVsBuyChart monthly={result.monthly} sellMonth={sellMonth} />
        <CostBreakdownChart monthly={result.monthly} sellMonth={sellMonth} />
        <HomeValueChart monthly={result.monthly} bands={result.percentiles?.home_value} />
      </div>
      <ProInsights result={result} isPro={isPro} />
    </div>
  );
}
