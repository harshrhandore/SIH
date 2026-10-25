# API

Business endpoints are under `/api/v1`; browser requests use `/api/backend` through Next.js. Live API schema: http://127.0.0.1:8000/docs. Committed OpenAPI is `packages/api-client/openapi.json`; generated TypeScript is `apps/web/src/lib/generated/api.d.ts`.

Errors contain code, message, fields and request_id for declared request/domain failures. Protected endpoints reload active users and assignments. List queries use exact counts and bounded pagination. Marked core mutations require a UUID Idempotency-Key; remaining incomplete replay paths are listed in V4.

Most response functions still lack rich Pydantic response models, and the current frontend uses generic wrappers rather than the required generated openapi-fetch transport throughout. Generated paths alone do not prove full contract conformance. Unsupported HTTP benchmark and audit-copy controls fail explicitly and provide local CLI instructions.
