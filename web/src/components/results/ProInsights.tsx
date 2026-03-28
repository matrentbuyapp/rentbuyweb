"use client";

import { useState } from "react";
import { SummaryResponse } from "@/lib/types";
import { PRO_FEATURES } from "@/lib/premium";
import ProBadge from "@/components/ui/ProBadge";

interface Props {
  result: SummaryResponse;
  isPro: boolean;
}

const ICONS: Record<string, React.ReactNode> = {
  "ai-summary": (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
    </svg>
  ),
  sensitivity: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  ),
  trend: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  "zip-compare": (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
    </svg>
  ),
};

const ACCENT: Record<string, string> = {
  "ai-summary": "from-violet-50 to-purple-50 border-violet-100",
  sensitivity: "from-sky-50 to-blue-50 border-sky-100",
  trend: "from-emerald-50 to-teal-50 border-emerald-100",
  "zip-compare": "from-rose-50 to-pink-50 border-rose-100",
};

const ICON_BG: Record<string, string> = {
  "ai-summary": "bg-violet-100 text-violet-600",
  sensitivity: "bg-sky-100 text-sky-600",
  trend: "bg-emerald-100 text-emerald-600",
  "zip-compare": "bg-rose-100 text-rose-600",
};

export default function ProInsights({ result, isPro }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isPro) {
    // TODO: render actual pro content from API responses
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-gray-500">Pro Insights</h2>
          <div className="h-px flex-1 bg-gray-200/60" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {PRO_FEATURES.map((f) => (
            <div
              key={f.id}
              className={`rounded-2xl border bg-gradient-to-br p-5 ${ACCENT[f.id]}`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${ICON_BG[f.id]}`}>
                  {ICONS[f.id]}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">{f.title}</h3>
                  <p className="text-xs text-gray-400 mt-1">{f.description}</p>
                  <p className="text-xs text-gray-400 mt-3 italic">Coming soon</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Free tier: gentle teaser
  return (
    <div className="rounded-2xl border border-gray-100 bg-white/60 backdrop-blur-sm p-6">
      <div className="text-center mb-5">
        <h2 className="text-base font-semibold text-gray-700">
          Want to dig deeper?
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Unlock additional tools to fine-tune your decision.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {PRO_FEATURES.map((f) => {
          const isExpanded = expandedId === f.id;
          return (
            <button
              key={f.id}
              onClick={() => setExpandedId(isExpanded ? null : f.id)}
              className={`text-left rounded-xl border bg-gradient-to-br p-4 transition-all card-hover ${ACCENT[f.id]}`}
            >
              <div className="flex items-center gap-2.5">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${ICON_BG[f.id]}`}>
                  {ICONS[f.id]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-gray-700">{f.title}</span>
                    <ProBadge />
                  </div>
                </div>
              </div>
              {isExpanded && (
                <p className="text-[11px] text-gray-500 mt-2.5 leading-relaxed">
                  {f.description}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
