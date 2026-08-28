# VILEORUF CRM

VILEORUF CRM is a modular-monolith CRM project for VILEORUF Studio. The planned MVP will support AI-assisted sales automation, while the current repository contains only the verified application foundation.

## Current status

- **Day 1 — Foundation: COMPLETE**
- **Day 2 — CRM Core: NOT STARTED**

The current repository provides a runnable backend, database infrastructure, migrations, and a technical frontend. CRM domain models and workflows are not implemented yet. Authentication and authorization are also not implemented; their architecture must be defined before Day 2 begins.

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
├── docker-compose.yml    # PostgreSQL 16 service
├── .env.example          # Public environment template
├── .gitignore
├── .nvmrc                # Project Node.js version
└── README.md
```

## Local development

### Prerequisites

- Python 3.10.x
- Node.js 24 LTS (NVM is recommended)
- Docker with Docker Compose

Run the commands below from the repository root unless a different directory is shown.

### Environment

Create a local environment file from the public template:

```bash
cp .env.example .env
```

Review `.env` before starting the services. Replace template placeholders with local development values and keep `POSTGRES_PASSWORD` consistent with the password inside `DATABASE_URL`.

Do not commit `.env`.

### PostgreSQL

Start the project PostgreSQL service and wait for its healthcheck:

```bash
docker compose up -d --wait postgres
```

The default local binding is `127.0.0.1:55432`; PostgreSQL still uses port `5432` inside the Docker network.

To stop the service without deleting its persistent volume:

```bash
docker compose stop postgres
```

### Backend

Create the Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

Apply the current Alembic migrations to the configured PostgreSQL database:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

Start FastAPI:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

In another terminal, activate the project Node.js version and install frontend dependencies:

```bash
nvm use
cd frontend
npm install
npm run dev
```

The frontend reads its backend URL from `VITE_API_BASE_URL` in the root environment configuration.

### Development URLs

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- Backend health: `http://127.0.0.1:8000/health`
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

Authentication and authorization are not implemented. No authentication mechanism, user model, role model, or permission model has been selected. These decisions must be made before implementing Day 2 CRM Core.

## Security and secrets

- Never commit `.env`.
- `.env.example` contains template configuration only.
- Never commit passwords, API keys, OAuth secrets, access tokens, or other credentials.
- Use only synthetic data for local development and demonstrations.
