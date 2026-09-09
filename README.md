# VILEORUF CRM

VILEORUF CRM is a modular-monolith CRM project for VILEORUF Studio. The repository contains the verified Day 1 foundation, Day 2 CRM Core, Day 3 Communications/Tasks workflows, and complete Day 4 AI Automation.

## Current status

- **Day 1 — Foundation: COMPLETE**
- **Day 2 — CRM Core: COMPLETE**
- **Day 3 — Communications, Tasks, and Initial Operational Dashboard: COMPLETE**
- **D4.1 — AI Foundation: DONE**
- **D4.2 — Business Configuration + Lead Scoring: DONE**
- **D4.3 — Deal Prediction: DONE**
- **D4.4 — Next Best Action + Initial AI Orchestration: DONE**
- **D4.5 — AI Email Draft: DONE**
- **D4.6 — AI History + AI Settings + Hardening: DONE**
- **D4.7 — Final verification: COMPLETE** — regression, runtime, controlled real-provider, public and authenticated ADMIN/MANAGER Chromium smoke checks pass; D4.7.2 verified safe temporary-credential harness handling.
- **D5.0 — Integrations Architecture/Product Contract: APPROVED / ACTIVE** — [`DAY5_INTEGRATIONS_CONTRACT.md`](docs/DAY5_INTEGRATIONS_CONTRACT.md) governs all Day 5 work.
- **D5.1 — Integration Foundation: DONE** — shared persistence/state, safe ADMIN settings API/UI, adapter/encryption/queue foundation, migration and migration/API/browser verification are complete.
- **D5.2 — Gmail: DONE / LIVE VERIFIED**.
- **D5.2a — Google OAuth Connection + Encrypted Token Lifecycle: DONE / LIVE VERIFIED** — secure state/callback, encrypted token persistence/refresh foundation and ADMIN connection-management UI are implemented; the configured corporate Google OAuth connection was verified live.
- **D5.2b — Gmail Outbound Send: DONE / LIVE VERIFIED** — one owner-controlled synthetic message completed the normal explicit-send, integrations-queue and real Gmail provider flow; provider-confirmed success created exactly one Communication and immutable/readable/copyable historical EmailDraft.
- **D5.2c — Gmail Inbound Synchronization: DONE / LIVE VERIFIED** — bounded ADMIN-triggered synchronization uses a persisted post-install checkpoint, a fixed five-minute provider-visibility overlap and page token, database provider-message deduplication, exact normalized Client email match and deterministic outbound-thread Deal correlation; a controlled corrected-recipient retry accepted exactly one real provider fact, created exactly one incoming EMAIL Communication without a Deal, and repeat sync created no duplicate.
- **D5.3 — Telegram: DONE / LIVE PROVIDER VERIFIED** — one corporate Bot uses environment-backed secrets, authenticated webhook delivery and `IntegrationConnection` lifecycle. Live verification proved real inbound persistence, unmatched preservation, explicit manual linking, subsequent stable `telegram_provider_user_id` auto-matching (never username), and one CRM/Celery/provider outbound flow from `PENDING` to `SENT` with exactly one outgoing Communication and owner receipt. PostgreSQL-backed authenticity/idempotency and terminal lifecycle coverage remains automated; deliberate live redelivery/replay was not performed.
- **D5.4a — Google Calendar OAuth Reuse + Adapter Foundation: DONE (local)** — the separate Calendar connection safely derives state from the encrypted Gmail Google-token owner and validated persisted `calendar.events` scope; no duplicate OAuth flow, duplicate token, CalendarEvent operation, or live Calendar API call was introduced.
- **D5.6 — Unified Integration UX + Hardening: DONE / VERIFIED** — D5.6a protected unmatched Inbox, D5.6b safe Settings/security reconciliation and D5.6c PostgreSQL retry/idempotency regression are complete. Gmail, Telegram and Calendar terminal lifecycles retain exactly-once CRM effects; WhatsApp remains deferred. Day 5 is not yet complete: D5.7 is next.
- **Day 5 — Integrations: COMPLETE WITH DEFERRED TECHNICAL DEBT** — D5.7 final PostgreSQL, migration, runtime, build, security and regression gates passed. Gmail, Telegram and Google Calendar retain their historical live-verification status; D5.5 WhatsApp is intentionally deferred until after MVP under the approved contract, without a consumer/personal workaround.

The D4.6 workflow adds a unified, safe AI history for all four AI functions, an ADMIN-only runtime AI settings surface, and a shared per-employee Redis fixed-window limit for manual AI launches. Existing AI results remain readable when AI is disabled. `/` is public; `/login` and `/crm/*` are employee-only.

D4.7 ran the complete PostgreSQL backend regression (237 passed), Alembic/static checks, frontend production build, live service health checks, a controlled two-call OpenAI smoke through the normal Celery/provider path, and Chromium public plus authenticated ADMIN/MANAGER route smoke. D4.7.1 removed all synthetic local employee identities and related CRM/AI fixture data afterward. D4.7.2 remediated local smoke credential handling: forced failure and successful temporary authentication both verified no secret in captured stdout/stderr, with no residue. No send/integration behavior was introduced.

Current routes are `/` (public request page), `/login` (employee login), `/crm` (operational dashboard), `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks`, `/crm/ai-history`, and ADMIN-only `/crm/settings/business`, `/crm/settings/ai`, plus `/crm/settings/integrations`. Integration Settings has safe Gmail Connect/Reconnect/Disconnect controls; the provider callback is `GET /settings/integrations/google/callback`. A public visitor is never a User and receives no customer account, password, JWT or personal cabinet.

## Planned MVP capabilities

The shared D5.1 integration foundation, D5.2 Gmail, D5.3 Telegram and the bounded D5.4a Calendar OAuth-reuse foundation are complete as documented above. The following provider-specific capabilities are **not implemented yet**. Their approved Day 5 MVP architecture/product contract is [`DAY5_INTEGRATIONS_CONTRACT.md`](docs/DAY5_INTEGRATIONS_CONTRACT.md):

- WhatsApp and Calendar integrations;
- sales analytics and reporting.

Communication persistence, authenticated create/get/list API, and Client/Deal context timeline are implemented. Task persistence, authenticated create/list/get/update/completion API, and protected employee Tasks UI are implemented. Payment processing is not part of the approved scope.

## Implemented foundation, CRM Core, Communications timeline, and Tasks

- FastAPI backend with `GET /health`;
- centralized environment configuration;
- PostgreSQL-only database configuration;
- SQLAlchemy 2.x engine and session infrastructure using Psycopg 3;
- Alembic configuration with current applied head `20260907_0011`;
- internal User persistence with `ADMIN`/`MANAGER` roles;
- Argon2id password and JWT access/refresh token primitives;
- secure interactive first-ADMIN bootstrap CLI;
- backend login/refresh/logout/me endpoints and reusable Bearer current-user authentication;
- localized frontend login and protected CRM shell with memory-only access JWT, reload restoration and logout;
- PostgreSQL 16 service through Docker Compose, with persistent storage and a healthcheck;
- one-command Docker Compose development environment for PostgreSQL, FastAPI, and React/Vite;
- React/Vite technical frontend;
- frontend-to-backend health status check;
- restricted development CORS;
- `ru`, `en`, and `es` localization with persisted language selection;
- responsive VILEORUF light CRM UI, Clients, Deals and Pipeline Kanban;
- protected operational `/crm` Dashboard with bounded open Tasks, recent Communications, and quick CRM navigation; no global counts or analytics;
- public request form/API and explicit deterministic development demo seed.
- Communication and Task persistence models with PostgreSQL enums, foreign keys, and timeline/worklist indexes; authenticated Communication create/get/list API and Client/Deal context timeline; authenticated Task create/list/get/update/completion API and protected `/crm/tasks` UI with role-aware responsibility rules.
- common `AIAnalysis` history/audit persistence with `QUEUED`/`RUNNING`/`SUCCESS`/`FAILED`, validated JSON results, safe error categories, input fingerprint/snapshot metadata, and a PostgreSQL duplicate in-flight guard;
- separate `EmailDraft` persistence foundation and environment-default/DB-override model settings foundation;
- Celery 5.6 with logical `ai` and `integrations` queues, Redis broker/result backend, JSON-only serialization, and infrastructure/foundation smoke tasks;
- official OpenAI Python SDK behind an internal provider abstraction with Pydantic structured responses; no real key or provider call is required for backend startup/tests.
- D4.2 business catalog and settings persistence, typed management APIs, deterministic Commercial Value/overall calculation, manual Celery Lead Scoring, safe structured AI factors, and freshness/authorization enforcement.
- D4.3 manual Celery Deal Prediction with distinct probability/evidence-confidence semantics and privacy-bounded current-Deal plus same-client aggregate context.
- D4.4 advisory Next Best Action with 1–3 validated ranked recommendations, directed LS/DP freshness dependencies, and failure-tolerant `LS ∥ DP → NBA` orchestration for newly created active Deals.
- D4.5 manual AI Email Draft generation, optional backend-resolved NBA action context, explicit working-draft CRUD, client-language selection, placeholder privacy, and localized Deal UI. Closed Deals remain eligible; `AI Enabled` blocks only new generation, not manual EmailDraft CRUD.
- D4.6 ADMIN AI Settings with safe model overrides/reset, unified role-aware AI History, typed result presentation, and fail-open Redis rate limiting shared across the four manual AI launch endpoints.
- D5.1 Integration Foundation: `IntegrationConnection`, `ExternalMessage`, and `CalendarEvent`; EmailDraft `DRAFT`/`SENT` state plus historical `SENT` immutability; provider adapter and safe error/retry classification boundaries; application-level encrypted token-storage foundation using environment-only `INTEGRATION_TOKEN_ENCRYPTION_KEY`; safe ADMIN `GET /settings/integrations`; and localized ADMIN `/crm/settings/integrations` cards for Gmail, Telegram, Google Calendar, and WhatsApp.
- D5.2a Google OAuth foundation: ADMIN-only `POST /settings/integrations/google/connect`, `/reconnect`, and `/disconnect`; provider callback; one-time PostgreSQL-hashed/expiring OAuth state; code exchange and access-token refresh behind the Google service boundary; and encrypted token ciphertext only in the existing Gmail `IntegrationConnection` internal field.
- D5.4a Calendar foundation: a persisted, separate `GOOGLE_CALENDAR` connection has safe state derived from the Gmail Google-token owner only after encrypted persisted `calendar.events` scope validation; shared access-token acquisition and Calendar transport setup remain behind integration services/adapters. Calendar never copies the token payload.
- D5.2b Gmail outbound foundation: authenticated `POST /deals/{deal_id}/email-drafts/{draft_id}/send`, explicit UI confirmation with recipient/subject, a one-to-one EmailDraft-to-ExternalMessage correlation, integrations-queue Gmail adapter execution and provider-confirmed finalization to Communication plus immutable EmailDraft `SENT`.

## Tech stack

### Backend

- Python 3.10
- FastAPI
- Uvicorn
- SQLAlchemy
- Psycopg 3
- Alembic
- pydantic-settings
- argon2-cffi
- PyJWT
- pytest
- Celery
- redis-py
- OpenAI Python SDK

### Frontend

- Node.js 24 LTS
- JavaScript
- React
- Vite
- i18next
- react-i18next

### Database and infrastructure

- PostgreSQL 16
- Redis 7 (Celery broker/result backend and non-persistent manual AI launch rate limiting)
- Docker
- Docker Compose

D5.2a implements and live-verifies Google OAuth connection/token lifecycle for the configured corporate Google account. D5.2b is also live-provider verified through one owner-controlled synthetic outbound message; its provider-confirmed result created exactly one CRM Communication and immutable historical EmailDraft. D5.2c Gmail inbound synchronization is also live-provider verified: a controlled corrected-recipient message was accepted through the bounded Gmail API sync, exact-matched to its synthetic Client, persisted as exactly one incoming EMAIL Communication without a Deal, and remained deduplicated on repeat sync. D5.3 Telegram is DONE / LIVE PROVIDER VERIFIED: real HTTPS webhook delivery persisted inbound facts, preserved an unmatched sender until explicit linking, subsequently auto-matched stable `telegram_provider_user_id` (never username), and sent one provider-confirmed outbound message through the normal CRM/Celery flow. Automated PostgreSQL coverage proves webhook and HTTP idempotency; deliberate live provider redelivery was not performed. Google Calendar D5.4 is DONE / LIVE VERIFIED. WhatsApp Business Cloud API D5.5 is **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ** until after the current MVP because the original 7-day schedule has been exceeded; it remains planned under the approved Business Platform / Cloud API architecture, without consumer/personal workaround. D5.6a Unified Unmatched Inbox, D5.6b Integration UX + Security Reconciliation and D5.6c Retry / Idempotency Hardening Regression are DONE / VERIFIED: focused PostgreSQL evidence confirms retained Gmail/Telegram/Calendar exactly-once and safe terminal semantics, while provider cards never expose secrets. D5.7 is next; Day 5 is not yet COMPLETE. Redis is not used for JWT, refresh tokens, session state, or persistent AI business settings.

## Internationalization

The frontend supports:

- Russian (`ru`) — default and fallback;
- English (`en`);
- Spanish (`es`).

The selected language is stored in browser local storage and restored between sessions. The document language is synchronized through the HTML `lang` attribute.

## Repository structure

```text
vileoruf-crm/
├── backend/              # FastAPI, database infrastructure, Alembic, tests
├── frontend/             # React/Vite technical frontend
├── docs/                 # Project contract and technical documentation
├── docker-compose.yml    # PostgreSQL, Redis, FastAPI, Celery, and Vite services
├── .env.example          # Public environment template
├── .gitignore
├── .nvmrc                # Project Node.js version
└── README.md
```

## Local development

### Prerequisites

- Docker with Docker Compose

Python 3.10.x and Node.js 24 LTS are required only for the optional manual workflow below.

Run the commands below from the repository root unless a different directory is shown.

### Environment

Create a local environment file from the public template:

```bash
cp .env.example .env
```

Review `.env` before starting the services. Replace template placeholders with local development values and keep `POSTGRES_PASSWORD` consistent with the password inside `DATABASE_URL`.

Set `JWT_SECRET_KEY` to a strong local secret. The value in `.env.example` is an explicit non-production placeholder; backend security configuration has no built-in signing-secret default. JWT defaults are HS256, 30-minute access tokens, and 7-day refresh tokens.

`AUTH_COOKIE_SECURE=false` supports local HTTP development. Production HTTPS deployments must set `AUTH_COOKIE_SECURE=true` so the refresh cookie is sent only over secure transport.

`OPENAI_API_KEY` is optional for ordinary backend startup and tests. Set it only when an AI operation that calls OpenAI is intentionally run. `AI_ANALYSIS_MODEL` and `AI_EMAIL_MODEL` default to `gpt-5.4-mini`; `AI_MODEL_ALLOWLIST` controls permitted runtime models. Celery/Redis URLs, provider timeout, retry count (maximum 2), and increasing-backoff base are environment-backed technical settings.

`INTEGRATION_TOKEN_ENCRYPTION_KEY` is the environment-only application encryption key for a future OAuth token payload. It must be a valid Fernet key when OAuth-token storage is used. Do not commit it, expose it through an API/UI, or place a real value in `.env.example`. D5.1 itself does not perform OAuth or any provider operation.

To enable a real local Google OAuth connection, set the following environment variables without committing their values: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `GOOGLE_OAUTH_STATE_TTL_SECONDS`, and `INTEGRATION_TOKEN_ENCRYPTION_KEY`. The default local redirect URI is `http://localhost:8000/settings/integrations/google/callback`; register exactly that URI in a Google Cloud **Web application** OAuth client, or set the variable to the registered HTTPS deployment callback. Enable the Gmail API and Google Calendar API. The requested least-privilege Day 5 authorization scopes are `https://www.googleapis.com/auth/gmail.send` (D5.2b explicit send), `https://www.googleapis.com/auth/gmail.readonly` (D5.2c bounded inbound synchronization), and `https://www.googleapis.com/auth/calendar.events` (future D5.4 CRM-created events). Configure the OAuth consent screen and, while the app remains in testing, add the corporate test user. After editing `.env`, recreate `backend` and `celery_worker` with `docker compose up -d --force-recreate backend celery_worker`; D5.2a does not make a provider call until an ADMIN explicitly starts the connection.

The persisted singleton `ai_model_settings` controls `ai_enabled` and `automatic_new_deal_analysis` (both default `true`), optional analysis/email model overrides, and Deal Prediction/Next Best Action validity periods (both default 7 days, accepted range 1–365). ADMIN manages these values at `/crm/settings/ai`; the API returns only safe configuration and never exposes provider credentials. A blank model override resets it to the environment default, and every changed field is recorded through privacy-safe application logging. Disabling AI blocks creation of new manual and automatic AI operations but does not hide history or cancel already accepted work. Disabling only automatic new-Deal analysis leaves manual operations available and never backfills existing Deals when re-enabled.

D4.6 adds the non-secret `AI_RATE_LIMIT_REQUESTS=10` and `AI_RATE_LIMIT_WINDOW_SECONDS=60` defaults. Existing local `.env` files do not need an update because application and Compose defaults are present; add either value only to override it, then recreate the backend container (`docker compose up -d --force-recreate backend`). Manual Lead Scoring, Deal Prediction, Next Best Action, and Email Draft generation share this per-authenticated-employee fixed window. Redis failures are logged safely and fail open; automatic orchestration, reads, and EmailDraft CRUD do not consume the quota.

Do not commit `.env`.

### Local environment setup

For a local setup, first create the ignored environment file:

```bash
cp .env.example .env
```

Open `.env` and fill in a real `OPENAI_API_KEY` only when you intend to make real OpenAI calls; the other AI/Celery defaults may remain unchanged. Never commit `.env`. After changing the key, recreate the backend and Celery containers so Compose passes the updated environment:

```bash
docker compose up -d --force-recreate backend celery_worker
```

The application and Celery worker start safely without an OpenAI key. An AI provider operation attempted without one returns a safe `CONFIGURATION_ERROR`; the key is required only for an actual OpenAI request.

### Start the complete development environment

Build and start PostgreSQL, Redis, FastAPI, the Celery AI worker, and React/Vite from the repository root:

```bash
docker compose up --build
```

Detached startup is also supported:

```bash
docker compose up -d --build
```

Compose waits for PostgreSQL and Redis to become healthy, applies `alembic upgrade head`, starts FastAPI, starts the Celery worker on the logical `ai` and `integrations` queues, and then starts Vite. Backend and frontend source directories are bind-mounted for development reload; frontend dependencies remain in a container volume so the bind mount does not hide `node_modules`.

Stop all services while preserving PostgreSQL data:

```bash
docker compose down
```

Remove the development database and frontend dependency volumes for a clean start:

```bash
docker compose down -v
```

Inspect individual service logs with:

```bash
docker compose logs backend
docker compose logs frontend
docker compose logs postgres
docker compose logs redis
docker compose logs celery_worker
```

Inside the Compose network, backend connects to PostgreSQL at `postgres:5432`, while Celery uses Redis at `redis:6379`. Browser-side React requests use `VITE_API_BASE_URL` and therefore target the host-published backend URL, not the Docker-only `backend` hostname.

### Create the first ADMIN

After Compose is running and migrations are current, start the interactive bootstrap command:

```bash
docker compose exec backend python -m backend.app.scripts.create_admin
```

The command asks for email, display name, password, and password confirmation. Password input is hidden. Email is normalized with trim/lowercase, and the password uses the shared 12–128 character policy and Argon2id hashing. The command creates only an active `ADMIN`, never stores plaintext, and refuses duplicate email or repeated bootstrap if any active/inactive ADMIN already exists. There are no default credentials or force option.

### Optional manual workflow

The services can still be run independently for troubleshooting. Start PostgreSQL and Redis first:

```bash
docker compose up -d --wait postgres redis
```

Create the backend environment, install dependencies, apply migrations, and start FastAPI:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, start the AI worker:

```bash
.venv/bin/python -m celery -A backend.app.workers.celery_app:celery_app worker --loglevel=INFO --queues=ai,integrations
```

In another terminal, start the frontend:

```bash
nvm use
cd frontend
npm install
npm run dev
```

The frontend reads its backend URL from `VITE_API_BASE_URL` in the root environment configuration.

### Development URLs

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`
- PostgreSQL host connection: `127.0.0.1:55432`
- Redis host connection: `127.0.0.1:56379` (Celery only)

### Application routes and public requests

- `/` — public VILEORUF request form, without authentication;
- `/login` — employee email/password login;
- `/crm` — protected operational Dashboard; `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks` — protected ADMIN/MANAGER CRM pages;
- `/crm/settings/business` — ADMIN-only Categories, Services and Lead Scoring business settings.
- `/crm/settings/integrations` — ADMIN-only safe Integration Settings status cards. It shows the four approved providers as disconnected until later provider-specific work; it does not connect accounts or expose credentials.

The public form loads active Services from `GET /public/services` and sends an approved Service, contact/project fields, and preferred communication language to `POST /public/requests`. Category is always derived by the backend from Service. One accepted request atomically creates `Client(status=CUSTOMER, lead_source=Website)` and an unassigned Deal in the system `New Lead` stage. It does not accept status, stage, probability, responsible employee or internal notes and does not create customer authentication.

### Required business catalog bootstrap

After migrations, explicitly install the minimal required non-demo catalog:

```bash
docker compose exec backend python -m backend.app.scripts.bootstrap_business_catalog
```

The command is deterministic and idempotent. It creates only the required `Другое / Other / Otro` Category (50 EUR/person-hour, 8 person-hours) and `Общий запрос / General request / Solicitud general` Service with fixed UUIDs. It is valid in every environment because this is required system data, not demo content. Re-run it safely after a fresh database; use the ADMIN business settings page to replace the minimal values with approved studio configuration.

### Development demo seed

Run the explicit deterministic seed only against development or test:

```bash
docker compose exec backend python -m backend.app.scripts.seed_demo
```

It is idempotent and creates exactly three fictitious Clients and five Deals; it creates no Users or credentials. Remove only these deterministic demo records with:

```bash
docker compose exec backend python -m backend.app.scripts.seed_demo --clean
```

Both commands refuse `APP_ENV=production`; they never truncate tables or remove unrelated data. Demo data is separate from the seven system PipelineStages and is governed by [`DEVELOPMENT_SEED_STRATEGY.md`](docs/DEVELOPMENT_SEED_STRATEGY.md).

The frontend development origin is intentionally restricted to `http://localhost:5173` by the backend CORS configuration.

## Testing and verification

Run the existing backend test suite from the repository root:

```bash
.venv/bin/python -m pytest backend/tests
```

PostgreSQL integration coverage is opt-in and expects the configured local development database:

```bash
RUN_DATABASE_TESTS=1 APP_ENV=test .venv/bin/python -m pytest backend/tests
```

Create a frontend production build:

```bash
nvm use
cd frontend
npm run build
```

No frontend lint command or frontend automated test suite is currently configured.

## Documentation

The project contract and detailed status are maintained in [`docs/`](docs/):

- [`PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) — stable product and implementation context;
- [`REQUIREMENTS.md`](docs/REQUIREMENTS.md) — approved product requirements and scope;
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) — target architecture and implemented foundation;
- [`DEVELOPMENT_STATUS.md`](docs/DEVELOPMENT_STATUS.md) — operational source of truth for progress;
- [`CODEX_RULES.md`](docs/CODEX_RULES.md) — development workflow and implementation rules;
- [`DEVELOPMENT_SEED_STRATEGY.md`](docs/DEVELOPMENT_SEED_STRATEGY.md) — system/bootstrap and development seed rules.
- [`DAY4_AI_CONTRACT.md`](docs/DAY4_AI_CONTRACT.md) — approved Day 4 AI architecture/product contract.
- [`DAY5_INTEGRATIONS_CONTRACT.md`](docs/DAY5_INTEGRATIONS_CONTRACT.md) — approved/active Day 5 integrations architecture/product contract.

## Authentication status

Backend authentication is implemented for internal employees:

- `POST /auth/login` accepts JSON email/password, returns an access token and safe user data, and sets the refresh token only as an `HttpOnly` cookie;
- `POST /auth/refresh` reads that cookie and returns a new access token plus current user data;
- `POST /auth/logout` idempotently clears the refresh cookie;
- `GET /auth/me` requires `Authorization: Bearer <access JWT>` and returns the current database user.

Login normalizes email with trim/lowercase. The refresh cookie is named `refresh_token`, uses `SameSite=Lax`, path `/auth`, a lifetime matching the configured refresh JWT, and environment-controlled `Secure`. Access/refresh tokens contain only `sub`, `type`, `iat`, and `exp`; user roles and profile data are loaded from PostgreSQL. Both Bearer and refresh requests reject missing, deleted, or inactive users.

Example login (use your bootstrapped synthetic/local employee credentials, never commit them):

```bash
curl -i -c /tmp/vileoruf-cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.test","password":"replace-with-local-password"}' \
  http://localhost:8000/auth/login
```

Open `http://localhost:5173` after starting Compose. If no ADMIN exists, create the first one with the bootstrap command above, then sign in using that employee email/password. The access token remains only in React memory; a page reload restores the session through the backend HttpOnly refresh cookie. The authenticated foundation screen shows display name, email and role. Use **Sign out / Выйти / Cerrar sesión** to clear local authentication and the refresh cookie.

For local browser authentication, keep both frontend and backend on the `localhost` hostnames documented above. Refresh remains stateless, so logout cannot centrally revoke an already copied JWT before expiration. CRM role/ownership authorization is enforced by the backend. External customers are not authenticated users.

## Employee management

After signing in as ADMIN, use the **Employees / Сотрудники / Empleados** section in the protected CRM shell. ADMIN can create MANAGER or additional ADMIN accounts, edit display name and role, and deactivate/reactivate accounts. Deactivation preserves the database row; physical deletion, email change and password reset are intentionally absent. MANAGER cannot see this section and receives HTTP 403 from `/users`. The current ADMIN cannot deactivate or downgrade itself, and the backend always preserves at least one active ADMIN.

## Security and secrets

- Never commit `.env`.
- `.env.example` contains template configuration only.
- Never commit passwords, API keys, OAuth secrets, access tokens, or other credentials.
- Use only synthetic data for local development and demonstrations.
