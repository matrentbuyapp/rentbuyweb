"use client";

import { useState, useCallback, useEffect } from "react";
import { Scenario, SummaryRequest, SummaryResponse } from "@/lib/types";
import {
  listScenarios,
  saveScenario,
  runScenario,
  deleteScenario,
} from "@/lib/api";

export function useScenarios(isPro: boolean) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isPro) return;
    setLoading(true);
    setError(null);
    try {
      const list = await listScenarios();
      setScenarios(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }, [isPro]);

  // Load on mount when pro
  useEffect(() => {
    if (isPro) refresh();
  }, [isPro, refresh]);

  const save = useCallback(
    async (name: string, inputs: SummaryRequest, response?: SummaryResponse | null) => {
      const scenario = await saveScenario(name, inputs, response);
      setScenarios((prev) => [scenario, ...prev]);
      return scenario;
    },
    [],
  );

  const rerun = useCallback(async (id: string): Promise<SummaryResponse> => {
    const result = await runScenario(id);
    // Update cached response in local state
    setScenarios((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, response: result, updated_at: Date.now() / 1000 } : s,
      ),
    );
    return result;
  }, []);

  const remove = useCallback(async (id: string) => {
    await deleteScenario(id);
    setScenarios((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { scenarios, loading, error, save, rerun, remove, refresh };
}
