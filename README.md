# VILEORUF CRM

VILEORUF CRM is a modular-monolith CRM project for VILEORUF Studio. The planned MVP will support AI-assisted sales automation, while the current repository contains only the verified application foundation.

## Current status

- **Day 1 — Foundation: COMPLETE**
- **Day 2 — CRM Core: NOT STARTED**

The current repository provides a runnable backend, database infrastructure, migrations, and a technical frontend. CRM domain models and workflows are not implemented yet. Authentication and authorization are also not implemented; their architecture is approved and documented for a separate controlled implementation stage before Day 2 begins.

## Planned MVP capabilities

The following capabilities are planned and are **not implemented yet**:

- clients and deals;
- a persistent sales pipeline and Kanban workflow;
- communication history;
- manager tasks;
- AI lead scoring;
- deal prediction;
- next-best-action recommendations;
- AI-generated email drafts;
- Gmail, Telegram, WhatsApp, and Calendar integrations;
- sales analytics and reporting.

Payment processing is not part of the approved scope.

## Implemented foundation

- FastAPI backend with `GET /health`;
- centralized environment configuration;
- PostgreSQL-only database configuration;
- SQLAlchemy 2.x engine and session infrastructure using Psycopg 3;
- Alembic configuration and applied initial revision;
- PostgreSQL 16 service through Docker Compose, with persistent storage and a healthcheck;
- one-command Docker Compose development environment for PostgreSQL, FastAPI, and React/Vite;
- React/Vite technical frontend;
- frontend-to-backend health status check;
- restricted development CORS;
- `ru`, `en`, and `es` localization with persisted language selection;
- responsive VILEORUF dark SaaS visual foundation;
- documented development seed strategy without executable seed data.

## Tech stack

### Backend

- Python 3.10
- FastAPI
- Uvicorn
- SQLAlchemy
- Psycopg 3
- Alembic
- pydantic-settings
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

Authentication and authorization are not implemented. The approved architecture uses internal employee users with `ADMIN` and `MANAGER` roles, short-lived access JWTs kept only in React memory, stateless refresh JWTs in secure `HttpOnly` cookies, email/password login with Argon2id, and backend-enforced role/Deal-ownership rules. External customers are not authenticated users. Full requirements and boundaries are documented in [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Security and secrets

- Never commit `.env`.
- `.env.example` contains template configuration only.
- Never commit passwords, API keys, OAuth secrets, access tokens, or other credentials.
- Use only synthetic data for local development and demonstrations.
