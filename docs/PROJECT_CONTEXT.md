# VILEORUF CRM — Project Context

## Project
Full-stack CRM with AI sales automation for VILEORUF Studio.

## Current phase
Day 1 Foundation, Day 2 CRM Core and Day 3 (D3.0–D3.8) are complete. D4.0–D4.7 are complete. D4.8's initial Codex verification was PARTIAL, but its remaining authenticated browser scenarios were subsequently verified manually by the project owner; no active D4.8 blocker remains. D4.9 is DONE: it corrected the public services-load/submit error semantics and the Business Settings `updated_at` PUT mismatch, then passed targeted and full PostgreSQL regression, Alembic/static/frontend checks, and public/ADMIN/MANAGER Chromium smoke with settings restoration. Day 4 is COMPLETE. D5.0 — Integrations Architecture/Product Contract remains APPROVED / ACTIVE in `docs/DAY5_INTEGRATIONS_CONTRACT.md`. D5.1 — Integration Foundation is DONE. D5.2 — Gmail is DONE / LIVE VERIFIED: D5.2a Google OAuth Connection + Encrypted Token Lifecycle, D5.2b Gmail Outbound Send and D5.2c Gmail Inbound are each DONE / LIVE VERIFIED. D5.2c accepted one controlled real inbound Gmail message through its bounded sync, exact-matched the one synthetic Client, created one incoming EMAIL Communication without a Deal, and kept both facts exactly one after repeat sync. D5.3 Telegram is DONE / LIVE PROVIDER VERIFIED: its actual Bot/HTTPS webhook path, inbound persistence, unmatched preservation, explicit manual linking, stable provider-identity automatic matching and one CRM/Celery/provider outbound `PENDING` to `SENT` lifecycle have been verified live. The earlier controlled synthetic-runtime limitation is no longer a D5.3 blocker; deliberate live redelivery/replay was not performed.

The verified application includes FastAPI, PostgreSQL/SQLAlchemy/Alembic, Docker Compose, Redis/Celery AI infrastructure, an internal OpenAI provider foundation, a React/Vite frontend with `ru`/`en`/`es`, employee authentication and ADMIN employee management. D4.5 provides async AI email proposals and employee-controlled EmailDraft CRUD without sending; D4.6 adds unified safe AI history, ADMIN runtime AI settings, and shared per-employee Redis limiting for manual AI launches. D5.1 adds the shared integration boundary: `IntegrationConnection`, `ExternalMessage`, `CalendarEvent`, EmailDraft `DRAFT`/`SENT` foundation with `SENT` immutability, adapter/error-retry boundaries, encrypted token-storage foundation, the logical `integrations` Celery queue, and the ADMIN-only `/crm/settings/integrations` page with four disconnected provider cards. D5.2a adds a single-corporate Google OAuth connection flow with persisted one-time state hash, encrypted token lifecycle/refresh and ADMIN Connect/Reconnect/Disconnect UI. `AIAnalysis`, `EmailDraft`, `ExternalMessage`, and `Communication` remain distinct records; `Task` remains distinct from `CalendarEvent`. AI disablement prevents new generation without hiding prior results.

D5.2a Google OAuth connection/token lifecycle and D5.2b explicit employee-controlled Gmail outbound delivery are live-provider verified for the configured corporate connection. One owner-controlled synthetic message followed the normal PENDING/integrations-queue/Gmail-adapter flow, received provider-confirmed success, persisted a safe provider message identifier, created exactly one outgoing EMAIL Communication and transitioned its draft to immutable/readable/copyable SENT. The later API error-semantics correction ensures ordinary SENT update/delete paths return safe 409 without changing content. D5.2c Gmail inbound synchronization is live-provider verified through a corrected-recipient controlled message and repeat deduplication. D5.3 Telegram is DONE / LIVE PROVIDER VERIFIED: PostgreSQL-backed automated tests cover webhook authenticity/idempotency, matching/linking and terminal lifecycle; live evidence covers Bot connection, real webhook receipt, manual and automatic stable-identity matching, plus one outbound provider-confirmed `SENT` Communication. No deliberate live redelivery was needed. Google Calendar D5.4 and WhatsApp D5.5 remain not started.

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
