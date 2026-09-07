# VILEORUF CRM — Development Status

> This file is the operational status source of truth. Update it after every completed implementation task.

## Current phase
Day 1 — Foundation: COMPLETE.

Day 2 — CRM Core: COMPLETE. D2.1–D2.9 are implemented and verified, including the public request boundary and deterministic development demo seed.

Day 3 — COMPLETE. D3.0–D3.7 are complete, covering Communications persistence/API/timeline, Tasks persistence/API/frontend, bounded Initial Operational Dashboard, final verification, and documentation closure.

D4.0 — Architecture/Product Contract: APPROVED / CLOSED.

D4.1 — AI Foundation: DONE. Common AI persistence/lifecycle, provider abstraction, Celery/Redis, runtime model configuration foundation, migration, tests, and runtime smoke are implemented and verified. No D4.2+ AI business function or UI was added.

D4.2 — Business Configuration + Lead Scoring: DONE. Categories/Services and scoring settings, Deal/Client business fields, backend-only Commercial Value/overall score, manual role-aware Celery Lead Scoring, freshness invalidation, localized UI, migration, tests, and runtime smoke are implemented and verified.

D4.3 — Deal Prediction: DONE. Manual role-aware Celery Deal Prediction is implemented with strict independent probability/evidence-confidence output, bounded current-Deal communication context, structured tasks/activity indicators, anonymized same-client aggregate history, persisted seven-day validity configuration, freshness/invalidation, typed API, localized Deal UI, migration and PostgreSQL verification.

D4.4 — Next Best Action + Initial AI Orchestration: DONE. Advisory-only manual/background NBA, strict 1–3 ranked output, optional freshness-labelled LS/DP context, bounded/privacy-safe primary context, directed freshness, persisted kill/automatic/validity settings, typed API, localized Deal UI, and failure-tolerant exact-ID `LS ∥ DP → NBA` orchestration for newly created active Deals are implemented and verified.

D4.5 — AI Email Draft: DONE. Manual asynchronous generation produces a strict, placeholder-form `AIAnalysis` proposal using the runtime Email model and Client preferred language; explicit save/manual CRUD creates independent editable EmailDraft working documents. Optional selected NBA is backend-resolved, context is frozen/retry-safe and later mismatch is flagged, while no SMTP/send/integration/Communication action exists. Closed Deals are permitted; `AI Enabled` blocks only new generation. No schema change was required; Alembic head remains `20260903_0008`.

D4.6 — AI History + AI Settings + Hardening: DONE. Unified safe history covers all four functions with ADMIN/all and MANAGER/owned-Deal authorization, filters, stable pagination, typed result validation and freshness/current markers. ADMIN can manage runtime switches, allowlisted analysis/email model overrides and 1–365 day DP/NBA validity with atomic updates, reset-to-environment behavior and safe application-log auditing. A shared per-employee Redis fixed window limits only manual launch endpoints and fails open safely. No schema change was required; Alembic head remains `20260903_0008`.

D4.7 — Final Day 4 Regression + Runtime/OpenAI/Browser Smoke + Documentation Closure: COMPLETE. The full PostgreSQL backend suite (237 passed), Alembic/static checks, frontend production build, service health, Redis limiter API boundary, controlled two-call real OpenAI/Celery/provider smoke, and public/unauthenticated Chromium smoke passed. D4.7.1 passed the remaining authenticated browser functionality using temporary synthetic ADMIN/MANAGER users and removed all fixture rows. D4.7.2 identified the prior local-only argv/`CalledProcessError` rendering mechanism, moved credential transfer out of command arguments into stdin, added sanitized harness-boundary handling, and verified both forced failure and successful temporary authentication emit no secret in captured stdout/stderr with zero residue.

Day 4 — AI Automation: COMPLETE.

D4.8 — Manual Email Draft + AI History authenticated browser defect correction: initial Codex verification PARTIAL. Targeted Email/History PostgreSQL tests (29 passed), frontend production build, Alembic/static/locale checks passed; the initial report correctly recorded that Codex had not completed the final browser regression/full-suite terminal summary. The remaining browser scenarios were subsequently verified manually by the project owner: Email Draft NBA selection, manual create/save, AI generation, MANAGER foreign-Deal non-error semantics, Deal-level manual LS/DP/NBA history, and Global AI History. Therefore no active D4.8 functional release blocker remains.

D4.9 — Public Request + Business Settings regression correction: DONE. Public services-load and submit errors have independent localized semantics. Business Settings PUT now sends only the strict settings payload, excluding response-only `updated_at`. The canonical backend test invocation was restored, targeted tests (33 passed), full PostgreSQL regression (237 passed), Alembic, production build, locale/static checks, and Chromium ADMIN/MANAGER/public persistence/authorization smoke all passed. Temporary users were removed and Business Settings were restored exactly. Day 4 remains COMPLETE; no Day 5 work was started.

D5.0 — Integrations Architecture/Product Contract: APPROVED / ACTIVE. `docs/DAY5_INTEGRATIONS_CONTRACT.md` is the mandatory source of truth for all Day 5 implementation iterations. It approves the bounded Gmail, Telegram Bot, Google Calendar and WhatsApp Business Cloud API MVP, preserves Communication/EmailDraft/Task semantics, and defines integration persistence, authorization, secrets/OAuth, idempotency, background work, provider honesty and verification.

D5.1 — Integration Foundation: DONE. Shared `IntegrationConnection`, `ExternalMessage`, and `CalendarEvent` persistence/lifecycle foundations are implemented at Alembic head `20260905_0009`; `ExternalMessage != Communication` and `Task != CalendarEvent` remain enforced domain boundaries. EmailDraft has a `DRAFT`/`SENT` state foundation and ordinary mutation blocks historical `SENT` content. The implementation includes adapter/error-retry classification boundaries, application-level encrypted token-storage foundation with environment-only key configuration, logical Celery `integrations` queue while preserving `ai`, ADMIN-only safe `GET /settings/integrations`, and localized ADMIN `/crm/settings/integrations` four-provider status cards. Full PostgreSQL regression passed (`240 passed in 37.74s`), focused PostgreSQL persistence verification passed (`1 passed in 1.04s`), and ADMIN/MANAGER API plus RU/EN/ES Chromium verification passed. No live provider operation was implemented or called.

D5.2 — Gmail: DONE / LIVE VERIFIED. D5.2a — Google OAuth Connection + Encrypted Token Lifecycle: DONE / LIVE VERIFIED. D5.2b — Gmail Outbound Send: DONE / LIVE VERIFIED. D5.2c — Gmail Inbound Synchronization: DONE / LIVE VERIFIED. It uses ADMIN-triggered bounded sync on the existing integrations queue: the first run establishes a persisted checkpoint without historical import; later runs query from a fixed five-minute provider-visibility overlap before that checkpoint in pages of at most 25, persist a page token until the window completes, and rely on the existing connection/provider-message unique constraint. A corrected controlled live retry performed real Gmail API read, accepted exactly one inbound provider fact, exact-normalized it to the one synthetic Client, created exactly one incoming EMAIL Communication with no Deal, and verified a repeat sync did not duplicate either record. D5.2c focused PostgreSQL tests passed (`4 passed in 2.47s`); prior frontend locale/build and full PostgreSQL local evidence remain recorded in `ANSWER_71`. Alembic head/check remains `20260907_0012`, and runtime worker registration passed.

D5.3 — Telegram: DONE / LIVE PROVIDER VERIFIED. One-Bot integration uses environment-backed secrets and a safe `IntegrationConnection` lifecycle; webhook authenticity validation, provider-scoped inbound idempotency, stable `telegram_provider_user_id` matching (username is not authoritative), unmatched preservation with explicit manual linking, no automatic Client creation/Deal inference, protected Client/optional-Deal outbound send, HTTP `Idempotency-Key`, PENDING/SENT/FAILED/UNKNOWN lifecycle, integrations-queue routing, and RU/EN/ES Communication Timeline controls are implemented. Canonical PostgreSQL regression passed (`264 passed in 69.96s`), Alembic head is `20260907_0014`, frontend build/locales and backend/PostgreSQL/Redis/Celery checks passed. Live verification proved real Bot connection, HTTPS webhook `200` receipt, inbound persistence, unmatched handling, manual linking, subsequent stable-identity automatic matching, and one normal CRM/Celery/provider outbound operation from `PENDING` to provider-confirmed `SENT` with exactly one outgoing Communication and owner receipt. Automated PostgreSQL tests cover deliberate webhook/HTTP idempotency; normal live inbound facts were exactly once, while deliberate live provider redelivery/replay was not performed. The prior controlled synthetic-runtime limitation is superseded by this actual live provider verification.

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
- [x] D3.0a — Residual Documentation Reconciliation — DONE: remaining Day 2 baseline statements in README corrected without application changes.
- [x] D3.1 — Communications + Tasks Persistence / Schema Foundation — DONE: SQLAlchemy models, PostgreSQL enums/FKs/indexes/relationships, Alembic migration `20260901_0004`, targeted PostgreSQL coverage and full backend regression verified; API/UI intentionally absent.
- [x] D3.2 — Communications Backend API — DONE: authenticated create/get/list `/communications`, backend-authoritative Client/Deal consistency and manager ownership validation, bounded filtered timeline list, PostgreSQL integration coverage and full backend regression verified; no update/delete or frontend.
- [x] D3.3 — Communication Timeline Frontend — DONE: Client edit and Deal detail context timelines, authenticated create form, bounded load-more pagination, role-aware Deal creation UX, RU/EN/ES, and no standalone Communications route or backend changes.
- [x] D3.4 — Tasks Backend API + Authorization — DONE: authenticated create/list/get/update/completion API, authoritative responsibility and Client/Deal validation, ADMIN/MANAGER authorization, bounded operational filtering, PostgreSQL integration coverage, and no frontend/schema changes.
- [x] D3.5 — Tasks Frontend — DONE: protected `/crm/tasks`, employee task list/filter/pagination/create/edit/complete flows, active responsible selector for ADMIN, manager self-assignment and all-task read UX, RU/EN/ES, derived overdue presentation, and no backend/schema changes.
- [x] D3.6 — Initial Operational Dashboard — DONE: protected `/crm` operational home, independently loaded bounded open Tasks and recent Communications previews, quick CRM navigation, RU/EN/ES, and no global counts, analytics, backend, or schema changes.
- [x] D3.7 — Day 3 Final Verification + Documentation Closure — DONE: full Day 1–3 contract/regression verification and source-of-truth reconciliation; final Alembic head `20260901_0004`.
- [x] D3.8 — Browser Smoke Logout/Public Navigation UX Fix — DONE: manual Day 1–3 browser smoke PASS; logout now returns to public `/`, and localized Login navigation provides an explicit public-home action.
- [x] D4.0 — AI Architecture/Product Contract — APPROVED / CLOSED: `docs/DAY4_AI_CONTRACT.md` is the Day 4 source of truth.
- [x] D4.1 — AI Foundation — DONE: `AIAnalysis`, separate `EmailDraft`, model override persistence, strict structured provider boundary, safe retry/failure lifecycle, deterministic fingerprint/compact snapshot, PostgreSQL duplicate in-flight protection, Celery/Redis/OpenAI SDK infrastructure, migration `20260902_0005`, full PostgreSQL regression, and worker smoke verified; no AI business endpoints/UI.
- [x] D4.2 — Business Configuration + Lead Scoring — DONE: multilingual Category/Service catalog and deterministic bootstrap, target rate/effort and Lead Scoring settings, Deal/Client business fields, manual typed Lead Scoring API/Celery task, backend-only Commercial Value/overall score, freshness/authorization rules, ADMIN settings UI and Deal Lead Scoring section, migration `20260902_0006`, full PostgreSQL regression, frontend build, and runtime smoke verified.
- [x] D4.3 — Deal Prediction — DONE: manual typed API/Celery task, independent probability/evidence-confidence result, bounded current-Deal and anonymized same-client aggregate context, persisted validity, directed freshness, authorization, localized Deal UI, migration `20260903_0007`, full PostgreSQL regression, frontend build, and runtime smoke verified.
- [x] D4.4 — Next Best Action + Initial AI Orchestration — DONE: advisory-only typed NBA API/Celery task/UI, strict ranked output, LS/DP auxiliary freshness, persistent runtime switches/NBA validity, exact-analysis correlation, parallel sibling dispatch, terminal-success-or-failure continuation, three Deal creation sources/languages, migration `20260903_0008`, 208-test PostgreSQL regression, frontend build, and runtime smoke verified.
- [x] D4.5 — AI Email Draft — DONE: typed Email model generation/history API plus EmailDraft CRUD, strict Subject/Body/security schema, `{{client_name}}` privacy rendering, client-language selection, optional validated NBA context, frozen request/freshness warning, explicit save/manual multiple-draft CRUD, localized Deal UI/copy actions, no-send/no-Communication scope, and PostgreSQL/frontend verification. No migration required.
- [x] D4.6 — AI History + AI Settings + Hardening — DONE: ADMIN-safe runtime settings, model allowlist/reset, 1–365 day validity, application-log audit, Redis per-employee shared manual-launch quota, unified typed AI history, Deal/global filters and pagination, manager ownership enforcement, localized UI, and no migration.
- [x] D4.7 — COMPLETE: functional regression/runtime/provider/public/authenticated-browser gates passed; D4.7.2 credential-output remediation verified safe failure/success paths and cleanup.

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

### Day 3 — Communications / tasks: COMPLETE
- [x] D3.0 Contract & Documentation Reconciliation.
- [x] D3.1 Communications + Tasks persistence/schema foundation.
- [x] D3.2 Communications backend API.
- [x] D3.3 Communication Timeline frontend.
- [x] D3.4 Tasks backend API + authorization.
- [x] D3.5 Tasks frontend.
- [x] D3.6 Initial Operational Dashboard.
- [x] D3.7 Day 3 final verification + docs closure.

### Day 4 — AI
- [x] D4.0 Architecture/Product Contract.
- [x] D4.1 AI Foundation.
- [x] D4.2 Business Configuration + Lead Scoring.
- [x] D4.3 Deal Prediction.
- [x] D4.4 Next Best Action + Initial AI Orchestration.
- [x] D4.5 AI Email Draft.
- [x] D4.6 AI History + AI Settings + Hardening.
- [x] D4.7 Final Day 4 Regression + Runtime/OpenAI/Browser Smoke + Documentation Closure — COMPLETE.

### Day 5 — Integrations
- [x] D5.0 Integrations Architecture/Product Contract — APPROVED / ACTIVE: `docs/DAY5_INTEGRATIONS_CONTRACT.md`.
- [x] D5.1 Integration Foundation — DONE: shared persistence/state, safe ADMIN settings API/UI, adapter/encryption/queue foundation, migration and verification.
- [x] D5.2 Gmail — DONE / LIVE VERIFIED.
- [x] D5.2a Google OAuth Connection + Encrypted Token Lifecycle — DONE / LIVE VERIFIED.
- [x] D5.2b Gmail Outbound Send — DONE / LIVE VERIFIED.
- [x] D5.2c Gmail Inbound Synchronization — DONE / LIVE VERIFIED.
- [x] D5.3 Telegram — DONE / LIVE PROVIDER VERIFIED.
- [ ] D5.4 Google Calendar — NOT STARTED.
- [ ] D5.5 WhatsApp or documented external limitation — NOT STARTED.

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

## DEFERRED NON-BLOCKING UX BACKLOG
- Consider an expandable deterministic Commercial Value breakdown: budget, effective effort and its source, calculated Deal hourly rate, Category target hourly rate, ratio, and resulting Commercial Value.
- Consider a role-aware foreign-Deal MANAGER AI state instead of neutral text such as `Привлекательность ещё не рассчитана`, making unavailable ownership/permission results explicit.
- Retain owner browser-review layout/usability observations for future UI/UX polishing. None of these items is a Day 4 release blocker.

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

Implemented baseline: UUID `User` model, native PostgreSQL enums for bounded domain values, Argon2id password validation/hashing/verification, environment-backed HS256 access/refresh JWT creation/typed decoding, current Alembic head `20260907_0011`, Communication/Task persistence, D4.1 AI persistence/lifecycle/provider/Celery foundation, D4.2 business configuration/manual Lead Scoring, D4.3 Deal Prediction, D4.4 advisory NBA/initial orchestration, D4.5 AI Email Draft, D4.6 AI settings/history/hardening, D5.1 shared integration foundation, D5.2a Google OAuth/token lifecycle, D5.2b automated-local outbound Gmail lifecycle, and interactive first-ADMIN bootstrap CLI.

Authentication, employee management and Day 2 CRM Core are implemented through protected `/login` and `/crm/*` routes plus the public `/` request boundary. External visitors remain unauthenticated Client records; CRM role/ownership authorization is enforced by the backend.

## VERIFIED BASELINE THROUGH D4.7 (COMPLETE)

- Python 3.10.12; FastAPI 0.115.12; Uvicorn 0.34.3.
- SQLAlchemy 2.0.41; Psycopg 3.2.9; Alembic 1.16.1; pydantic-settings 2.9.1.
- PostgreSQL 16 via Docker Compose; database `vileoruf_crm`; development user `vileoruf_app`; host port `55432`; persistent volume and healthcheck.
- Compose development services for PostgreSQL, Redis, FastAPI, non-root Celery AI worker, and React/Vite; healthy dependency ordering, automatic Alembic upgrade, loopback host publishing, and source bind mounts verified.
- Alembic revision `20260907_0011` applied; D4.1 adds `ai_analyses`, `email_drafts`, and `ai_model_settings`; D4.2 adds business configuration and Deal/Client fields; D4.3 adds DP validity; D4.4 adds persistent AI/automatic switches, NBA validity, and exact-ID `initial_ai_analysis_pipelines` correlation; D5.1 adds integration foundation tables/enums and the EmailDraft send state; D5.2a adds one-time Google OAuth state hashes with expiry/consumption metadata; D5.2b adds EmailDraft/ExternalMessage correlation and unique finalization guards. Existing Deal rows remain valid through additive schema evolution. Required pipeline stages and the minimal business catalog remain explicit bootstrap data, not migration data.
- Authenticated Clients API exposes `POST /clients`, `GET /clients`, `GET /clients/{client_id}` and `PATCH /clients/{client_id}` for both ADMIN and MANAGER. Client lifecycle status remains server-managed; DELETE is absent.
- Authenticated Deals API exposes `POST /deals`, `GET /deals`, `GET /deals/{deal_id}`, `PATCH /deals/{deal_id}` and `POST /deals/{deal_id}/transition`. ADMIN can edit/transition any Deal and assign active MANAGER, active ADMIN or `NULL`; MANAGER sees all Deals, is automatically assigned on create, and can edit/transition only owned Deals without changing responsibility. Ordinary PATCH cannot change stage/client. Transition to DB stage named `Won` atomically promotes CUSTOMER to CLIENT; promotion is irreversible. Direct create in Won and same-stage Won do not promote. DELETE is absent.
- Frontend provides protected `/crm/clients`, `/crm/deals`, and `/crm/pipeline`, including actual API-backed CRM flows and role-aware Pipeline Kanban with drag/drop plus accessible Move fallback. Client status remains readonly; DELETE/search are absent.
- Authentication dependencies: argon2-cffi 25.1.0 and PyJWT 2.13.0.
- Node.js 24.20.0 LTS; npm 11.19.0; React/React DOM 19.2.8; Vite 8.2.2; `@vitejs/plugin-react` 6.1.1; i18next 26.4.0; react-i18next 17.0.12.
- Frontend languages `ru`/`en`/`es`; Russian default/fallback; localStorage persistence; synchronized `<html lang>`.
- Restricted development CORS and frontend-to-backend `/health` connectivity verified.
- Backend pytest, frontend build, npm audit and browser runtime checks passed; npm audit reported 0 vulnerabilities.
- Development/demo seed strategy remains production-restricted; separate explicit system bootstraps install the seven required stages and the minimal fixed-UUID `Другое`/`Общий запрос` business catalog.
- Employee management, end-to-end authentication, CRM Core, Communications/Tasks/Dashboard, D4.1–D4.7, D5.1 Integration Foundation, D5.2 Gmail and D5.3 Telegram are verified. Redis is used as the Celery broker/result backend and for fail-open ephemeral manual AI launch counters, never authentication or persistent settings. D4.7 passed its complete 237-test PostgreSQL regression, Alembic/static checks, frontend build, runtime health, Redis limiter API boundary, and controlled two-call real OpenAI provider/Celery smoke. Chromium confirmed public-form validation/submission, unauthenticated protection, and authenticated ADMIN/MANAGER login/logout, Day 4 UI, ownership and settings denial through temporary synthetic users that were fully removed afterward. D5.3 passed the 264-test PostgreSQL regression, Alembic/static checks, frontend build/locales and integrations-queue registration, then completed live Bot connection, webhook, inbound/manual/automatic matching and outbound provider verification. The earlier controlled valid-webhook/separate-worker fake-provider smoke limitation is not a blocker after actual live verification. Google Calendar and WhatsApp remain unimplemented.

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
- The minimum D4.2 Category/Service foundation is installed by explicit idempotent `python -m backend.app.scripts.bootstrap_business_catalog`; it is required system data and does not invent a larger production catalog.
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
- D3.1 persistence uses `communication_channel`, `communication_direction`, `communication_status`, and `task_status` PostgreSQL enums. Foreign keys use restrictive default behavior; no cascade, trigger, role duplication, or denormalization was introduced. Task responsible-user active/role checks remain future Task service-layer rules.
- D3.2 Communications API is append-only: authenticated ADMIN/MANAGER may list/read all history; ADMIN may create for any consistent Client/Deal and MANAGER may create a client-level record for any Client or a Deal-linked record only on their responsible Deal. The service assigns `RECORDED`, validates Client/Deal consistency, orders lists by `occurred_at DESC, id DESC`, and exposes no PATCH/PUT/DELETE.
- D3.3 renders Communication history only inside existing Client edit and Deal detail contexts. It consumes the bounded D3.2 list filters, preserves backend newest-first order, posts only the create contract fields, refetches after create, and converts local date/time form input to UTC ISO. There is no standalone Communications route or navigation entry.
- D3.4 Tasks API supports authenticated create/list/get/PATCH/explicit completion with `due_at ASC, id ASC` ordering and bounded responsibility/client/deal/status filters. ADMIN may assign or reassign any active ADMIN/MANAGER. MANAGER reads all Tasks, creates only self-assigned Tasks, and updates/completes only own Tasks without reassignment. Task associations validate Client/Deal consistency but intentionally do not enforce Communications Deal ownership. `OVERDUE` remains derived and is neither persisted nor returned.
- D3.5 adds `/crm/tasks` to the existing protected CRM shell. It consumes the D3.4 API without client-side resorting, uses active employee references for ADMIN assignment, derives overdue only for `OPEN` tasks, sends timezone-aware timestamps, and sends explicit `null` for cleared optional description/Client/Deal fields. MANAGER sees all Tasks and Deals but gets only self-assignment/create and own-task mutation controls; backend remains authoritative.
- D3.6 uses `/crm` as the bounded operational home screen. It requests the first five OPEN Tasks in backend due-date order and the first five recent Communications in backend newest-first order, loading sections independently. Global counts, Pipeline counts, aggregation/page crawling, charts, analytics and `/dashboard/summary` were explicitly excluded; the Dashboard is not Day 6 Reporting.

## LAST CODEX RESULT
Task: D5.3 Telegram Final Live Closure.
Result: DONE / LIVE PROVIDER VERIFIED. Local canonical evidence remains `264 passed in 69.96s` with Alembic head `20260907_0014`, frontend build/locales and infrastructure checks; live evidence then verified Bot connection, HTTPS webhook inbound handling, manual/automatic stable-identity matching and one provider-confirmed outbound `SENT` Communication.
Files created: `history/ANSWER_98.md`.
Dependencies: None.
Tests/checks: canonical PostgreSQL suite, Alembic upgrade/current/check, frontend build, RU/EN/ES locale validation, Celery task registration/routing, health, automated Telegram-focused tests, live inbound/manual/automatic/outbound evidence and `git diff --check` passed.
Known issues/blockers: no D5.3 blocker. Deliberate live provider redelivery/replay was not performed; PostgreSQL-backed automated idempotency evidence remains authoritative.
Next recommended step: D5.4 Google Calendar; do not start it automatically.

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
