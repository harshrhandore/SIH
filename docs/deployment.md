# Deployment preparation

The native local path is measured; Docker and external providers are not verified. Use the persistent local demo for judging. Never push `.env`, local databases, token-bearing browser traces or storage contents. Credentials for owner migrations stay out of web runtime environments.

## Local Docker

Follow README's five commands after installing Docker Desktop in Linux-container mode. The API runtime is nonroot UID10001; bootstrap alone receives `DATABASE_OWNER_URL`. Named storage persists original uploads. The container builds target Python3.11 and Node22; host validation used Python3.12 and Node25. Dependency compatibility validation and Docker execution must both be checked before claiming this path works.

## Optional public preview

Finish the gaps in V3 before exposing this build. In particular, cloud-specific upload rate/size controls, bounded wake UI and persistent seed certificate handling need verification. The Render filesystem is unsuitable for persistent evidence; missing files must produce a re-upload path. Current runtime code reports a missing file rather than inventing a successful verification.

Neon documents a free storage allowance of1GB/project and scale-to-zero after5minutes; keep the prompt's conservative400MB application budget. See [Neon plans](https://neon.com/docs/introduction/plans). The measured full100k seed was448,324,111bytes, so begin with5000students and measure the complete database. Inspect the owner's current account limits again before provisioning.

1. Create an empty PostgreSQL16 Neon project. Do not put real student data in it.
2. Create separate migrator and runtime credentials. Store the direct migrator URL locally as `DATABASE_OWNER_URL`, the runtime pooled SSL URL as `DATABASE_URL`, and the runtime password as `RUNTIME_DB_PASSWORD` in a private environment. No owner URL goes into Render.
3. The current bootstrap refuses nonempty targets and can accept `--students 5000`, but an explicitly named, budget-guarded cloud-bootstrap command remains unfinished. Implement and verify that gate before using an external database. Never substitute a reset command on a remote host.
4. Apply migrations, seed5000, refresh views, check the chain and measure `SELECT pg_database_size(current_database())`. Retain measured headroom.
5. Create the Render free Docker service from `render.yaml`. Configure `DATABASE_URL`, `JWT_SECRET`, `MASK_SECRET`, `GRANT_SECRET`, `WEB_ORIGIN`; use generated local values or rotate them privately. Leave model integration off. Health path is `/api/v1/health/ready`.
6. Confirm Render's current cold-start and filesystem behavior in [its free-service documentation](https://render.com/docs/free). That page was unavailable to the builder's web fetch, so provider-specific behavior remains an owner verification item.
7. Import the owner's private GitHub repository into Vercel, set root `apps/web`, select Next.js and Node22. Use repository-root `npm ci` and workspace build `npm run build --workspace apps/web` with monorepo access enabled. Set server-only `API_INTERNAL_ORIGIN` to the backend HTTPS origin, `WEB_ORIGIN` to the exact frontend HTTPS origin and `COOKIE_SECURE=true`. No database, JWT or Gemini secret belongs in Vercel frontend settings.
8. Align the API's `WEB_ORIGIN`. Test login, refresh, CSRF mutation, scoped search, certificate upload/download and unavailable-file behavior through the frontend origin. Record actual URLs and dataset volume only after success.
9. Check that this usage qualifies under the current [Vercel Hobby plan](https://vercel.com/docs/plans/hobby). No provider terms, payment enrollment or account creation were performed by the builder.

## Optional tunnel

Run `cloudflared tunnel --url http://localhost:3000`. Set `.env` `WEB_ORIGIN` to its exact returned HTTPS origin and `COOKIE_SECURE=true`, then restart both processes using `scripts/launch.py`. Keep the API private. No tunnel was installed or published during this run.

## Optional Gemini

Set `GEMINI_API_KEY`, `GEMINI_MODEL` and `LLM_ENABLED=true` privately, restart the API and run `python -m app.cli preflight`. The adapter uses structured JSON, an8second request timeout and rule fallback. Account/model availability is not proven by configuration presence. Run a real fixture and inspect `extraction_source`; the deterministic score must remain unchanged. Do not enable billing solely for this demo.
