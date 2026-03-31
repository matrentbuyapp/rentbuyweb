"use client";

import { useState, useRef } from "react";
import { SummaryRequest, SummaryResponse } from "@/lib/types";

interface Props {
  inputs: SummaryRequest;
  response: SummaryResponse;
  onSave: (name: string, inputs: SummaryRequest, response: SummaryResponse) => Promise<unknown>;
}

export default function SaveButton({ inputs, response, onSave }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSave = async () => {
    const trimmed = inputRef.current?.value?.trim() || name.trim();
    if (!trimmed) {
      setError("Enter a name");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await onSave(trimmed, inputs, response);
      setSaved(true);
      setOpen(false);
      setName("");
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <span className="text-xs text-emerald-600 font-medium px-3 py-1.5">
        Saved!
      </span>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs font-medium text-indigo-600 hover:text-indigo-700 px-3 py-2
          rounded-lg border border-indigo-200 hover:border-indigo-300 bg-indigo-50/50
          transition-colors flex items-center gap-1.5"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        Save Scenario
      </button>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={(e) => { setName(e.target.value); setError(null); }}
          onKeyDown={(e) => e.key === "Enter" && handleSave()}
          placeholder="e.g. Downtown 2BR"
          autoFocus
          className="text-xs rounded-lg border border-gray-200 px-3 py-2.5 w-40 min-h-[44px]
            focus:border-indigo-300 focus:ring-1 focus:ring-indigo-100 outline-none"
        />
        <button
          type="button"
          onPointerDown={(e) => {
            // Prevent input blur from stealing the event on mobile
            e.preventDefault();
            handleSave();
          }}
          disabled={saving}
          className="text-xs font-medium text-white bg-indigo-500 hover:bg-indigo-600
            active:bg-indigo-700 disabled:opacity-40 px-4 py-2.5 rounded-lg transition-colors
            min-h-[44px] min-w-[44px] select-none"
        >
          {saving ? "..." : "Save"}
        </button>
        <button
          type="button"
          onClick={() => { setOpen(false); setName(""); setError(null); }}
          className="text-xs text-gray-400 hover:text-gray-600 px-2 py-2.5 min-h-[44px]"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-[10px] text-rose-500 mt-1">{error}</p>}
    </div>
  );
}
