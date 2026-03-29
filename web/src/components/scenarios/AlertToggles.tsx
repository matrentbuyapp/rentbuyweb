"use client";

import { useState, useEffect, useCallback } from "react";
import { Alert } from "@/lib/types";
import { listAlerts, addAlert, deleteAlert, registerEmail } from "@/lib/api";

const ALERT_TYPES = [
  {
    type: "threshold" as const,
    label: "Verdict flips",
    desc: "Notified when buy/rent recommendation changes",
  },
  {
    type: "shift" as const,
    label: "Breakeven shifts",
    desc: "Notified when breakeven moves by 3+ months",
  },
  {
    type: "digest" as const,
    label: "Monthly digest",
    desc: "Monthly summary email with latest numbers",
  },
];

interface Props {
  scenarioId: string;
}

export default function AlertToggles({ scenarioId }: Props) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [emailPrompt, setEmailPrompt] = useState(false);
  const [email, setEmail] = useState("");
  const [emailSet, setEmailSet] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const list = await listAlerts(scenarioId);
      setAlerts(list);
    } catch {
      // endpoint may not exist yet
    } finally {
      setLoading(false);
    }
  }, [scenarioId]);

  useEffect(() => { refresh(); }, [refresh]);

  const hasEmail = emailSet || !!localStorage.getItem("alert_email");

  const handleToggle = async (alertType: "threshold" | "shift" | "digest") => {
    const existing = alerts.find((a) => a.alert_type === alertType);
    if (existing) {
      await deleteAlert(scenarioId, existing.id);
      setAlerts((prev) => prev.filter((a) => a.id !== existing.id));
    } else {
      // Need email first
      if (!hasEmail) {
        setEmailPrompt(true);
        return;
      }
      try {
        const alert = await addAlert(scenarioId, alertType);
        setAlerts((prev) => [...prev, alert]);
      } catch {
        // 409 or other
      }
    }
  };

  const handleEmailSubmit = async () => {
    if (!email.trim()) return;
    try {
      await registerEmail(email.trim());
      localStorage.setItem("alert_email", email.trim());
      setEmailSet(true);
      setEmailPrompt(false);
      setEmail("");
    } catch {
      // fail silently for now
    }
  };

  if (loading) return null;

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Alerts</p>
      {ALERT_TYPES.map(({ type, label, desc }) => {
        const active = alerts.some((a) => a.alert_type === type);
        return (
          <button
            key={type}
            onClick={() => handleToggle(type)}
            className="flex items-center gap-2 w-full text-left group"
          >
            <div
              className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                active
                  ? "bg-indigo-500 border-indigo-500"
                  : "border-gray-300 group-hover:border-gray-400"
              }`}
            >
              {active && (
                <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <div>
              <span className="text-xs text-gray-600">{label}</span>
              <span className="text-[10px] text-gray-400 ml-1.5 hidden sm:inline">{desc}</span>
            </div>
          </button>
        );
      })}
      {emailPrompt && (
        <div className="flex items-center gap-2 mt-2 pl-6">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleEmailSubmit()}
            placeholder="your@email.com"
            autoFocus
            className="text-xs rounded-lg border border-gray-200 px-2.5 py-1.5 w-48
              focus:border-indigo-300 focus:ring-1 focus:ring-indigo-100 outline-none"
          />
          <button
            onClick={handleEmailSubmit}
            disabled={!email.trim()}
            className="text-xs font-medium text-white bg-indigo-500 hover:bg-indigo-600
              disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
          >
            Set
          </button>
        </div>
      )}
    </div>
  );
}
