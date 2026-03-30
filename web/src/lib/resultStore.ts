/**
 * localStorage-backed store for sharing simulation results across pages.
 * Stores the last result + inputs + cache metadata + viewing context.
 */

import { SummaryResponse, SummaryRequest } from "./types";

const STORE_KEY = "rent-buy-session";

export interface StoredSession {
  result: SummaryResponse;
  inputs: SummaryRequest;
  cache_key: string | null;
  data_vintage: string | null;
  stored_at: number;
  /** If viewing a saved scenario, its name and id */
  scenario_name: string | null;
  scenario_id: string | null;
}

export function storeResult(
  result: SummaryResponse,
  inputs: SummaryRequest,
  scenario?: { id: string; name: string } | null,
): void {
  try {
    const session: StoredSession = {
      result,
      inputs,
      cache_key: result.cache_key ?? null,
      data_vintage: result.data_vintage ?? null,
      stored_at: Date.now(),
      scenario_name: scenario?.name ?? null,
      scenario_id: scenario?.id ?? null,
    };
    localStorage.setItem(STORE_KEY, JSON.stringify(session));
  } catch {
    // storage full or blocked
  }
}

export function loadResult(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // corrupted or missing
  }
  return null;
}
