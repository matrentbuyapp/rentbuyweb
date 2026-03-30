"use client";

import { useState } from "react";
import { WhatIfResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";

interface Props {
  data: WhatIfResponse | null;
  loading: boolean;
  onLoad: () => void;
}

export default function WhatIfSection({ data, loading, onLoad }: Props) {
  if (!data && !loading) {
    return (
      <button
        onClick={onLoad}
        className="w-full rounded-xl bg-white/60 border border-dashed border-gray-200 p-6 text-center
          hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors"
      >
        <p className="text-sm text-gray-500">Run What-If Analysis</p>
        <p className="text-[11px] text-gray-400 mt-1">See how common changes would affect your outcome</p>
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-5 h-5 rounded-full border-2 border-indigo-200 border-t-indigo-500 animate-spin" />
        <span className="text-xs text-gray-400 ml-2">Running scenarios...</span>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-gray-400">
        Base case: {data.base_net_diff > 0 ? "Buy" : "Rent"} wins by {formatCurrency(Math.abs(data.base_net_diff))}
      </p>
      <div className="space-y-1.5">
        {data.scenarios.map((s) => (
          <div
            key={s.id}
            className="flex items-center gap-3 rounded-xl bg-white/60 border border-gray-100 p-3"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700">{s.name}</p>
              <p className="text-[11px] text-gray-400">{s.description}</p>
            </div>
            <div className="text-right shrink-0">
              <p className={`text-sm font-semibold ${s.net_difference > 0 ? "text-emerald-600" : "text-rose-500"}`}>
                {s.net_difference > 0 ? "Buy" : "Rent"} +{formatCurrency(Math.abs(s.net_difference))}
              </p>
              <p className={`text-[10px] ${s.delta_from_base > 0 ? "text-emerald-500" : s.delta_from_base < 0 ? "text-rose-400" : "text-gray-400"}`}>
                {s.delta_from_base > 0 ? "+" : ""}{formatCurrency(s.delta_from_base)} vs base
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
