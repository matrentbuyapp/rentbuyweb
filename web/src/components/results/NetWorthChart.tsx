"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { MonthlyData } from "@/lib/types";
import { formatCompact, formatCurrency } from "@/lib/formatters";
import ChartCard from "./ChartCard";

interface Props {
  monthly: MonthlyData[];
  breakevenMonth?: number | null;
  sellMonth?: number | null;
}

export default function NetWorthChart({ monthly, breakevenMonth, sellMonth }: Props) {
  const data = monthly.map((m, i) => ({
    month: i,
    buyer: Math.round(m.buyer_net_worth),
    renter: Math.round(m.renter_net_worth),
  }));

  return (
    <ChartCard title="Net Worth Comparison">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="month" tickFormatter={(m) => `Yr ${Math.floor(m / 12) + 1}`}
            interval={11} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#e2e8f0" }}
          />
          <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11, fill: "#94a3b8" }} width={55} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(v: number) => formatCurrency(v)}
            labelFormatter={(m: number) => `Month ${m + 1}`}
            contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
          />
          <Legend iconType="line" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
          <Line type="monotone" dataKey="buyer" stroke="#6366f1" strokeWidth={2.5} dot={false} name="Buyer" />
          <Line type="monotone" dataKey="renter" stroke="#f59e0b" strokeWidth={2.5} dot={false} name="Renter" />
          {breakevenMonth != null && breakevenMonth >= 0 && (
            <ReferenceLine x={breakevenMonth} stroke="#34d399" strokeDasharray="4 4" label={{ value: "Breakeven", fontSize: 10, fill: "#10b981" }} />
          )}
          {sellMonth != null && (
            <ReferenceLine x={sellMonth} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "Sell", fontSize: 10, fill: "#ef4444" }} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
