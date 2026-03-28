"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { MonthlyData } from "@/lib/types";
import { formatCompact, formatCurrency } from "@/lib/formatters";
import ChartCard from "./ChartCard";

interface Props {
  monthly: MonthlyData[];
}

export default function NetWorthChart({ monthly }: Props) {
  const buyerWinsAtEnd =
    monthly[monthly.length - 1].buyer_net_worth > monthly[monthly.length - 1].renter_net_worth;
  let breakeven = -1;
  if (buyerWinsAtEnd) {
    for (let i = monthly.length - 1; i >= 0; i--) {
      if (monthly[i].buyer_net_worth <= monthly[i].renter_net_worth) {
        breakeven = i + 1;
        break;
      }
    }
    if (breakeven === -1) breakeven = 0;
  }

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
          <Line type="monotone" dataKey="buyer" stroke="#6366f1" strokeWidth={2.5} dot={false} name="Buyer" />
          <Line type="monotone" dataKey="renter" stroke="#f59e0b" strokeWidth={2.5} dot={false} name="Renter" />
          {breakeven > 0 && (
            <ReferenceLine x={breakeven} stroke="#34d399" strokeDasharray="4 4" label={{ value: "Breakeven", fontSize: 10, fill: "#10b981" }} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
