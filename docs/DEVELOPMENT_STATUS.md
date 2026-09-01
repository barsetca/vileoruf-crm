# VILEORUF CRM — Development Status

> This file is the operational status source of truth. Update it after every completed implementation task.

## Current phase
Day 1 — Foundation: COMPLETE.

Day 2 — CRM Core: COMPLETE. D2.1–D2.9 are implemented and verified, including the public request boundary and deterministic development demo seed.

Day 3 — D3.0 Contract & Documentation Reconciliation: COMPLETE. Communications and Tasks remain unimplemented; their minimal contracts are now the source of truth for D3.1.

## Overall deadline
7-day MVP implementation plan.

## DONE
- [x] Source project specification reviewed.
- [x] 7-day implementation strategy defined.
- [x] Modular-monolith architecture selected.
- [x] Core stack fixed: FastAPI + React + PostgreSQL + SQLAlchemy + Celery + Docker.
- [x] Redis proposed as Celery broker.
- [x] Required i18n defined: Russian default + English + Spanish.
- [x] VILEORUF visual direction defined.
- [x] Payment functionality explicitly excluded from current scope.
- [x] Initial project documentation created.
- [x] Minimal FastAPI backend skeleton initialized and verified.
- [x] Backend `GET /health` endpoint implemented and verified.
- [x] PostgreSQL-only environment configuration added and validated.
- [x] SQLAlchemy engine, session factory, dependency and empty metadata infrastructure added and validated without opening a database connection.
- [x] Alembic configured against shared application settings; empty initial revision and offline PostgreSQL SQL generation verified.
- [x] Docker Compose PostgreSQL 16 service configured with persistent storage and a healthcheck.
- [x] Authenticated SQLAlchemy connection to the project PostgreSQL database verified.
- [x] Initial Alembic revision applied online and verified as current.
- [x] React/Vite frontend foundation initialized, built and verified at runtime.
- [x] Frontend i18n configured for `ru`, `en` and `es`; Russian default/fallback and localStorage persistence verified in a browser.
- [x] VILEORUF light visual foundation and responsive technical screen added; the current visual contract is Modern Minimal Light UI, Apple-inspired.
- [x] Frontend-to-backend `GET /health` connectivity and restricted development CORS verified in a browser.
- [x] Frontend toolchain migrated from Node.js 14/Vite 4 to Node.js 24 LTS/Vite 8; clean install, audit, build and browser regression checks passed.
- [x] Foundation repository structure established without premature empty feature directories.
- [x] Development seed strategy documented without creating domain models or seed data.
- [x] Codex architectural/context contract prepared and applied through the five project source-of-truth documents.
- [x] Authentication/authorization architecture gate: ARCHITECTURE DECIDED / DOCUMENTED.
- [x] PostgreSQL + FastAPI + React/Vite development environment starts through one verified `docker compose up --build` flow, including automatic migrations and development reload.
- [x] Authentication backend foundation implemented and verified: `User`, `ADMIN`/`MANAGER`, Argon2id password primitives/policy, HS256 access/refresh JWT primitives/configuration, and users migration.
- [x] Secure first-ADMIN bootstrap CLI implemented and verified with hidden password confirmation, controlled normalization/validation, repeated-bootstrap protection and transactional rollback.
- [x] Backend authentication HTTP flow implemented and verified: login, stateless cookie refresh, idempotent logout, and current-user response.
- [x] Reusable Bearer current-user authentication implemented and verified with per-request database existence/active-state checks.
- [x] Frontend employee authentication implemented and browser-verified: localized login, memory-only access token, refresh-cookie reload restoration, protected screen, identity display and logout.
- [x] ADMIN-only employee management implemented and verified: list/create/update, deactivate/reactivate, MANAGER 403, self/last-active-admin protection and localized UI.
- [x] D2.1 CRM Core domain schema implemented and verified: `Client`, database-backed `PipelineStage`, `Deal`, `CUSTOMER`/`CLIENT` lifecycle enum, optional employee ownership, PostgreSQL constraints/indexes and reversible Alembic migration.
- [x] D2.2a runtime environment contract implemented and verified: required typed `APP_ENV` with only `development`/`test`/`production`, explicit local Compose development value and configuration tests.
- [x] D2.2 system pipeline bootstrap implemented and verified: explicit atomic/idempotent CLI installs the seven required stages in development/test/production, safely completes partial data and refuses position conflicts without changing user data.
- [x] D2.3 Clients backend vertical slice implemented and verified: authenticated ADMIN/MANAGER create/list/get/partial-update API, CUSTOMER-only creation, lifecycle-protected writes, stable bounded pagination and PostgreSQL coverage.
- [x] D2.4 Deals backend and ownership authorization implemented and verified: authenticated create/list/get/partial-update API, all-employee visibility, ADMIN assignment and all-Deal edit, MANAGER self-assignment on create and own-Deal-only edit, protected stage/client links and PostgreSQL coverage.
- [x] D2.4a responsible policy corrected and verified: Deal responsible may be an active MANAGER, active ADMIN or `NULL`; ADMIN remains unrestricted by ownership while MANAGER behavior is unchanged.
- [x] D2.5 pipeline transition business operation implemented and verified: dedicated authenticated endpoint, existing ownership enforcement, unrestricted existing-stage movement, atomic `Won` promotion from CUSTOMER to CLIENT and irreversible lifecycle semantics.
- [x] D2.6 CRM shell/navigation, base design system and Clients frontend implemented and verified: protected `/crm/clients`, real Clients API list/create/detail/edit/pagination, RU/EN/ES, responsive light UI and preserved authentication.
- [x] D2.7a Deals reference-data APIs implemented and verified: authenticated ADMIN/MANAGER read-only `/pipeline-stages` and `/employees/reference`; the existing ADMIN-only `/users` management contract remains unchanged.
- [x] D2.7 — Deals Frontend — DONE: protected `/crm/deals`, real list/create/detail/edit/transition flows, ADMIN/MANAGER ownership-aware controls, reference-data labels, pagination, RU/EN/ES and existing PNG logo integration.
- [x] D2.8 — Pipeline Kanban + Drag-and-Drop — DONE: protected `/crm/pipeline`, seven ordered API-backed columns, role-aware native drag/drop through transition endpoint, accessible Move fallback, all-page loading and RU/EN/ES.
- [x] D2.9 — Public Request Boundary + Minimal Demo Seed + Day 2 Final Verification — DONE: public `/`, employee `/login` and `/crm/*` boundary, atomic public Client/Deal creation, and explicit idempotent development/test-only demo seed.
- [x] D3.0 — Day 3 Contract & Documentation Reconciliation — DONE: Day 1/Day 2 stale statements removed; unified visual contract; Communications and Tasks contracts plus Initial Dashboard boundary documented; no application code, schema, or migration changes.

## IN PROGRESS
None.

## NEXT

### Day 1 — Foundation: COMPLETE
- [x] Create repository structure.
- [x] Initialize FastAPI.
- [x] Initialize React frontend.
- [x] Configure PostgreSQL.
- [x] Configure SQLAlchemy and migrations.
- [x] Configure Docker Compose.
- [x] Add `.env.example`.
- [x] Add backend `/health`.
- [x] Configure frontend i18n: ru/en/es.
- [x] Establish VILEORUF UI tokens/base layout.
- [x] Add development seed strategy.

### Day 2 — CRM core: COMPLETE
- [x] D2.1 domain schema and migration for Clients, Deals and Pipeline stages.
- [x] D2.2a runtime environment contract; D2.2 seed blocker resolved.
- [x] D2.2 standard system PipelineStage bootstrap data.
- [x] D2.3 Clients backend API.
- [x] D2.4 Deals backend API and ownership authorization.
- [x] D2.4a allow active ADMIN as Deal responsible without multi-role RBAC or schema changes.
- [x] D2.5 PipelineStage transition API and atomic Won promotion.
- [x] D2.6 CRM shell/navigation and Clients frontend.
- [x] D2.7a PipelineStages and employee reference data APIs for Deals frontend.
- [x] D2.7 Deals frontend and logo integration.
- [x] D2.8 Pipeline Kanban and role-aware drag-and-drop with accessible Move fallback.
- [x] D2.9 Public Request Boundary + Minimal Demo Seed + Day 2 final verification.

### Day 3 — Communications / tasks
- [x] D3.0 Contract & Documentation Reconciliation.
- [ ] D3.1 Communications + Tasks persistence/schema foundation.
- [ ] Communication timeline.
- [ ] Manager tasks.
- [ ] Initial dashboard (contract deferred to D3.6 preflight after Communications and Tasks).

### Day 4 — AI
- [ ] Lead scoring.
- [ ] Deal prediction.
- [ ] Next best action.
- [ ] AI email draft.

### Day 5 — Integrations
- [ ] Gmail.
- [ ] Telegram.
- [ ] Calendar.
- [ ] WhatsApp or documented external limitation.

### Day 6 — Analytics / UX / i18n
- [ ] Analytics.
- [ ] Complete translations.
- [ ] Responsive/UX pass.
- [ ] Error/empty/loading states.

### Day 7 — QA / delivery
- [ ] End-to-end functional verification.
- [ ] Tests.
- [ ] Docker clean-start verification.
- [ ] README.
- [ ] Final technical specification DOCX.
- [ ] Screenshots.
- [ ] Screencast.
- [ ] Public GitHub repository ready.

## KNOWN ISSUES / BLOCKERS
None currently. The project PostgreSQL container uses host port `55432` because ports `5432` and `5433` were already occupied.

## AUTHENTICATION / AUTHORIZATION ARCHITECTURE GATE

Status: **ARCHITECTURE DECIDED / DOCUMENTED**.

Authentication + employee management gate: **COMPLETE**.

CRM authorization contract: **DECIDED / DOCUMENTED**.

Deal ownership authorization implementation: **IMPLEMENTED / VERIFIED** for create/list/get/PATCH and the D2.5 transition business operation.

Authentication backend foundation: **IMPLEMENTED / VERIFIED**.

First ADMIN bootstrap CLI: **IMPLEMENTED / VERIFIED**.

Backend authentication HTTP flow: **IMPLEMENTED / VERIFIED**.

Current-user Bearer authentication: **IMPLEMENTED / VERIFIED**.

Frontend authentication: **IMPLEMENTED / VERIFIED**.

Employee management: **IMPLEMENTED / VERIFIED**.

The approved design uses internal employee `User` accounts with `ADMIN` and `MANAGER` roles; for the MVP, ADMIN is a sales-capable employee with additional administrative privileges. Email/password login uses Argon2id, short-lived access JWTs held only in React memory, and stateless refresh JWTs in secure `HttpOnly` cookies. A Deal responsible may be an active MANAGER, active ADMIN or `NULL`; backend authorization enforces manager ownership through `responsible_user_id`, while ADMIN may edit any Deal regardless of ownership. External customers remain unauthenticated `Client` records, with `CUSTOMER`/`CLIENT` lifecycle status separate from auth roles.

Implemented baseline: UUID `User` model, native `ADMIN`/`MANAGER` role enum, Argon2id password validation/hashing/verification, environment-backed HS256 access/refresh JWT creation/typed decoding, current Alembic head `20260831_0003`, and interactive first-ADMIN bootstrap CLI.

Authentication, employee management and Day 2 CRM Core are implemented through protected `/login` and `/crm/*` routes plus the public `/` request boundary. External visitors remain unauthenticated Client records; CRM role/ownership authorization is enforced by the backend.

## VERIFIED DAY 2 BASELINE

- Python 3.10.12; FastAPI 0.115.12; Uvicorn 0.34.3.
- SQLAlchemy 2.0.41; Psycopg 3.2.9; Alembic 1.16.1; pydantic-settings 2.9.1.
- PostgreSQL 16 via Docker Compose; database `vileoruf_crm`; development user `vileoruf_app`; host port `55432`; persistent volume and healthcheck.
- Compose development services for PostgreSQL, FastAPI, and React/Vite; healthy dependency ordering, automatic Alembic upgrade, loopback host publishing, and source bind mounts verified from a clean volume.
- Alembic revision `20260831_0003` applied; `clients`, `pipeline_stages` and `deals` exist. Clients, Deals and Deal transition APIs are implemented. The seven required system pipeline stages are installed separately through the explicit bootstrap command, not through Alembic.
- Authenticated Clients API exposes `POST /clients`, `GET /clients`, `GET /clients/{client_id}` and `PATCH /clients/{client_id}` for both ADMIN and MANAGER. Client lifecycle status remains server-managed; DELETE is absent.
- Authenticated Deals API exposes `POST /deals`, `GET /deals`, `GET /deals/{deal_id}`, `PATCH /deals/{deal_id}` and `POST /deals/{deal_id}/transition`. ADMIN can edit/transition any Deal and assign active MANAGER, active ADMIN or `NULL`; MANAGER sees all Deals, is automatically assigned on create, and can edit/transition only owned Deals without changing responsibility. Ordinary PATCH cannot change stage/client. Transition to DB stage named `Won` atomically promotes CUSTOMER to CLIENT; promotion is irreversible. Direct create in Won and same-stage Won do not promote. DELETE is absent.
- Frontend provides protected `/crm/clients`, `/crm/deals`, and `/crm/pipeline`, including actual API-backed CRM flows and role-aware Pipeline Kanban with drag/drop plus accessible Move fallback. Client status remains readonly; DELETE/search are absent.
- Authentication dependencies: argon2-cffi 25.1.0 and PyJWT 2.13.0.
- Node.js 24.20.0 LTS; npm 11.19.0; React/React DOM 19.2.8; Vite 8.2.2; `@vitejs/plugin-react` 6.1.1; i18next 26.4.0; react-i18next 17.0.12.
- Frontend languages `ru`/`en`/`es`; Russian default/fallback; localStorage persistence; synchronized `<html lang>`.
- Restricted development CORS and frontend-to-backend `/health` connectivity verified.
- Backend pytest, frontend build, npm audit and browser runtime checks passed; npm audit reported 0 vulnerabilities.
- Development/demo seed strategy remains production-restricted; the separate explicit system pipeline bootstrap is implemented and installs only the seven required non-demo stages.
- Employee management, end-to-end authentication, CRM Core, and Deal ownership authorization are verified. Communications/Tasks, Celery/Redis, OpenAI, and external integrations are not implemented.

## DECISIONS / CHANGES LOG
- Initial architecture: modular monolith.
- Russian is default/fallback UI language; English and Spanish mandatory.
- Payment processing is not part of the approved requirements.
- External integrations must not be falsely presented as working when credentials/provider access prevent live verification.
- PostgreSQL access uses SQLAlchemy 2.x with the Psycopg 3 `postgresql+psycopg` driver.
- Local project PostgreSQL uses the official `postgres:16` image and host port `55432`.
- Development CORS is restricted to the configured `FRONTEND_ORIGIN`, defaulting to `http://localhost:5173`.
- Frontend development uses project-pinned Node.js 24.20.0 (LTS), npm 11.19.0 and Vite 8.2.2.
- Development seed data will use the documented opt-in, development-only, idempotent strategy after domain models exist.
- Runtime environment is explicitly identified by the required typed `APP_ENV` setting with allowed values `development`, `test` and `production`; local Compose passes `development`.
- Required system pipeline stages are installed by the explicit, atomic and idempotent `python -m backend.app.scripts.bootstrap_pipeline` command in any valid `APP_ENV`; demo/development seeds remain a separate production-prohibited category.
- The complete application foundation starts with `docker compose up --build`; backend uses `postgres:5432` internally while browser-side frontend requests use the host-published backend URL.
- Internal authenticated users are employees with fixed MVP roles `ADMIN` and `MANAGER`; external customers are not authenticated users.
- Authentication uses in-memory short-lived access JWTs and stateless refresh JWTs in secure `HttpOnly` cookies, without server-side session storage.
- Login uses unique email plus an Argon2id-hashed password; the first production `ADMIN` requires a secure CLI/bootstrap mechanism, not seed/default credentials.
- Backend authorization is authoritative; managers may modify only Deals they own, while admins may manage all CRM Core records and responsible-user assignments.
- For MVP responsibility semantics, `ADMIN` is sales-capable in addition to having administrative privileges; `Deal.responsible_user_id` accepts active MANAGER, active ADMIN or `NULL` without introducing multiple roles.
- Deal stage changes are a dedicated business operation, not ordinary PATCH. No strict transition matrix is imposed: an authorized employee may move to any existing stage, including backward/from Won/Lost. A real transition into system stage `Won` atomically promotes CUSTOMER to CLIENT; leaving Won never downgrades the Client, while create-in-Won has no promotion side effect.
- Client lifecycle status is `CUSTOMER` until the first won Deal promotes it to `CLIENT`; this status is separate from authentication roles and is not automatically reversed.
- User IDs use UUID; roles use a native PostgreSQL enum with no default; email remains unchanged in the persistence model pending a future input/service normalization boundary.
- Password primitives use argon2-cffi 25.1.0 Argon2id with the approved 12–128 character policy.
- JWT primitives use PyJWT 2.13.0 and HS256 with required environment signing secret, `sub`/`type`/`iat`/`exp` claims, and no role/PII claims.
- First ADMIN is created only by `python -m backend.app.scripts.create_admin`; the CLI uses hidden password confirmation, trim/lowercase email normalization, shared Argon2id helpers, explicit `ADMIN`, transactional locking/rollback and refuses any repeated bootstrap.
- Backend auth exposes only login/refresh/logout/me; refresh uses the `refresh_token` HttpOnly, SameSite=Lax, `/auth` cookie with environment-controlled Secure behavior and no server-side refresh state.
- Every Bearer/refresh identity resolution reloads the User and enforces existence/is_active; roles and PII are never trusted from JWT claims.
- CRM visual direction is permanently `Modern Minimal Light UI, Apple-inspired`: light neutral background, white surfaces, VILEORUF blue functional accents, graphite typography, subtle borders/shadows, moderate radius and practical CRM information density; metallic, 3D, glow and glass UI effects are excluded.
- Day 3 Communications and Tasks remain a modular-monolith extension. Their backend must authoritatively enforce Client/Deal relationship invariants and the documented ADMIN/MANAGER permissions; no live provider integration, delivery tracking, DELETE, analytics architecture, or new infrastructure is approved. Initial Dashboard is only a future operational overview, not Day 6 Analytics/Reporting.

## LAST CODEX RESULT
Task: D3.0 — Day 3 Contract & Documentation Reconciliation.
Result: Day 1/Day 2 documentation reconciled; Communications and Tasks minimal contracts plus Initial Dashboard boundary documented.
Files created: local ignored report `history/ANSWER_33.md`.
Files modified: `README.md`, `docs/PROJECT_CONTEXT.md`, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_STATUS.md`, `docs/CODEX_RULES.md`.
Database/migrations: None; head remains `20260831_0003`.
API endpoints: None; application API unchanged.
Dependencies: None.
Tests/checks: documentation review, `git diff`, `git diff --check`, and application-code/migration scope inspection; full regression and frontend build not run because this is docs-only.
Known issues: Communications/Tasks persistence and UI, Initial Dashboard, and later integrations remain unimplemented.
Next recommended step: D3.1 — Communications + Tasks persistence/schema foundation.

## UPDATE TEMPLATE

After each Codex task, replace/update the sections above and record:

```text
Task:
Result:
Files created:
Files modified:
Database/migrations:
API endpoints:
Dependencies:
Tests/checks:
Known issues:
Next recommended step:
```
