# VILEORUF CRM — Development Seed Strategy

## Purpose

Development seed data will provide deterministic test data for local development and demonstrations after the corresponding CRM domain models exist.

Required system/bootstrap data is a separate category from demo/development seed data. System data needed for approved application behavior may be installed explicitly in development, test and production. Demo/development data remains forbidden in production.

The implemented `python -m backend.app.scripts.seed_demo` command installs exactly three fictitious Clients and five Deals with deterministic UUIDs. It is allowed only in `development` and `test`, is idempotent, creates no User/credentials, and is forbidden in `production`. `--clean` removes only those deterministic demo Deals/Clients, never real data or stages.

The implemented `python -m backend.app.scripts.bootstrap_business_catalog` command is required system/bootstrap data, not a production demo seed. It idempotently installs fixed-UUID records for the minimum agreed D4.2 foundation: Category `Другое / Other / Otro` with 50 EUR/person-hour and 8 person-hours, plus Service `Общий запрос / General request / Solicitud general`. It is explicit, may run in any valid environment, creates no Users/credentials, and detects conflicting records instead of silently duplicating or overwriting them. Studio-specific catalog expansion remains an ADMIN business-settings action.

## Rules

1. Demo/development seed execution must be explicit and limited to development/test environments.
2. Demo/development seed commands must refuse to run in production; explicit system/bootstrap commands may run in production when they create only required non-demo application data.
3. Seed data must contain no real personal data, credentials, tokens or provider secrets.
4. Database schema changes remain in Alembic migrations; seed data remains outside migrations.
5. Seed execution must be repeatable and idempotent, using deterministic identifiers or stable lookup keys where appropriate.
6. Seed content must include only entities and fields approved by the current project requirements.
7. Seed implementation is added incrementally after the relevant models and migrations are verified.
8. Development seed data must not be used to bootstrap the first production `ADMIN`; that requires the separately approved secure CLI/bootstrap mechanism.

## Verification criteria

When the seed mechanism is implemented, its task is complete only when:

- it runs against the development PostgreSQL database;
- repeated execution does not create unintended duplicates;
- created records are usable through the corresponding backend/frontend flow;
- automated checks cover the environment guard and repeatability;
- setup and cleanup instructions are documented.

Required business catalog bootstrap has no cleanup command because existing Deals may retain its historical foreign keys and physical deletion is outside the Category/Service contract.
