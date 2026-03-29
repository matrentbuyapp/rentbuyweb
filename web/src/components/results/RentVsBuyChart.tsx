"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from "recharts";
import { MonthlyData } from "@/lib/types";
import { formatCompact, formatCurrency } from "@/lib/formatters";
import ChartCard from "./ChartCard";

interface Props { monthly: MonthlyData[]; sellMonth?: number | null; }

export default function RentVsBuyChart({ monthly, sellMonth }: Props) {
  const data = monthly.map((m, i) => ({ month: i, rent: Math.round(m.rent), buy: Math.round(m.total_housing_cost) }));
  const allValues = data.flatMap((d) => [d.rent, d.buy]);
  const dataMin = Math.min(...allValues);
  const dataMax = Math.max(...allValues);
  const pad = (dataMax - dataMin) * 0.15 || 200;
  const yMin = Math.max(0, Math.floor((dataMin - pad) / 250) * 250);
  const yMax = Math.ceil((dataMax + pad) / 250) * 250;

  return (
    <ChartCard title="Monthly Cost: Rent vs Buy">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tickFormatter={(m) => `Yr ${Math.floor(m / 12) + 1}`} interval={11} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11, fill: "#94a3b8" }} width={55} axisLine={false} tickLine={false} domain={[yMin, yMax]} />
          <Tooltip formatter={(v: number) => formatCurrency(v)} labelFormatter={(m: number) => `Month ${m + 1}`}
            contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }} />
          <Legend iconType="line" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
          <Line type="monotone" dataKey="rent" stroke="#f59e0b" strokeWidth={2.5} dot={false} name="Rent" />
          <Line type="monotone" dataKey="buy" stroke="#6366f1" strokeWidth={2.5} dot={false} name="Buy (total)" />
          {sellMonth != null && (
            <ReferenceLine x={sellMonth} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "Sell", fontSize: 10, fill: "#ef4444" }} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
