"use client";

import { SummaryResponse } from "@/lib/types";

interface Props {
  result: SummaryResponse;
  scenarioName?: string | null;
  /** "live" shows green dot, "saved" shows bookmark icon, null shows neither */
  source?: "live" | "saved" | null;
}

export default function QuickStats({ result, scenarioName, source }: Props) {
  return (
    <div className="flex items-center justify-center flex-wrap gap-x-3 gap-y-1 sm:gap-x-5 text-[10px] text-gray-400">
      {source === "saved" && scenarioName && (
        <>
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            <span className="text-indigo-500 font-medium truncate max-w-[120px]">{scenarioName}</span>
          </span>
          <span className="text-gray-200">|</span>
        </>
      )}
      {source === "live" && (
        <>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-gray-500">Live</span>
          </span>
          <span className="text-gray-200">|</span>
        </>
      )}
      <span>
        <span className="text-gray-500 font-medium">${result.house_price.toLocaleString()}</span>
        {" "}@ {(result.mortgage_rate * 100).toFixed(1)}%
      </span>
      <span className="text-gray-200">|</span>
      <span>
        <span className="text-gray-500 font-medium">${Math.round(result.monthly[0]?.total_housing_cost ?? 0).toLocaleString()}</span>/mo
      </span>
      <span className="text-gray-200">|</span>
      <span className={result.avg_buyer_net_worth > result.avg_renter_net_worth ? "text-emerald-500" : "text-rose-500"}>
        {result.avg_buyer_net_worth > result.avg_renter_net_worth ? "Buy" : "Rent"} wins by ${Math.abs(Math.round(result.avg_buyer_net_worth - result.avg_renter_net_worth)).toLocaleString()}
      </span>
    </div>
  );
}
