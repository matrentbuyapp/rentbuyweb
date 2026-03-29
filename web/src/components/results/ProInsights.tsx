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
  scenarios: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
    </svg>
  ),
  "buying-memo": (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  ),
};

const ACCENT: Record<string, string> = {
  "ai-summary": "from-violet-50 to-purple-50 border-violet-100",
  sensitivity: "from-sky-50 to-blue-50 border-sky-100",
  trend: "from-emerald-50 to-teal-50 border-emerald-100",
  "zip-compare": "from-rose-50 to-pink-50 border-rose-100",
  scenarios: "from-indigo-50 to-blue-50 border-indigo-100",
  "buying-memo": "from-amber-50 to-orange-50 border-amber-100",
};

const ICON_BG: Record<string, string> = {
  "ai-summary": "bg-violet-100 text-violet-600",
  sensitivity: "bg-sky-100 text-sky-600",
  trend: "bg-emerald-100 text-emerald-600",
  "zip-compare": "bg-rose-100 text-rose-600",
  scenarios: "bg-indigo-100 text-indigo-600",
  "buying-memo": "bg-amber-100 text-amber-600",
};

/* Grayed-out mock previews shown to free users */
const PREVIEWS: Record<string, React.ReactNode> = {
  "ai-summary": (
    <div className="space-y-2 text-xs text-gray-500">
      <div className="flex items-start gap-2">
        <span className="text-green-500 mt-0.5">+</span>
        <p>Based on your numbers, <strong>buying looks favorable</strong> over a 7-year horizon with a projected net-worth advantage of ~$45k.</p>
      </div>
      <div className="flex items-start gap-2">
        <span className="text-red-400 mt-0.5">&minus;</span>
        <p>However, you&apos;re sensitive to a market correction in the first 2 years &mdash; if home prices dip 15%, renting wins.</p>
      </div>
      <div className="flex items-start gap-2">
        <span className="text-amber-500 mt-0.5">!</span>
        <p>Your low down payment means PMI for ~3 years, adding $180/mo in hidden cost.</p>
      </div>
    </div>
  ),
  sensitivity: (
    <div className="space-y-2">
      <div className="grid grid-cols-4 gap-1 text-[10px] text-center">
        <div />
        <div className="font-medium text-gray-500">4.5%</div>
        <div className="font-medium text-gray-500">5.5%</div>
        <div className="font-medium text-gray-500">6.5%</div>

        <div className="font-medium text-gray-500 text-left">10% DP</div>
        <div className="rounded py-1 bg-green-100 text-green-700">+$62k</div>
        <div className="rounded py-1 bg-green-50 text-green-600">+$38k</div>
        <div className="rounded py-1 bg-gray-100 text-gray-500">+$12k</div>

        <div className="font-medium text-gray-500 text-left">15% DP</div>
        <div className="rounded py-1 bg-green-100 text-green-700">+$58k</div>
        <div className="rounded py-1 bg-green-50 text-green-600">+$34k</div>
        <div className="rounded py-1 bg-gray-100 text-gray-500">+$8k</div>

        <div className="font-medium text-gray-500 text-left">20% DP</div>
        <div className="rounded py-1 bg-green-100 text-green-700">+$71k</div>
        <div className="rounded py-1 bg-green-50 text-green-600">+$45k</div>
        <div className="rounded py-1 bg-gray-100 text-gray-500">+$19k</div>
      </div>
      <p className="text-[10px] text-gray-400 text-center">Buy advantage by rate &times; down payment</p>
    </div>
  ),
  trend: (
    <div className="space-y-2">
      <div className="flex items-end gap-1 h-16 px-2">
        {[28, 32, 38, 35, 42, 48, 44, 50, 46, 40, 36, 30].map((h, i) => (
          <div key={i} className="flex-1 rounded-t bg-emerald-200" style={{ height: `${h * 1.2}%` }} />
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-gray-400 px-2">
        <span>Now</span><span>+6mo</span><span>+12mo</span><span>+24mo</span>
      </div>
      <p className="text-[10px] text-gray-400 text-center">Buy advantage if you wait N months</p>
    </div>
  ),
  "zip-compare": (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <div>
          <span className="font-medium text-gray-600">90210</span>
          <span className="text-gray-400 ml-1.5">Beverly Hills</span>
        </div>
        <span className="font-medium text-green-600">+$82k</span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <div>
          <span className="font-medium text-gray-600">90025</span>
          <span className="text-gray-400 ml-1.5">West LA</span>
        </div>
        <span className="font-medium text-green-600">+$54k</span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <div>
          <span className="font-medium text-gray-600">90034</span>
          <span className="text-gray-400 ml-1.5">Culver City</span>
        </div>
        <span className="font-medium text-green-600">+$41k</span>
      </div>
      <p className="text-[10px] text-gray-400 text-center pt-1">Projected buy advantage by ZIP</p>
    </div>
  ),
  scenarios: (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs">
        <span className="w-2 h-2 rounded-full bg-indigo-400" />
        <span className="font-medium text-gray-600 flex-1">Downtown 2BR</span>
        <span className="text-emerald-600 font-medium">Buy +$45k</span>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="w-2 h-2 rounded-full bg-indigo-300" />
        <span className="font-medium text-gray-600 flex-1">Suburbs 3BR</span>
        <span className="text-emerald-600 font-medium">Buy +$82k</span>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="w-2 h-2 rounded-full bg-indigo-200" />
        <span className="font-medium text-gray-600 flex-1">Wait 6 months</span>
        <span className="text-rose-500 font-medium">Rent +$12k</span>
      </div>
      <p className="text-[10px] text-gray-400 text-center pt-1">Save scenarios and get alerts when things change</p>
    </div>
  ),
  "buying-memo": (
    <div className="space-y-2">
      <div className="rounded-lg border border-gray-200 bg-white p-2.5 text-[10px] text-gray-500 space-y-1.5">
        <div className="font-semibold text-gray-700 text-xs">Buying Memo — Prepared for Jane Doe</div>
        <div className="border-t border-gray-100 pt-1.5">
          <span className="font-medium">Property:</span> 123 Main St, 90210
        </div>
        <div><span className="font-medium">Price:</span> $845,000 &middot; <span className="font-medium">Down:</span> 10% ($84,500)</div>
        <div><span className="font-medium">Rate:</span> 6.73% &middot; <span className="font-medium">Monthly:</span> $4,920</div>
        <div className="border-t border-gray-100 pt-1.5"><span className="font-medium">Verdict:</span> Buying builds $45k more wealth over 10 years</div>
      </div>
      <p className="text-[10px] text-gray-400 text-center">PDF ready to share with your lender or agent</p>
    </div>
  ),
};

export default function ProInsights({ result, isPro }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isPro) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-gray-500">Pro Insights</h2>
          <div className="h-px flex-1 bg-gray-200/60" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {PRO_FEATURES.map((f) => (
            <a
              key={f.id}
              href={`/insights#${f.id}`}
              className={`rounded-2xl border bg-gradient-to-br p-5 card-hover block ${ACCENT[f.id]}`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${ICON_BG[f.id]}`}>
                  {ICONS[f.id]}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">{f.title}</h3>
                  <p className="text-xs text-gray-400 mt-1">{f.description}</p>
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    );
  }

  // Free tier: gentle teaser with grayed-out previews
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
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-2.5">
        {PRO_FEATURES.map((f) => {
          const isExpanded = expandedId === f.id;
          return (
            <div key={f.id} className="flex flex-col">
              <button
                onClick={() => setExpandedId(isExpanded ? null : f.id)}
                className={`text-left rounded-xl border bg-gradient-to-br p-4 transition-all card-hover ${ACCENT[f.id]}
                  ${isExpanded ? "rounded-b-none border-b-0" : ""}`}
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
                  <svg
                    className={`w-4 h-4 text-gray-300 shrink-0 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>
              {isExpanded && (
                <div className={`rounded-b-xl border border-t-0 bg-gradient-to-br overflow-hidden ${ACCENT[f.id]}`}>
                  <div className="relative px-4 pb-4 pt-2">
                    {/* Grayed-out preview */}
                    <div className="opacity-40 pointer-events-none select-none" aria-hidden="true">
                      {PREVIEWS[f.id]}
                    </div>
                    {/* Fade overlay + unlock hint */}
                    <div className="absolute inset-0 bg-gradient-to-t from-white/80 via-transparent to-transparent flex items-end justify-center pb-3">
                      <span className="text-[10px] font-medium text-gray-400 bg-white/70 backdrop-blur-sm rounded-full px-3 py-1 border border-gray-200/60">
                        Upgrade to unlock
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="text-center mt-4">
        <a
          href="/insights"
          className="text-xs font-medium text-indigo-500 hover:text-indigo-600 transition-colors"
        >
          See all Pro features &rarr;
        </a>
      </div>
    </div>
  );
}
