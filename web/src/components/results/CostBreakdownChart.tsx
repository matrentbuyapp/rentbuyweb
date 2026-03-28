"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { MonthlyData } from "@/lib/types";
import { formatCompact, formatCurrency } from "@/lib/formatters";
import ChartCard from "./ChartCard";

interface Props { monthly: MonthlyData[]; }

export default function CostBreakdownChart({ monthly }: Props) {
  const data = monthly.map((m, i) => ({
    month: i,
    mortgage: Math.round(m.mortgage_payment),
    maintenance: Math.round(m.maintenance),
    tax: Math.round(m.property_tax),
    insurance: Math.round(m.insurance),
    pmi: Math.round(m.pmi),
  }));
  return (
    <ChartCard title="Buyer Cost Breakdown">
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tickFormatter={(m) => `Yr ${Math.floor(m / 12) + 1}`} interval={11} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11, fill: "#94a3b8" }} width={55} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v: number) => formatCurrency(v)} labelFormatter={(m: number) => `Month ${m + 1}`}
            contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }} />
          <Area type="monotone" dataKey="mortgage" stackId="1" stroke="#818cf8" fill="#818cf8" fillOpacity={0.6} name="Mortgage" />
          <Area type="monotone" dataKey="tax" stackId="1" stroke="#f87171" fill="#f87171" fillOpacity={0.5} name="Property Tax" />
          <Area type="monotone" dataKey="maintenance" stackId="1" stroke="#fb923c" fill="#fb923c" fillOpacity={0.5} name="Maintenance" />
          <Area type="monotone" dataKey="insurance" stackId="1" stroke="#7dd3fc" fill="#7dd3fc" fillOpacity={0.5} name="Insurance" />
          <Area type="monotone" dataKey="pmi" stackId="1" stroke="#f9a8d4" fill="#f9a8d4" fillOpacity={0.5} name="PMI" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
