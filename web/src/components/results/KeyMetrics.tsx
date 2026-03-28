"use client";

import { SummaryResponse } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/formatters";

interface Props {
  data: SummaryResponse;
}

export default function KeyMetrics({ data }: Props) {
  const last = data.monthly[data.monthly.length - 1];
  const diff = last.buyer_net_worth - last.renter_net_worth;
  const buyerWins = diff > 0;

  let breakeven = -1;
  if (buyerWins) {
    for (let i = data.monthly.length - 1; i >= 0; i--) {
      if (data.monthly[i].buyer_net_worth <= data.monthly[i].renter_net_worth) {
        breakeven = i + 1;
        break;
      }
    }
    if (breakeven === -1) breakeven = 0;
  }
  const breakevenText =
    breakeven < 0
      ? "Never"
      : `Year ${Math.floor(breakeven / 12) + 1}, Mo ${(breakeven % 12) + 1}`;

  const years = Math.round(data.monthly.length / 12);
  const cards = [
    {
      label: buyerWins
        ? `You'd be better off buying`
        : `You'd be better off renting`,
      value: formatCurrency(Math.abs(diff)),
      bg: buyerWins ? "from-emerald-50 to-teal-50 border-emerald-100" : "from-rose-50 to-pink-50 border-rose-100",
      color: buyerWins ? "text-emerald-700" : "text-rose-700",
      sub: `more wealth after ${years} years`,
    },
    {
      label: "Buying Pays Off At",
      value: breakevenText,
      bg: "from-indigo-50 to-violet-50 border-indigo-100",
      color: breakeven < 0 ? "text-gray-500" : "text-indigo-700",
      sub: breakeven < 0
        ? `Renting stays ahead for ${years}+ years`
        : "When owning starts winning",
    },
    {
      label: "Your Home Would Be Worth",
      value: formatCurrency(last.home_value),
      bg: "from-sky-50 to-cyan-50 border-sky-100",
      color: "text-sky-700",
      sub: `${formatCurrency(last.buyer_equity)} in equity you own`,
    },
    {
      label: "Your Mortgage Rate",
      value: formatPercent(data.mortgage_rate),
      bg: "from-amber-50 to-yellow-50 border-amber-100",
      color: "text-amber-700",
      sub: `${formatPercent(data.property_tax_rate)} property tax`,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-2xl border bg-gradient-to-br p-4 card-hover ${card.bg}`}
        >
          <p className="text-[11px] font-medium text-gray-500 mb-1">{card.label}</p>
          <p className={`text-lg font-bold tracking-tight ${card.color}`}>{card.value}</p>
          <p className="text-[11px] text-gray-400 mt-1.5">{card.sub}</p>
        </div>
      ))}
    </div>
  );
}
