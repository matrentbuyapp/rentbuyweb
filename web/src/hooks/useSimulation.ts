"use client";

import { useState, useCallback, useRef } from "react";
import { FormData, SummaryResponse } from "@/lib/types";
import { DEFAULT_FORM_VALUES } from "@/lib/defaults";
import { postSummary } from "@/lib/api";

export function useSimulation() {
  const [formData, setFormData] = useState<FormData>(DEFAULT_FORM_VALUES);
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  const updateField = useCallback(
    <K extends keyof FormData>(field: K, value: FormData[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  const scrollToResults = useCallback(() => {
    setTimeout(() => {
      const el = resultsRef.current;
      if (!el) return;
      const headerHeight = 60;
      const top = el.getBoundingClientRect().top + window.scrollY - headerHeight;
      window.scrollTo({ top, behavior: "smooth" });
    }, 100);
  }, []);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await postSummary(formData);
      setResult(res);
      setHasRun(true);
      scrollToResults();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      scrollToResults();
    } finally {
      setLoading(false);
    }
  }, [formData, scrollToResults]);

  return { formData, updateField, result, setResult, loading, error, hasRun, runSimulation, resultsRef };
}
