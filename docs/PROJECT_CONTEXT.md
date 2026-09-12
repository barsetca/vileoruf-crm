# VILEORUF CRM — Project Context

## Project
Full-stack CRM with AI sales automation for VILEORUF Studio.

## Current phase
Day 1 Foundation, Day 2 CRM Core and Day 3 (D3.0–D3.8) are complete. D4.0–D4.7 are complete. D4.8's initial Codex verification was PARTIAL, but its remaining authenticated browser scenarios were subsequently verified manually by the project owner; no active D4.8 blocker remains. D4.9 is DONE: it corrected the public services-load/submit error semantics and the Business Settings `updated_at` PUT mismatch, then passed targeted and full PostgreSQL regression, Alembic/static/frontend checks, and public/ADMIN/MANAGER Chromium smoke with settings restoration. Day 4 is COMPLETE. D5.0 — Integrations Architecture/Product Contract remains APPROVED / ACTIVE in `docs/DAY5_INTEGRATIONS_CONTRACT.md`. D5.1 — Integration Foundation is DONE. D5.2 — Gmail is DONE / LIVE VERIFIED: D5.2a Google OAuth Connection + Encrypted Token Lifecycle, D5.2b Gmail Outbound Send and D5.2c Gmail Inbound are each DONE / LIVE VERIFIED. D5.2c accepted one controlled real inbound Gmail message through its bounded sync, exact-matched the one synthetic Client, created one incoming EMAIL Communication without a Deal, and kept both facts exactly one after repeat sync. D5.3 Telegram is DONE / LIVE PROVIDER VERIFIED: its actual Bot/HTTPS webhook path, inbound persistence, unmatched preservation, explicit manual linking, stable provider-identity automatic matching and one CRM/Celery/provider outbound `PENDING` to `SENT` lifecycle have been verified live. The earlier controlled synthetic-runtime limitation is no longer a D5.3 blocker; deliberate live redelivery/replay was not performed.

The verified application includes FastAPI, PostgreSQL/SQLAlchemy/Alembic, Docker Compose, Redis/Celery AI infrastructure, an internal OpenAI provider foundation, a React/Vite frontend with `ru`/`en`/`es`, employee authentication and ADMIN employee management. D4.5 provides async AI email proposals and employee-controlled EmailDraft CRUD without sending; D4.6 adds unified safe AI history, ADMIN runtime AI settings, and shared per-employee Redis limiting for manual AI launches. D5.1 adds the shared integration boundary: `IntegrationConnection`, `ExternalMessage`, `CalendarEvent`, EmailDraft `DRAFT`/`SENT` foundation with `SENT` immutability, adapter/error-retry boundaries, encrypted token-storage foundation, the logical `integrations` Celery queue, and the ADMIN-only `/crm/settings/integrations` page with four disconnected provider cards. D5.2a adds a single-corporate Google OAuth connection flow with persisted one-time state hash, encrypted token lifecycle/refresh and ADMIN Connect/Reconnect/Disconnect UI. `AIAnalysis`, `EmailDraft`, `ExternalMessage`, and `Communication` remain distinct records; `Task` remains distinct from `CalendarEvent`. AI disablement prevents new generation without hiding prior results.

D5.2a Google OAuth connection/token lifecycle and D5.2b explicit employee-controlled Gmail outbound delivery are live-provider verified for the configured corporate connection. One owner-controlled synthetic message followed the normal PENDING/integrations-queue/Gmail-adapter flow, received provider-confirmed success, persisted a safe provider message identifier, created exactly one outgoing EMAIL Communication and transitioned its draft to immutable/readable/copyable SENT. The later API error-semantics correction ensures ordinary SENT update/delete paths return safe 409 without changing content. D5.2c Gmail inbound synchronization is live-provider verified through a corrected-recipient controlled message and repeat deduplication. D5.3 Telegram is DONE / LIVE PROVIDER VERIFIED: PostgreSQL-backed automated tests cover webhook authenticity/idempotency, matching/linking and terminal lifecycle; live evidence covers Bot connection, real webhook receipt, manual and automatic stable-identity matching, plus one outbound provider-confirmed `SENT` Communication. D5.4 Google Calendar is DONE / LIVE VERIFIED, including one controlled provider-confirmed create, update and cancel lifecycle with historical CRM preservation. D5.5 WhatsApp Business Cloud API is **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ**, not cancelled: because the original 7-day implementation schedule has been exceeded, its approved implementation moves until after the current MVP. The approved Business Platform / Cloud API architecture, the ban on consumer/personal workarounds and reuse of the existing integration foundation remain mandatory when D5.5 resumes. D5.6 Unified Integration UX + Hardening is DONE / VERIFIED: Inbox remains protected/manual and Settings presents safe reconciled provider states, deferred WhatsApp and ADMIN-only route UX without exposing provider secrets.

Day 5 — Integrations is **COMPLETE WITH DEFERRED TECHNICAL DEBT** after D5.7 final verification. Gmail remains DONE / LIVE VERIFIED, Telegram DONE / LIVE PROVIDER VERIFIED, Google Calendar DONE / LIVE VERIFIED, and D5.6 DONE / VERIFIED. D5.5 WhatsApp is intentionally deferred until after the MVP, not cancelled; its approved Business Platform / Cloud API architecture remains governed by `docs/DAY5_INTEGRATIONS_CONTRACT.md`, and consumer/personal workarounds remain forbidden. D6.0 Analytics Architecture / Product Contract is APPROVED / CLOSED in `docs/DAY6_ANALYTICS_CONTRACT.md`; its bounded deterministic CRM-wide Analytics MVP is implemented and final-verified through D6.5.

D6.1 Analytics Backend is DONE / VERIFIED. Alembic `20260909_0016` adds nullable timezone-aware `Deal.first_won_at` without a historical backfill; the existing transition service sets it exactly once on the first successful transition to Won while preserving Client promotion. Authenticated ADMIN/MANAGER `GET /analytics/summary` returns CRM-wide deterministic PostgreSQL client/deal counts, active/won values, nullable zero-denominator conversion, persisted-stage breakdown and bounded monthly created/first-Won series. No AI, Celery/Redis or provider data is used by Analytics.

D6.2 Analytics UI is DONE / BROWSER VERIFIED: protected `/crm/analytics` consumes only `GET /analytics/summary`, adds navigation, localized KPI/stage breakdown, two dependency-free SVG monthly charts and keyboard/mouse accessible help. Controlled authenticated ADMIN/MANAGER browser verification confirmed CRM-wide equality, all KPI/help controls, charts, RU/EN/ES, desktop/tablet/mobile, loading/empty/error-retry and unchanged operational `/crm` Dashboard; no AI forecast, payment semantics, client-side business aggregation or backend contract change was introduced.

D6.3 CRM-wide i18n Audit is DONE / BROWSER VERIFIED. The complete 16-area route matrix passed in RU, EN and ES with isolated browser profiles, temporary authenticated ADMIN identities and controlled Client/Deal/Task/Communication/AI/Inbox fixtures. The runs verified document language and persisted locale selection where switched, localized date/number/currency/percent output, accessible labels and a safe localized Analytics failure state; cleanup residue and AI/provider operations were zero. The limited pluralization correction covers singular `1 day` / `1 día`.

D6.4 CRM-wide Responsive / UX Pass is DONE / BROWSER VERIFIED. A bounded Chromium harness covered all 16 MVP areas with long synthetic content and isolated temporary ADMIN data. Seven critical routes passed desktop/tablet/mobile, the remaining areas passed desktop/mobile, and selected long EN/ES layouts passed on mobile. Minimal frontend fixes address narrow navigation, global overflow, responsive settings/forms/modals, controlled table/Kanban scrolling and critical touch targets. Cleanup residue and provider operations were zero.

D6.5 Loading / Empty / Error States + Final Day 6 Verification is DONE / VERIFIED. Browser-local controlled API delay/empty/503 boundaries verified localized non-blocking loading, meaningful empty states, safe errors and Retry recovery, while mutation failures preserve entered data and never show false success. Synthetic persisted-style AI and integration lifecycles, final Analytics, RU/EN/ES switch, seven-route mobile regression, ADMIN smoke and MANAGER authorization smoke passed without provider operations. Canonical PostgreSQL regression passed all 291 tests; Alembic `20260909_0016`, Node 24 build, locale/static/import checks and PostgreSQL/Redis/backend/frontend/Celery health passed. Cleanup residue is zero. **Day 6 — Analytics / UX / i18n is COMPLETE. D7.0 is APPROVED / CLOSED; D7.1 and D7.2 are DONE / VERIFIED.** D7.1a established isolated clean-start/bootstrap/runtime health. D7.1b then passed the real RU browser acceptance flow in disposable `vileoruf-d71b`: public request → CUSTOMER Client/unassigned New Lead Deal with Service/Category → ADMIN CRM actions → Analytics state → MANAGER settings/mutation authorization boundary. AI History opened without launch; OpenAI/provider operations and fixture/profile residue were zero. Its project, volumes and override were removed; the existing development runtime remained healthy. D7.2 finalized the developer README, valid Office Open XML technical specification, bounded repository/secret hygiene audit, nine representative RU `1440×900` screenshots, safe owner-recordable screencast scenario and manifest. **D7.3 final release gate is DONE / VERIFIED:** PostgreSQL `291 passed in 88.84s`, Alembic `20260909_0016` current/head/check, backend compile/import, Node 24 production build, 594-key locale parity, runtime/Celery health, delivery artifact and final hygiene checks all pass. Browser matrices and live provider operations were correctly reused, not replayed; D7.3 AI/provider operations are zero. **Day 7 QA / Delivery is DONE / VERIFIED; MVP implementation and technical verification are complete, and MVP is TECHNICALLY READY FOR DELIVERY.** Public GitHub publication, final narrated screencast, license decision and commit/push remain manual owner actions.

P1.0 Public Request Personal Data Consent is DONE / VERIFIED as a bounded post-MVP privacy enhancement. The public form has one unchecked mandatory consent checkbox, links in a new tab to the owner-maintained Russian legal PDFs, and RU/EN/ES parity. Backend `POST /public/requests` requires only `personal_data_consent=true` as the consent fact and rejects missing/false consent or client-supplied version fields before creating any CRM records. Successful public requests persist nullable-safe Client metadata: consent fact, server timestamp, `PERSONAL_DATA_CONSENT_VERSION = "2026-09-10"`, and `PRIVACY_POLICY_VERSION = "2026-09-10"`; historical Clients remain valid. Migration `20260910_0017`, targeted PostgreSQL coverage, Node 24 production build, locale parity and isolated desktop/mobile Chromium smoke passed with zero fixture/profile residue and zero AI/provider operations. When an owner replaces either legal PDF, they must assign a new version, update the application constant and archive the prior revision. This bounded feature is not a claim of general Russian/GDPR compliance. **Day 7 remains DONE / VERIFIED and the core MVP remains TECHNICALLY READY FOR DELIVERY.**

P1.2 — Google Calendar Timezone Fix is **AUTOMATED VERIFIED / OWNER LIVE VERIFIED**. P1.2 correctly normalizes the actual worker payload with `ZoneInfo(event.timezone)`; P1.2a established that CRM sent `19:00+02:00` with `Europe/Madrid` and Google confirmed the same instant as `17:00Z` with event timezone `Europe/Madrid`. The owner then corrected the Google Calendar display timezone and confirmed the live event time. No CRM Calendar logic, schema, API or provider configuration was changed for that acceptance action.

P1.3 — Gmail Automatic Inbound Sync is **DONE / VERIFIED**. Owner live testing confirmed automatic Gmail transport/polling without pressing Sync Gmail. P1.3a found duplicate normalized Client-email ambiguity; P1.3b is **DONE / VERIFIED** and owner-live verified its narrow same-thread fallback when one persisted SENT Gmail history candidate identifies one Client/Deal. Celery Beat scheduling, 600-second Redis single-flight, five-minute checkpoint overlap, page size 25 and deduplication remain unchanged. **Gmail automatic inbound and auto-linking are CLOSED.** P1.3c established that the former Lead Scoring contract intentionally excluded Communication text. P1.3d is **DONE / VERIFIED (automated and synthetic runtime); owner live acceptance pending**: the approved contract now includes bounded newest-first Communications of the current Deal only as untrusted supplemental context for Service Fit, Lead Quality and Feasibility. Structured CRM facts remain authoritative, Commercial Value and the overall formula remain deterministic, and the frozen AI payload contains only launch-time bounded context plus safe count/truncation snapshot metadata. New current-Deal Communications stale only that Deal’s latest successful Lead Scoring result; other-Deal and other-Client Communications do not.

P1.5a.1 — **PublicRequest Immutable Snapshot — DONE / VERIFIED**. Every new successful public submission now atomically creates its existing new `Client` and new `Deal` plus an immutable `PublicRequest` historical snapshot of submitted contact/request values, selected Service ID and multilingual service-name snapshot, and server-authoritative consent evidence. There is no public snapshot API/UI and no AI/provider use. Existing Client reuse by email, duplicate remediation and DB-level Client-email uniqueness remain explicitly **not implemented** and belong only to a future P1.5b iteration.

P1.5b.1 — **Controlled Test Data Cleanup + Telegram Identity Re-home — DONE / VERIFIED**. The canonical development manual-test Client is `Иван Тестов` with its one current Deal. Owner-approved local-only cleanup removed obsolete synthetic/test business data and two cross-linked cancelled CalendarEvent history rows; no Google/provider operation occurred. Telegram stable provider identity plus eight ExternalMessages and eight client-level Communications were re-homed from the obsolete D5 synthetic Client to canonical Client without assigning a Deal. Canonical Gmail history, AI analyses and valid local Calendar history were retained. Client normalized-email DB uniqueness, public existing-Client reuse and ADMIN Delete Client/Deal remain explicitly unimplemented.

`ADMIN` has CRM-wide access. `MANAGER` sees all Clients and Deals, but may change business state only for Deals they own; backend enforcement is authoritative. The public `/` request creates a `CUSTOMER` Client and unassigned Deal in `New Lead`. It is not a customer portal and creates no customer account, password, JWT, or `User` role.

## Business context
VILEORUF Studio creates turnkey video content: scripting, professional editing from client materials or stock footage, AI-generated visuals/video, color correction, transitions, sound effects, music, text, and adaptation for social networks.

## Goal
Build a working CRM that automates the sales cycle and uses AI for lead scoring, deal prediction, next-best-action recommendations, and email draft generation.

## Delivery constraint
Target implementation period: 7 days. Development follows an MVP-first approach. The application must remain runnable after each major stage.

## Required stack
- Backend: Python 3.10 + FastAPI
- Frontend: JavaScript + React, built with Node.js 24 LTS and Vite
- Database: PostgreSQL 16
- ORM/migrations: SQLAlchemy + Alembic
- Background tasks: Celery with Redis for background AI operations
- AI provider foundation: official OpenAI Python SDK behind an internal provider abstraction
- Deployment foundation: Docker / Docker Compose
- Development assistant: Codex in Cursor

## Architectural additions
- Redis is implemented as the Celery broker/result backend for background AI operations only; it is not auth/session storage.
- Frontend i18n uses i18next/react-i18next.
- Architecture style: modular monolith.
- External channels are isolated behind integration adapters.
- Internal CRM users are VILEORUF Studio employees with `ADMIN` or `MANAGER` roles. Authentication uses short-lived access JWTs held only in React memory and stateless refresh JWTs in secure `HttpOnly` cookies.
- External customers are CRM `Client` records, not authenticated `User` accounts; the MVP has no customer portal.

## Product principles
1. Build a real working CRM, not only a UI prototype.
2. Do not expand scope without explicit approval.
3. Prefer simple maintainable solutions compatible with the 7-day deadline.
4. Keep AI calls isolated in an AI service layer.
5. Keep external APIs isolated in integration adapters.
6. Do not implement payment functionality unless requirements are explicitly changed.

## Brand / UI direction
The CRM uses a Modern Minimal Light UI, Apple-inspired direction:
- very light neutral background and white surfaces;
- VILEORUF electric/deep blue as a functional accent;
- graphite typography and neutral-gray secondary details;
- subtle borders/shadows and moderate radius;
- no metallic gradients, chrome, glow, 3D or glass effects;
- practical daily CRM readability and information density take priority over decoration.

## Internationalization
Required UI languages:
- Russian (`ru`) — default and fallback;
- English (`en`);
- Spanish (`es`).

All user-facing UI strings must be translatable. Dates, times, and numeric formats should be localized.

## Source of truth
When chat history conflicts with the current project documentation, stop and report the conflict. Do not silently choose one interpretation.

For Day 5 integration work, `docs/DAY5_INTEGRATIONS_CONTRACT.md` is the approved, active source of truth within that scope. It refines earlier general integration statements without overriding project-wide security, authorization, migration, i18n, or reporting rules.
# P1.5b.2 — Client/Deal archive lifecycle

Client and Deal use `archived_at` as an ADMIN-only soft-delete marker. Archive and restore retain all related history and never invoke providers. Operational lists use active Client and effective-active Deal semantics; historical communication and historical analytics are retained. Archived-list access and archive/restore mutations are ADMIN-only.
# P1.5b.3 — Canonical email identity

Client email identity is `email.strip().lower()` (empty values are absent). PostgreSQL enforces uniqueness across active and archived Clients. A repeated public request reuses the matching Client, preserves its profile, creates a new Deal and immutable PublicRequest snapshot, and reactivates an archived matching Client.
# P1.6 — Telegram unmatched Deal linking

**DONE / VERIFIED (AUTOMATED); OWNER LIVE ACCEPTANCE PENDING.** Inbox manual Telegram linking supports a Deal-first target: the server derives Client exclusively from the selected active Deal, retains provider-ID conflict and idempotency policy, creates a Deal-linked incoming Communication, and marks the latest successful Lead Scoring of that Deal stale through the existing invalidation path. Client-only linking remains available and does not invalidate an arbitrary Deal. Focused PostgreSQL/API and Telegram-regression tests passed (15), as did a RU isolated-profile ADMIN browser flow for Deal-first, Client-only and controlled identity-conflict behavior. Synthetic residue and all provider operations were zero.

# P1.7 — Incoming Communication Workflow

Incoming Communication has nullable UTC `read_at`: `NULL` is unread and only an explicit employee action sets it. Migration `20260911_0021` marks pre-existing incoming history read at its historical `occurred_at`, so deployment does not create a false unread queue; new matched Gmail/Telegram and manually linked inbound communications remain unread. Inbox remains the authoritative queue only for unmatched inbound ExternalMessage records. Incoming Communication can be assigned only to an active Deal of its existing Client or detached without changing Client identity; linked ExternalMessage mirrors the Deal link and existing AI invalidation hooks are used for both changes. Dashboard exposes separate unread-known-client and unmatched Email/Telegram views. Inbox filtering is channel-based and local bulk deletion is ADMIN-only after a locked re-check that every target remains unmatched; providers are never called.

# P1.7a — Unmatched Sender Context

Gmail unmatched facts already expose persisted sender email (`sender_identifier`) and optional subject. Telegram unmatched facts now persist optional display-only `sender_username`, `sender_first_name` and `sender_last_name` through migration `20260911_0022`; provider user ID remains internal authoritative identity and display metadata never participates in matching. Historical rows may have null display fields and UI uses a neutral Telegram-sender fallback.
