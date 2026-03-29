"use client";

import { useRef, useState, useEffect } from "react";
import SettingsPanel from "@/components/form/SettingsPanel";
import ResultsDashboard from "@/components/results/ResultsDashboard";
import SaveButton from "@/components/scenarios/SaveButton";
import ScenarioList from "@/components/scenarios/ScenarioList";
import { useSimulation } from "@/hooks/useSimulation";
import { usePremium } from "@/hooks/usePremium";
import { useScenarios } from "@/hooks/useScenarios";
import { useZipPrices } from "@/hooks/useZipPrices";
import { formToRequest } from "@/lib/api";
import { SummaryResponse } from "@/lib/types";

export default function Home() {
  const { formData, updateField, result, setResult, loading, error, hasRun, runSimulation, resultsRef } =
    useSimulation();
  const { isPro, toggle: togglePro } = usePremium();
  const scenarioCtx = useScenarios(isPro);
  const zipPrices = useZipPrices();
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

  const handleViewResult = (r: SummaryResponse) => {
    setResult(r);
    setTimeout(() => scrollToResults(), 50);
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
            <div className={`flex flex-col sm:flex-row gap-2 justify-center transition-opacity duration-200 ${showBottomBar || result ? "opacity-0 pointer-events-none h-0 overflow-hidden" : ""}`}>
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

        {/* Results + Save button */}
        <div ref={resultsRef}>
          {result && isPro && (
            <div className="flex justify-end mb-2">
              <SaveButton
                inputs={formToRequest(formData)}
                response={result}
                onSave={scenarioCtx.save}
              />
            </div>
          )}
          <ResultsDashboard
            result={result} loading={loading} error={error} isPro={isPro}
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
            />
          </section>
        )}

        {/* Settings */}
        <section ref={settingsRef} className="pb-4">
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-sm font-semibold text-gray-500">Settings</h2>
            <div className="h-px flex-1 bg-gray-200/60" />
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
          transition-all duration-200 ${showBottomBar || result ? "translate-y-0 opacity-100" : "translate-y-full opacity-0 pointer-events-none"}`}
      >
        <div className="bg-white/80 backdrop-blur-md border-t border-gray-100">
          {/* Quick reference stats — only when results exist */}
          {result && (
            <div className="max-w-5xl mx-auto px-4 pt-2 pb-0">
              <div className="flex items-center justify-center gap-3 sm:gap-5 text-[10px] text-gray-400">
                <span>
                  <span className="text-gray-500 font-medium">${result.house_price.toLocaleString()}</span>
                  {" "}@ {(result.mortgage_rate * 100).toFixed(1)}%
                </span>
                <span className="text-gray-200">|</span>
                <span>
                  <span className="text-gray-500 font-medium">${Math.round(result.monthly[0]?.total_housing_cost ?? 0).toLocaleString()}</span>/mo
                </span>
                <span className="text-gray-200">|</span>
                <span className={result.avg_buyer_net_worth > result.avg_renter_net_worth ? "text-emerald-500" : "text-rose-500"}>
                  {result.avg_buyer_net_worth > result.avg_renter_net_worth ? "Buy" : "Rent"} wins by ${Math.abs(Math.round(result.avg_buyer_net_worth - result.avg_renter_net_worth)).toLocaleString()}
                </span>
              </div>
            </div>
          )}
          {/* Action buttons */}
          <div className="max-w-5xl mx-auto px-4 py-2.5 flex gap-3">
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
      </div>
    </main>
  );
}
