"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import SettingsPanel from "@/components/form/SettingsPanel";
import ResultsDashboard from "@/components/results/ResultsDashboard";
import SaveButton from "@/components/scenarios/SaveButton";
import ScenarioList from "@/components/scenarios/ScenarioList";
import { useSimulation } from "@/hooks/useSimulation";
import { usePremium } from "@/hooks/usePremium";
import { useScenarios } from "@/hooks/useScenarios";
import { useZipPrices } from "@/hooks/useZipPrices";
import { formToRequest } from "@/lib/api";
import QuickStats from "@/components/ui/QuickStats";
import { storeResult } from "@/lib/resultStore";
import { SummaryResponse, Scenario } from "@/lib/types";

export default function Home() {
  const { formData, updateField, resetAll, result, setResult, loading, error, hasRun, isDirty, runSimulation, resultsRef } =
    useSimulation();
  const { isPro, toggle: togglePro } = usePremium();
  const scenarioCtx = useScenarios(isPro);
  const zipPrices = useZipPrices();
  const settingsRef = useRef<HTMLDivElement>(null);
  const heroButtonRef = useRef<HTMLDivElement>(null);
  const [showBottomBar, setShowBottomBar] = useState(false);

  // Track whether we're viewing a saved scenario vs live results
  const [viewingScenario, setViewingScenario] = useState<Scenario | null>(null);
  const [liveResult, setLiveResult] = useState<SummaryResponse | null>(null);

  // When simulation runs, it's a live result — clear any scenario view
  const displayResult = viewingScenario ? viewingScenario.response : result;

  // Keep liveResult in sync with simulation result
  const prevResult = useRef(result);
  if (result !== prevResult.current) {
    prevResult.current = result;
    if (result && !viewingScenario) {
      setLiveResult(result);
    }
  }

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
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const scrollToSettings = () => scrollWithOffset(settingsRef);
  const scrollToResults = () => scrollWithOffset(resultsRef);

  const handleViewScenario = (scenario: Scenario) => {
    if (result && !viewingScenario) {
      setLiveResult(result);
    }
    setViewingScenario(scenario);
    if (scenario.response) {
      setResult(scenario.response);
      storeResult(scenario.response, scenario.inputs, { id: scenario.id, name: scenario.name });
    }
    setTimeout(() => scrollToResults(), 50);
  };

  const handleViewResult = (r: SummaryResponse) => {
    // Called from ScenarioList "View last result" — find the matching scenario
    const scenario = scenarioCtx.scenarios.find((s) => s.response === r);
    if (scenario) {
      handleViewScenario(scenario);
    } else {
      setResult(r);
      setTimeout(() => scrollToResults(), 50);
    }
  };

  const dismissScenarioView = () => {
    setViewingScenario(null);
    if (liveResult) {
      setResult(liveResult);
    }
  };

  // Clear scenario view when user runs a new simulation
  const handleRunSimulation = () => {
    setViewingScenario(null);
    setLiveResult(null);
    runSimulation();
  };

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
              Where will you be in {formData.stay_years} years? We run hundreds of simulations
              <br className="hidden sm:block" />
              {" "}using real market data to find out which option builds more wealth.
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

            {/* Estimated price + inline validation */}
            {(() => {
              const estPrice = result?.house_price
                ?? (formData.house_price ? Number(formData.house_price) : null)
                ?? zipPrices.lookup(formData.zip_code)?.price
                ?? zipPrices.nationalMedian;
              const downAmt = estPrice * (formData.down_payment_pct / 100);
              const closingAmt = estPrice * (formData.closing_cost_pct / 100);
              const cashNeeded = downAmt + closingAmt + formData.move_in_cost;
              const hints: string[] = [];
              if (formData.monthly_budget > 0 && formData.monthly_rent > 0 && formData.monthly_budget < formData.monthly_rent) {
                hints.push("Budget is less than your current rent");
              }
              if (formData.initial_cash > 0 && cashNeeded > formData.initial_cash) {
                hints.push(`You'd need ~$${Math.round(cashNeeded).toLocaleString()} to close (have $${formData.initial_cash.toLocaleString()})`);
              }
              if (formData.down_payment_pct > 0 && formData.down_payment_pct < 3) {
                hints.push("Most lenders require at least 3% down");
              }
              return (
                <div className="text-center mb-3 space-y-1">
                  <p className="text-[11px] text-gray-400">
                    {formData.house_price ? "Home price" : "Estimated home price"}:{" "}
                    <span className="font-medium text-gray-500">${estPrice.toLocaleString()}</span>
                    {formData.house_price
                      ? <span className="ml-1">(your price)</span>
                      : formData.zip_code
                        ? <span className="ml-1">(ZIP {formData.zip_code} median)</span>
                        : <span className="ml-1">(national median)</span>}
                  </p>
                  {hints.map((h, i) => (
                    <p key={i} className="text-[11px] text-amber-500">{h}</p>
                  ))}
                </div>
              );
            })()}

            <div ref={heroButtonRef} />
            <div className={`flex flex-col sm:flex-row gap-2 justify-center transition-opacity duration-200 ${showBottomBar || displayResult ? "opacity-0 pointer-events-none h-0 overflow-hidden" : ""}`}>
              <button
                onClick={handleRunSimulation}
                disabled={loading || formData.monthly_rent <= 0 || formData.monthly_budget <= 0 || (hasRun && !isDirty)}
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
                className="px-6 py-3 text-sm font-semibold text-white rounded-xl
                  bg-gradient-to-r from-sky-400 to-cyan-400 hover:from-sky-500 hover:to-cyan-500
                  shadow-lg shadow-sky-200 hover:shadow-sky-300
                  transition-all active:scale-[0.98] flex items-center justify-center gap-2"
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

        {/* Results + context banner */}
        <div ref={resultsRef} className="scroll-mt-16">
          {/* Viewing indicator */}
          {viewingScenario && (
            <div className="flex items-center gap-3 mb-3 rounded-xl border border-indigo-100 bg-indigo-50/50 px-4 py-2.5">
              <svg className="w-4 h-4 text-indigo-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-indigo-700 truncate">
                  Viewing: {viewingScenario.name}
                </p>
                <p className="text-[10px] text-indigo-400">
                  Saved {new Date(viewingScenario.created_at * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  {viewingScenario.data_vintage && ` · Data: ${viewingScenario.data_vintage}`}
                </p>
              </div>
              <button
                onClick={dismissScenarioView}
                className="text-xs text-indigo-500 hover:text-indigo-700 font-medium px-2 py-1 rounded-lg
                  hover:bg-indigo-100/50 transition-colors shrink-0"
              >
                {liveResult ? "Back to live results" : "Dismiss"}
              </button>
            </div>
          )}
          {/* Save button — only for live results */}
          {displayResult && isPro && !viewingScenario && (
            <div className="flex justify-end mb-2">
              <SaveButton
                inputs={formToRequest(formData)}
                response={displayResult}
                onSave={scenarioCtx.save}
              />
            </div>
          )}
          <ResultsDashboard
            result={displayResult ?? null} loading={loading} error={error} isPro={isPro}
            sellMonth={formData.stay_years < formData.years ? formData.buy_delay_months + formData.stay_years * 12 : null}
          />
        </div>

        {/* Saved Scenarios (Pro only) */}
        {isPro && (
          <section>
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-sm font-semibold text-gray-500">My Scenarios</h2>
              <div className="h-px flex-1 bg-gray-200/60" />
            </div>
            <ScenarioList
              scenarios={scenarioCtx.scenarios}
              loading={scenarioCtx.loading}
              onRerun={scenarioCtx.rerun}
              onDelete={scenarioCtx.remove}
              onViewResult={handleViewResult}
              onViewScenario={handleViewScenario}
            />
          </section>
        )}

        {/* Settings */}
        <section ref={settingsRef} className="pb-4 scroll-mt-32">
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-sm font-semibold text-gray-500">Settings</h2>
            <div className="h-px flex-1 bg-gray-200/60" />
            <button
              onClick={resetAll}
              className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors"
            >
              Reset all
            </button>
          </div>
          <SettingsPanel
            formData={formData} updateField={updateField} hasRun={hasRun} isPro={isPro}
            zipLookup={zipPrices.lookup} nationalMedian={zipPrices.nationalMedian}
            onZipFocus={zipPrices.ensureLoaded} lastHousePrice={result?.house_price ?? null}
          />
        </section>

        {/* Footer: About + Data Attribution */}
        <footer className="border-t border-gray-100 pt-6 pb-8 space-y-5">
          {/* About */}
          <div className="max-w-xl">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">About</h3>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              Rent vs Buy runs hundreds of Monte Carlo simulations using real market data
              to help you decide whether renting or buying builds more wealth over time.
              Every scenario accounts for mortgage amortization, PMI, property taxes, maintenance,
              tax deductions, investment returns, and home appreciation — all with realistic
              variance from historical data. No two runs are identical because markets aren&apos;t.
            </p>
            <p className="text-[11px] text-gray-400 leading-relaxed mt-2">
              This tool is for informational purposes only and does not constitute financial advice.
              Consult a qualified financial advisor before making real estate decisions.
            </p>
          </div>

          {/* Data Sources */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Data Sources</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-[11px] text-gray-400">
              <p>Home values and forecasts provided by <span className="text-gray-500">Zillow Research</span></p>
              <p>Mortgage rates from <span className="text-gray-500">Freddie Mac via FRED</span></p>
              <p>Property tax rates from <span className="text-gray-500">US Census Bureau ACS</span></p>
              <p>CPI and stock market data from <span className="text-gray-500">FRED (Federal Reserve)</span></p>
            </div>
          </div>

          {/* Copyright */}
          <p className="text-[10px] text-gray-300">
            &copy; {new Date().getFullYear()} rentbuysellapp.com
          </p>
        </footer>
      </div>

      {/* Sticky bottom bar — appears when hero buttons scroll out of view */}
      <div
        className={`fixed bottom-0 inset-x-0 z-50 safe-bottom
          transition-all duration-200 ${showBottomBar || displayResult ? "translate-y-0 opacity-100" : "translate-y-full opacity-0 pointer-events-none"}`}
      >
        <div className="bg-white/80 backdrop-blur-md border-t border-gray-100">
          {/* Quick reference stats */}
          {displayResult && (
            <div className="max-w-5xl mx-auto px-4 pt-2 pb-0">
              <QuickStats
                result={displayResult}
                scenarioName={viewingScenario?.name}
                source={viewingScenario ? "saved" : hasRun ? "live" : null}
              />
            </div>
          )}
          {/* Action buttons */}
          <div className="max-w-5xl mx-auto px-4 py-2.5 flex gap-2">
            <button
              onClick={scrollToSettings}
              className="flex-1 py-2.5 text-sm font-semibold text-white rounded-xl
                bg-gradient-to-r from-sky-400 to-cyan-400 hover:from-sky-500 hover:to-cyan-500
                shadow-lg shadow-sky-200
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
              onClick={() => { handleRunSimulation(); if (hasRun) scrollToResults(); }}
              disabled={loading || formData.monthly_rent <= 0 || formData.monthly_budget <= 0 || (hasRun && !isDirty)}
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
            {/* Pro quick actions: Save + Insights */}
            {isPro && displayResult && !viewingScenario && (
              <button
                onClick={() => {
                  const name = `Scenario ${new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
                  scenarioCtx.save(name, formToRequest(formData), displayResult);
                }}
                className="py-2.5 px-3 rounded-xl border border-gray-200 text-gray-500
                  hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50/50
                  transition-all active:scale-[0.98]"
                title="Quick save scenario"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </button>
            )}
            {isPro && displayResult && (
              <Link
                href="/insights"
                className="py-2.5 px-3 rounded-xl border border-gray-200 text-gray-500
                  hover:border-violet-300 hover:text-violet-600 hover:bg-violet-50/50
                  transition-all active:scale-[0.98] flex items-center"
                title="Pro Insights"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </Link>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
