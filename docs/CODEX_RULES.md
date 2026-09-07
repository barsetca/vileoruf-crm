# VILEORUF CRM — Codex Working Rules

## Purpose
These rules define how Codex should work on the VILEORUF CRM repository.

## 1. Read project context first
Before any substantial implementation task, inspect:
1. `docs/PROJECT_CONTEXT.md`
2. `docs/REQUIREMENTS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DEVELOPMENT_STATUS.md`
5. this file

Treat them as the current project contract.

Read `docs/DEVELOPMENT_SEED_STRATEGY.md` before implementing or changing development seed behavior.

For every substantial Day 5 iteration, read `docs/DAY5_INTEGRATIONS_CONTRACT.md` completely before changing code. It is the approved Day 5 architecture/product contract.

## 2. Do not expand scope
Do not invent product features because they are common in other CRMs.

In particular, do not add without explicit instruction:
- payments/payment gateways;
- invoices/accounting;
- inventory;
- HR;
- ERP functionality;
- native mobile apps;
- microservices.

If a requested implementation appears to require a scope or architecture change, explain it before making the change.

## 3. Preserve architecture
The project is a modular monolith:
- React frontend;
- FastAPI backend;
- PostgreSQL;
- SQLAlchemy;
- Celery;
- Redis as proposed Celery broker;
- Docker Compose;
- isolated AI service;
- isolated integration adapters.

Do not substantially reorganize the repository or introduce major infrastructure/dependencies without approval.
Use `docs/DEVELOPMENT_STATUS.md` to distinguish implemented components from planned architecture; do not claim a planned component already exists.

## 4. Work incrementally
Do not attempt to implement the entire CRM in one uncontrolled change.

For each task:
1. inspect relevant existing code;
2. state/understand the smallest implementation scope;
3. implement it;
4. run relevant checks/tests;
5. fix errors introduced by the change;
6. report exactly what changed.

Keep the project runnable after each major task.

## 5. Do not overwrite working code unnecessarily
Prefer minimal targeted changes.
Do not replace whole modules/components when a smaller safe modification is sufficient.
Do not remove existing functionality unless explicitly requested or required to fix a confirmed problem.

## 6. Backend rules
- Keep route handlers thin.
- Put business logic in services.
- Keep database access organized through the agreed data layer/repositories where applicable.
- Use typed Pydantic schemas.
- Use SQLAlchemy consistently.
- Use migrations for schema changes.
- Validate inputs.
- Return appropriate HTTP status codes/errors.
- Never hard-code secrets.
- Temporary or generated credentials must never be printed, embedded in inline command arguments that could be rendered in a traceback, or persisted in source, docs, `.env`, reports, or test assertions. Secret-bearing smoke harnesses must pass secrets out-of-band from executable text and sanitize failures at their boundary.

## 7. Frontend rules
- Use reusable components.
- Keep API access in a service/client layer rather than scattered raw calls.
- Implement loading, error and empty states for user-facing flows.
- Maintain the Modern Minimal Light UI, Apple-inspired visual contract: light neutral background, white surfaces, VILEORUF blue functional accents, graphite text, subtle borders/shadows, moderate radius, and practical information density. Preserve the existing VILEORUF logo. Do not introduce dark theme, gradients, glassmorphism, metallic effects, or glow without a separate decision.
- Avoid decorative effects that harm usability.

## 8. Internationalization is mandatory
Supported languages:
- `ru` — default/fallback;
- `en`;
- `es`.

Do not hard-code user-facing strings in React components when they should be translation keys.

Whenever a new user-facing string is introduced:
- add the Russian translation;
- add the English translation;
- add the Spanish translation.

Language selection must persist between sessions.

## 9. AI rules
AI functionality must go through the AI service layer.
Do not scatter direct OpenAI calls across route handlers/components.

Required AI functions:
- lead scoring;
- deal prediction;
- next best action;
- email draft generation.

Prefer validated structured outputs.
AI-generated email content is a draft; do not automatically send it without explicit user action.

## 10. Integration rules
Use adapters/services for:
- Gmail;
- Telegram;
- WhatsApp;
- Calendar.

Do not fake successful integration behavior.
If credentials, verification or external provider limitations block live operation:
- implement what can be implemented honestly;
- report the blocker;
- document required setup.

## 11. Security/configuration
- Secrets only via environment variables or an appropriate secret mechanism.
- Maintain `.env.example` with non-secret placeholders.
- Do not commit API keys, passwords, tokens or OAuth secrets.
- Use test data for demonstration.
- Follow the project's privacy/GDPR requirements to the extent concretely specified and document unresolved acceptance criteria.

## 12. Dependencies
Before adding a new dependency:
- prefer existing project dependencies when suitable;
- add only dependencies justified by the task;
- report every dependency added.

Major infrastructure or framework changes require approval.

## 13. Tests and verification
After changes, run the relevant available checks. Depending on the task these may include:
- backend tests;
- frontend tests;
- lint/type/build checks;
- migrations;
- API health check;
- Docker Compose build/start.

Never claim a test passed if it was not run.

## 14. Required completion report
After every implementation task, provide:

```text
TASK COMPLETED

1. Summary
2. Files created
3. Files modified
4. Database/migrations changed
5. API endpoints added/changed
6. Dependencies added/changed
7. Tests/checks actually run and their results
8. Known issues or limitations
9. Any deviations from REQUIREMENTS.md or ARCHITECTURE.md
10. Recommended next step
```

If a section has no changes, explicitly say `None`.

For every future substantial implementation iteration, Codex must provide the full completion report directly in the Cursor chat and save the same full report in a new `history/ANSWER_XX.md` file. A short summary alone is insufficient: the chat and history report must substantively match and include all mandatory sections, tests/checks actually run, migrations, known issues, deviations, and the recommended next step.

## 15. Status update
When explicitly requested, update `docs/DEVELOPMENT_STATUS.md` to reflect verified work. Do not mark work DONE merely because code was written; mark it done only after the relevant verification has succeeded.

## 16. Conflict rule
If the current user/Codex instruction conflicts with project documentation:
- follow the newest explicit instruction when the conflict is clear;
- report the conflict;
- recommend updating the relevant project document so the repository remains the source of truth.

If the conflict is ambiguous, stop and ask rather than guessing.

## 17. Local history directory

`history/` is a temporary local technical directory used only for full Codex completion reports. It is ignored by Git, is not a delivery artifact, and will be removed before final delivery. Do not delete it during development without an explicit user instruction.
