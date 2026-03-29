"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { MonthlyData } from "@/lib/types";
import { formatCompact, formatCurrency } from "@/lib/formatters";
import ChartCard from "./ChartCard";

interface Props { monthly: MonthlyData[]; sellMonth?: number | null; }

export default function EquityGrowthChart({ monthly, sellMonth }: Props) {
  const data = monthly.map((m, i) => ({ month: i, equity: Math.round(m.buyer_equity) }));
  return (
    <ChartCard title="Equity Growth">
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tickFormatter={(m) => `Yr ${Math.floor(m / 12) + 1}`} interval={11} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11, fill: "#94a3b8" }} width={55} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v: number) => formatCurrency(v)} labelFormatter={(m: number) => `Month ${m + 1}`}
            contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }} />
          <Area type="monotone" dataKey="equity" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.2} strokeWidth={2.5} name="Equity" />
          {sellMonth != null && (
            <ReferenceLine x={sellMonth} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "Sell", fontSize: 10, fill: "#ef4444" }} />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
