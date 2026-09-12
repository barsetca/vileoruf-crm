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

D5.4a — Google Calendar OAuth Reuse + Adapter Foundation: DONE (local implementation; not live-provider verified). `GOOGLE_CALENDAR` remains a separate persisted one-corporate `IntegrationConnection`, with no token payload of its own. Its safe status is derived from the Gmail Google-token owner: persisted encrypted scopes must include `calendar.events`; a missing/insufficient scope produces only Calendar `ERROR/PERMISSION_DENIED` and leaves Gmail usable. Calendar token acquisition reuses the existing Google decrypt/refresh lifecycle, and Calendar transport-header preparation is isolated behind the integration adapter boundary. The ADMIN settings list persists/returns that safe derived Calendar state; existing ADMIN-only authorization remains unchanged. No migration, CalendarEvent operation, Calendar API call, worker change, or new UI string was introduced.

D5.4b — CalendarEvent Create + Google Calendar Provider Sync: DONE; the later controlled D5.4c.2 Client/Deal/Task browser flows live-verified the normal provider create lifecycle. Authenticated `POST /calendar-events` persists a single `PENDING` event and dispatches the existing integrations queue; worker success updates the same row to `SYNCED` with safe provider identity/link, while failure is normalized to `ERROR` without retrying uncertain creates. A narrowly scoped persisted Calendar idempotency key and migration `20260908_0015` prevent repeated accepted requests from producing another logical event.

D5.4c.1 — Contextual CalendarEvent Read + Presentation: DONE. D5.4c.1a backend verified a bounded authenticated `GET /calendar-events` requiring Client, Deal or Task context, explicit-combination validation, authoritative ADMIN/MANAGER Deal/Task authorization and deterministic `start_at DESC, id DESC` safe responses. D5.4c.1b — DONE / BROWSER VERIFIED: the reusable read-only section is connected in Client, Deal and Task contexts; RU/EN/ES presentation, lifecycle/content states, safe external-link condition, safe degraded error and ADMIN/MANAGER browser paths were verified using cleaned synthetic local data. D5.4 remains IN PROGRESS: Calendar create UI and update/cancel work are not included.

D5.4c.2a — Reusable Create Event Form + Frontend API Mutation Foundation: DONE. An unmounted reusable form provides explicit Client/Deal/Task props without relation inference, browser-IANA-timezone default, local required/range validation, local logical-submission idempotency-key reuse and asynchronous accepted/PENDING wording. Its service sends authenticated `POST /calendar-events` with `Idempotency-Key`; there is no page entry point, polling, update or cancel. D5.4c.2 remains PARTIAL pending separately approved entry-point integration; D5.4 remains IN PROGRESS.

D5.4c.2b — Client + Deal Create Event Entry Points: DONE / LIVE BROWSER VERIFIED. The reusable form is explicitly mounted from existing Client and authorized Deal contexts only, preserves client-only/deal-only payload semantics, closes/resets on `202 Accepted`, and triggers bounded contextual list refresh. Controlled real-provider verification completed exactly one Client and one Deal create, both later `SYNCED`; no update/cancel was added.

D5.4c.2c.1 — Task Create Event Entry Point + Reusable Bounded PENDING Polling: DONE. The authorized Task detail uses the same reusable form with only its persisted `taskId`, never inferring Client/Deal links; accepted creation closes/resets the form and refreshes the same bounded Task list. `CalendarEventsSection` now polls its existing bounded contextual GET only while its successfully loaded list contains `PENDING`, every 2.5 seconds for at most 6 attempts; it stops on terminal list, bound, unmount, context change or read error, while stale work is aborted. Client and Deal reuse the same lifecycle refresh. D5.4c.2 remains PARTIAL pending D5.4c.2c.2 final authenticated browser verification; D5.4 remains IN PROGRESS.

D5.4c.2c.2 — Controlled Task Live Browser + PENDING Polling Verification: DONE / LIVE BROWSER VERIFIED. One synthetic ADMIN Task without Client/Deal completed the real UI → `POST /calendar-events` → `202 Accepted` flow exactly once with an Idempotency-Key and task-only payload. The form closed, bounded Task refresh first observed `PENDING`, one same-context 2.5-second polling GET observed `SYNCED`, and no additional GET followed the terminal state. The Task remained `OPEN`, with unchanged due date, responsibility and absent Client/Deal links. D5.4c — DONE. D5.4c.2 — DONE. No update/cancel was added; D5.4 remains IN PROGRESS.

D5.4d.1 — CalendarEvent Update Backend + Provider Lifecycle: DONE / backend verified. Authenticated strict `PATCH /calendar-events/{event_id}` permits only desired title/description/start/end/timezone changes. It locks the same event, authorizes all existing contexts, requires `SYNCED` plus a stable provider event identity, applies desired values and transitions the row to `PENDING` before post-commit dispatch to `integrations.google_calendar.update`. The worker targets the same Google provider event with PATCH through the existing Gmail-owned OAuth/token boundary; success returns the same row to `SYNCED`, while confirmed and uncertain failures safely produce `ERROR` without blind resend. Context links, provider identity and Client/Deal/Task lifecycle remain unchanged. No migration, frontend update UI or cancel exists. Focused PostgreSQL/API/adapter/OAuth/read/create regression passed (`16 passed`). D5.4d.2 live provider update verification remains separately scoped; D5.4 remains IN PROGRESS.

D5.4d.2a — CalendarEvent Update UI Foundation + Frontend Verification: DONE / frontend implementation verified. The shared `CalendarEventsSection` shows localized Edit only for `SYNCED` events and mounts one reusable update form in Client, Deal and Task contexts. The form prepopulates title, description, start/end and the persisted event timezone, validates required values, IANA timezone and end-after-start, and submits only editable PATCH fields. On accepted update it closes/resets and refreshes the same bounded context, so the existing PENDING polling handles the provider lifecycle; safe localized 409 conflict feedback is shown. No live provider update or cancel was performed. D5.4d live provider update verification remains pending; D5.4 remains IN PROGRESS.

D5.4d.2b — Controlled Live Browser/Provider CalendarEvent Update Verification: PARTIAL / NOT LIVE VERIFIED. Runtime services, Google OAuth prerequisites and a standalone Chrome CDP harness passed health/compile/import checks. One browser-created synthetic Client CalendarEvent reached provider-confirmed `SYNCED` with persisted provider identity, but the harness failed to capture its create response reliably; no PATCH was sent. Consequently provider update, update polling and identity-after-update evidence remain unverified. No retry/replay or product-code change occurred. D5.4d remains pending; D5.4 remains IN PROGRESS.

D5.4d.2b-final — Stable Browser Selectors + Single Live CalendarEvent Update Verification: PARTIAL / LIVE UPDATE PENDING. Minimal non-visible `data-testid` selectors were added to the CalendarEvent card/Edit action and reusable update form/fields/submit; Node 24 production build passed. The existing synthetic event remained `SYNCED`, unchanged, with stable provider identity/context and one context row. The standalone harness passed compile/import but terminated before dispatching PATCH in both observed executions; backend, PostgreSQL and Celery confirmed zero update operations. No provider retry or cancel occurred. D5.4d remains IN PROGRESS; D5.4 remains IN PROGRESS.

D5.4d.2b-h2 — Deterministic Browser Harness Checkpoint Diagnosis: DONE / READY_TO_SUBMIT. The existing synthetic Client-only `SYNCED` event was opened through the authenticated browser with all stable update test ids. Checkpoints 01–21 passed: deterministic Edit/form fields, persisted prepopulation, preserved event timezone, no editable context relationships, locally modified valid unsaved form, and enabled Save were verified. Browser-local `datetime-local` values correctly reflected Europe/Madrid while persisted values remain UTC. No submit, PATCH, create, provider operation or cancel occurred; PostgreSQL state and worker logs remained unchanged. D5.4d.2b remains PARTIAL / LIVE UPDATE PENDING; D5.4d and D5.4 remain IN PROGRESS.

D5.4d.2b-live — Single Controlled Live CalendarEvent Update Verification: DONE / LIVE BROWSER + PROVIDER VERIFIED. One browser Save issued exactly one authenticated `PATCH /calendar-events/{id}` and received `202`, updating the same synthetic Client-only row to `PENDING`; no second PATCH occurred. The initially running worker was stale and discarded the update task before any provider call. After a worker restart loaded the already-defined task, the accepted PENDING job was delivered once: exactly one integrations-queue Google Calendar PATCH returned `200` and the same row reached `SYNCED`. Updated title/description persisted; start/end/timezone and Client-only context remained unchanged, provider identity remained present, `last_synced_at` advanced, and context row count stayed one. No provider create/delete, replacement, blind replay, or cancel occurred. D5.4d — DONE. D5.4 remains IN PROGRESS pending cancel.

D5.4e.1 — CalendarEvent Cancel Backend + Provider Lifecycle: DONE / backend verified. Authenticated `POST /calendar-events/{event_id}/cancel` accepts only an authorized `SYNCED` event with its persisted provider identity and synchronously targets that Google event through the existing Gmail-owned OAuth/token boundary. Only confirmed Google DELETE success marks the same CRM row `CANCELLED`; history, context links, provider identity and Client/Deal/Task state remain intact. Provider failure or uncertain network/5xx outcome leaves the row `SYNCED`, returns a safe `503`, and is not automatically retried. No cancel Celery task, route, schema/migration or frontend Cancel action was added. The service deliberately does not hold a PostgreSQL lock across the external call; post-call locking/revalidation prevents a second CRM finalization, but two truly concurrent requests can still both reach Google before the first finalizes because the approved model has no persistent operation state. D5.4e live/browser cancellation verification remains pending; D5.4 remains IN PROGRESS.

D5.4e.2 — CalendarEvent Cancel UI + Single Controlled Live Provider Verification: DONE / LIVE BROWSER + PROVIDER VERIFIED. `CalendarEventsSection` now provides localized explicit Cancel only for `SYNCED`, with a small in-place confirmation, one-submission disabling and safe failure/uncertain messaging; it refreshes the bounded current context only after the synchronous backend response. A retained synthetic Client-only event was cancelled once through the authenticated browser: exactly one bodyless `POST /calendar-events/{id}/cancel` returned `200`; the existing Google OAuth-backed adapter performed its one confirmed provider DELETE and the same historical row became `CANCELLED`. It remains visible through browser and authorized by-id/context reads, while Edit and Cancel are absent. PostgreSQL evidence preserved title/content/times/timezone, Client-only links, provider identity, one CalendarEvent row, nine Communications and Client `CUSTOMER`; no PENDING transition, cancel Celery task/message, replacement, retry or replay occurred. The temporary browser/admin fixture was cleaned up. D5.4e — DONE. D5.4 — DONE.

D5.5 — WhatsApp Business Cloud API: **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ**. Реализация намеренно перенесена до завершения текущего MVP, поскольку первоначальный 7-дневный срок уже превышен. WhatsApp не исключён из продукта: после MVP он остаётся необходимой интеграцией для реального использования CRM. Утверждённая архитектура `docs/DAY5_INTEGRATIONS_CONTRACT.md` сохраняется без изменений: только WhatsApp Business Platform / Cloud API, без consumer/personal workaround; при возврате должны быть переиспользованы `IntegrationConnection`, `ExternalMessage`, `Communication`, очередь `integrations` Celery/Redis, webhook boundary, Client matching/manual unmatched linking, idempotency, adapter/error boundaries и Integration Settings foundation. Существующая WhatsApp foundation не удаляется и не заменяется временным решением. D5.6 и D5.7 завершены; Day 5 — COMPLETE WITH DEFERRED TECHNICAL DEBT.

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
- [x] D5.4 Google Calendar — DONE / LIVE VERIFIED: OAuth reuse, CalendarEvent create/update/cancel lifecycle, contextual Client/Deal/Task presentation and entry points, bounded create/update polling, live provider update and one controlled live browser/provider cancellation are verified. Historical CRM events remain preserved; no full CRM calendar/import/recurrence scope was added.
- [ ] D5.5 WhatsApp Business Cloud API — ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ: реализация перенесена после текущего MVP из-за превышения первоначального 7-дневного графика; это не отмена продукта и не разрешение на consumer/personal workaround. D5.5 возвращается после завершения текущего MVP.
- [x] D5.6 Unified Integration UX + Hardening — DONE / VERIFIED: D5.6a Unified Unmatched Inbox, D5.6b Integration UX + Security Reconciliation и D5.6c Retry / Idempotency Hardening Regression завершены. Focused PostgreSQL regression подтверждает Gmail/Telegram/Calendar exactly-once, terminal-state и safe retry semantics; Day 5 не отмечен COMPLETE. Следующий этап — D5.7 Final Day 5 Regression / Runtime / Provider / Browser Verification + Documentation Closure.
- [x] D5.7 Final Day 5 Regression / Runtime / Provider / Browser Verification + Documentation Closure — DONE / VERIFIED: canonical full PostgreSQL regression, Alembic head/current/check, backend compile, Node 24 production build, RU/EN/ES JSON, runtime health, Celery `ai`/`integrations`, security audit and documentation closure passed. Historical Gmail/Telegram/Google Calendar live evidence remains valid; no new provider mutation was performed. **Day 5 — Integrations: COMPLETE WITH DEFERRED TECHNICAL DEBT.** D5.5 WhatsApp remains intentionally deferred until after MVP.

### Day 6 — Analytics / UX / i18n
- **Day 6 — Analytics / UX / i18n: COMPLETE.** Все D6.0–D6.5 gates фактически пройдены.
- [x] D6.0 Analytics Architecture / Product Contract — APPROVED / CLOSED: `docs/DAY6_ANALYTICS_CONTRACT.md` зафиксировал отдельный protected CRM-wide `/crm/analytics`, deterministic backend aggregation, KPI/formулы, persisted-stage breakdown, EUR semantics, two monthly charts, `first_won_at` lifecycle без false backfill, mandatory accessible help/i18n и non-goals. Контракт реализован и закрыт после прохождения финальных gates D6.5.
- [x] D6.1 Analytics Backend — DONE / VERIFIED: Alembic `20260909_0016` добавляет nullable timezone-aware `Deal.first_won_at` без historical backfill; existing dedicated transition устанавливает timestamp только при первом successful Won и сохраняет Client promotion. Authenticated ADMIN/MANAGER `GET /analytics/summary` возвращает CRM-wide PostgreSQL aggregation KPI, nullable zero-denominator conversion, persisted-stage breakdown и bounded monthly created/first-Won series. AI/Celery/Redis/provider data/frontend не используются. Focused PostgreSQL regression passed.
- [x] D6.2 Analytics UI — DONE / BROWSER VERIFIED: protected `/crm/analytics`, navigation, summary service, KPI/stage table, two dependency-free SVG charts, accessible click/focus/keyboard help, loading/empty/error/retry, RU/EN/ES and Analytics-only responsive CSS verified in a controlled authenticated browser harness. ADMIN and MANAGER receive identical CRM-wide browser-loaded summary; all 10 KPI and 13 info controls, both charts, desktop/tablet/mobile, locale formatting, controlled empty/error/retry/loading states and operational `/crm` Dashboard pass. Provider operations were not performed.
- [x] D6.3 CRM-wide i18n Audit — DONE / BROWSER VERIFIED: static audit and minimal i18n fixes are complete. D6.3a CRM-wide route matrices passed 16/16 in RU, EN and ES with isolated profiles, temporary authenticated ADMIN and controlled Client/Deal/Task/Communication/AI/Inbox fixtures; document language/persistence, localized formatting and accessible names, plus safe localized Analytics error state, are verified. Cleanup residue is zero and AI/provider operations are zero. The minimal effort-days plural correction supports `1 day` / `1 día`.
- [x] D6.4 CRM-wide Responsive / UX Pass — DONE / BROWSER VERIFIED: all 16 required MVP areas passed a bounded authenticated Chromium audit with synthetic long-content fixtures. Dashboard, Clients, Deals, Pipeline, Tasks, Analytics and Business Settings passed desktop `1440×900`, tablet `768×1000` and mobile `390×844`; other areas passed desktop and mobile. Minimal fixes remove Public/Dashboard/Business Settings/AI History/Inbox overflow, provide usable mobile navigation, preserve controlled table/Kanban scrolling and raise critical touch targets. EN/ES narrow checks passed, cleanup residue and provider operations are zero.
- [x] D6.5 Loading / Empty / Error States + Final Day 6 Verification — DONE / VERIFIED: bounded isolated Chromium verified representative localized loading, empty, safe read-error/retry, mutation-error, persisted-style AI and integration lifecycle states, final Analytics and seven-route mobile regression, ADMIN 13-area smoke, MANAGER CRM/Analytics access and Settings denial. Minimal UI fixes add AI History load text/retry, empty Pipeline-stage explanation, non-destructive Business Settings mutation failure, Email Draft empty/load-error and Calendar retry states. Canonical PostgreSQL regression passed `291 passed in 89.56s`; Alembic `20260909_0016` single-head/check, Node 24 build, 594-key locale parity/JSON, backend compile/import and runtime health passed. Synthetic and Chrome residue is zero; AI/provider operations are zero.
- [x] Complete translations — D6.3 CRM-wide i18n Audit browser gate passed in RU/EN/ES.
- [x] Responsive/UX pass — D6.4 passed CRM-wide browser verification.
- [x] Error/empty/loading states — D6.5 representative CRM-wide controlled states and recovery were browser verified.

### Day 7 — QA / delivery
- **Day 7 — QA / Delivery: DONE / VERIFIED.** MVP implementation и technical verification complete; MVP — **TECHNICALLY READY FOR DELIVERY**. Public GitHub publication и narrated screencast остаются manual owner actions.
- [x] D7.0 QA / Delivery Contract + Release Readiness Audit — APPROVED / CLOSED: создан `docs/DAY7_QA_DELIVERY_CONTRACT.md`; bounded documentation/repository audit исправил однозначные stale Day 5/6 operational statements и добавил safety note к destructive clean-start command. Product code/schema/config/tests не менялись; runtime/test/browser/provider checks намеренно не запускались.
- [x] D7.1a Isolated Clean-start / Bootstrap / Runtime Verification — DONE / VERIFIED: отдельный Compose project `vileoruf-d71a` с isolated network/volumes и temporary host ports поднял новую PostgreSQL через `initdb`, автоматически применил migrations `20260827_0001` → `20260909_0016`, затем прошёл `current`/`heads`/`check`. Required PipelineStage и business catalog bootstraps выполнены и повторены idempotently; штатный first-ADMIN CLI и one local login sanity passed. PostgreSQL/Redis/backend/frontend/Celery health и `ai`/`integrations` queues passed. Temporary project, volumes, synthetic ADMIN и override удалены; original `vileoruf-crm` runtime остался healthy. Product code/config/tests не менялись.
- [x] D7.1b Representative Browser Acceptance — DONE / BROWSER VERIFIED: disposable isolated `vileoruf-d71b` browser E2E (RU, 1440×900) passed public request → CUSTOMER Client/unassigned New Lead Deal with persisted Service/Category → ADMIN Client/Deal visibility → UI transition to Contact → UI Task create/complete → MANUAL Communication/timeline → Analytics `/analytics/summary` state → AI History route without launch → MANAGER CRM visibility, ADMIN-settings redirect and backend-authoritative `403` for foreign Deal transition. OpenAI/provider operations: 0; fixture/profile residue: 0; temporary project/volumes/override removed and original runtime remained healthy. Product code unchanged.
- [x] D7.1 Isolated Clean-start / Representative Acceptance — DONE / VERIFIED: D7.1a clean-start/bootstrap/runtime and D7.1b representative browser acceptance complete.
- [x] D7.2a Final README + Technical Specification + Repository Readiness — DONE / VERIFIED: final delivery-oriented `README.md` now documents the implemented MVP, current stack/architecture, D7.1a-proven fresh setup/bootstrap, configuration, verification and deferred scope. Valid Office Open XML `docs/VILEORUF_CRM_TECHNICAL_SPECIFICATION.docx` covers the implemented system in 21 concise sections and passed archive/XML/content validation. Bounded repository audit found no tracked secret/local credential artifact or machine-specific path; `.env`, caches, dependencies/build output and local `history/` remain ignored. Public-repository content has no identified secret/content blocker; owner review, staging/commit, license decision and GitHub push/publication remain manual. Product code/config/dependencies unchanged.
- [x] D7.2b Screenshots / Screencast Preparation — DONE / VERIFIED: nine representative RU desktop `1440×900` PNG delivery screenshots (`docs/delivery/screenshots/`) were captured through an isolated Chromium/CDP profile using presentation-safe temporary ADMIN/CRM/AI fixtures. Browser-only staging hid pre-existing local development records without changing product code or historical data. PNG header/dimensions/readability and visual sanity passed; fixture/profile residue is zero and AI/provider operations are zero. `docs/delivery/SCREENCAST_SCENARIO.md` provides a 3–5 minute owner-recordable safe flow; `docs/delivery/README.md` is the visual-artifact manifest. Existing DOCX received a LibreOffice PDF-render visual sanity check. Product code/config/dependencies unchanged.
- [x] D7.2 Delivery Package — DONE / VERIFIED: D7.2a README/specification/repository-readiness and D7.2b visual delivery materials are complete.
- [x] D7.3 Final Release Gate + Documentation Closure — DONE / VERIFIED: canonical PostgreSQL regression `291 passed in 88.84s`; Alembic current/heads/check confirmed one `20260909_0016` head with no pending upgrade operations; backend compile/import and RU/EN/ES 594-key parity passed; production Vite build passed in project-pinned Node 24 Compose image; PostgreSQL/Redis/backend/frontend/Celery health, `ai`/`integrations` queues and expected task registration passed. Delivery README/DOCX/9 PNG/scenario/manifest and safe repository hygiene passed. Existing D6/D7 browser and Day 4/5 live-provider evidence was reused, not replayed. D7.3 AI/provider operations: 0. WhatsApp remains **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ**. No product code/config/dependency change.

### Post-MVP privacy enhancement
- [x] P1.0 Public Request Personal Data Consent — DONE / VERIFIED: public RU/EN/ES form has one unchecked mandatory consent checkbox and new-tab links to immutable Russian legal PDFs. `POST /public/requests` accepts only `personal_data_consent=true`; absence, false and client-supplied document-version fields are rejected before Client/Deal creation. Successful public requests persist nullable-safe Client consent fact, backend timestamp, and authoritative `PERSONAL_DATA_CONSENT_VERSION` / `PRIVACY_POLICY_VERSION` both set to `2026-09-10`; historical Clients remain valid. Alembic `20260910_0017` is current/head/check. Targeted PostgreSQL tests (`23 passed`), Node 24 production build, locale parity and isolated Chromium desktop/mobile smoke passed; synthetic Client/Deal/Service/Category/profile residue and AI/provider operations are zero. Replacing either legal PDF requires a new version, an application-constant update and archival of the prior revision. P1.0 is not a general Russian/GDPR compliance program.
- [x] P1.2 Google Calendar Timezone Fix — AUTOMATED VERIFIED / OWNER LIVE VERIFIED: P1.1 diagnosed inconsistent provider-boundary serialization of stored UTC instants together with `Europe/Madrid`; P1.2 changed the shared create/update helper to `ZoneInfo` normalization and focused automated coverage passed. P1.2a excluded stale backend/worker code and established the payload `19:00+02:00` plus `Europe/Madrid`; Google returned the equivalent `17:00Z` plus event timezone `Europe/Madrid`. The owner then corrected Google Calendar display timezone and confirmed the live event time. No additional CRM Calendar code or provider-configuration change was made.
- [x] P1.3 Gmail Automatic Inbound Sync — DONE / VERIFIED: owner live testing confirmed periodic transport without pressing manual Sync Gmail. P1.3a diagnosed duplicate normalized Client-email ambiguity; P1.3b — DONE / VERIFIED / OWNER LIVE VERIFIED — preserves exact-email precedence and resolves only a uniquely evidenced same-connection/same-thread `GMAIL` `OUTGOING` `SENT` Client/Deal. **Gmail automatic inbound and auto-linking are CLOSED.** P1.3c diagnosed the former approved Lead Scoring boundary. P1.3d — **DONE / VERIFIED (automated and synthetic runtime); owner live acceptance pending** — changes that boundary: Lead Scoring now uses bounded newest-first current-Deal Communications (raw content plus channel/direction/timestamp) solely as untrusted supplemental evidence for Service Fit, Lead Quality and Feasibility. Structured fields win conflicts; Commercial Value and overall calculation remain deterministic. Launch freezes the bounded payload, snapshots retain only count/truncation metadata, and a new current-Deal Communication stales only that Deal’s latest successful Lead Scoring result.
- [x] P1.5a.1 PublicRequest Immutable Snapshot — DONE / VERIFIED: additive model/table `public_requests` and Alembic `20260910_0018` preserve every new successful public form submission as an immutable historical snapshot linked to its newly created Client and Deal. The snapshot records submitted contact/request fields, Service FK plus multilingual service-name snapshot, budget/deadline and server-authoritative consent evidence; no snapshot CRUD/public API/UI or AI/provider coupling was added. Public flow intentionally remains new Client + new Deal for every accepted request. Existing Client reuse by email, duplicate remediation and DB-level Client email uniqueness remain deferred exclusively to P1.5b. Focused PostgreSQL/public API tests passed (`10 passed`); migration current/head/check is clean.
- [x] P1.5b.1 Controlled Test Data Cleanup + Telegram Identity Re-home — DONE / VERIFIED: owner-approved one-transaction local development cleanup retained canonical manual-test Client `Иван Тестов`, its one current Deal, Gmail history, ten Deal AI analyses and valid local Calendar history. It re-homed the unique Telegram provider identity plus eight Telegram ExternalMessages and eight client-level Communications from obsolete D5 synthetic Client, preserving their content/status/timestamps/IDs and `deal_id=NULL`. Eight obsolete synthetic/test Clients, nine Deals and exclusively owned related artifacts were removed; exactly two owner-approved cross-linked `CANCELLED` CalendarEvent rows and one obsolete synthetic Client CalendarEvent were removed locally without Google/provider calls. Final DB has one Client/Deal, zero duplicate normalized-email groups, one remaining canonical CalendarEvent and zero PublicRequest rows. Authenticated Clients/Deals/detail reads and health passed; provider operations were zero. DB email uniqueness, public existing-Client reuse and ADMIN Delete Client/Deal remain unimplemented.

## KNOWN ISSUES / BLOCKERS
The project PostgreSQL container uses host port `55432` because ports `5432` and `5433` were already occupied. The intermittent CRM-wide tab-availability/screen-failure observation remains **OPEN / DEFERRED**: it was not reproduced during P1.3, has insufficient causal evidence, and is outside this bounded Gmail change.

## DEFERRED NON-BLOCKING UX BACKLOG
- Expandable deterministic Commercial Value breakdown remains deferred after D6.4: it is a new information-presentation feature rather than a responsive blocker and should have its own bounded product/UI scope.
- A role-aware foreign-Deal MANAGER AI state remains deferred after D6.4: it changes permission-state product messaging and requires a dedicated MANAGER behavior pass rather than a layout-only correction.
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
- Employee management, end-to-end authentication, CRM Core, Communications/Tasks/Dashboard, D4.1–D4.7, D5.1 Integration Foundation, D5.2 Gmail, D5.3 Telegram and D5.4 Google Calendar are verified. Redis is used as the Celery broker/result backend and for fail-open ephemeral manual AI launch counters, never authentication or persistent settings. D4.7 passed its complete 237-test PostgreSQL regression, Alembic/static checks, frontend build, runtime health, Redis limiter API boundary, and controlled two-call real OpenAI provider/Celery smoke. Chromium confirmed public-form validation/submission, unauthenticated protection, and authenticated ADMIN/MANAGER login/logout, Day 4 UI, ownership and settings denial through temporary synthetic users that were fully removed afterward. D5.3 passed the 264-test PostgreSQL regression, Alembic/static checks, frontend build/locales and integrations-queue registration, then completed live Bot connection, webhook, inbound/manual/automatic matching and outbound provider verification. The earlier controlled valid-webhook/separate-worker fake-provider smoke limitation is not a blocker after actual live verification. D5.5 WhatsApp is deferred technical debt after the current MVP, not removed from product scope; D5.6 is next.

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
Task: P1.3d Lead Scoring Communication Context Enhancement.
Result: IMPLEMENTED; verification is recorded in `history/ANSWER_160.md`. The approved Lead Scoring boundary now includes bounded newest-first current-Deal Communication context as untrusted supplemental evidence for Service Fit, Lead Quality and Feasibility. Structured CRM fields prevail; Commercial Value and the overall formula remain deterministic. The launch payload is frozen and snapshots hold only count/truncation metadata. A new linked current-Deal Communication invalidates the latest successful Lead Scoring only for that Deal. Owner live acceptance remains pending; no OpenAI/provider call is authorized by this iteration.

### D5.6a — Unified Unmatched Inbox

Result: DONE / VERIFIED. Защищённый `/crm/inbox` выводит ограниченную newest-first очередь только входящих `ExternalMessage` без Client и Communication, показывает безопасные provider/channel/sender/time/content поля и даёт MANAGER/ADMIN выбрать только существующего Client. Новый `GET /inbox/external-messages` нужен потому, что прежний Telegram endpoint выполнял лишь link одной записи, но не безопасный provider-neutral list; Telegram linking переиспользует существующие правила stable identity. Повторный link создаёт ровно одну `Communication(INCOMING)` и не создаёт Client или Deal. Миграция не требуется. PostgreSQL: 13 focused D5.6a + Telegram regression tests passed; Node 24 frontend build и RU/EN/ES JSON validation passed. Headless Chromium verified synthetic Telegram Inbox → existing Client → disappearance without reload → one normal Client timeline communication; fixtures removed. Provider operations were not performed. This checkpoint preceded D5.6b; D5.6 and D5.7 are now complete.

### D5.6b — Integration UX + Security Reconciliation

Result: DONE / VERIFIED. Settings UX теперь согласованно показывает безопасные connection/error/last-activity states Gmail, Telegram и Google Calendar; Calendar явно использует corporate Google connection. WhatsApp честно показан как `ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ`, без fake error или provider controls. Исправлен SPA role guard, чтобы MANAGER при client-side переходе не мог остаться на ADMIN settings route; backend ADMIN-only boundary не менялся и подтверждён. No schema/migration/provider workflow changes. PostgreSQL focused security/regression: 11 passed; Node 24 build, RU/EN/ES validation, diff check и authenticated ADMIN/MANAGER headless browser smoke passed. Browser также подтвердил Inbox и ordinary Clients route при безопасно unavailable Telegram context. Fixtures removed; provider operations were not performed. This checkpoint preceded D5.6c; D5.6 and D5.7 are now complete.

### D5.6c — Retry / Idempotency Hardening Regression

Result: DONE / VERIFIED. Production lifecycle code did not require a defect fix. New Celery routing/autoretry regression coverage and reused PostgreSQL lifecycle tests confirmed Gmail inbound/outbound, Telegram inbound/manual-link/outbound and Calendar create/update/cancel exactly-once and terminal-state semantics: `34 passed in 13.08s`. No provider operation, browser check, frontend change, schema change or migration occurred. D5.6 is DONE / VERIFIED; this checkpoint preceded completed D5.7.
Files modified: source-of-truth documentation only; no product code, configuration, schema, migration or test change.
Dependencies: None.
Tests/checks: documentation consistency search across affected source-of-truth documents and `git diff --check` passed; runtime/provider/browser checks intentionally not run for documentation-only work.
Known issues/blockers: none. The established WhatsApp Business Platform / Cloud API architecture remains future technical debt and must not be replaced by consumer/personal WhatsApp.
Next recommended step: D5.6 Unified Integration UX + Hardening; do not begin it automatically.

# P1.7 — Incoming Communication Workflow

Result: IMPLEMENTED / FOCUSED VERIFIED. Added persisted explicit incoming read state, safe historical-read migration semantics, protected read/assign/detach operations, Dashboard unread-known-client and unmatched counters, Inbox channel filtering, and ADMIN-only local unmatched bulk deletion. Matched messages are not put in Inbox; no provider call or automatic Deal inference was added. Focused PostgreSQL Inbox/Telegram regression passed: `16 passed in 9.72s`.

# P1.7a — Unmatched Sender Context

Result: DONE / VERIFIED (AUTOMATED); OWNER LIVE ACCEPTANCE PENDING. Dedicated Inbox-only Chromium smoke passed with isolated fixtures/profile and verified sender context, filters, linking controls and ADMIN bulk delete; cleanup and provider-operation counts were zero.

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
# P1.5b.2 — ADMIN Client / Deal Soft Delete (Archive + Restore)

Implementation is in progress: additive archive timestamps, ADMIN archive/restore APIs and active-query semantics are present. Final UI browser acceptance and owner acceptance remain pending.
# P1.5b.3 — Normalized Email Uniqueness + Public Existing-Client Reuse

Implemented and focused verified: normalized email uniqueness, authenticated manual conflict boundary and public existing-Client reuse/snapshot flow. Gmail duplicate-fixture tests require adaptation to the new database invariant; provider behavior was not changed.
# P1.6 — Telegram Unmatched Deal Linking

**DONE / VERIFIED (AUTOMATED); OWNER LIVE ACCEPTANCE PENDING.** Focused PostgreSQL/API acceptance and existing Telegram regression passed (`15 passed`): Deal Client is authoritative, Client-only behavior is retained, duplicate/conflicting Telegram provider identities reject atomically, repeated successful requests create one Communication, archived/foreign-manager targets reject, and Deal-linked communication stales only that Deal's latest successful Lead Scoring through the existing mechanism. RU isolated-profile ADMIN browser verification passed Deal-first, Client-only and controlled conflict flows with zero cleanup residue and zero provider operations. No automatic Deal inference or permanent thread-to-Deal routing was added.
