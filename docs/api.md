# API

Business endpoints are under `/api/v1`; browser requests use `/api/backend` through Next.js. Live API schema: http://127.0.0.1:8000/docs. Committed OpenAPI is `packages/api-client/openapi.json`; generated TypeScript is `apps/web/src/lib/generated/api.d.ts`.

Errors contain code, message, fields and request_id for declared request/domain failures. Protected endpoints reload active users and assignments. List queries use exact counts and bounded pagination. Marked core mutations require a UUID Idempotency-Key; remaining incomplete replay paths are listed in V4.

Most response functions still lack rich Pydantic response models, and the frontend uses generic wrappers alongside the generated openapi-fetch auth transport. Generated paths alone do not prove full contract conformance. Local benchmark execution/polling and read-only audit-copy verification are implemented. Creating or tampering with the isolated audit copy remains owner-CLI-only; no HTTP reset or tamper-write endpoint exists.
