"use client";
import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "@/lib/api";

export function useData<T>(path: string | null, interval = 0, grant = "") {
  const [dataGrant, setDataGrant] = useState(grant);
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState<ApiError | null>(null),
    [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!path) {
      setLoading(false);
      return;
    }
    try {
      const result = await api<T>(path, {
        headers: grant ? { "X-Case-Access": grant } : {},
      });
      setData(result);
      setDataGrant(grant);
      setError(null);
    } catch (e) {
      if ([401, 403, 404].includes((e as ApiError).status || 0)) setData(null);
      setError(e as ApiError);
    } finally {
      setLoading(false);
    }
  }, [path, grant]);
  useEffect(() => {
    let active = true;
    async function fetchData() {
      if (!path) {
        setLoading(false);
        return;
      }
      try {
        const result = await api<T>(path, {
          headers: grant ? { "X-Case-Access": grant } : {},
        });
        if (active) {
          setData(result);
          setDataGrant(grant);
          setError(null);
        }
      } catch (e) {
        if (active) {
          if ([401, 403, 404].includes((e as ApiError).status || 0))
            setData(null);
          setError(e as ApiError);
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchData();
    const id = interval
      ? setInterval(() => {
          if (!document.hidden) fetchData();
        }, interval)
      : undefined;
    return () => {
      active = false;
      if (id) clearInterval(id);
    };
  }, [path, interval, grant]);
  return { data: dataGrant === grant ? data : null, error, loading, reload };
}
