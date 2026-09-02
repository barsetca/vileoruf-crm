# VILEORUF CRM — Project Context

## Project
Full-stack CRM with AI sales automation for VILEORUF Studio.

## Current phase
Day 1 Foundation, Day 2 CRM Core, and Day 3 (D3.0–D3.7) are complete, including Communications, Tasks, and the bounded Initial Operational Dashboard. The next planned step is Day 4 AI work.

The verified application includes FastAPI, PostgreSQL/SQLAlchemy/Alembic, Docker Compose, a React/Vite frontend with `ru`/`en`/`es`, employee authentication and ADMIN employee management. Day 2 adds Clients, Deals, database-backed PipelineStages, Deal ownership authorization, a dedicated stage transition, CUSTOMER-to-CLIENT promotion on a real transition to Won, protected Clients/Deals/Pipeline CRM pages, and the public request boundary.

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
- Background tasks (planned): Celery
- AI (planned): OpenAI
- Deployment foundation: Docker / Docker Compose
- Development assistant: Codex in Cursor

## Architectural additions
- Redis may be used as the Celery broker when background processing is implemented.
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
