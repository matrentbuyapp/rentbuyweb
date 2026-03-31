"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { FormData, SummaryResponse } from "@/lib/types";
import { DEFAULT_FORM_VALUES } from "@/lib/defaults";
import { postSummary, formToRequest } from "@/lib/api";
import { storeLiveResult, loadView, loadLiveResult, clearAll } from "@/lib/resultStore";

const FORM_KEY = "rent-buy-form";

function loadFormData(): FormData {
  try {
    const raw = localStorage.getItem(FORM_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const merged = { ...DEFAULT_FORM_VALUES, ...parsed };
      // Sanity clamp: years must be 2-15, stay_years within years
      merged.years = Math.max(2, Math.min(15, merged.years || 10));
      merged.stay_years = Math.max(1, Math.min(merged.years, merged.stay_years || merged.years));
      return merged;
    }
  } catch {}
  return DEFAULT_FORM_VALUES;
}

function saveFormData(data: FormData): void {
  try {
    localStorage.setItem(FORM_KEY, JSON.stringify(data));
  } catch {}
}

export function useSimulation() {
  const [formData, setFormData] = useState<FormData>(DEFAULT_FORM_VALUES);
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Hydrate form + result from localStorage on mount
  useEffect(() => {
    setFormData(loadFormData());
    const live = loadLiveResult();
    if (live) {
      setResult(live.result);
      setHasRun(true);
    }
  }, []);

  const updateField = useCallback(
    <K extends keyof FormData>(field: K, value: FormData[K]) => {
      setFormData((prev) => {
        const next = { ...prev, [field]: value };
        saveFormData(next);
        setIsDirty(true);
        return next;
      });
    },
    []
  );

  const scrollToResults = useCallback(() => {
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }, []);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await postSummary(formData);
      setResult(res);
      setHasRun(true);
      setIsDirty(false);
      storeLiveResult(res, formToRequest(formData));
      scrollToResults();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      scrollToResults();
    } finally {
      setLoading(false);
    }
  }, [formData, scrollToResults]);

  const resetAll = useCallback(() => {
    setFormData(DEFAULT_FORM_VALUES);
    saveFormData(DEFAULT_FORM_VALUES);
    setResult(null);
    setHasRun(false);
    setIsDirty(false);
    setError(null);
    try {
      clearAll();
      localStorage.removeItem("rent-buy-form");
      localStorage.removeItem("rent-buy-premium");
      localStorage.removeItem("device_id");
      localStorage.removeItem("alert_email");
    } catch {}
  }, []);

  return { formData, updateField, resetAll, result, setResult, loading, error, hasRun, isDirty, runSimulation, resultsRef };
}
