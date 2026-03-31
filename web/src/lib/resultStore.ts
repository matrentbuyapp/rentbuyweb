/**
 * localStorage-backed store for sharing simulation state across pages.
 * Two keys:
 *   - LIVE_KEY: the latest simulation result (never overwritten by scenario views)
 *   - VIEW_KEY: what the user is currently looking at (live or a specific scenario)
 */

import { SummaryResponse, SummaryRequest } from "./types";

const LIVE_KEY = "rent-buy-live";
const VIEW_KEY = "rent-buy-view";

export interface StoredSession {
  result: SummaryResponse;
  inputs: SummaryRequest;
  cache_key: string | null;
  data_vintage: string | null;
  stored_at: number;
  scenario_name: string | null;
  scenario_id: string | null;
}

/** Store the latest live simulation result */
export function storeLiveResult(result: SummaryResponse, inputs: SummaryRequest): void {
  try {
    const session: StoredSession = {
      result, inputs,
      cache_key: result.cache_key ?? null,
      data_vintage: result.data_vintage ?? null,
      stored_at: Date.now(),
      scenario_name: null,
      scenario_id: null,
    };
    localStorage.setItem(LIVE_KEY, JSON.stringify(session));
    // Also set as current view
    localStorage.setItem(VIEW_KEY, JSON.stringify(session));
  } catch {}
}

/** Store what the user is currently viewing (live or saved scenario) */
export function storeView(
  result: SummaryResponse,
  inputs: SummaryRequest,
  scenario?: { id: string; name: string } | null,
): void {
  try {
    const session: StoredSession = {
      result, inputs,
      cache_key: result.cache_key ?? null,
      data_vintage: result.data_vintage ?? null,
      stored_at: Date.now(),
      scenario_name: scenario?.name ?? null,
      scenario_id: scenario?.id ?? null,
    };
    localStorage.setItem(VIEW_KEY, JSON.stringify(session));
  } catch {}
}

/** Load current view (what the user last looked at) */
export function loadView(): StoredSession | null {
  try {
    const raw = localStorage.getItem(VIEW_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

/** Load the live result (always the latest simulation, never a scenario) */
export function loadLiveResult(): StoredSession | null {
  try {
    const raw = localStorage.getItem(LIVE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

/** Clear everything */
export function clearAll(): void {
  try {
    localStorage.removeItem(LIVE_KEY);
    localStorage.removeItem(VIEW_KEY);
  } catch {}
}

// Legacy compat
export const storeResult = storeView;
export const loadResult = loadView;
