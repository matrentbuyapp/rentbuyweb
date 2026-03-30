"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getApiUrl } from "@/lib/api";

interface ZipInfo {
  price: number;
  tax_rate: number | null;
}

interface ZipPriceData {
  national_median: number;
  updated_at: string;
  zips: Record<string, ZipInfo>;
}

export function useZipPrices() {
  const [data, setData] = useState<ZipPriceData | null>(null);
  const [loading, setLoading] = useState(false);
  const fetchedRef = useRef(false);

  const doFetch = useCallback(async () => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    setLoading(true);
    try {
      const res = await fetch(`${getApiUrl()}/data/zip_prices.json`);
      if (res.ok) {
        setData(await res.json());
      }
    } catch {
      // File may not exist yet
      fetchedRef.current = false; // allow retry
    } finally {
      setLoading(false);
    }
  }, []);

  // Load eagerly on mount
  useEffect(() => {
    doFetch();
  }, [doFetch]);

  const lookup = useCallback(
    (zip: string): ZipInfo | null => {
      if (!data || !zip) return null;
      return data.zips[zip] ?? null;
    },
    [data],
  );

  const nationalMedian = data?.national_median ?? 277000;

  return { ensureLoaded: doFetch, lookup, nationalMedian, loading, loaded: !!data };
}
