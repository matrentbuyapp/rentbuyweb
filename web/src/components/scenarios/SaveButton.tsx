"use client";

import { useState } from "react";
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

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave(name.trim(), inputs, response);
      setSaved(true);
      setOpen(false);
      setName("");
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // error handled upstream
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
        onClick={() => setOpen(true)}
        className="text-xs font-medium text-indigo-600 hover:text-indigo-700 px-3 py-1.5
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
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSave()}
        placeholder="e.g. Downtown 2BR"
        autoFocus
        className="text-xs rounded-lg border border-gray-200 px-2.5 py-1.5 w-40
          focus:border-indigo-300 focus:ring-1 focus:ring-indigo-100 outline-none"
      />
      <button
        onClick={handleSave}
        disabled={!name.trim() || saving}
        className="text-xs font-medium text-white bg-indigo-500 hover:bg-indigo-600
          disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
      >
        {saving ? "..." : "Save"}
      </button>
      <button
        onClick={() => { setOpen(false); setName(""); }}
        className="text-xs text-gray-400 hover:text-gray-600 px-1"
      >
        Cancel
      </button>
    </div>
  );
}
