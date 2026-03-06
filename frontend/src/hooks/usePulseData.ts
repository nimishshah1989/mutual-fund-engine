"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import type { ApiResponse } from "@/types/api";
import type {
  PulseFundItem,
  PulseCategorySummary,
  PulseCategoryResponse,
  PulsePeriod,
  PulseSignal,
} from "@/types/pulse";

/* ------------------------------------------------------------------ */
/*  Paginated pulse data hook                                          */
/* ------------------------------------------------------------------ */

interface PulseDataParams {
  period: PulsePeriod;
  category?: string | null;
  signal?: PulseSignal | null;
  sortBy?: string;
  sortDesc?: boolean;
  page?: number;
  limit?: number;
}

interface PulseDataResult {
  funds: PulseFundItem[];
  loading: boolean;
  error: string | null;
  total: number;
  totalPages: number;
  snapshotDate: string | null;
  refetch: () => void;
}

export function usePulseData(params: PulseDataParams): PulseDataResult {
  const {
    period,
    category,
    signal,
    sortBy = "ratio_return",
    sortDesc = true,
    page = 1,
    limit = 50,
  } = params;

  const [funds, setFunds] = useState<PulseFundItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [snapshotDate, setSnapshotDate] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams({
        period,
        sort_by: sortBy,
        sort_desc: String(sortDesc),
        page: String(page),
        limit: String(limit),
      });
      if (category) queryParams.set("category_name", category);
      if (signal) queryParams.set("signal", signal);

      const res = await apiFetch<{
        success: boolean;
        data: PulseFundItem[];
        meta: { page: number; limit: number; total: number; total_pages: number };
      }>(`/api/v1/pulse?${queryParams.toString()}`);

      setFunds(res.data ?? []);
      setTotal(res.meta?.total ?? 0);
      setTotalPages(res.meta?.total_pages ?? 0);
      // Extract snapshot_date from first item
      const firstFund = (res.data ?? [])[0];
      setSnapshotDate(firstFund?.snapshot_date ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pulse data");
    } finally {
      setLoading(false);
    }
  }, [period, category, signal, sortBy, sortDesc, page, limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { funds, loading, error, total, totalPages, snapshotDate, refetch: fetchData };
}

/* ------------------------------------------------------------------ */
/*  Category summary hook                                              */
/* ------------------------------------------------------------------ */

interface PulseCategoryResult {
  categories: PulseCategorySummary[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePulseCategories(period: PulsePeriod): PulseCategoryResult {
  const [categories, setCategories] = useState<PulseCategorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<PulseCategoryResponse>>(
        `/api/v1/pulse/categories?period=${period}`,
      );
      setCategories(res.data?.categories ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load categories");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { categories, loading, error, refetch: fetchData };
}
