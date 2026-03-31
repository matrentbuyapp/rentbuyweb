"use client";

import { useState } from "react";
import { SummaryResponse } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/formatters";

interface Props {
  data: SummaryResponse;
  isPro?: boolean;
}

const CONFIDENCE_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  high: { bg: "bg-emerald-100", text: "text-emerald-700", label: "High confidence" },
  moderate: { bg: "bg-amber-100", text: "text-amber-700", label: "Moderate confidence" },
  low: { bg: "bg-gray-100", text: "text-gray-600", label: "Low confidence" },
};

function breakevenSub(breakeven: number | null, crossings: number, years: number): string {
  if (breakeven == null || breakeven < 0) {
    return `Renting stays ahead for ${years}+ years`;
  }
  if (crossings <= 1) return "When owning pulls ahead";
  if (crossings <= 3) return `Lead changes ${crossings} times — timing matters`;
  return `Lead changes ${crossings} times — essentially a toss-up`;
}

export default function KeyMetrics({ data, isPro }: Props) {
  const [showDetail, setShowDetail] = useState(false);
  const h = data.headline;
  const last = data.monthly[data.monthly.length - 1];
  const diff = last.buyer_net_worth - last.renter_net_worth;
  const crossings = data.crossing_count ?? 0;
  const years = Math.round(data.monthly.length / 12);

  const breakeven = data.breakeven_month;
  const breakevenText =
    breakeven == null || breakeven < 0
      ? crossings >= 4 ? "Toss-up" : "Never"
      : `Year ${Math.floor(breakeven / 12) + 1}, Mo ${(breakeven % 12) + 1}`;

  // Winner color
  const winnerColor = h
    ? h.winner === "buy" ? "from-emerald-50 to-teal-50 border-emerald-100"
      : h.winner === "rent" ? "from-rose-50 to-pink-50 border-rose-100"
      : "from-gray-50 to-slate-50 border-gray-200"
    : diff > 0 ? "from-emerald-50 to-teal-50 border-emerald-100"
    : "from-rose-50 to-pink-50 border-rose-100";

  const winnerTextColor = h
    ? h.winner === "buy" ? "text-emerald-700"
      : h.winner === "rent" ? "text-rose-700"
      : "text-gray-600"
    : diff > 0 ? "text-emerald-700" : "text-rose-700";

  const conf = h ? CONFIDENCE_STYLE[h.confidence] ?? CONFIDENCE_STYLE.moderate : null;

  return (
    <div className="space-y-3">
      {/* Headline card — the primary result */}
      {h ? (
        <div
          className={`rounded-2xl border bg-gradient-to-br p-5 card-hover cursor-pointer ${winnerColor}`}
          onClick={() => setShowDetail(!showDetail)}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <p className={`text-lg font-bold tracking-tight ${winnerTextColor}`}>{h.short}</p>
              {conf && (
                <span className={`inline-block mt-2 text-[10px] font-medium px-2 py-0.5 rounded-full ${conf.bg} ${conf.text}`}>
                  {conf.label}
                </span>
              )}
            </div>
            {h.monthly_savings > 0 && (
              <div className="text-right shrink-0">
                <p className="text-xs text-gray-400">Monthly difference</p>
                <p className={`text-sm font-semibold ${winnerTextColor}`}>${h.monthly_savings.toLocaleString()}/mo</p>
              </div>
            )}
          </div>
          {showDetail && (
            <p className="text-xs text-gray-500 mt-3 leading-relaxed">{h.detail}</p>
          )}
          {!showDetail && (
            <p className="text-[10px] text-gray-400 mt-2">Tap for details</p>
          )}
        </div>
      ) : (
        /* Fallback if headline not available */
        <div className={`rounded-2xl border bg-gradient-to-br p-5 ${winnerColor}`}>
          <p className="text-[11px] font-medium text-gray-500 mb-1">
            {diff > 0 ? "You'd be better off buying" : "You'd be better off renting"}
          </p>
          <p className={`text-lg font-bold tracking-tight ${winnerTextColor}`}>{formatCurrency(Math.abs(diff))}</p>
          <p className="text-[11px] text-gray-400 mt-1.5">more wealth after {years} years</p>
        </div>
      )}

      {/* Detail cards */}
      <div className="grid grid-cols-3 gap-3">
        {/* Breakeven */}
        <div className="rounded-2xl border bg-gradient-to-br from-indigo-50 to-violet-50 border-indigo-100 p-4 card-hover">
          <p className="text-[11px] font-medium text-gray-500 mb-1">Buying Pays Off At</p>
          <p className={`text-base font-bold tracking-tight ${breakeven == null || breakeven < 0 ? "text-gray-500" : "text-indigo-700"}`}>
            {breakevenText}
          </p>
          <p className="text-[10px] text-gray-400 mt-1">{breakevenSub(breakeven, crossings, years)}</p>
        </div>

        {/* Home Value */}
        <div className="rounded-2xl border bg-gradient-to-br from-sky-50 to-cyan-50 border-sky-100 p-4 card-hover">
          <p className="text-[11px] font-medium text-gray-500 mb-1">Home Would Be Worth</p>
          <p className="text-base font-bold tracking-tight text-sky-700">{formatCurrency(last.home_value)}</p>
          <p className="text-[10px] text-gray-400 mt-1">{formatCurrency(last.buyer_equity)} in equity</p>
        </div>

        {/* Rate */}
        <div className="rounded-2xl border bg-gradient-to-br from-amber-50 to-yellow-50 border-amber-100 p-4 card-hover">
          <p className="text-[11px] font-medium text-gray-500 mb-1">Mortgage Rate</p>
          <p className="text-base font-bold tracking-tight text-amber-700">{formatPercent(data.mortgage_rate)}</p>
          <p className="text-[10px] text-gray-400 mt-1">{formatPercent(data.property_tax_rate)} property tax</p>
        </div>
      </div>

      {/* Pro detail row */}
      {isPro && (
        <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-[11px] text-gray-400 px-1">
          <span>Score: <span className="font-medium text-gray-600">{data.buy_score}/100</span></span>
          <span className="text-gray-200">|</span>
          <span>Verdict: <span className="font-medium text-gray-600">{data.verdict}</span></span>
          {crossings > 0 && (
            <>
              <span className="text-gray-200">|</span>
              <span>Lead changes: <span className="font-medium text-gray-600">{crossings}x</span></span>
            </>
          )}
          {data.refi_summary && (
            <>
              <span className="text-gray-200">|</span>
              <span>
                Refi: <span className="font-medium text-emerald-600">
                  {Math.round(data.refi_summary.pct_sims_refinanced * 100)}% chance, saves {formatCurrency(data.refi_summary.refi_benefit)}
                </span>
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
