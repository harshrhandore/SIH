"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useCurrentUser } from "@/hooks/use-current-user";

export function useData<T>(
  path: string | null,
  interval: number | ((data: T | null) => number | false) = 0,
  grant = "",
) {
  const session = useCurrentUser();
  const client = useQueryClient();
  const key = queryKeys.data(session.data, path, grant);
  const query = useQuery<T | null, ApiError>({
    queryKey: key,
    enabled: Boolean(path && session.data),
    queryFn: async ({ signal }) => {
      if (!path) return null;
      try {
        return await api<T>(path, {
          signal,
          headers: grant ? { "X-Case-Access": grant } : {},
        });
      } catch (error) {
        if ([401, 403, 404].includes((error as ApiError).status || 0))
          client.setQueryData(key, null);
        throw error;
      }
    },
    gcTime: grant ? 0 : 300000,
    refetchInterval:
      typeof interval === "function"
        ? (state) => interval(state.state.data ?? null)
        : interval || (grant ? 30000 : false),
    refetchIntervalInBackground: false,
  });
  const forbidden = [401, 403, 404].includes(query.error?.status || 0);
  return {
    data: forbidden ? null : (query.data ?? null),
    error: query.error,
    loading: Boolean(path) && query.isPending,
    reload: () => query.refetch(),
  };
}
