# VILEORUF CRM — Architecture

## 1. Architecture style
Use a modular monolith for the 7-day MVP.

Reasons:
- lower implementation and DevOps overhead than microservices;
- simpler debugging;
- faster delivery;
- clear module boundaries still allow later extraction if needed.

## 2. High-level architecture

The diagram below is the target MVP architecture. Day 1–4 functionality is implemented, including Lead Scoring, Deal Prediction, advisory Next Best Action, initial new-Deal AI orchestration, employee-controlled AI Email Drafts, unified AI history, runtime AI settings, manual-launch hardening, final public/authenticated browser verification, and safe local smoke credential handling. Day 4 is complete. D5.1 shared Integration Foundation and D5.2a Google OAuth/token lifecycle are implemented; Gmail business operations and other provider-specific Day 5 workflows remain planned and are governed by the approved `docs/DAY5_INTEGRATIONS_CONTRACT.md`.

```text
React Frontend
      |
      | REST/JSON
      v
FastAPI Backend
      |
      +----------------+------------------+
      |                |                  |
      v                v                  v
 PostgreSQL        AI Service       Integration Layer
                                         |
                              +----------+----------+----------+
                              |          |          |          |
                            Gmail     Telegram   WhatsApp   Calendar

Celery Workers
      |
      v
Redis (broker, architectural addition)
```

## 3. Backend responsibilities
The target FastAPI backend contains:
- API routes/controllers;
- validation schemas;
- ORM models;
- repositories/data access;
- business services;
- AI service;
- integration adapters;
- background job definitions;
- configuration/security infrastructure.

Avoid putting business logic directly in route handlers.

Implemented backend baseline through D4.6:
- Python 3.10.12 and FastAPI;
- `GET /health`, independent of database availability;
- centralized environment settings using `pydantic-settings`;
- PostgreSQL-only SQLAlchemy 2.x engine/session infrastructure using Psycopg 3;
- Alembic with shared application configuration and current head `20260907_0010`;
- restricted development CORS for the configured `FRONTEND_ORIGIN`.
- `Client`, `PipelineStage`, and `Deal` domain models and services, including backend-authoritative CRM role/ownership authorization;
- the public request action endpoint and development/test-only deterministic demo seed.
- common `AIAnalysis`, separate `EmailDraft`, and model-override persistence foundations at Alembic head `20260902_0005`;
- reusable deterministic fingerprint/compact snapshot, strict structured validation, normalized failure/retry lifecycle, and duplicate in-flight protection;
- OpenAI Responses API adapter behind the internal provider boundary, with no API key required until a provider operation runs;
- Redis-backed Celery application with dedicated `ai` and logical `integrations` queues; D5.1 registers only a non-provider integration foundation task.
- `Category`, `Service`, singleton Lead Scoring settings, Deal Service/effort fields, and Client preferred communication language persistence;
- typed business-management and manual Deal Lead Scoring APIs, deterministic backend Commercial Value/overall scoring, and targeted freshness invalidation.
- typed manual Deal Prediction and Next Best Action APIs plus Celery tasks on the common `AIAnalysis` lifecycle;
- persisted `AI Enabled`, automatic-new-Deal-analysis, DP validity, and NBA validity business settings;
- a minimal `InitialAIAnalysisPipeline` correlation row that freezes the creator-selected language and exact initial LS/DP/NBA analysis IDs.
- `ai.email_draft.execute`, typed generation/history and EmailDraft CRUD endpoints. Generation stores a placeholder-form `AIAnalysis` only; explicit save creates an editable EmailDraft and never creates a Communication.
- ADMIN-only safe runtime AI settings API, role-aware unified AI history, and a Redis-backed per-employee fixed-window limiter shared by the four manual launch endpoints.
- D5.1 `IntegrationConnection`, `ExternalMessage`, and `CalendarEvent` persistence/lifecycle foundation, with one corporate connection per provider, provider-message uniqueness, and `ExternalMessage != Communication` / `Task != CalendarEvent` separation.
- EmailDraft `DRAFT`/`SENT` foundation with service-level immutability for historical `SENT` content; provider adapter and safe error/retry classification boundaries; application-level encrypted token payload storage configured by an environment-only key.
- D5.1 ADMIN-only safe `GET /settings/integrations` and localized `/crm/settings/integrations` with Gmail, Telegram, Google Calendar, and WhatsApp disconnected status cards; D5.1 itself introduced no OAuth, provider calls, send/sync/webhook, or provider-confirmed Communication workflow.
- D5.2a Google OAuth boundary: ADMIN-only connect/reconnect/disconnect endpoints, short-lived single-use hashed state records, callback code exchange and refresh isolated in `google_oauth`, Fernet-encrypted token payload persistence on the single corporate Gmail connection, and safe redirect/UI outcomes. No Gmail API, Calendar API, provider message or Communication operation is included.

## 4. Frontend responsibilities
The target React frontend contains:
- application shell/navigation;
- Dashboard;
- Pipeline;
- Clients;
- Client details;
- Deals;
- Tasks;
- Settings/integrations;
- reusable components;
- feature modules;
- API client layer;
- i18n resources (`ru`, `en`, `es`).

The implemented JavaScript React frontend uses project-pinned Node.js 24.20.0, npm 11.19.0, Vite 8.2.2 and `@vitejs/plugin-react`. It includes `AuthProvider`/`useAuth`, i18next/react-i18next resources, protected CRM shell/navigation, Clients, Deals with all four AI sections and Deal-level history, Pipeline Kanban, Tasks, unified AI History, ADMIN business/AI settings, ADMIN Integration Settings with four safe status cards, and a Service-aware public request page. Access JWT exists only in React memory; refresh restores the employee session from the cookie. The UI is translated in ru/en/es and reflects roles, but backend authorization remains authoritative.

Target application boundary:

```text
React application
├── Public area
│   └── unauthenticated information/request entry
└── Employee CRM
    └── ADMIN/MANAGER authentication required
```

Current routes are `/` for public request, `/login` for employee login, `/crm`, `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks`, and `/crm/ai-history` for protected employee CRM, plus ADMIN-only `/crm/settings/business` and `/crm/settings/ai`. `/crm` is the bounded operational Dashboard, not a reporting route. Public area does not mean customer portal.

## 5. Target repository structure

```text
vileoruf-crm/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── clients/
│   │   │   ├── deals/
│   │   │   ├── pipeline/
│   │   │   ├── communications/
│   │   │   ├── tasks/
│   │   │   ├── analytics/
│   │   │   ├── ai/
│   │   │   └── integrations/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   └── integrations/
│   │   ├── repositories/
│   │   ├── core/
│   │   ├── workers/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── features/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── i18n/
│   │       ├── ru.json
│   │       ├── en.json
│   │       └── es.json
│   └── package.json
├── docker/
├── docs/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Codex must not substantially reorganize this architecture without explicit approval.

Future feature directories are created only with their corresponding implementation; empty directories are not required. The implemented repository also contains CRM API modules, models, schemas, services, scripts, tests, frontend pages/services, and the VILEORUF logo asset for Day 2.

```text
vileoruf-crm/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── scripts/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── i18n/locales/
│   │   ├── services/
│   │   ├── styles/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── docs/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── .nvmrc
```

## 6. Core domain entities
Initial domain model:
- User
- Client
- Deal
- PipelineStage
- Communication
- Task
- AIAnalysis
- EmailDraft
- IntegrationConnection
- ExternalMessage
- CalendarEvent

Core relationships:

```text
Client
 ├── Deals
 ├── Communications
 └── Tasks

Deal
 ├── PipelineStage
 ├── Communications
 ├── Tasks
 ├── AIAnalysis
 └── EmailDraft

IntegrationConnection
 ├── ExternalMessages
 └── CalendarEvents
```

`Deal` ownership uses `responsible_user_id` (or an equivalent foreign key) to `User`. `Client` has the lifecycle states `CUSTOMER` and `CLIENT`; the first Deal moved successfully to `Won` promotes `CUSTOMER` to `CLIENT`, with no automatic reverse transition.

The implemented public boundary is an action endpoint, not an entity: `POST /public/requests` atomically creates a `CUSTOMER` Client and unassigned Deal in system stage `New Lead`. Public visitors never become `User`; `/` is public while `/login` and `/crm/*` remain employee routes.

Do not introduce Payment, Invoice, Subscription or similar financial-processing entities unless requirements change.

`User`, `Client`, `Deal`, `PipelineStage`, `Communication`, `Task`, `Category`, `Service`, `LeadScoringSettings`, `AIAnalysis`, `InitialAIAnalysisPipeline`, and `EmailDraft` persistence models are implemented. D4.5 uses EmailDraft as an employee-controlled working document: multiple drafts per Deal, explicit manual/AI-origin save, edit and physical deletion without deleting the source AIAnalysis. It is distinct from Communication and has no send path.

### 6.1 Day 3 Communications contract

`Communication` is an append-oriented CRM history record, not a live integration. It has a required Client, optional Deal, channel (`EMAIL`, `TELEGRAM`, `WHATSAPP`, `MANUAL`, `OTHER`), direction (`INCOMING`, `OUTGOING`), content, actual communication timestamp, and the sole initial CRM status `RECORDED`.

When linked to a Deal, the Deal must belong to its Client; the backend authoritatively validates this invariant. Day 3 supports create and get/list/read only, with no DELETE or arbitrary edit. ADMIN may create history for any Client/Deal. MANAGER may create client-level records for any Client and Deal-linked records only on Deals they own. Both roles can read history. Channel classification does not create Gmail, Telegram, WhatsApp, or other live integration semantics; delivery tracking, provider IDs, delivery/read states, retries, errors, and synchronization are excluded.

### 6.2 Day 3 Tasks contract

`Task` is an internal CRM task with title, optional description, due datetime, persisted `OPEN`/`COMPLETED` status, responsible active ADMIN/MANAGER employee, and optional Client and Deal associations. General tasks are allowed. Where both Client and Deal are specified, the Deal must belong to the Client; a Deal-only task does not need a duplicate Client. The backend authoritatively validates these relationships.

ADMIN sees and updates all Tasks, may create for any active ADMIN/MANAGER, and may reassign responsibility. MANAGER sees all Tasks but may create only for themself and update/complete only Tasks assigned to themself; they cannot reassign. The implemented API provides create, list/get, PATCH of business fields, and explicit `POST /tasks/{task_id}/complete`; DELETE is absent. `OVERDUE` is derived from an open task with a past due datetime, not persisted or returned as an API field.

### 6.3 D4.2 business configuration and Lead Scoring

Each `Service` belongs to exactly one `Category`; Deals reference Service only, so Category cannot conflict and is derived through that relation. Records use active/inactive state instead of physical deletion, while existing Deals retain historical foreign keys. Category holds positive target EUR/person-hour and target person-hours. A separate singleton stores four non-negative Lead Scoring weights constrained to exactly 100 and a validated ordered Commercial Value scale.

Commercial Value is deterministic backend business logic. Effective effort uses `Deal.manager_effort_estimate` when present, otherwise Category target effort. With a budget, the backend computes deal hourly rate and its ratio to Category target rate, applies clamped piecewise-linear interpolation, and rounds scores with decimal half-up semantics to one decimal. Missing budget is `NO_BUDGET` with score `0.0`, not a negative AI judgment; missing/invalid rate or effort is a configuration error and prevents launch. The provider schema contains only Service Fit, Lead Quality, Feasibility, explanations, summary, optional missing-data/security information, and an allowlisted Category suggestion. It cannot submit Commercial Value, weights, rates, effort, ratio, or overall score. The backend recomputes the final overall weighted score.

Manual Lead Scoring creates one `AIAnalysis` row and dispatches `ai.lead_scoring.execute` to the dedicated Celery queue. ADMIN can run/read any Deal; MANAGER can run/read only an owned Deal. Won/Lost Deals cannot start new calculations. Relevant Deal or business-configuration changes mark only the latest successful Lead Scoring of affected active Deals outdated; stage-only changes do not, closed historical analyses are preserved, and no automatic recomputation or time expiry exists.

### 6.4 D4.3 Deal Prediction

Deal Prediction estimates `probability_won` separately from evidence `confidence`. Its input is the current Deal, deterministic newest-first character-bounded current-Deal Communications, structured Task/activity indicators, and anonymized same-Client aggregate history. It never uses global CRM history, raw other-Deal data, structured Client/employee PII, or Lead Scoring. Active results expire lazily after the persisted validity period (default 7 days); closed history does not age out.

### 6.5 D4.4 Next Best Action and initial orchestration

Next Best Action is advisory only: it returns 1–3 strictly validated ranked actions with priority, action, reason and timing, but cannot execute CRM mutations, create/complete Tasks or Communications, send messages, or call integrations. It reuses the Deal Prediction primary context builder and optionally adds the latest successful Lead Scoring and Deal Prediction with explicit `available`/`is_outdated` metadata. Probability, evidence confidence, commercial attractiveness and NBA urgency remain distinct concepts. New successful LS or DP results stale the latest successful NBA; dependencies never flow backwards. Active NBA expires lazily after its persisted validity period (default 7 days), while closed history is preserved.

For a newly committed active Deal, when both persistent switches are enabled, the service creates one correlation row and two independently queued sibling analyses in one transaction, then dispatches both after commit:

```text
Lead Scoring (specific analysis id) ─────┐
                                        ├──> Next Best Action (once)
Deal Prediction (specific analysis id) ─┘
```

Each branch records expected provider/configuration failure as terminal `FAILED`; the correlator waits for both exact initial rows to reach `SUCCESS` or `FAILED`, then freezes NBA's own current context using whichever successful auxiliary results exist. Unique database constraints prevent duplicate pipeline/branch/NBA identity. Public requests freeze `RU`; employee-created Deals freeze the creator's current UI language. Deal creation is committed before dispatch and remains successful if the broker is unavailable. If the Deal closes before follow-on NBA creation, orchestration no-ops; already accepted operations may finish as outdated historical results.

### 6.6 D4.5 AI Email Draft

`POST/GET /deals/{deal_id}/email-draft` creates/reads an asynchronous `EMAIL_DRAFT` AIAnalysis proposal; CRUD at `/deals/{deal_id}/email-drafts` is a separate employee document flow. The selected NBA reference is optional and backend-resolved from a successful same-Deal action. The generation input is frozen for retries; a later context mismatch marks the proposal outdated but never changes a saved EmailDraft. Client preferred communication language controls the email independently of UI language. No structured Client PII is sent to the provider: `{{client_name}}` is the only supported token and is substituted for authorized presentation only. ADMIN is unrestricted; MANAGER is limited to owned Deals. Unlike LS/DP/NBA, closed Deals remain eligible. `AI Enabled` rejects new AI generation but not history or manual EmailDraft CRUD. No SMTP/provider/integration/send/Communication side effect exists.

### 6.7 D4.6 AI History, settings, and hardening

`GET /ai-history` and `GET /deals/{deal_id}/ai-history` provide one paginated newest-first history across Lead Scoring, Deal Prediction, Next Best Action, and Email Draft analyses. ADMIN sees all authorized CRM history; MANAGER is constrained in the database query to owned Deals. Filters cover function, status, Deal, language, outdated state, and current successful result. Responses revalidate stored typed results and expose only safe metadata/usage; malformed legacy results degrade to an unavailable payload and raw prompts, snapshots, fingerprints, provider errors, and secrets are never returned.

`GET/PATCH /settings/ai` is ADMIN-only and manages runtime switches, allowlisted analysis/email model overrides, and 1–365 day DP/NBA validity. Updates are atomic, model reset falls back to environment defaults, prepared analyses keep their frozen model, and changed fields produce safe application-log audit events. Manual launch requests for all four functions share a per-authenticated-employee Redis fixed window. The limiter runs before the handler, returns `429` with `Retry-After` at the boundary, and fails open on Redis errors; automatic orchestration and read/CRUD routes are excluded.

## 7. AI architecture
AI calls must be isolated behind an AI service layer.

```text
CRM domain/service
      |
      v
AI Service
      |
      v
Prompt templates / structured input
      |
      v
LLM provider
      |
      v
Validated structured result
```

AI capabilities:
- lead scoring;
- next-best-action;
- email draft generation.

Prefer structured/validated outputs rather than parsing arbitrary prose where practical.

## 8. Integration architecture
External services must use adapters/services instead of being called directly throughout business logic.

```text
Integration interface
 ├── Gmail adapter
 ├── Telegram adapter
 ├── WhatsApp adapter
 └── Calendar adapter
```

Credentials belong in environment configuration/secrets, never source control.

## 9. Background processing
Use Celery for operations that should not block request handling. D4.1 implements Redis as the broker/result backend and a dedicated JSON-serialized `ai` queue; D4.2–D4.5 add `ai.lead_scoring.execute`, `ai.deal_prediction.execute`, `ai.next_best_action.execute`, and `ai.email_draft.execute`. D4.6 also uses Redis for ephemeral manual AI launch counters, not durable business state. D5.1 adds the logical `integrations` queue and a non-provider foundation ping task; provider operations remain unimplemented.

Do not move ordinary simple CRUD into background tasks without a reason.

Ordinary CRM CRUD remains synchronous. Redis is not used for authentication/session state or business settings. D4.1 includes the worker application and infrastructure smoke task; D4.2–D4.4 add only their approved analysis tasks and minimal terminal-state orchestration. Email Draft work remains scoped to D4.5; D4.6 adds only request-path manual-launch rate limiting and no new worker task.

## 10. i18n architecture
Frontend translations live outside UI components.

Expected pattern:

```jsx
t("clients.create")
```

Avoid:

```jsx
<button>Создать клиента</button>
```

Russian is default/fallback. English and Spanish are mandatory.

Implemented Day 1 details:
- translations are stored in `frontend/src/i18n/locales/`;
- supported languages are `ru`, `en` and `es`;
- Russian is explicitly selected when no valid saved value exists and is the i18next fallback;
- the selected language persists under the `vileoruf.language` localStorage key;
- `<html lang>` follows the active language;
- backend base URL comes from `VITE_API_BASE_URL`, not React components.

## 11. UI architecture / brand
Use a professional Modern Minimal Light UI based on the VILEORUF logo:
- light neutral background and white surfaces;
- blue primary actions/highlights as a functional accent;
- graphite text and restrained neutral-gray secondary accents;
- subtle borders/shadows and moderate radius; no metallic, glow, 3D or glass effects.

Decorative branding must not reduce contrast, readability, accessibility or information density.

## 12. Architectural change rule
Any change that introduces a new major dependency, new infrastructure component, new domain module, new external service, or significant repository restructuring must be reported before implementation unless explicitly requested in the current task.

## 13. Day 1 infrastructure

- Docker Compose runs the official `postgres:16` image as service `postgres`.
- Project database/user: `vileoruf_crm` / `vileoruf_app`.
- PostgreSQL is exposed locally as `127.0.0.1:55432` to avoid occupied ports `5432` and `5433`.
- Data persists in the `vileoruf_postgres_data` volume and the service has a healthcheck.
- Application and Alembic read the same `DATABASE_URL`; credentials are not stored in `alembic.ini`.
- `.env.example` contains public placeholders; the local `.env` is ignored.
- Development seed rules are defined in `docs/DEVELOPMENT_SEED_STRATEGY.md`; the implemented explicit demo seed is deterministic, idempotent, development/test-only, and never creates users or credentials.
- Development Compose includes PostgreSQL, FastAPI backend, and React/Vite frontend services. `docker compose up --build` starts the complete verified foundation.
- Backend waits for healthy PostgreSQL, uses `postgres:5432` through the Compose network, applies `alembic upgrade head`, and runs Uvicorn on `0.0.0.0:8000` with reload.
- Frontend uses Node.js 24, installs from `package-lock.json` with `npm ci`, and runs Vite on `0.0.0.0:5173`. A separate container volume preserves `node_modules` beneath the source bind mount.
- Browser-side API requests use the host-published `VITE_API_BASE_URL` (`http://localhost:8000` by default); the Docker-only backend hostname is not exposed to React browser code.
- Host bindings remain restricted to loopback: backend `8000`, frontend `5173`, and PostgreSQL `55432`. CORS remains restricted to the configured frontend origin.

## 14. Authentication and authorization architecture

Authentication is for VILEORUF Studio employees using the internal CRM. External customers remain unauthenticated `Client` records; there is no customer portal in the MVP. Internal roles are `ADMIN` and `MANAGER`.

### 14.1 Target User model

The implemented model contains `id`, unique login `email`, `password_hash`, `display_name`, `role`, `is_active`, `created_at`, and `updated_at`. It uses a UUID primary key, a native PostgreSQL `user_role` enum restricted to `ADMIN`/`MANAGER` with no default role, `is_active=true`, and timezone-aware timestamps; ORM updates refresh `updated_at`. Email is not canonicalized in the persistence model; the shared controlled input boundary normalizes it with trim/lowercase for bootstrap and login. Deactivation through `is_active = false` preserves historical ownership references.

### 14.2 JWT flow

```text
email + password (Argon2id verification)
              |
              v
Access JWT (~30 min) ----> React memory ----> Authorization: Bearer
              +
Refresh JWT (~7 days) ---> HttpOnly cookie --> refresh --> new access JWT
```

The backend does not use PostgreSQL/Redis session storage or server-side HTTP sessions. The access JWT is never persisted in `localStorage` or `sessionStorage`. The refresh cookie is inaccessible to JavaScript, uses `Secure=true` in production, and receives security attributes appropriate to the deployment environment.

MVP refresh is stateless until `exp`, without a refresh-token table, blacklist, server-side refresh store, or complex rotation/reuse detection. Refresh validates that the current user exists and is active. Every authenticated API request resolves the current user and enforces `is_active`; future CRM endpoints must additionally enforce the current database role and ownership rules. Logout clears React memory and the refresh cookie. Because issued JWTs cannot be centrally revoked in this design, access tokens remain short-lived.

Passwords use Argon2id and a 12–128 character policy. Public employee registration is absent. A secure CLI/bootstrap mechanism creates the first `ADMIN` from email, display name, and an interactively entered password; default/hard-coded/master credentials, credentials in Git or `.env.example`, and production ADMIN creation through development seed data are prohibited.

Implemented security primitives use `argon2-cffi` for salted Argon2id hashing/verification and `PyJWT` with HS256. JWT configuration is environment-backed and requires `JWT_SECRET_KEY`; token lifetime defaults are 30 minutes for access and 7 days for refresh. Tokens contain only `sub`, `type`, `iat`, and `exp`; role and other PII are intentionally absent. Reusable decoding requires an expected token type and normalizes expired, invalid-signature, malformed and wrong-type failures behind the internal security interface.

The implemented `backend.app.scripts.create_admin` module is the controlled first-ADMIN input boundary. It reads and confirms the password through hidden `getpass` input, reuses the shared password policy/hash helpers, normalizes email with trim/lowercase plus conservative validation, trims/validates display name, and explicitly creates an active `ADMIN`. Creation is transactional; a PostgreSQL transaction-level table lock serializes concurrent bootstrap attempts. Duplicate email or any existing active/inactive ADMIN causes rollback/refusal with exit code 1. There is no force path, default credential, seed or automatic Compose bootstrap.

The implemented HTTP flow exposes `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, and `GET /auth/me`. Login reuses the shared trim/lowercase email normalization and Argon2id verification, returns an access JWT plus a safe user schema, and stores the refresh JWT only in the `refresh_token` cookie. The cookie is `HttpOnly`, `SameSite=Lax`, scoped to `/auth`, aligned to the configured refresh lifetime, and uses environment-backed `AUTH_COOKIE_SECURE` (`false` for local HTTP, required `true` for production HTTPS). Refresh accepts only that cookie and issues a new access token without rotation or server-side state. Logout idempotently clears the same cookie path/attributes.

`backend.app.api.dependencies.get_current_user` uses standard Bearer credentials, requires an access token, safely parses its UUID subject, and loads the current `User` from PostgreSQL for every authenticated request. Both Bearer authentication and refresh reject missing or inactive users. Role and user profile data come from the current database row; JWT claims remain only `sub`, `type`, `iat`, and `exp`. Development CORS remains origin-restricted and now permits credentials for the configured frontend origin.

### 14.3 Authorization enforcement

`ADMIN` has full access to all Clients and Deals in CRM Core, can move any Deal, and can assign/change its responsible user. `MANAGER` sees all Clients and Deals and may create them and edit any Client's common card, but may edit or move only Deals they own. Backend enforcement is authoritative; frontend controls are only a UX reflection.

### 14.4 Public request boundary

Unauthenticated `POST /public/requests` atomically creates `Client(status=CUSTOMER, lead_source=Website)` and an unassigned Deal in system stage `New Lead`. `/` provides its public form; `/login` and `/crm/*` remain protected employee routes. This introduces neither an authenticated external user nor a customer portal or new lead-like domain entity.

All future authentication, authorization, user-management, role, access-denied, and Client lifecycle UI follows the established `ru`/`en`/`es` localization architecture.

OAuth/SSO, LDAP, magic links, 2FA, email verification, password reset by email, multi-tenancy, dynamic roles, enterprise permission infrastructure, and Redis authentication state are outside the current MVP scope.

## 15. Planned components and architecture gates

Lead Scoring and its business-settings UI are implemented in D4.2, Deal Prediction in D4.3, advisory Next Best Action plus initial new-Deal orchestration in D4.4, AI Email Draft in D4.5, unified AI settings/history plus manual-launch hardening in D4.6, final regression/runtime/provider/browser verification in D4.7/D4.7.1, and credential-output process remediation in D4.7.2. Day 4 AI Automation is COMPLETE. D5.1 shared integration foundation is implemented: `IntegrationConnection`, `ExternalMessage`, `CalendarEvent`, EmailDraft `DRAFT`/`SENT` foundation, adapter/error classification boundaries, encrypted token storage foundation, logical `integrations` queue, and ADMIN integration settings. D5.2a adds the one-corporate-account Google OAuth encrypted token lifecycle; the token owner is the `GMAIL` connection, while D5.4 may reuse the internal token lifecycle for its separate Calendar connection without duplicating a Google authorization flow. D5.2b Gmail send, D5.2c inbound synchronization, Telegram D5.3, Google Calendar D5.4 operations, WhatsApp D5.5, and later integration UX/hardening are not started. Existing Communications, Tasks, Dashboard, employee management, CRM authorization, and synchronous CRUD contracts remain unchanged; backend authorization remains authoritative.

Authentication backend/frontend, employee management, CRM Core, and Deal ownership authorization are `IMPLEMENTED / VERIFIED`.

## 16. Dashboard boundary

The implemented Initial Dashboard is a small protected operational overview of existing CRM data. It uses bounded existing `GET /tasks?status=OPEN` and `GET /communications` requests, each with no aggregation or page crawling, plus quick navigation. It is not the Day 6 Analytics / Reporting subsystem: it has no global counts, Pipeline counts, charts, forecasts, trends, reporting, analytics architecture, or new infrastructure. `/dashboard/summary` is not part of the architecture.
