"use client";

import { SensitivityResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";

interface Props {
  data: SensitivityResponse | null;
  loading: boolean;
  onLoad: () => void;
}

const PARAM_LABELS: Record<string, string> = {
  mortgage_rate: "Mortgage Rate",
  house_price: "Home Price",
  down_payment_pct: "Down Payment",
  outlook: "Market Outlook",
  stay_years: "Years Owned",
  yearly_income: "Income",
  initial_cash: "Savings",
  risk_appetite: "Risk Level",
};

function barColor(val: number): string {
  if (val > 0) return "bg-emerald-400";
  return "bg-rose-400";
}

export default function SensitivitySection({ data, loading, onLoad }: Props) {
  if (!data && !loading) {
    return (
      <button onClick={onLoad}
        className="w-full rounded-xl bg-white/60 border border-dashed border-gray-200 p-6 text-center hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors">
        <p className="text-sm text-gray-500">Run Sensitivity Analysis</p>
        <p className="text-[11px] text-gray-400 mt-1">See which inputs matter most for your decision</p>
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-5 h-5 rounded-full border-2 border-sky-200 border-t-sky-500 animate-spin" />
        <span className="text-xs text-gray-400 ml-2">Sweeping parameters...</span>
      </div>
    );
  }

  if (!data) return null;

  // Compute global range for bar scaling
  const allValues = Object.values(data.axes).flatMap((pts) => pts.map((p) => p.net_difference));
  const globalMax = Math.max(Math.abs(Math.min(...allValues)), Math.abs(Math.max(...allValues)), 1);

  return (
    <div className="space-y-4">
      {/* 1D axes as mini bar charts */}
      {Object.entries(data.axes).map(([param, points]) => (
        <div key={param}>
          <p className="text-[11px] font-medium text-gray-600 mb-1.5">{PARAM_LABELS[param] || param}</p>
          <div className="space-y-1">
            {points.map((p, i) => {
              const pct = Math.abs(p.net_difference) / globalMax * 100;
              const isBase = p.param_value === (param === "mortgage_rate" ? data.base_buy_score : 0); // rough
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-500 w-24 shrink-0 text-right truncate">{p.label}</span>
                  <div className="flex-1 h-4 bg-gray-50 rounded overflow-hidden relative">
                    {/* center line */}
                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-200" />
                    {/* bar from center */}
                    <div
                      className={`absolute top-0 bottom-0 rounded ${barColor(p.net_difference)}`}
                      style={{
                        width: `${pct / 2}%`,
                        ...(p.net_difference >= 0
                          ? { left: "50%" }
                          : { right: "50%" }),
                        opacity: 0.7,
                      }}
                    />
                  </div>
                  <span className={`text-[10px] w-16 shrink-0 text-right font-medium ${p.net_difference >= 0 ? "text-emerald-600" : "text-rose-500"}`}>
                    {formatCurrency(p.net_difference)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* 2D heatmap */}
      {data.heatmap && data.heatmap.cells && data.heatmap.cells.length > 0 && (() => {
        const cells = data.heatmap.cells;
        const xLabels = [...new Set(cells.map((c) => c.x_label))];
        const yLabels = [...new Set(cells.map((c) => c.y_label))];
        const maxAbs = Math.max(...cells.map((c) => Math.abs(c.net_difference)), 1);

        function heatColor(val: number): string {
          const r = val / maxAbs;
          if (r > 0.3) return "bg-emerald-300 text-emerald-900";
          if (r > 0) return "bg-emerald-100 text-emerald-700";
          if (r > -0.3) return "bg-rose-100 text-rose-700";
          return "bg-rose-300 text-rose-900";
        }

        return (
          <div className="pt-3 border-t border-gray-100">
            <p className="text-[11px] font-medium text-gray-600 mb-2">
              {PARAM_LABELS[data.heatmap.x_param] || data.heatmap.x_param} vs {PARAM_LABELS[data.heatmap.y_param] || data.heatmap.y_param}
            </p>
            <div className="overflow-x-auto -mx-2 px-2">
              <table className="text-[10px] w-full border-collapse">
                <thead>
                  <tr>
                    <th className="p-1.5" />
                    {xLabels.map((x) => (
                      <th key={x} className="p-1.5 text-center text-gray-500 font-medium">{x}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {yLabels.map((y) => (
                    <tr key={y}>
                      <td className="p-1.5 text-gray-500 font-medium whitespace-nowrap">{y}</td>
                      {xLabels.map((x) => {
                        const cell = cells.find((c) => c.x_label === x && c.y_label === y);
                        if (!cell) return <td key={x} className="p-1.5" />;
                        return (
                          <td key={x} className={`p-1.5 text-center rounded font-medium ${heatColor(cell.net_difference)}`}>
                            {formatCurrency(cell.net_difference)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[10px] text-gray-400 mt-1.5 text-center">
              Green = buying wins, Red = renting wins
            </p>
          </div>
        );
      })()}
    </div>
  );
}
