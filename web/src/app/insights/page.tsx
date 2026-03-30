"use client";

import { useEffect, useState, useCallback } from "react";
import { SummaryRequest, WhatIfResponse, SensitivityResponse, TrendResponse, LlmSummaryResponse } from "@/lib/types";
import { loadResult, StoredSession } from "@/lib/resultStore";
import { postWhatIf, postSensitivity, postTrend, postLlmSummary } from "@/lib/api";
import { usePremium } from "@/hooks/usePremium";
import QuickStats from "@/components/ui/QuickStats";
import ProBadge from "@/components/ui/ProBadge";
import LlmSummarySection from "@/components/insights/LlmSummarySection";
import WhatIfSection from "@/components/insights/WhatIfSection";
import SensitivitySection from "@/components/insights/SensitivitySection";
import TrendSection from "@/components/insights/TrendSection";
import Link from "next/link";
/* eslint-disable @next/next/no-img-element */

const SECTIONS = [
  { id: "ai-summary", title: "AI-Powered Summary", description: "A plain-English analysis with personalized pros and cons.", screenshot: "/preview/summary.png", border: "border-violet-200", bg: "from-violet-50 to-purple-50", iconBg: "bg-violet-100 text-violet-600" },
  { id: "whatif", title: "What-If Scenarios", description: "See how common changes would affect your outcome.", screenshot: null, border: "border-sky-200", bg: "from-sky-50 to-blue-50", iconBg: "bg-sky-100 text-sky-600" },
  { id: "sensitivity", title: "Sensitivity Analysis", description: "Which inputs matter most? Interactive heatmap included.", screenshot: null, border: "border-cyan-200", bg: "from-cyan-50 to-sky-50", iconBg: "bg-cyan-100 text-cyan-600" },
  { id: "trend", title: "Best Time to Buy", description: "Should you buy now or wait?", screenshot: "/preview/trend.png", border: "border-emerald-200", bg: "from-emerald-50 to-teal-50", iconBg: "bg-emerald-100 text-emerald-600" },
  { id: "zip-compare", title: "Neighborhood Comparison", description: "Compare buying outcomes across nearby ZIP codes.", screenshot: "/preview/map.png", border: "border-rose-200", bg: "from-rose-50 to-pink-50", iconBg: "bg-rose-100 text-rose-600" },
  { id: "buying-memo", title: "Export Buying Memo", description: "Download a personalized PDF for your lender or agent.", screenshot: null, border: "border-amber-200", bg: "from-amber-50 to-orange-50", iconBg: "bg-amber-100 text-amber-600" },
];

export default function InsightsPage() {
  const [session, setSession] = useState<StoredSession | null>(null);
  const { isPro } = usePremium();

  // Pro analysis state
  const [llmData, setLlmData] = useState<LlmSummaryResponse | null>(null);
  const [whatIfData, setWhatIfData] = useState<WhatIfResponse | null>(null);
  const [sensitivityData, setSensitivityData] = useState<SensitivityResponse | null>(null);
  const [trendData, setTrendData] = useState<TrendResponse | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const stored = loadResult();
    if (stored) setSession(stored);
  }, []);

  const result = session?.result;
  const inputs = session?.inputs;

  const runAnalysis = useCallback(async (id: string) => {
    if (!inputs) return;
    setLoadingId(id);
    try {
      switch (id) {
        case "ai-summary": setLlmData(await postLlmSummary(inputs)); break;
        case "whatif": setWhatIfData(await postWhatIf(inputs)); break;
        case "sensitivity": setSensitivityData(await postSensitivity(inputs)); break;
        case "trend": setTrendData(await postTrend(inputs)); break;
      }
    } catch (e) {
      console.error(`Failed to load ${id}:`, e);
    } finally {
      setLoadingId(null);
    }
  }, [inputs]);

  function renderProContent(id: string) {
    switch (id) {
      case "ai-summary":
        return <LlmSummarySection data={llmData} loading={loadingId === id} onLoad={() => runAnalysis(id)} />;
      case "whatif":
        return <WhatIfSection data={whatIfData} loading={loadingId === id} onLoad={() => runAnalysis(id)} />;
      case "sensitivity":
        return <SensitivitySection data={sensitivityData} loading={loadingId === id} onLoad={() => runAnalysis(id)} />;
      case "trend":
        return <TrendSection data={trendData} loading={loadingId === id} onLoad={() => runAnalysis(id)} />;
      case "zip-compare":
        return (
          <div className="rounded-xl bg-white/60 border border-white p-6 text-center">
            <p className="text-sm text-gray-400 italic">Coming soon</p>
          </div>
        );
      case "buying-memo":
        return (
          <div className="rounded-xl bg-white/60 border border-white p-6 text-center">
            <p className="text-sm text-gray-400 italic">Coming soon</p>
          </div>
        );
      default: return null;
    }
  }

  function renderLockedPreview(section: typeof SECTIONS[0]) {
    return (
      <div className="relative rounded-xl overflow-hidden">
        {section.screenshot ? (
          <div className="relative">
            <img src={section.screenshot} alt={`${section.title} preview`} className="w-full max-w-sm mx-auto rounded-xl opacity-60" />
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
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-medium text-gray-500 bg-white/80 backdrop-blur-sm rounded-full px-4 py-2 border border-gray-200/60 shadow-sm">
            Upgrade to Pro to unlock
          </span>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen pb-20">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-400 to-violet-400 flex items-center justify-center">
              <span className="text-white text-sm font-bold">R</span>
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-800 leading-tight">Pro Insights</h1>
              <p className="text-[10px] text-gray-400 leading-tight">Deeper analysis for your scenario</p>
            </div>
          </Link>
          <Link href="/" className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to calculator
          </Link>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6 pb-24 space-y-6">
        {!result && (
          <div className="rounded-2xl border border-amber-100 bg-amber-50/50 p-5 text-center">
            <p className="text-sm text-amber-700 font-medium">No simulation results yet</p>
            <p className="text-xs text-amber-500 mt-1">
              <Link href="/" className="underline hover:text-amber-600">Run a simulation</Link> first to unlock Pro insights.
            </p>
          </div>
        )}

        {/* Pro feature sections */}
        {SECTIONS.map((section) => {
          const isCollapsed = collapsed[section.id] ?? false;
          const hasData = section.id === "ai-summary" ? !!llmData
            : section.id === "whatif" ? !!whatIfData
            : section.id === "sensitivity" ? !!sensitivityData
            : section.id === "trend" ? !!trendData
            : false;

          return (
            <section
              key={section.id}
              id={section.id}
              className={`rounded-2xl border bg-gradient-to-br scroll-mt-20 overflow-hidden ${section.border} ${section.bg}`}
            >
              {/* Clickable header */}
              <button
                onClick={() => setCollapsed((prev) => ({ ...prev, [section.id]: !isCollapsed }))}
                className="w-full flex items-center gap-3 p-5 text-left"
              >
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${section.iconBg}`}>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-gray-700">{section.title}</h2>
                    {!isPro && <ProBadge />}
                    {hasData && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Loaded" />
                    )}
                  </div>
                  <p className="text-[11px] text-gray-400 mt-0.5">{section.description}</p>
                </div>
                <svg
                  className={`w-4 h-4 text-gray-300 shrink-0 transition-transform duration-200 ${isCollapsed ? "" : "rotate-180"}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Collapsible content */}
              {!isCollapsed && (
                <div className="px-5 pb-5">
                  {isPro && result ? renderProContent(section.id) : renderLockedPreview(section)}
                </div>
              )}
            </section>
          );
        })}
      </div>

      {/* Sticky bottom bar */}
      {result && (
        <div className="fixed bottom-0 inset-x-0 z-50 safe-bottom">
          <div className="bg-white/80 backdrop-blur-md border-t border-gray-100">
            <div className="max-w-4xl mx-auto px-4 py-2.5">
              <QuickStats
                result={result}
                scenarioName={session?.scenario_name}
                source={session?.scenario_name ? "saved" : "live"}
              />
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
