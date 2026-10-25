import createClient from "openapi-fetch";
import type { paths } from "./generated/api";
const generatedClient = createClient<paths>({ baseUrl: "/api/backend" });
generatedClient.use({
  onRequest({ request }) {
    const url = new URL(request.url);
    url.pathname = url.pathname.replace(
      "/api/backend/api/v1/",
      "/api/backend/",
    );
    return new Request(url, request);
  },
});

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public requestId?: string,
    public status?: number,
  ) {
    super(message);
  }
}
let refreshInFlight: Promise<unknown> | null = null;
export async function api<T = Record<string, unknown>>(
  path: string,
  init: RequestInit = {},
  refresh = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("content-type", "application/json");
  if (init.method && init.method !== "GET") {
    headers.set(
      "idempotency-key",
      headers.get("idempotency-key") || crypto.randomUUID(),
    );
    const csrf = document.cookie
      .split("; ")
      .find((c) => c.startsWith("shiksham_csrf="))
      ?.split("=")[1];
    if (csrf) headers.set("x-csrf-token", csrf);
  }
  const response =
    path === "/auth/me" && (!init.method || init.method === "GET")
      ? (
          await generatedClient.GET("/api/v1/auth/me", {
            headers,
            cache: "no-store",
            parseAs: "stream",
          })
        ).response
      : await fetch("/api/backend" + path, {
          ...init,
          headers,
          cache: "no-store",
        });
  if (
    response.status === 401 &&
    refresh &&
    (!path.startsWith("/auth/") || path === "/auth/me")
  ) {
    try {
      if (!refreshInFlight)
        refreshInFlight = api(
          "/auth/refresh",
          { method: "POST", body: "{}" },
          false,
        ).finally(() => {
          refreshInFlight = null;
        });
      await refreshInFlight;
      return api<T>(path, init, false);
    } catch {
      location.href = "/login";
    }
  }
  if (!response.ok) {
    const data = await response.json();
    throw new ApiError(
      data.error?.code || "REQUEST_FAILED",
      data.error?.message || "Request failed",
      data.error?.request_id,
      response.status,
    );
  }
  return response.json();
}
