# VILEORUF CRM — Architecture

## 1. Architecture style
Use a modular monolith for the 7-day MVP.

Reasons:
- lower implementation and DevOps overhead than microservices;
- simpler debugging;
- faster delivery;
- clear module boundaries still allow later extraction if needed.

## 2. High-level architecture

The diagram below is the target MVP architecture. Day 1 Foundation and Day 2 CRM Core are implemented. AI Service, integration adapters, Celery and Redis remain planned and must not be treated as existing functionality.

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

Implemented backend baseline through Day 2:
- Python 3.10.12 and FastAPI;
- `GET /health`, independent of database availability;
- centralized environment settings using `pydantic-settings`;
- PostgreSQL-only SQLAlchemy 2.x engine/session infrastructure using Psycopg 3;
- Alembic with shared application configuration and current head `20260831_0003`;
- restricted development CORS for the configured `FRONTEND_ORIGIN`.
- `Client`, `PipelineStage`, and `Deal` domain models and services, including backend-authoritative CRM role/ownership authorization;
- the public request action endpoint and development/test-only deterministic demo seed.

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

The implemented JavaScript React frontend uses project-pinned Node.js 24.20.0, npm 11.19.0, Vite 8.2.2 and `@vitejs/plugin-react`. It includes `AuthProvider`/`useAuth`, i18next/react-i18next resources, protected CRM shell/navigation, Clients, Deals, and Pipeline Kanban pages, native drag-and-drop with accessible Move fallback, and a public request page. Access JWT exists only in React memory; refresh restores the employee session from the cookie. The UI is translated in ru/en/es and reflects roles, but backend authorization remains authoritative.

Target application boundary:

```text
React application
├── Public area
│   └── unauthenticated information/request entry
└── Employee CRM
    └── ADMIN/MANAGER authentication required
```

Current routes are `/` for public request, `/login` for employee login, and `/crm/clients`, `/crm/deals`, and `/crm/pipeline` for protected employee CRM. Public area does not mean customer portal.

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
- Integration

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
 └── AIAnalysis
```

`Deal` ownership uses `responsible_user_id` (or an equivalent foreign key) to `User`. `Client` has the lifecycle states `CUSTOMER` and `CLIENT`; the first Deal moved successfully to `Won` promotes `CUSTOMER` to `CLIENT`, with no automatic reverse transition.

The implemented public boundary is an action endpoint, not an entity: `POST /public/requests` atomically creates a `CUSTOMER` Client and unassigned Deal in system stage `New Lead`. Public visitors never become `User`; `/` is public while `/login` and `/crm/*` remain employee routes.

Do not introduce Payment, Invoice, Subscription or similar financial-processing entities unless requirements change.

`User`, `Client`, `Deal`, and `PipelineStage` are implemented. `Communication` and `Task` are planned Day 3 entities; AIAnalysis and Integration remain planned.

### 6.1 Day 3 Communications contract

`Communication` is an append-oriented CRM history record, not a live integration. It has a required Client, optional Deal, channel (`EMAIL`, `TELEGRAM`, `WHATSAPP`, `MANUAL`, `OTHER`), direction (`INCOMING`, `OUTGOING`), content, actual communication timestamp, and the sole initial CRM status `RECORDED`.

When linked to a Deal, the Deal must belong to its Client; the backend authoritatively validates this invariant. Day 3 supports create and get/list/read only, with no DELETE or arbitrary edit. ADMIN may create history for any Client/Deal. MANAGER may create client-level records for any Client and Deal-linked records only on Deals they own. Both roles can read history. Channel classification does not create Gmail, Telegram, WhatsApp, or other live integration semantics; delivery tracking, provider IDs, delivery/read states, retries, errors, and synchronization are excluded.

### 6.2 Day 3 Tasks contract

`Task` is an internal CRM task with title, optional description, due datetime, persisted `OPEN`/`COMPLETED` status, responsible active ADMIN/MANAGER employee, and optional Client and Deal associations. General tasks are allowed. Where both Client and Deal are specified, the Deal must belong to the Client; a Deal-only task does not need a duplicate Client. The backend authoritatively validates these relationships.

ADMIN sees and updates all Tasks, may create for any active ADMIN/MANAGER, and may reassign responsibility. MANAGER sees all Tasks but may create only for themself and update/complete only Tasks assigned to themself; they cannot reassign. Future implementation supports create, list/get and update/completion, never DELETE. `OVERDUE` is derived from an open task with a past due datetime, not persisted.

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
- deal prediction;
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
Use Celery for operations that should not block request handling. Redis is the proposed broker.

Do not move ordinary simple CRUD into background tasks without a reason.

Celery and Redis are not implemented at the end of Day 1.

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

The following remain planned and are not implemented: Communications and Tasks persistence/API/UI, Initial Dashboard, AI Service/OpenAI calls, integration adapters, Celery and Redis. Employee management uses `/users`, typed schemas, `services/users.py`, and reusable `require_admin`; role comes from the current DB User. PATCH uses a PostgreSQL table lock for active-admin safety, forbids self-deactivation/self-downgrade, and preserves one active ADMIN. The frontend renders employee management only for ADMIN; backend authorization remains authoritative.

Authentication backend/frontend, employee management, CRM Core, and Deal ownership authorization are `IMPLEMENTED / VERIFIED`.

## 16. Dashboard boundary

The future Initial Dashboard is a small operational overview of existing CRM data. It is not the Day 6 Analytics / Reporting subsystem. D3.0 defines no analytics architecture, reporting subsystem, forecast, conversion analytics, complex aggregations, or new infrastructure. Its exact minimal contract is deferred to a D3.6 preflight/contract iteration after Communications and Tasks are implemented.
