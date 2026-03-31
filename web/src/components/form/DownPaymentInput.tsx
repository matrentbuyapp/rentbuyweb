"use client";

import { useState, useRef, useCallback } from "react";

interface Props {
  pct: number;
  onPctChange: (pct: number) => void;
  homePrice: number;
  savings: number;
  closingPct: number;
  moveInCost: number;
}

export default function DownPaymentInput({ pct, onPctChange, homePrice, savings, closingPct, moveInCost }: Props) {
  const [editMode, setEditMode] = useState<"pct" | "dollar" | null>(null);
  const [dollarInput, setDollarInput] = useState("");
  const barRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);

  const dpDollars = Math.round(homePrice * (pct / 100));
  const closingDollars = Math.round(homePrice * (closingPct / 100));
  const totalNeeded = dpDollars + closingDollars + moveInCost;
  const remaining = savings - totalNeeded;

  // Max DP based on savings
  const maxDpDollars = Math.max(0, savings - closingDollars - moveInCost);
  const maxDpPct = homePrice > 0 ? Math.min(100, Math.round((maxDpDollars / homePrice) * 100)) : 100;
  const minDpPct = 3;

  // Bar segments as % of savings
  const dpShare = savings > 0 ? Math.min((dpDollars / savings) * 100, 100) : 0;
  const closingShare = savings > 0 ? Math.min((closingDollars / savings) * 100, 100 - dpShare) : 0;
  const moveInShare = savings > 0 && moveInCost > 0 ? Math.min((moveInCost / savings) * 100, 100 - dpShare - closingShare) : 0;
  const overBudget = totalNeeded > savings;

  const handlePctChange = (v: string) => {
    const num = v === "" ? 0 : Number(v);
    if (!isNaN(num)) onPctChange(Math.max(0, Math.min(num, maxDpPct)));
  };

  const handleDollarChange = (v: string) => {
    setDollarInput(v);
    const num = Number(v.replace(/,/g, ""));
    if (!isNaN(num) && homePrice > 0) {
      const newPct = Math.round((num / homePrice) * 1000) / 10;
      onPctChange(Math.max(0, Math.min(newPct, maxDpPct)));
    }
  };

  // Drag on the bar to adjust DP
  const updateFromPointer = useCallback((clientX: number) => {
    const bar = barRef.current;
    if (!bar || savings <= 0 || homePrice <= 0) return;
    const rect = bar.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const dpAmount = ratio * savings;
    const newPct = Math.round((dpAmount / homePrice) * 100);
    onPctChange(Math.max(minDpPct, Math.min(newPct, maxDpPct)));
  }, [savings, homePrice, maxDpPct, onPctChange]);

  const handlePointerDown = (e: React.PointerEvent) => {
    // Blur any focused text input so it picks up slider updates
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    setDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    updateFromPointer(e.clientX);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragging) return;
    updateFromPointer(e.clientX);
  };

  const handlePointerUp = () => {
    setDragging(false);
  };

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">
        Down Payment
      </label>

      {/* Dual input: % and $ */}
      <div className="flex items-center gap-1.5">
        <div className="relative">
          <input
            type="text"
            inputMode="decimal"
            value={editMode === "pct" ? (pct || "") : pct || ""}
            onChange={(e) => { setEditMode("pct"); handlePctChange(e.target.value); }}
            onFocus={() => setEditMode("pct")}
            onBlur={() => setEditMode(null)}
            className={`w-16 rounded-lg border bg-white/80 px-2 py-2 text-sm text-right pr-6 outline-none transition-all
              ${editMode === "pct" ? "border-indigo-300 ring-2 ring-indigo-100" : "border-gray-200"}
              ${overBudget ? "text-rose-600" : "text-gray-700"}`}
          />
          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">%</span>
        </div>

        <span className="text-gray-300 text-xs">=</span>

        <div className="relative flex-1">
          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
          <input
            type="text"
            inputMode="numeric"
            value={editMode === "dollar" ? dollarInput : dpDollars.toLocaleString()}
            onChange={(e) => { setEditMode("dollar"); handleDollarChange(e.target.value); }}
            onFocus={() => { setEditMode("dollar"); setDollarInput(String(dpDollars)); }}
            onBlur={() => { setDollarInput(""); setEditMode(null); }}
            className={`w-full rounded-lg border bg-white/80 pl-5 pr-2 py-2 text-sm outline-none transition-all
              ${editMode === "dollar" ? "border-indigo-300 ring-2 ring-indigo-100" : "border-gray-200"}
              ${overBudget ? "text-rose-600" : "text-gray-700"}`}
          />
        </div>
      </div>

      {/* Interactive savings bar — drag to adjust */}
      {homePrice > 0 && savings > 0 && (
        <div className="mt-2">
          <div
            ref={barRef}
            className={`h-5 rounded-full bg-gray-100 overflow-hidden flex relative cursor-pointer select-none ${dragging ? "ring-2 ring-indigo-200" : ""}`}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            style={{ touchAction: "none" }}
          >
            {/* Down payment segment */}
            <div
              className={`${overBudget ? "bg-rose-400" : "bg-indigo-400"} transition-colors relative`}
              style={{ width: `${dpShare}%` }}
            >
              {/* Drag handle */}
              <div className="absolute right-0 top-0 bottom-0 w-3 flex items-center justify-center">
                <div className="w-0.5 h-3 bg-white/70 rounded-full" />
              </div>
            </div>
            {/* Closing costs segment */}
            <div className="bg-amber-300" style={{ width: `${closingShare}%` }} />
            {/* Move-in segment */}
            {moveInCost > 0 && (
              <div className="bg-sky-300" style={{ width: `${moveInShare}%` }} />
            )}
          </div>
          <div className="flex items-center justify-between mt-1">
            <div className="flex items-center gap-2 text-[9px] text-gray-400">
              <span className="flex items-center gap-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${overBudget ? "bg-rose-400" : "bg-indigo-400"}`} />
                Down
              </span>
              <span className="flex items-center gap-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-300" />
                Closing
              </span>
              {moveInCost > 0 && (
                <span className="flex items-center gap-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-300" />
                  Move-in
                </span>
              )}
            </div>
            <span className={`text-[10px] font-medium ${overBudget ? "text-rose-500" : remaining < savings * 0.1 ? "text-amber-500" : "text-gray-400"}`}>
              {overBudget
                ? `$${Math.abs(remaining).toLocaleString()} short`
                : `$${remaining.toLocaleString()} savings left`}
            </span>
          </div>
        </div>
      )}

      <p className="text-[11px] text-gray-400 mt-1">
        {pct < 20
          ? `${pct}% down — you'll pay PMI until you reach 20% equity`
          : `${pct}% down — no PMI required`}
      </p>
    </div>
  );
}
