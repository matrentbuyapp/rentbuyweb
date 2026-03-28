"use client";

import { useRef, useState, useEffect } from "react";
import SettingsPanel from "@/components/form/SettingsPanel";
import ResultsDashboard from "@/components/results/ResultsDashboard";
import { useSimulation } from "@/hooks/useSimulation";
import { usePremium } from "@/hooks/usePremium";

export default function Home() {
  const { formData, updateField, result, loading, error, hasRun, runSimulation, resultsRef } =
    useSimulation();
  const { isPro, toggle: togglePro } = usePremium();
  const settingsRef = useRef<HTMLDivElement>(null);
  const heroButtonRef = useRef<HTMLDivElement>(null);
  const [showBottomBar, setShowBottomBar] = useState(false);

  // Show sticky bottom bar when hero Calculate button scrolls out of view
  useEffect(() => {
    const target = heroButtonRef.current;
    if (!target) return;
    const observer = new IntersectionObserver(
      ([entry]) => setShowBottomBar(!entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, []);

  const scrollWithOffset = (ref: React.RefObject<HTMLDivElement | null>) => {
    const el = ref.current;
    if (!el) return;
    const headerHeight = 60;
    const top = el.getBoundingClientRect().top + window.scrollY - headerHeight;
    window.scrollTo({ top, behavior: "smooth" });
  };

  const scrollToSettings = () => scrollWithOffset(settingsRef);
  const scrollToResults = () => scrollWithOffset(resultsRef);

  return (
    <main className="min-h-screen pb-20">
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-400 to-violet-400 flex items-center justify-center">
              <span className="text-white text-sm font-bold">R</span>
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-800 leading-tight">Rent vs Buy</h1>
              <p className="text-[10px] text-gray-400 leading-tight">Should you rent or buy a home?</p>
            </div>
          </div>
          {/* Dev-only premium toggle */}
          {process.env.NODE_ENV === "development" && (
            <button
              onClick={togglePro}
              className={`text-[10px] font-mono px-2 py-1 rounded-md border transition-colors ${
                isPro
                  ? "bg-amber-50 border-amber-200 text-amber-700"
                  : "bg-gray-50 border-gray-200 text-gray-400"
              }`}
            >
              {isPro ? "PRO" : "FREE"}
            </button>
          )}
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Hero */}
        <section className="rounded-3xl bg-white/70 backdrop-blur-sm border border-gray-100 p-6 md:p-8">
          <div className="max-w-xl mx-auto text-center mb-6">
            <h2 className="text-2xl md:text-3xl font-bold text-gray-800 tracking-tight">
              Should you rent
              <br className="sm:hidden" />
              {" "}or buy?
            </h2>
            <p className="text-sm text-gray-400 mt-2 leading-relaxed">
              We run hundreds of simulations using real market data
              <br className="hidden sm:block" />
              {" "}to see which option builds more wealth over time.
            </p>
          </div>

          <div className="max-w-lg mx-auto">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                  Monthly Rent
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                  <input
                    type="text"
                    value={formData.monthly_rent}
                    onChange={(e) => updateField("monthly_rent", Number(e.target.value) || 0)}
                    className="w-full rounded-xl border border-gray-200 bg-white pl-7 pr-3 py-3 text-lg font-semibold text-gray-700
                      focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>
                <p className="text-[10px] text-gray-400 mt-1">What you pay now</p>
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                  Housing Budget
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                  <input
                    type="text"
                    value={formData.monthly_budget}
                    onChange={(e) => updateField("monthly_budget", Number(e.target.value) || 0)}
                    className="w-full rounded-xl border border-gray-200 bg-white pl-7 pr-3 py-3 text-lg font-semibold text-gray-700
                      focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>
                <p className="text-[10px] text-gray-400 mt-1">Max you can spend on housing</p>
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                  Savings
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                  <input
                    type="text"
                    value={formData.initial_cash}
                    onChange={(e) => updateField("initial_cash", Number(e.target.value) || 0)}
                    className="w-full rounded-xl border border-gray-200 bg-white pl-7 pr-3 py-3 text-lg font-semibold text-gray-700
                      focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>
                <p className="text-[10px] text-gray-400 mt-1">Cash you have available</p>
              </div>
            </div>

            <div ref={heroButtonRef} className="flex flex-col sm:flex-row gap-2 justify-center">
              <button
                onClick={() => runSimulation()}
                disabled={loading || formData.monthly_rent <= 0 || formData.monthly_budget <= 0}
                className="px-8 py-3 text-sm font-semibold text-white rounded-xl
                  bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-600 hover:to-violet-600
                  disabled:opacity-40 disabled:cursor-not-allowed
                  shadow-lg shadow-indigo-200 hover:shadow-indigo-300
                  transition-all active:scale-[0.98] flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Running...
                  </>
                ) : hasRun ? (
                  "Re-Calculate"
                ) : (
                  "Show Me the Numbers"
                )}
              </button>
              <button
                onClick={scrollToSettings}
                className="px-6 py-3 text-sm font-medium text-gray-500 rounded-xl
                  border border-gray-200 hover:border-gray-300 hover:text-gray-700
                  transition-all flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {hasRun ? "Settings" : "Customize First"}
              </button>
            </div>
          </div>
        </section>

        {/* Results */}
        <div ref={resultsRef}>
          <ResultsDashboard result={result} loading={loading} error={error} />
        </div>

        {/* Settings */}
        <section ref={settingsRef} className="pb-4">
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-sm font-semibold text-gray-500">Settings</h2>
            <div className="h-px flex-1 bg-gray-200/60" />
          </div>
          <SettingsPanel formData={formData} updateField={updateField} hasRun={hasRun} />
        </section>
      </div>

      {/* Sticky bottom bar — appears when hero buttons scroll out of view */}
      <div
        className={`fixed bottom-0 inset-x-0 z-50 bg-white/80 backdrop-blur-md border-t border-gray-100 safe-bottom
          transition-all duration-200 ${showBottomBar ? "translate-y-0 opacity-100" : "translate-y-full opacity-0 pointer-events-none"}`}
      >
        <div className="max-w-5xl mx-auto px-4 py-3 flex gap-3">
          <button
            onClick={scrollToSettings}
            className="flex-1 py-2.5 text-sm font-semibold rounded-xl
              border border-gray-200 text-gray-600
              hover:border-gray-300 hover:text-gray-800 hover:bg-gray-50
              transition-all active:scale-[0.98]
              flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
          <button
            onClick={() => { runSimulation(); if (hasRun) scrollToResults(); }}
            disabled={loading || formData.monthly_rent <= 0 || formData.monthly_budget <= 0}
            className="flex-1 py-2.5 text-sm font-semibold text-white rounded-xl
              bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-600 hover:to-violet-600
              disabled:opacity-40 disabled:cursor-not-allowed
              shadow-lg shadow-indigo-200
              transition-all active:scale-[0.98]
              flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Running...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {hasRun ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  )}
                </svg>
                {hasRun ? "Re-Calculate" : "Show Me the Numbers"}
              </>
            )}
          </button>
        </div>
      </div>
    </main>
  );
}
