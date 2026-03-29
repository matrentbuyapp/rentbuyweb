"use client";

import { useEffect, useState } from "react";
import { SummaryResponse, SummaryRequest } from "@/lib/types";
import { loadResult } from "@/lib/resultStore";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { usePremium } from "@/hooks/usePremium";
import ProBadge from "@/components/ui/ProBadge";
/* eslint-disable @next/next/no-img-element */

interface StoredData {
  result: SummaryResponse;
  inputs: SummaryRequest;
}

const SECTIONS = [
  {
    id: "ai-summary",
    title: "AI-Powered Summary",
    description: "A plain-English analysis of your situation with personalized pros and cons.",
    screenshot: "/preview/summary.png",
    accentBorder: "border-violet-200",
    accentBg: "from-violet-50 to-purple-50",
    iconBg: "bg-violet-100 text-violet-600",
  },
  {
    id: "sensitivity",
    title: "What-If Analysis",
    description: "See how changing your rate, price, or down payment would shift the outcome.",
    screenshot: null,
    accentBorder: "border-sky-200",
    accentBg: "from-sky-50 to-blue-50",
    iconBg: "bg-sky-100 text-sky-600",
  },
  {
    id: "trend",
    title: "Best Time to Buy",
    description: "Should you buy now or wait? See how delaying changes the picture.",
    screenshot: "/preview/trend.png",
    accentBorder: "border-emerald-200",
    accentBg: "from-emerald-50 to-teal-50",
    iconBg: "bg-emerald-100 text-emerald-600",
  },
  {
    id: "zip-compare",
    title: "Neighborhood Comparison",
    description: "Compare buying outcomes across nearby ZIP codes.",
    screenshot: "/preview/map.png",
    accentBorder: "border-rose-200",
    accentBg: "from-rose-50 to-pink-50",
    iconBg: "bg-rose-100 text-rose-600",
  },
  {
    id: "scenarios",
    title: "Save & Compare Scenarios",
    description: "Save different scenarios, compare them side by side, and get alerts when market changes affect your decision.",
    screenshot: null,
    accentBorder: "border-indigo-200",
    accentBg: "from-indigo-50 to-blue-50",
    iconBg: "bg-indigo-100 text-indigo-600",
  },
  {
    id: "buying-memo",
    title: "Export Buying Memo",
    description: "Download a personalized PDF ready to share with your lender or real estate agent.",
    screenshot: null,
    accentBorder: "border-amber-200",
    accentBg: "from-amber-50 to-orange-50",
    iconBg: "bg-amber-100 text-amber-600",
  },
];

export default function InsightsPage() {
  const [data, setData] = useState<StoredData | null>(null);
  const { isPro } = usePremium();

  useEffect(() => {
    const stored = loadResult();
    if (stored) setData(stored);
  }, []);

  const result = data?.result;
  const inputs = data?.inputs;

  return (
    <main className="min-h-screen pb-20">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-400 to-violet-400 flex items-center justify-center">
              <span className="text-white text-sm font-bold">R</span>
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-800 leading-tight">Pro Insights</h1>
              <p className="text-[10px] text-gray-400 leading-tight">Deeper analysis for your scenario</p>
            </div>
          </a>
          <a
            href="/"
            className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to calculator
          </a>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Context banner — what scenario we're looking at */}
        {result && inputs ? (
          <div className="rounded-2xl border border-gray-100 bg-white/70 backdrop-blur-sm p-5">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
              <div>
                <span className="text-gray-400 text-xs">Home Price</span>
                <p className="font-semibold text-gray-700">{formatCurrency(result.house_price)}</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Rate</span>
                <p className="font-semibold text-gray-700">{formatPercent(result.mortgage_rate)}</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Verdict</span>
                <p className="font-semibold text-gray-700">{result.verdict}</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Score</span>
                <p className="font-semibold text-gray-700">{result.buy_score}/100</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Advantage</span>
                <p className={`font-semibold ${result.avg_buyer_net_worth > result.avg_renter_net_worth ? "text-emerald-600" : "text-rose-600"}`}>
                  {result.avg_buyer_net_worth > result.avg_renter_net_worth ? "Buy" : "Rent"} +{formatCurrency(Math.abs(result.avg_buyer_net_worth - result.avg_renter_net_worth))}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-amber-100 bg-amber-50/50 p-5 text-center">
            <p className="text-sm text-amber-700 font-medium">No simulation results yet</p>
            <p className="text-xs text-amber-500 mt-1">
              <a href="/" className="underline hover:text-amber-600">Run a simulation</a> first to unlock Pro insights.
            </p>
          </div>
        )}

        {/* Pro feature sections */}
        {SECTIONS.map((section) => (
          <section
            key={section.id}
            id={section.id}
            className={`rounded-2xl border bg-gradient-to-br p-6 ${section.accentBorder} ${section.accentBg}`}
          >
            <div className="flex items-start gap-3 mb-4">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${section.iconBg}`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-gray-700">{section.title}</h2>
                  {!isPro && <ProBadge />}
                </div>
                <p className="text-xs text-gray-400 mt-1">{section.description}</p>
              </div>
            </div>

            {isPro && result ? (
              /* Pro user with results — placeholder for real content */
              <div className="rounded-xl bg-white/60 border border-white p-8 text-center">
                <p className="text-sm text-gray-400 italic">Coming soon — this feature is being built.</p>
              </div>
            ) : (
              /* Free user or no results — show screenshot preview or mock */
              <div className="relative rounded-xl overflow-hidden">
                {section.screenshot ? (
                  <div className="relative">
                    <img
                      src={section.screenshot}
                      alt={`${section.title} preview`}
                      className="w-full max-w-sm mx-auto rounded-xl opacity-60"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-white via-white/30 to-transparent" />
                  </div>
                ) : (
                  <div className="bg-white/40 rounded-xl p-8 opacity-50">
                    <div className="space-y-2">
                      <div className="h-3 bg-gray-200 rounded w-3/4" />
                      <div className="h-3 bg-gray-200 rounded w-1/2" />
                      <div className="h-3 bg-gray-200 rounded w-2/3" />
                      <div className="h-8 bg-gray-100 rounded mt-4" />
                      <div className="h-8 bg-gray-100 rounded" />
                    </div>
                  </div>
                )}
                {!isPro && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs font-medium text-gray-500 bg-white/80 backdrop-blur-sm rounded-full px-4 py-2 border border-gray-200/60 shadow-sm">
                      Upgrade to Pro to unlock
                    </span>
                  </div>
                )}
              </div>
            )}
          </section>
        ))}
      </div>
    </main>
  );
}
