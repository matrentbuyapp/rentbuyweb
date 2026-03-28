"use client";

import { SummaryResponse } from "@/lib/types";
import KeyMetrics from "./KeyMetrics";
import NetWorthChart from "./NetWorthChart";
import HomeValueChart from "./HomeValueChart";
import CostBreakdownChart from "./CostBreakdownChart";
import RentVsBuyChart from "./RentVsBuyChart";
import EquityGrowthChart from "./EquityGrowthChart";
import CumulativeCostChart from "./CumulativeCostChart";
import ProInsights from "./ProInsights";

interface Props {
  result: SummaryResponse | null;
  loading: boolean;
  error: string | null;
  isPro: boolean;
}

export default function ResultsDashboard({ result, loading, error, isPro }: Props) {
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
    return (
      <div className="rounded-2xl border border-rose-100 bg-rose-50/50 p-6">
        <p className="font-semibold text-rose-700 text-sm">Something went wrong</p>
        <p className="text-xs text-rose-500 mt-1">{error}</p>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className="space-y-4">
      <KeyMetrics data={result} />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <NetWorthChart monthly={result.monthly} />
        <RentVsBuyChart monthly={result.monthly} />
        <CostBreakdownChart monthly={result.monthly} />
        <CumulativeCostChart monthly={result.monthly} />
        <HomeValueChart monthly={result.monthly} />
        <EquityGrowthChart monthly={result.monthly} />
      </div>
      <ProInsights result={result} isPro={isPro} />
    </div>
  );
}
