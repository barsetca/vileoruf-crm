# VILEORUF CRM — Project Context

## Project
Full-stack CRM with AI sales automation for VILEORUF Studio.

## Current phase
Day 1 foundation is complete. Day 2 CRM Core has not started.

The verified foundation currently includes a FastAPI health endpoint, PostgreSQL/SQLAlchemy/Alembic infrastructure, a Docker Compose PostgreSQL service, and a React/Vite technical frontend with mandatory `ru`/`en`/`es` localization.

CRM domain models, CRM workflows, authentication/authorization, Celery/Redis, OpenAI functionality and external integrations are not implemented yet.

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

## Product principles
1. Build a real working CRM, not only a UI prototype.
2. Do not expand scope without explicit approval.
3. Prefer simple maintainable solutions compatible with the 7-day deadline.
4. Keep AI calls isolated in an AI service layer.
5. Keep external APIs isolated in integration adapters.
6. Do not implement payment functionality unless requirements are explicitly changed.

## Brand / UI direction
The interface should visually relate to the VILEORUF Studio logo:
- dark graphite/black SaaS interface;
- electric/deep blue primary accent;
- light steel/metallic secondary accents;
- restrained glow/3D effects;
- readability and daily usability take priority over decorative effects.

## Internationalization
Required UI languages:
- Russian (`ru`) — default and fallback;
- English (`en`);
- Spanish (`es`).

All user-facing UI strings must be translatable. Dates, times, and numeric formats should be localized.

## Source of truth
When chat history conflicts with the current project documentation, stop and report the conflict. Do not silently choose one interpretation.
