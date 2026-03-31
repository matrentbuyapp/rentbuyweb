"use client";

import { useState, useRef, useEffect } from "react";
import { Scenario } from "@/lib/types";

interface Props {
  /** Currently viewing a saved scenario, or null for live */
  activeScenario: Scenario | null;
  /** Available saved scenarios to switch to */
  scenarios: Scenario[];
  /** Has live results available */
  hasLive: boolean;
  /** Called when user picks live */
  onSelectLive: () => void;
  /** Called when user picks a scenario */
  onSelectScenario: (scenario: Scenario) => void;
  /** Compact mode for bottom bars */
  compact?: boolean;
  /** Drop direction — "up" for bottom bars, "down" for inline */
  direction?: "up" | "down";
}

export default function ViewSwitcher({ activeScenario, scenarios, hasLive, onSelectLive, onSelectScenario, compact, direction = "up" }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", handler);
    return () => document.removeEventListener("pointerdown", handler);
  }, [open]);

  const hasOptions = hasLive || scenarios.length > 0;
  const showDropdown = hasOptions && (scenarios.length > 0 || (activeScenario && hasLive));

  return (
    <div ref={ref} className="relative">
      {/* Current state button */}
      <button
        type="button"
        onClick={() => showDropdown && setOpen(!open)}
        aria-label={`Viewing ${activeScenario ? activeScenario.name : "live results"}. ${showDropdown ? "Click to switch." : ""}`}
        className={`flex items-center gap-1.5 rounded-lg transition-colors w-full min-w-0
          ${showDropdown ? "hover:bg-gray-100/50 cursor-pointer" : "cursor-default"}
          ${compact ? "px-2 py-1" : "px-2.5 py-1.5"}`}
      >
        {activeScenario ? (
          <>
            <svg className={`${compact ? "w-3 h-3" : "w-3.5 h-3.5"} text-indigo-400 shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            <span className={`${compact ? "text-[10px]" : "text-xs"} text-indigo-700 truncate min-w-0`}>{activeScenario.name}</span>
          </>
        ) : (
          <>
            <span className={`${compact ? "w-1.5 h-1.5" : "w-2 h-2"} rounded-full bg-emerald-400 shrink-0`} />
            <span className={`${compact ? "text-[10px]" : "text-xs"} text-gray-500 whitespace-nowrap`}>Live</span>
          </>
        )}
        {showDropdown && (
          <svg className={`${compact ? "w-2.5 h-2.5" : "w-3 h-3"} text-gray-300 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className={`absolute left-0 z-50 min-w-[220px] rounded-xl border border-gray-200 bg-white shadow-lg py-1.5
          ${direction === "up" ? "bottom-full mb-1" : "top-full mt-1"}`}>
          {/* Live option */}
          {hasLive && (
            <button
              type="button"
              onClick={() => { onSelectLive(); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-gray-50 transition-colors
                ${!activeScenario ? "bg-emerald-50/50" : ""}`}
            >
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0" />
              <span className="text-sm text-gray-700 flex-1">Live results</span>
              {!activeScenario && (
                <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          )}
          {/* Divider */}
          {hasLive && scenarios.length > 0 && (
            <div className="border-t border-gray-100 my-1" />
          )}
          {/* Saved scenarios */}
          {scenarios.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => { onSelectScenario(s); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-gray-50 transition-colors
                ${activeScenario?.id === s.id ? "bg-indigo-50/50" : ""}`}
            >
              <svg className="w-4 h-4 text-indigo-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              <span className="text-sm text-gray-700 flex-1 truncate">{s.name}</span>
              {activeScenario?.id === s.id && (
                <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
