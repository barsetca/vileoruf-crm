# VILEORUF CRM — Development Seed Strategy

## Purpose

Development seed data will provide deterministic test data for local development and demonstrations after the corresponding CRM domain models exist.

No seed executable or domain records are created during Day 1 because the CRM domain model has not been implemented yet.

## Rules

1. Seed execution must be explicit and limited to development/test environments.
2. The seed command must refuse to run in production.
3. Seed data must contain no real personal data, credentials, tokens or provider secrets.
4. Database schema changes remain in Alembic migrations; seed data remains outside migrations.
5. Seed execution must be repeatable and idempotent, using deterministic identifiers or stable lookup keys where appropriate.
6. Seed content must include only entities and fields approved by the current project requirements.
7. Seed implementation is added incrementally after the relevant models and migrations are verified.

## Verification criteria

When the seed mechanism is implemented, its task is complete only when:

- it runs against the development PostgreSQL database;
- repeated execution does not create unintended duplicates;
- created records are usable through the corresponding backend/frontend flow;
- automated checks cover the environment guard and repeatability;
- setup and cleanup instructions are documented.
