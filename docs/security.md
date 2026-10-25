# Security boundaries

All records are synthetic. No official adapter exists. Operator access is institution-scoped; officers are limited to assigned institutions; students are restricted to their own UUID; administrator lists are masked or aggregated. A five-minute escalation grant is signed separately and bound to administrator, case, student and case version. State changes invalidate it.

JWTs use HS256 with issuer, audience, expiration, session-family and random identifier checks. The server fetches the current active user and assignments. Refresh tokens are opaque hashes, rotate on use and revoke the family on reuse. The browser holds access/refresh in HttpOnly cookies, and mutations check a readable CSRF cookie against its family-bound hash. The browser helper coalesces concurrent refreshes. Login checks Origin when supplied. Password hashing is bcrypt cost12 with a 72-byte limit.

The Next proxy removes caller authorization and forwarding headers, uses one server-configured origin, rejects redirects and sets no-store on responses. Local servers bind to loopback. Do not expose the API directly in a public deployment.

Storage paths are generated under a resolved containment root. Downloads authorize the owning student first. Document parsing checks magic bytes, limits size/pages and walks parsed PDF objects to reject active actions, scripts and attachments. The parser is not a general antivirus or a sandbox for arbitrary hostile files. CSV reports escape spreadsheet formula prefixes. XLSX formula cells are rejected.

Runtime has no owner credentials and cannot update/delete/truncate audit events or mutate audit heads directly. History tables have database immutability triggers. Full-chain verification proves consistency of the checked snapshot. A database owner could rewrite a complete chain and its head; real deployments need an external head anchor and a separately reviewed security model.

Known remaining limits are registered in OWNER_DECISIONS.md, including incomplete request/response typing, adversarial coverage, cloud upload throttles, some idempotency paths and large XLSX allocation behavior. Do not treat passing local tests as a production security audit.
