# VILEORUF CRM — Development Status

> This file is the operational status source of truth. Update it after every completed implementation task.

## Current phase
Day 1 — Foundation: COMPLETE.

Day 2 — CRM Core: NOT STARTED. Readiness gate passed; pending explicit authorization in a new controlled iteration.

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
- [x] VILEORUF dark SaaS design tokens and responsive technical foundation screen added.
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

### Day 2 — CRM core: NOT STARTED
- [ ] Clients.
- [ ] Deals.
- [ ] Pipeline stages.
- [ ] Kanban pipeline.
- [ ] Drag & drop with persisted stage changes.

### Day 3 — Communications / tasks
- [ ] Communication timeline.
- [ ] Manager tasks.
- [ ] Initial dashboard.

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

CRM authorization implementation: **NOT IMPLEMENTED**; it will be implemented together with the relevant CRM Core entities/endpoints before those endpoints are complete.

Authentication backend foundation: **IMPLEMENTED / VERIFIED**.

First ADMIN bootstrap CLI: **IMPLEMENTED / VERIFIED**.

Backend authentication HTTP flow: **IMPLEMENTED / VERIFIED**.

Current-user Bearer authentication: **IMPLEMENTED / VERIFIED**.

Frontend authentication: **IMPLEMENTED / VERIFIED**.

Employee management: **IMPLEMENTED / VERIFIED**.

The approved design uses internal employee `User` accounts with `ADMIN` and `MANAGER` roles; email/password login with Argon2id; short-lived access JWTs held only in React memory; and stateless refresh JWTs in secure `HttpOnly` cookies. Backend authorization enforces role and Deal ownership through `responsible_user_id`. External customers remain unauthenticated `Client` records, with `CUSTOMER`/`CLIENT` lifecycle status separate from auth roles.

Implemented foundation: UUID `User` model, native `ADMIN`/`MANAGER` role enum, Argon2id password validation/hashing/verification, environment-backed HS256 access/refresh JWT creation/typed decoding, Alembic revision `20260829_0002` for `users`, and interactive first-ADMIN bootstrap CLI.

Authentication and ADMIN employee management are implemented through the protected frontend and backend `/auth/*` plus `/users` APIs. The current frontend opens at the employee login/protected foundation; the target unauthenticated public area (`/`) and separate employee CRM route (`/crm`) are documented but not implemented. CRM role/ownership authorization remains not implemented and is not a prerequisite for creating its dependent Day 2 entities; it must accompany the relevant CRM endpoints. Day 2 CRM Core remains not started.

## VERIFIED DAY 1 BASELINE

- Python 3.10.12; FastAPI 0.115.12; Uvicorn 0.34.3.
- SQLAlchemy 2.0.41; Psycopg 3.2.9; Alembic 1.16.1; pydantic-settings 2.9.1.
- PostgreSQL 16 via Docker Compose; database `vileoruf_crm`; development user `vileoruf_app`; host port `55432`; persistent volume and healthcheck.
- Compose development services for PostgreSQL, FastAPI, and React/Vite; healthy dependency ordering, automatic Alembic upgrade, loopback host publishing, and source bind mounts verified from a clean volume.
- Alembic revision `20260829_0002` applied; `users` exists and no CRM Core domain tables exist.
- Authentication dependencies: argon2-cffi 25.1.0 and PyJWT 2.13.0.
- Node.js 24.20.0 LTS; npm 11.19.0; React/React DOM 19.2.8; Vite 8.2.2; `@vitejs/plugin-react` 6.1.1; i18next 26.4.0; react-i18next 17.0.12.
- Frontend languages `ru`/`en`/`es`; Russian default/fallback; localStorage persistence; synchronized `<html lang>`.
- Restricted development CORS and frontend-to-backend `/health` connectivity verified.
- Backend pytest, frontend build, npm audit and browser runtime checks passed; npm audit reported 0 vulnerabilities.
- Development seed strategy documented; executable seed and domain seed data do not exist yet.
- Employee management and end-to-end authentication are verified; CRM authorization, CRM Core, Celery/Redis, OpenAI and external integrations are not implemented.

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
- The complete application foundation starts with `docker compose up --build`; backend uses `postgres:5432` internally while browser-side frontend requests use the host-published backend URL.
- Internal authenticated users are employees with fixed MVP roles `ADMIN` and `MANAGER`; external customers are not authenticated users.
- Authentication uses in-memory short-lived access JWTs and stateless refresh JWTs in secure `HttpOnly` cookies, without server-side session storage.
- Login uses unique email plus an Argon2id-hashed password; the first production `ADMIN` requires a secure CLI/bootstrap mechanism, not seed/default credentials.
- Backend authorization is authoritative; managers may modify only Deals they own, while admins may manage all CRM Core records and responsible-user assignments.
- Client lifecycle status is `CUSTOMER` until the first won Deal promotes it to `CLIENT`; this status is separate from authentication roles and is not automatically reversed.
- User IDs use UUID; roles use a native PostgreSQL enum with no default; email remains unchanged in the persistence model pending a future input/service normalization boundary.
- Password primitives use argon2-cffi 25.1.0 Argon2id with the approved 12–128 character policy.
- JWT primitives use PyJWT 2.13.0 and HS256 with required environment signing secret, `sub`/`type`/`iat`/`exp` claims, and no role/PII claims.
- First ADMIN is created only by `python -m backend.app.scripts.create_admin`; the CLI uses hidden password confirmation, trim/lowercase email normalization, shared Argon2id helpers, explicit `ADMIN`, transactional locking/rollback and refuses any repeated bootstrap.
- Backend auth exposes only login/refresh/logout/me; refresh uses the `refresh_token` HttpOnly, SameSite=Lax, `/auth` cookie with environment-controlled Secure behavior and no server-side refresh state.
- Every Bearer/refresh identity resolution reloads the User and enforces existence/is_active; roles and PII are never trusted from JWT claims.

## LAST CODEX RESULT
Task: Isolate the first-ADMIN PostgreSQL integration scenario and re-run the Day 2 readiness blocker criterion.
Result: Bootstrap success/repeated-refusal tests now use a dedicated temporary PostgreSQL database; the persistent ADMIN remains unchanged and the full PostgreSQL suite passes. Day 2 readiness is READY, but Day 2 remains NOT STARTED pending explicit authorization.
Files created: local ignored report `history/ANSWER_17.md`.
Files modified: `backend/tests/test_create_admin_database.py`, `docs/DEVELOPMENT_STATUS.md`.
Database/migrations: None; head remains `20260829_0002`.
API endpoints: None.
Dependencies: None.
Tests/checks: focused PostgreSQL 2 passed; full PostgreSQL 63 passed; ordinary 58 passed with five intentional DB skips; persistent ADMIN integrity, Compose, health, Alembic and frontend build passed.
Known issues: No generic mid-session access-token expiry retry; stateless refresh JWTs cannot be centrally revoked before expiration. CRM authorization remains unimplemented by design until relevant CRM endpoints.
Next recommended step: Start Day 2 only in a new explicitly authorized controlled iteration.

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
