"use client";

import { TrendResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";

interface Props {
  data: TrendResponse | null;
  loading: boolean;
  onLoad: () => void;
}

export default function TrendSection({ data, loading, onLoad }: Props) {
  if (!data && !loading) {
    return (
      <button onClick={onLoad}
        className="w-full rounded-xl bg-white/60 border border-dashed border-gray-200 p-6 text-center hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors">
        <p className="text-sm text-gray-500">Run Timing Analysis</p>
        <p className="text-[11px] text-gray-400 mt-1">Should you buy now or wait?</p>
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-5 h-5 rounded-full border-2 border-emerald-200 border-t-emerald-500 animate-spin" />
        <span className="text-xs text-gray-400 ml-2">Simulating delays...</span>
      </div>
    );
  }

  if (!data || data.points.length === 0) return null;

  const best = data.points.reduce((a, b) => a.net_difference > b.net_difference ? a : b);
  const now = data.points[0];
  const maxAbs = Math.max(...data.points.map((p) => Math.abs(p.net_difference)), 1);

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="rounded-xl bg-white/60 border border-gray-100 p-3">
        <p className="text-sm text-gray-700">
          {best.delay_months === 0 ? (
            <><span className="font-semibold text-emerald-600">Buy now</span> is your best timing.</>
          ) : (
            <>
              <span className="font-semibold text-emerald-600">Waiting {best.delay_months} months</span> gives the best outcome
              {now.net_difference !== best.net_difference && (
                <> — {formatCurrency(best.net_difference - now.net_difference)} better than buying now</>
              )}.
            </>
          )}
        </p>
      </div>

      {/* Bar chart */}
      <div className="space-y-1">
        {data.points.map((p) => {
          const isBest = p.delay_months === best.delay_months;
          const pct = Math.abs(p.net_difference) / maxAbs * 100;

          return (
            <div key={p.delay_months} className="flex items-center gap-2">
              <span className={`text-[11px] w-12 shrink-0 ${isBest ? "font-bold text-emerald-600" : "text-gray-500"}`}>
                {p.delay_months === 0 ? "Now" : `+${p.delay_months}mo`}
              </span>
              <div className="flex-1 h-5 bg-gray-50 rounded-full overflow-hidden relative">
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-200" />
                <div
                  className={`absolute top-0.5 bottom-0.5 rounded-full transition-all ${p.net_difference >= 0 ? "bg-emerald-400" : "bg-rose-400"} ${isBest ? "opacity-100" : "opacity-50"}`}
                  style={{
                    width: `${pct / 2}%`,
                    ...(p.net_difference >= 0 ? { left: "50%" } : { right: "50%" }),
                  }}
                />
              </div>
              <span className={`text-[10px] w-20 text-right shrink-0 font-medium ${p.net_difference >= 0 ? "text-emerald-600" : "text-rose-500"}`}>
                {formatCurrency(p.net_difference)}
              </span>
              <span className="text-[10px] text-gray-400 w-10 text-right shrink-0">
                {(p.mortgage_rate_used * 100).toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-gray-400 text-center">
        Buy advantage at each delay. Center = break-even. Right column = projected rate.
      </p>
    </div>
  );
}
