"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface ZipInfo {
  price: number;
  tax_rate: number | null;
}

interface ZipPriceData {
  national_median: number;
  updated_at: string;
  zips: Record<string, ZipInfo>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useZipPrices() {
  const [data, setData] = useState<ZipPriceData | null>(null);
  const [loading, setLoading] = useState(false);
  const fetchedRef = useRef(false);

  const ensureLoaded = useCallback(async () => {
    if (data || fetchedRef.current) return;
    fetchedRef.current = true;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/data/zip_prices.json`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch {
      // File may not exist yet — silently fail
    } finally {
      setLoading(false);
    }
  }, [data]);

  const lookup = useCallback(
    (zip: string): ZipInfo | null => {
      if (!data || !zip) return null;
      return data.zips[zip] ?? null;
    },
    [data],
  );

  const nationalMedian = data?.national_median ?? 277000;

  return { ensureLoaded, lookup, nationalMedian, loading, loaded: !!data };
}
