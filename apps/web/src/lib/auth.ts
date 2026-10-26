import { api } from "@/lib/api";
import type { User } from "@/lib/schemas";

export function homeFor(user: User) {
  return user.role === "STUDENT"
    ? "/students/" + user.student_id
    : user.role === "ADMIN"
      ? "/oversight"
      : "/dashboard";
}

export async function signOut() {
  return api("/auth/logout", {
    method: "POST",
    body: JSON.stringify({ all_sessions: false }),
  });
}
