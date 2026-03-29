"use client";

import { useMemo } from "react";
import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Line } from "recharts";
import { MonthlyData, PercentileBands } from "@/lib/types";
import { formatCompact, formatCurrency } from "@/lib/formatters";
import ChartCard from "./ChartCard";

interface Props {
  monthly: MonthlyData[];
  bands?: PercentileBands;
}

export default function HomeValueChart({ monthly, bands }: Props) {
  const data = useMemo(() => {
    return monthly.map((m, i) => {
      const point: Record<string, number> = {
        month: i,
        value: Math.round(m.home_value),
      };
      if (bands) {
        point.p10 = Math.round(bands.p10[i]);
        point.p25 = Math.round(bands.p25[i]);
        point.p75 = Math.round(bands.p75[i]);
        point.p90 = Math.round(bands.p90[i]);
      }
      return point;
    });
  }, [monthly, bands]);

  // Tight Y domain based on data range
  const allValues = bands
    ? data.flatMap((d) => [d.p10, d.p90])
    : data.map((d) => d.value);
  const dataMin = Math.min(...allValues);
  const dataMax = Math.max(...allValues);
  const pad = (dataMax - dataMin) * 0.1 || 10000;
  const yMin = Math.floor((dataMin - pad) / 10000) * 10000;
  const yMax = Math.ceil((dataMax + pad) / 10000) * 10000;

  return (
    <ChartCard title="Home Value">
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data}>
          <defs>
            <linearGradient id="outerBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity={0.08} />
              <stop offset="100%" stopColor="#34d399" stopOpacity={0.08} />
            </linearGradient>
            <linearGradient id="innerBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity={0.18} />
              <stop offset="100%" stopColor="#34d399" stopOpacity={0.18} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tickFormatter={(m) => `Yr ${Math.floor(m / 12) + 1}`} interval={11} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11, fill: "#94a3b8" }} width={55} axisLine={false} tickLine={false} domain={[yMin, yMax]} />
          <Tooltip
            formatter={(v: number, name: string) => {
              const labels: Record<string, string> = {
                value: "Median",
                p10: "10th pctile",
                p25: "25th pctile",
                p75: "75th pctile",
                p90: "90th pctile",
              };
              return [formatCurrency(v), labels[name] || name];
            }}
            labelFormatter={(m: number) => `Month ${m + 1}`}
            contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
          />
          {/* Outer band: p90 area clipped by p10 area drawn white on top */}
          {bands && (
            <Area type="monotone" dataKey="p90" stroke="none" fill="url(#outerBand)" isAnimationActive={false} />
          )}
          {bands && (
            <Area type="monotone" dataKey="p10" stroke="none" fill="white" isAnimationActive={false} />
          )}
          {/* Inner band: p75 area clipped by p25 area drawn white on top */}
          {bands && (
            <Area type="monotone" dataKey="p75" stroke="none" fill="url(#innerBand)" isAnimationActive={false} />
          )}
          {bands && (
            <Area type="monotone" dataKey="p25" stroke="none" fill="white" isAnimationActive={false} />
          )}
          {/* Median line on top */}
          <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={2.5} dot={false} name="value" isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      {bands && (
        <div className="flex items-center justify-center gap-4 mt-1 text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-2 rounded-sm" style={{ background: "rgba(52,211,153,0.18)" }} />
            25th–75th %ile
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-2 rounded-sm" style={{ background: "rgba(52,211,153,0.08)" }} />
            10th–90th %ile
          </span>
        </div>
      )}
    </ChartCard>
  );
}
