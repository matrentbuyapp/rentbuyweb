"use client";

import { useState } from "react";
import { Scenario, SummaryResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";
import AlertToggles from "./AlertToggles";

interface Props {
  scenarios: Scenario[];
  loading: boolean;
  onRerun: (id: string) => Promise<SummaryResponse>;
  onDelete: (id: string) => Promise<void>;
  onViewResult: (result: SummaryResponse) => void;
  onViewScenario?: (scenario: Scenario) => void;
}

export default function ScenarioList({ scenarios, loading, onRerun, onDelete, onViewResult, onViewScenario }: Props) {
  const [runningId, setRunningId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  if (loading) {
    return <p className="text-xs text-gray-400 py-4 text-center">Loading scenarios...</p>;
  }

  if (scenarios.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-gray-400">No saved scenarios yet.</p>
        <p className="text-xs text-gray-300 mt-1">Run a simulation and save it to compare later.</p>
      </div>
    );
  }

  const handleRerun = async (id: string) => {
    setRunningId(id);
    try {
      const result = await onRerun(id);
      onViewResult(result);
    } finally {
      setRunningId(null);
    }
  };

  const handleDelete = async (id: string) => {
    await onDelete(id);
    setConfirmDeleteId(null);
  };

  return (
    <div className="space-y-2">
      {scenarios.map((s) => {
        const isExpanded = expandedId === s.id;
        const diff = s.response
          ? s.response.avg_buyer_net_worth - s.response.avg_renter_net_worth
          : null;
        const updatedDate = new Date(s.updated_at * 1000).toLocaleDateString("en-US", {
          month: "short", day: "numeric",
        });

        return (
          <div
            key={s.id}
            className="rounded-xl border border-gray-100 bg-white/60 backdrop-blur-sm overflow-hidden"
          >
            {/* Header row */}
            <button
              onClick={() => setExpandedId(isExpanded ? null : s.id)}
              className="w-full flex items-center gap-3 p-3 text-left hover:bg-gray-50/50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">{s.name}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-gray-400">{updatedDate}</span>
                  {diff != null && (
                    <span className={`text-[10px] font-medium ${diff > 0 ? "text-emerald-600" : "text-rose-500"}`}>
                      {diff > 0 ? "Buy" : "Rent"} wins by {formatCurrency(Math.abs(diff))}
                    </span>
                  )}
                  {s.data_vintage && (
                    <span className="text-[10px] text-gray-400">Data: {s.data_vintage}</span>
                  )}
                  {s.inputs.zip_code && (
                    <span className="text-[10px] text-gray-400">ZIP {s.inputs.zip_code}</span>
                  )}
                </div>
              </div>
              <svg
                className={`w-4 h-4 text-gray-300 shrink-0 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Expanded content */}
            {isExpanded && (
              <div className="px-3 pb-3 border-t border-gray-50 space-y-3">
                {/* Quick stats from cached response */}
                {s.response && (
                  <div className="grid grid-cols-3 gap-2 pt-2">
                    <div className="text-center">
                      <p className="text-[10px] text-gray-400">Home Price</p>
                      <p className="text-xs font-medium text-gray-600">{formatCurrency(s.response.house_price)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-gray-400">Rate</p>
                      <p className="text-xs font-medium text-gray-600">{(s.response.mortgage_rate * 100).toFixed(2)}%</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-gray-400">Horizon</p>
                      <p className="text-xs font-medium text-gray-600">{s.inputs.years ?? 10} yr</p>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleRerun(s.id)}
                    disabled={runningId === s.id}
                    className="text-xs font-medium text-white bg-indigo-500 hover:bg-indigo-600
                      disabled:opacity-50 px-3 py-1.5 rounded-lg transition-colors
                      flex items-center gap-1.5"
                  >
                    {runningId === s.id ? (
                      <>
                        <div className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                        Running...
                      </>
                    ) : (
                      "Re-run with fresh data"
                    )}
                  </button>
                  {s.response && (
                    <button
                      onClick={() => onViewScenario ? onViewScenario(s) : onViewResult(s.response!)}
                      className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1.5 rounded-lg
                        border border-gray-200 hover:border-gray-300 transition-colors"
                    >
                      View results
                    </button>
                  )}
                  <div className="flex-1" />
                  {confirmDeleteId === s.id ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-gray-400">Sure?</span>
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="text-[10px] text-rose-600 hover:text-rose-700 font-medium"
                      >
                        Delete
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-[10px] text-gray-400 hover:text-gray-600"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmDeleteId(s.id)}
                      className="text-xs text-gray-300 hover:text-rose-500 transition-colors p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
                      title="Delete scenario"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                </div>

                {/* Alert toggles */}
                <AlertToggles scenarioId={s.id} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
