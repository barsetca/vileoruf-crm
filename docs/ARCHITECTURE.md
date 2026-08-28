# VILEORUF CRM — Architecture

## 1. Architecture style
Use a modular monolith for the 7-day MVP.

Reasons:
- lower implementation and DevOps overhead than microservices;
- simpler debugging;
- faster delivery;
- clear module boundaries still allow later extraction if needed.

## 2. High-level architecture

The diagram below is the target MVP architecture. At the end of Day 1, React/FastAPI/PostgreSQL and their foundation wiring are implemented. AI Service, integration adapters, Celery and Redis remain planned and must not be treated as existing functionality.

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

Day 1 currently implements:
- Python 3.10.12 and FastAPI;
- `GET /health`, independent of database availability;
- centralized environment settings using `pydantic-settings`;
- PostgreSQL-only SQLAlchemy 2.x engine/session infrastructure using Psycopg 3;
- Alembic with shared application configuration and revision `20260827_0001`;
- restricted development CORS for the configured `FRONTEND_ORIGIN`.

No CRM domain models, repositories, business services or authentication/authorization are implemented yet.

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

Day 1 currently implements a JavaScript React foundation using project-pinned Node.js 24.20.0, npm 11.19.0, Vite 8.2.2 and `@vitejs/plugin-react`. It includes a responsive technical start screen, an API service for backend health, and i18next/react-i18next resources. CRM pages and navigation are not implemented yet.

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

Future feature directories in the target tree are created only with their corresponding implementation; empty directories are not required. The verified Day 1 foundation currently includes:

```text
vileoruf-crm/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── db/
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

Do not introduce Payment, Invoice, Subscription or similar financial-processing entities unless requirements change.

These entities are planned; none is implemented at the end of Day 1.

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
Use a professional dark SaaS dashboard based on the VILEORUF logo:
- dark graphite surfaces;
- blue primary actions/highlights;
- steel/light-gray text and secondary accents;
- restrained glow/metallic effects.

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
- Development seed rules are defined in `docs/DEVELOPMENT_SEED_STRATEGY.md`; no executable seed or seed records exist yet.

## 14. Planned components and architecture gates

The following remain planned and are not implemented: CRM domain modules, AI Service/OpenAI calls, integration adapters, Celery, Redis and authentication/authorization.

Authentication/authorization architecture is TBD and must be decided before Day 2 CRM Core implementation. No JWT/session mechanism, user model, role model or password policy is selected by the current contract.
