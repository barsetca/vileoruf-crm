# VILEORUF CRM

VILEORUF CRM is a modular-monolith CRM project for VILEORUF Studio. The planned MVP will support AI-assisted sales automation, while the current repository contains the verified Day 1 foundation, Day 2 CRM Core, and Day 3 Communications and Tasks workflows.

## Current status

- **Day 1 — Foundation: COMPLETE**
- **Day 2 — CRM Core: COMPLETE**
- **Day 3 — Communications, Tasks, and Initial Operational Dashboard: COMPLETE**

The repository provides the verified Day 1 foundation, Day 2 CRM Core, and Day 3 Communications, Tasks, and bounded Initial Operational Dashboard. `/` is public; `/login` and `/crm/*` are employee-only. A public request creates a `CUSTOMER` Client and unassigned Deal in `New Lead`; it does not create a customer account.

Current routes are `/` (public request page), `/login` (employee login), `/crm` (operational dashboard), `/crm/clients`, `/crm/deals`, `/crm/pipeline` and `/crm/tasks` (protected employee CRM). A public visitor is never a User and receives no customer account, password, JWT or personal cabinet.

## Planned MVP capabilities

The following capabilities are planned and are **not implemented yet**:

- AI lead scoring;
- deal prediction;
- next-best-action recommendations;
- AI-generated email drafts;
- Gmail, Telegram, WhatsApp, and Calendar integrations;
- sales analytics and reporting.

Communication persistence, authenticated create/get/list API, and Client/Deal context timeline are implemented. Task persistence, authenticated create/list/get/update/completion API, and protected employee Tasks UI are implemented. Payment processing is not part of the approved scope.

## Implemented foundation, CRM Core, Communications timeline, and Tasks

- FastAPI backend with `GET /health`;
- centralized environment configuration;
- PostgreSQL-only database configuration;
- SQLAlchemy 2.x engine and session infrastructure using Psycopg 3;
- Alembic configuration with current applied head `20260901_0004`;
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

### Frontend

- Node.js 24 LTS
- JavaScript
- React
- Vite
- i18next
- react-i18next

### Database and infrastructure

- PostgreSQL 16
- Docker
- Docker Compose

Celery, Redis, OpenAI, and external integration adapters are planned but are not implemented.

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
├── docker-compose.yml    # PostgreSQL, FastAPI, and Vite development services
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

Do not commit `.env`.

### Start the complete development environment

Build and start PostgreSQL, FastAPI, and React/Vite from the repository root:

```bash
docker compose up --build
```

Detached startup is also supported:

```bash
docker compose up -d --build
```

Compose waits for PostgreSQL to become healthy, applies `alembic upgrade head`, starts FastAPI with reload, and then starts the Vite development server. Backend and frontend source directories are bind-mounted for development reload; frontend dependencies remain in a container volume so the bind mount does not hide `node_modules`.

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
```

Inside the Compose network, backend connects to PostgreSQL at `postgres:5432`. Browser-side React requests use `VITE_API_BASE_URL` and therefore target the host-published backend URL, not the Docker-only `backend` hostname.

### Create the first ADMIN

After Compose is running and migrations are current, start the interactive bootstrap command:

```bash
docker compose exec backend python -m backend.app.scripts.create_admin
```

The command asks for email, display name, password, and password confirmation. Password input is hidden. Email is normalized with trim/lowercase, and the password uses the shared 12–128 character policy and Argon2id hashing. The command creates only an active `ADMIN`, never stores plaintext, and refuses duplicate email or repeated bootstrap if any active/inactive ADMIN already exists. There are no default credentials or force option.

### Optional manual workflow

The services can still be run independently for troubleshooting. Start PostgreSQL first:

```bash
docker compose up -d --wait postgres
```

Create the backend environment, install dependencies, apply migrations, and start FastAPI:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
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

### Application routes and public requests

- `/` — public VILEORUF request form, without authentication;
- `/login` — employee email/password login;
- `/crm` — protected operational Dashboard; `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks` — protected ADMIN/MANAGER CRM pages.

The public form sends only approved contact and project fields to `POST /public/requests`. One accepted request atomically creates `Client(status=CUSTOMER, lead_source=Website)` and an unassigned `Deal` in the system `New Lead` stage. It does not accept status, stage, probability, responsible employee or internal notes and does not create customer authentication.

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
- [`DEVELOPMENT_SEED_STRATEGY.md`](docs/DEVELOPMENT_SEED_STRATEGY.md) — future development seed rules.

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
