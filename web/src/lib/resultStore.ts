/**
 * Simple localStorage-backed store for sharing the last simulation result
 * across pages (main calculator → insights page).
 */

import { SummaryResponse, SummaryRequest } from "./types";

const RESULT_KEY = "rent-buy-last-result";
const INPUTS_KEY = "rent-buy-last-inputs";

export function storeResult(result: SummaryResponse, inputs: SummaryRequest): void {
  try {
    localStorage.setItem(RESULT_KEY, JSON.stringify(result));
    localStorage.setItem(INPUTS_KEY, JSON.stringify(inputs));
  } catch {
    // storage full or blocked
  }
}

export function loadResult(): { result: SummaryResponse; inputs: SummaryRequest } | null {
  try {
    const r = localStorage.getItem(RESULT_KEY);
    const i = localStorage.getItem(INPUTS_KEY);
    if (r && i) return { result: JSON.parse(r), inputs: JSON.parse(i) };
  } catch {
    // corrupted or missing
  }
  return null;
}
