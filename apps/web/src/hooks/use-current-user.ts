"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { User } from "@/lib/schemas";

export function useCurrentUser() {
  const query = useQuery<User, ApiError>({
    queryKey: queryKeys.currentUser,
    queryFn: ({ signal }) => api<User>("/auth/me", { signal }),
  });
  return {
    data: query.data ?? null,
    loading: query.isPending,
    error: query.error,
    reload: () => query.refetch(),
  };
}

export function useRequiredUser(): User {
  const session = useCurrentUser();
  if (!session.data)
    throw new Error("This screen requires the authenticated workspace layout.");
  return session.data;
}
