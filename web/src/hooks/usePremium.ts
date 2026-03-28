"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "rent-buy-premium";

export function usePremium() {
  const [isPro, setIsPro] = useState(false);

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "true") setIsPro(true);
    } catch {}
  }, []);

  const toggle = useCallback(() => {
    setIsPro((prev) => {
      const next = !prev;
      try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
      return next;
    });
  }, []);

  return { isPro, toggle };
}
