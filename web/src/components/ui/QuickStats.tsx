"use client";

import { SummaryResponse } from "@/lib/types";

interface Props {
  result: SummaryResponse;
}

export default function QuickStats({ result }: Props) {
  const monthly = result.monthly?.[0];
  const diff = (result.avg_buyer_net_worth ?? 0) - (result.avg_renter_net_worth ?? 0);
  const buyerWins = diff > 0;

  return (
    <div className="flex items-center justify-center flex-wrap gap-x-3 gap-y-1 sm:gap-x-5 text-[11px] text-gray-400">
      <span>
        <span className="text-gray-500 font-medium">${(result.house_price ?? 0).toLocaleString()}</span>
        {" "}@ {((result.mortgage_rate ?? 0) * 100).toFixed(1)}%
      </span>
      <span className="text-gray-200">|</span>
      <span>
        <span className="text-gray-500 font-medium">${Math.round(monthly?.total_housing_cost ?? 0).toLocaleString()}</span>/mo
      </span>
      <span className="text-gray-200">|</span>
      <span className={buyerWins ? "text-emerald-500" : "text-rose-500"}>
        {buyerWins ? "Buy" : "Rent"} +${Math.abs(Math.round(diff)).toLocaleString()}
      </span>
    </div>
  );
}
