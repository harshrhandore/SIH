# Architecture

The browser calls a Next.js same-origin proxy, which injects the HttpOnly access cookie as a bearer token. FastAPI checks the current database user and assignments on every protected request. All data lives in one PostgreSQL database. Persistent uploads use the local storage volume; fixtures are synthetic and versioned.

```mermaid
flowchart LR
 B[Browser: synthetic role accounts] --> N[Next.js App Router and same-origin proxy]
 N --> AU[Authentication and backend scope]
 subgraph F[FastAPI modular monolith]
 AU --> IM[Import jobs and mapping]
 AU --> VE[Validation and human review]
 AU --> SE[Indexed search]
 AU --> AN[Analytics refresh]
 AU --> AD[Audit append and verifier]
 AU --> AI[Passport, certificate, trust, career]
 end
 SE <--> C[In-process TTL LRU cache]
 AU --> DB[(PostgreSQL 16)]
 IM --> DB
 VE --> DB
 SE --> DB
 AN --> DB
 AD --> DB
 AI --> DB
 IM --> ST[Persistent local storage]
 AI --> ST
 AI --> OC[PDF text then installed Tesseract]
 AI -. optional structured extraction .-> GM[Gemini with deterministic fallback]
 VE --> MK[MockApaarAdapter: MOCK, not official]
```

```mermaid
sequenceDiagram
 Browser->>Next: Search with filters and cookies
 Next->>API: Inject access token
 API->>DB: Active user, scope and institution epoch
 API->>Cache: Scope + user + epoch + filters
 alt Cache miss
 API->>DB: Exact count and indexed page
 API->>Cache: Store scoped rows; omit timer
 end
 API-->>Browser: Rows, total, fresh API timing, HIT or MISS
```

```mermaid
sequenceDiagram
 Operator->>API: Upload synthetic CSV or XLSX
 API->>DB: Store original source and staged rows
 Operator->>API: Map, preview, explicitly validate
 API->>DB: Freeze reference snapshot and create job
 loop Chunks of 250
 Worker->>DB: Student + finding + candidate + version + case + audit + checkpoint
 end
 API-->>Operator: Actual progress and report
 Officer->>API: Request correction with reason
 Operator->>API: Version-checked correction
 Officer->>API: Approve after blockers resolved
 API->>DB: Decision, audit, trust and epoch transaction
```

The API entry point now owns transport, errors, lifecycle and health checks and registers twelve domain routers. Auth, institutions, career and trust have separate schemas, service policy and repositories. Import mapping/rules/matching, certificate extraction/OCR/risk and audit canonicalization are separate modules. Some remaining domain routers still contain SQL and service policy; completing their service/repository extraction remains V2. Web screens still share components/workspace.tsx; table, badge, loading/error view, page heading, formatting and the shared data hook are extracted into their own modules. Tables have 32/44 px row-density controls hidden in print. The exact required tree is not complete; see the artifact report and S1 in the owner register.
