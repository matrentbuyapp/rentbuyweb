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

function HeatmapTable({ heatmap }: { heatmap: SensitivityResponse["heatmap"] }) {
  const { x_axis, y_axis, x_labels, y_labels, cells } = heatmap;

  if (!cells || cells.length === 0 || x_labels.length === 0 || y_labels.length === 0) return null;

  // Flatten to find max for color scaling
  const allVals = cells.flat().map((c) => c?.net_difference).filter((v): v is number => v != null && !isNaN(v));
  if (allVals.length === 0) return null;
  const maxAbs = Math.max(...allVals.map(Math.abs), 1);

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
        {PARAM_LABELS[x_axis] || x_axis} vs {PARAM_LABELS[y_axis] || y_axis}
      </p>
      <div className="overflow-x-auto -mx-2 px-2">
        <table className="text-[10px] w-full border-collapse">
          <thead>
            <tr>
              <th key="corner" className="p-1.5" />
              {x_labels.map((x, i) => (
                <th key={`x-${i}`} className="p-1.5 text-center text-gray-500 font-medium">{x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {y_labels.map((y, yi) => (
              <tr key={`y-${yi}`}>
                <td className="p-1.5 text-gray-500 font-medium whitespace-nowrap">{y}</td>
                {x_labels.map((_, xi) => {
                  const cell = cells[yi]?.[xi];
                  if (!cell || isNaN(cell.net_difference)) {
                    return <td key={`c-${yi}-${xi}`} className="p-1.5 text-center text-gray-300">&mdash;</td>;
                  }
                  return (
                    <td key={`c-${yi}-${xi}`} className={`p-1.5 text-center rounded font-medium ${heatColor(cell.net_difference)}`}>
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
  const allValues = Object.values(data.axes).flatMap((pts) => pts.map((p) => p.net_difference)).filter((v) => !isNaN(v));
  const globalMax = allValues.length > 0 ? Math.max(Math.abs(Math.min(...allValues)), Math.abs(Math.max(...allValues)), 1) : 1;

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
      {data.heatmap && data.heatmap.cells && data.heatmap.cells.length > 0 && (
        <HeatmapTable heatmap={data.heatmap} />
      )}
    </div>
  );
}
