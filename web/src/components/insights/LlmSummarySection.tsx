"use client";

import { LlmSummaryResponse } from "@/lib/types";

interface Props {
  data: LlmSummaryResponse | null;
  loading: boolean;
  onLoad: () => void;
}

export default function LlmSummarySection({ data, loading, onLoad }: Props) {
  if (!data && !loading) {
    return (
      <button
        onClick={onLoad}
        className="w-full rounded-xl bg-white/60 border border-dashed border-gray-200 p-6 text-center
          hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors"
      >
        <p className="text-sm text-gray-500">Generate AI Summary</p>
        <p className="text-[11px] text-gray-400 mt-1">Get a plain-English analysis of your situation</p>
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-5 h-5 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin" />
        <span className="text-xs text-gray-400 ml-2">Writing your analysis...</span>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-4">
      {/* Main summary */}
      <p className="text-sm text-gray-700 leading-relaxed">{data.summary}</p>

      {/* Cost summary */}
      {data.buy_costs_summary && (
        <p className="text-xs text-gray-500 italic">{data.buy_costs_summary}</p>
      )}

      {/* Pros columns */}
      <div className="grid grid-cols-2 gap-4">
        {data.buy_pros.length > 0 && (
          <div>
            <p className="text-xs font-medium text-emerald-600 mb-1.5">If you buy</p>
            <ul className="space-y-1">
              {data.buy_pros.map((p, i) => (
                <li key={i} className="text-[11px] text-gray-600 flex items-start gap-1.5">
                  <span className="text-emerald-400 mt-0.5 shrink-0">+</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.rent_pros.length > 0 && (
          <div>
            <p className="text-xs font-medium text-amber-600 mb-1.5">If you rent</p>
            <ul className="space-y-1">
              {data.rent_pros.map((p, i) => (
                <li key={i} className="text-[11px] text-gray-600 flex items-start gap-1.5">
                  <span className="text-amber-400 mt-0.5 shrink-0">+</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Costs/risks */}
      {(data.buy_costs.length > 0 || data.rent_costs.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {data.buy_costs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-rose-500 mb-1.5">Buying risks</p>
              <ul className="space-y-1">
                {data.buy_costs.map((c, i) => (
                  <li key={i} className="text-[11px] text-gray-500 flex items-start gap-1.5">
                    <span className="text-rose-300 mt-0.5 shrink-0">&minus;</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.rent_costs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-rose-500 mb-1.5">Renting risks</p>
              <ul className="space-y-1">
                {data.rent_costs.map((c, i) => (
                  <li key={i} className="text-[11px] text-gray-500 flex items-start gap-1.5">
                    <span className="text-rose-300 mt-0.5 shrink-0">&minus;</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Verdict */}
      <div className="rounded-xl bg-white/60 border border-gray-100 p-3 text-center">
        <p className="text-xs text-gray-400">AI Verdict</p>
        <p className="text-sm font-semibold text-gray-700">{data.verdict}</p>
      </div>
    </div>
  );
}
