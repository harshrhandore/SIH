import type { User } from "@/lib/schemas";

export const queryKeys = {
  currentUser: ["session", "me"] as const,
  data: (user: User | null, path: string | null, grant: string) =>
    [
      "workspace-data",
      user?.id,
      user?.role,
      user?.institution_id,
      [...(user?.assigned_institutions || [])].sort().join(","),
      path,
      grant,
    ] as const,
  studentSearch: (user: User, query: string) =>
    [
      "student-search",
      user.id,
      user.role,
      user.institution_id,
      [...user.assigned_institutions].sort().join(","),
      query,
    ] as const,
};
