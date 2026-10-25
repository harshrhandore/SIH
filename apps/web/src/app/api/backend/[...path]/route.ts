import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const origin = process.env.API_INTERNAL_ORIGIN || "http://127.0.0.1:8000";
const webOrigin = process.env.WEB_ORIGIN || "http://localhost:3000";
const secure = process.env.COOKIE_SECURE === "true";
async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  if (path.some((p) => p === ".." || p.includes("/") || p.includes("\\")))
    return NextResponse.json(
      { error: { code: "INVALID_PATH", message: "Invalid path", fields: [] } },
      { status: 400 },
    );
  const suppliedOrigin = req.headers.get("origin");
  if (suppliedOrigin && suppliedOrigin !== webOrigin)
    return NextResponse.json(
      {
        error: {
          code: "ORIGIN_FORBIDDEN",
          message: "Origin not permitted",
          fields: [],
        },
      },
      { status: 403 },
    );
  const headers = new Headers();
  for (const name of ["content-type", "idempotency-key", "x-case-access"]) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }
  const access = req.cookies.get("shiksham_access")?.value;
  if (access) headers.set("authorization", "Bearer " + access);
  if (suppliedOrigin) headers.set("origin", suppliedOrigin);
  const csrf = req.headers.get("x-csrf-token");
  if (csrf) headers.set("x-csrf-token", csrf);
  if (
    req.method !== "GET" &&
    path.join("/") !== "auth/login" &&
    (!csrf || csrf !== req.cookies.get("shiksham_csrf")?.value)
  )
    return NextResponse.json(
      {
        error: {
          code: "CSRF_INVALID",
          message: "Refresh your session and retry.",
          fields: [],
        },
      },
      { status: 403 },
    );
  let body: BodyInit | undefined;
  if (!["GET", "HEAD"].includes(req.method)) {
    if (Number(req.headers.get("content-length") || 0) > 20 * 1024 * 1024)
      return NextResponse.json(
        {
          error: {
            code: "FILE_TOO_LARGE",
            message: "Maximum upload is 20 MiB.",
            fields: [],
          },
        },
        { status: 413 },
      );
    const bytes = await req.arrayBuffer();
    if (bytes.byteLength > 20 * 1024 * 1024)
      return NextResponse.json(
        {
          error: {
            code: "FILE_TOO_LARGE",
            message: "Maximum upload is 20 MiB.",
            fields: [],
          },
        },
        { status: 413 },
      );
    body = bytes;
    if (path.join("/") === "auth/refresh")
      body = JSON.stringify({
        refresh_token: req.cookies.get("shiksham_refresh")?.value || "",
      });
  }
  try {
    const upstream = await fetch(
      origin +
        "/api/v1/" +
        path.map(encodeURIComponent).join("/") +
        req.nextUrl.search,
      {
        method: req.method,
        headers,
        body,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(60000),
      },
    );
    if (
      ["auth/login", "auth/refresh"].includes(path.join("/")) &&
      upstream.ok
    ) {
      const payload = await upstream.json();
      const response = NextResponse.json(
        { user: payload.user, expires_in: payload.expires_in },
        { headers: { "Cache-Control": "no-store" } },
      );
      const opts = { httpOnly: true, sameSite: "lax" as const, secure };
      response.cookies.set("shiksham_access", payload.access_token, {
        ...opts,
        path: "/",
        maxAge: 900,
      });
      response.cookies.set("shiksham_refresh", payload.refresh_token, {
        ...opts,
        path: "/api/backend/auth",
        maxAge: 604800,
      });
      response.cookies.set("shiksham_csrf", payload.csrf_token, {
        ...opts,
        httpOnly: false,
        path: "/",
        maxAge: 604800,
      });
      return response;
    }
    const response = new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
    const disposition = upstream.headers.get("content-disposition");
    if (disposition) response.headers.set("content-disposition", disposition);
    if (
      path.join("/") === "auth/logout" ||
      (path.join("/") === "auth/refresh" && !upstream.ok)
    ) {
      for (const name of ["shiksham_access", "shiksham_csrf"])
        response.cookies.set(name, "", { path: "/", maxAge: 0 });
      response.cookies.set("shiksham_refresh", "", {
        path: "/api/backend/auth",
        maxAge: 0,
      });
    }
    return response;
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "BACKEND_UNAVAILABLE",
          message: "Backend is unavailable. Start the API and retry.",
          fields: [],
        },
      },
      { status: 503 },
    );
  }
}
export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
};
