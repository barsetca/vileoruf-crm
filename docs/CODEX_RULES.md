# VILEORUF CRM — Codex Working Rules

## Purpose

These rules define the mandatory working discipline for Codex when modifying the VILEORUF CRM repository.

They are persistent project-wide instructions. Task-specific prompts should define only the scope, acceptance criteria, exclusions, and verification requirements that are unique to the current iteration.

Codex must not reinterpret, weaken, replace, or extend these rules on its own.

---

## 1. Source-of-truth hierarchy and required reading

Before every substantial implementation, refactoring, migration, integration, security, or documentation task, inspect the current repository and read:

1. `docs/PROJECT_CONTEXT.md`
2. `docs/REQUIREMENTS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DEVELOPMENT_STATUS.md`
5. `docs/CODEX_RULES.md`
6. every active task/domain contract explicitly applicable to the requested work.

Additional mandatory reading:

- read `docs/DEVELOPMENT_SEED_STRATEGY.md` before implementing or changing seed/bootstrap behavior;
- for every Day 5 integration task, read `docs/DAY5_INTEGRATIONS_CONTRACT.md` completely before changing code;
- when a later approved contract is introduced for another implementation phase, treat it as authoritative within its explicitly defined scope.

Use `docs/DEVELOPMENT_STATUS.md` and the existing repository to distinguish implemented functionality from planned functionality. Never assume that target architecture means implementation already exists.

### Conflict handling

If instructions conflict:

1. a current explicit task instruction may refine the task scope, but Codex must not silently treat it as permission to rewrite project-wide architecture or product contracts;
2. an applicable approved phase/domain contract takes precedence over older general statements within that contract's scope;
3. project-wide security, authorization, migration, i18n, privacy, and these Codex working rules remain in force unless an explicit approved decision says otherwise;
4. if a genuine conflict remains, stop before implementing the conflicting part, report it clearly, and request a decision rather than guessing.

Never silently choose one interpretation when source-of-truth documents disagree.

---

## 2. Scope discipline

Implement only the requested iteration.

Do not add adjacent features merely because they are useful, conventional, easy, or likely to be needed later.

Do not silently turn a bounded task into:
- a broader refactor;
- architecture cleanup;
- generalized framework/platform work;
- speculative future-proofing;
- unrelated bug fixing;
- additional product functionality.

Unless explicitly approved, do not introduce:
- payments/payment gateways;
- invoices/accounting;
- inventory;
- HR;
- ERP functionality;
- native mobile applications;
- microservices;
- customer portal/personal account;
- multi-tenancy;
- generic enterprise permission systems;
- generic integration platforms;
- other functionality excluded by the active project contracts.

If the requested work genuinely cannot be implemented safely without a scope or architecture change, report the required change before implementing it.

---

## 3. Preserve approved architecture

The project is a modular monolith.

Current architectural boundaries include:
- React frontend;
- FastAPI backend;
- PostgreSQL;
- SQLAlchemy + Alembic;
- Celery + Redis where asynchronous work is justified;
- Docker Compose;
- isolated AI service/provider boundary;
- isolated external integration adapters/services.

Do not substantially reorganize the repository, introduce microservices, add a second broker, replace core frameworks, or introduce major infrastructure without explicit approval.

Do not create abstractions merely for theoretical future flexibility. Prefer the smallest maintainable solution consistent with the approved architecture and current MVP.

External providers must be accessed through their approved adapter/service boundaries. Business logic must not be scattered into provider-specific route handlers or UI code.

AI provider calls must remain behind the AI service/provider boundary.

---

## 4. Inspect before modifying

Before writing code:

1. inspect the relevant existing implementation;
2. identify the current data model, service/API/UI boundaries, tests, migrations, and related documentation;
3. reuse established project patterns where they remain compatible with the current contract;
4. determine the smallest coherent change set;
5. identify whether schema, API, authorization, i18n, worker, provider, or documentation changes are actually required.

Do not replace working modules or components wholesale when a targeted safe modification is sufficient.

Do not remove or alter existing behavior outside the requested scope unless necessary to preserve correctness. If an unrelated defect is discovered, report it; do not automatically fix it unless it blocks the requested work or the prompt explicitly authorizes the fix.

---

## 5. Incremental implementation

For each task:

1. inspect;
2. implement the smallest approved scope;
3. add/update relevant automated coverage;
4. run the relevant verification;
5. fix regressions introduced by the task;
6. update source-of-truth documentation only when the verified implementation changes documented reality;
7. provide the required completion report.

Keep the project runnable after each substantial iteration.

Do not bundle future iterations into the current one.

---

## 6. Backend rules

- Keep route handlers thin.
- Put business rules and orchestration in services.
- Keep provider-specific behavior behind integration/provider boundaries.
- Use typed Pydantic schemas.
- Use SQLAlchemy consistently with established repository patterns.
- Use Alembic migrations for database schema changes.
- Never mutate production schema through ad-hoc startup SQL or seed logic.
- Preserve backend-authoritative authorization.
- Validate Client/Deal/User/Task/provider relationship invariants on the backend.
- Validate inputs and return intentional HTTP semantics.
- Do not expose stack traces, raw provider errors, secrets, internal prompts, or unsafe implementation details through APIs.
- Preserve existing historical records and lifecycle semantics unless the active contract explicitly changes them.
- Ordinary CRUD remains synchronous unless there is an approved reason for background processing.

When a schema change is required:
- create an Alembic migration;
- verify upgrade;
- verify current/head consistency;
- run `alembic check` where supported by the project workflow;
- do not rewrite or delete historical migrations merely to simplify the current change.

---

## 7. Authorization rules

Backend authorization is authoritative. Frontend hiding/disabling is UX only.

Every new protected endpoint or business operation must explicitly preserve the applicable ADMIN/MANAGER rules and ownership semantics from current project contracts.

Do not infer authorization from frontend visibility.

Do not weaken existing authorization because an operation is executed through:
- Celery;
- an integration adapter;
- a webhook;
- AI;
- a provider callback;
- an internal helper.

Background/provider finalization must preserve the authorization and business context established at the approved request boundary.

---

## 8. Frontend rules

- Reuse existing components and patterns where practical.
- Keep API access in the established service/client layer rather than scattering raw requests through components.
- Implement appropriate loading, pending, empty, success, and error states for user-facing flows.
- Do not present queued/accepted background work as completed provider/business success.
- Preserve role-aware UX without relying on it for security.
- Preserve responsive behavior.

### UI/brand contract

Maintain the existing Modern Minimal Light VILEORUF UI:
- very light neutral background;
- white surfaces;
- VILEORUF blue as a functional accent;
- graphite typography;
- restrained neutral-gray secondary details;
- subtle borders/shadows;
- moderate radius;
- practical CRM readability and information density.

Preserve the existing VILEORUF logo and established visual language.

Do not introduce dark theme, glassmorphism, metallic/chrome effects, glow, unnecessary gradients, 3D decoration, or visual effects that reduce usability unless explicitly requested.

---

## 9. Internationalization is mandatory

Supported UI languages:
- `ru` — default and fallback;
- `en`;
- `es`.

All new user-facing strings, states, validation messages, errors, labels, buttons, statuses, settings, and workflow messages must be translatable.

Do not hard-code user-facing strings in React components where translation keys belong.

Whenever a new user-facing string is introduced:
- add Russian;
- add English;
- add Spanish.

Preserve localized date/time/number behavior where applicable.

Language selection must continue to persist between sessions.

A feature with incomplete required RU/EN/ES user-facing localization is not complete.

---

## 10. AI rules

AI functionality must go through the approved AI service/provider abstraction.

Do not call the OpenAI SDK directly from route handlers, business modules, React components, or unrelated services.

Preserve the separation between deterministic CRM business logic and AI reasoning.

Prefer strict structured outputs with backend validation. Invalid AI output must not become a successful business result.

Never fabricate AI fallback scores/results when the provider fails.

AI recommendations are advisory unless an active contract explicitly approves an employee-triggered action.

AI-generated client-facing content must never be sent automatically. Sending requires the explicit approved employee action and the corresponding integration workflow.

Do not expose provider secrets, raw prompts, raw provider responses, or raw provider error bodies in normal API/UI/history output.

---

## 11. Integration rules

Use approved adapters/services for external providers, including:
- Gmail;
- Telegram;
- Google Calendar;
- WhatsApp.

For Day 5, `docs/DAY5_INTEGRATIONS_CONTRACT.md` is authoritative within the integration scope.

Persistent rules:
- never fake provider success;
- never create a successful CRM communication/provider state before the approved real provider confirmation;
- distinguish accepted/pending work from confirmed success;
- preserve provider idempotency/exactly-once business effects required by the active contract;
- do not blindly retry uncertain outbound provider outcomes;
- provider outages/configuration failures must degrade the integration rather than unrelated CRM functionality;
- disconnecting an integration must not erase historical CRM/provider records;
- provider secrets/tokens must never be exposed through frontend/API/logs/reports;
- do not convert the CRM into a full email client, messenger, calendar product, or generic integration platform unless explicitly approved.

If credentials, provider verification, public callback availability, account approval, or another external dependency prevents live verification:
- implement only the approved behavior that can be implemented honestly;
- report the concrete blocker;
- document required setup;
- mark the result as not live-verified rather than simulating success.

Mocks/fakes can verify application behavior but never prove live-provider verification.

---

## 12. Webhook and asynchronous-work rules

Webhook handlers must remain bounded and thin:
- validate authenticity using the approved provider mechanism;
- minimally validate payload shape;
- establish provider identity/idempotency;
- enqueue heavier work where appropriate;
- respond promptly.

An unverified callback must not create CRM business records.

Reuse the existing Celery + Redis infrastructure where asynchronous work is justified.

Do not add another broker or integration microservice.

Do not move ordinary CRUD to Celery without an explicit architectural reason.

Worker retries must follow the operation's approved safety/idempotency semantics.

---

## 13. Security, privacy, credentials, and configuration

Never commit or expose:
- passwords;
- API keys;
- OAuth client secrets;
- access/refresh tokens;
- Bot tokens;
- webhook secrets;
- encryption keys;
- JWT secrets;
- temporary credentials;
- other provider/account secrets.

Secrets belong only in environment/deployment-secret mechanisms or an explicitly approved encrypted persistence flow.

`.env.example` may contain only non-secret placeholders.

Do not commit `.env`.

Never print secrets to stdout/stderr or completion reports.

Temporary/generated credentials must never be:
- embedded in executable command text where failure/traceback can expose them;
- persisted in source;
- persisted in documentation/history reports;
- persisted in `.env`;
- placed in test assertions;
- returned in normal API/UI output.

Secret-bearing smoke/test harnesses must pass secrets out-of-band from executable text and sanitize failure output at their boundary.

Use synthetic/test data for development, demonstrations, and live-provider verification. Do not introduce real client personal data into fixtures or committed documentation.

Follow concrete privacy/GDPR requirements defined by project contracts. Do not invent compliance claims where acceptance criteria are not defined.

---

## 14. Seed/bootstrap rules

Before changing seed/bootstrap behavior, read `docs/DEVELOPMENT_SEED_STRATEGY.md`.

Preserve the distinction between:
- required system/bootstrap data;
- development/demo seed data;
- employee credential/bootstrap mechanisms.

Development/demo seed data:
- must be deterministic/idempotent where required;
- must use synthetic data;
- must not create production credentials;
- must refuse production execution where the current strategy requires it.

Database schema belongs in Alembic migrations, not seed scripts.

Do not use demo seed logic to bootstrap the first production ADMIN.

---

## 15. Dependencies

Before adding a dependency:
- first determine whether existing dependencies can safely satisfy the requirement;
- add only what the task actually requires;
- avoid framework/platform additions for speculative future use;
- report every dependency added or materially changed.

Any new major dependency, infrastructure component, external service, domain module, or significant repository restructuring requires explicit approval unless the current task/active contract already approves it.

---

## 16. Testing and verification

Verification must match the change.

Run all relevant available checks needed to support the completion claim. Depending on scope, this may include:
- focused unit/service tests;
- PostgreSQL-backed integration tests;
- full backend regression;
- API tests;
- authorization tests;
- idempotency/retry tests;
- Alembic upgrade/current/check;
- static/import checks;
- frontend production build;
- locale/i18n validation;
- Docker Compose/runtime health;
- Celery task registration/routing;
- authenticated browser smoke;
- public browser smoke;
- real provider verification when explicitly required and available.

Do not claim a test/check passed unless it was actually run successfully in the current task or there is an explicitly identified still-valid verification that the task did not affect. Prefer rerunning relevant checks after changes.

Do not convert:
- code inspection into `PASS`;
- mocks into live-provider verification;
- an HTTP request being accepted into provider success;
- a successful build into functional browser verification;
- automated tests into proof of real provider operation.

If a required verification cannot be run, state `NOT RUN` or `BLOCKED` and give the reason.

If a check fails because of a pre-existing unrelated issue, distinguish it clearly from regressions caused by the current task. Do not silently repair unrelated failures unless authorized or necessary to complete the task safely.

---

## 17. Live-provider verification

A provider integration may be described as `LIVE VERIFIED` only when the relevant operation actually traversed the real approved provider path and the required observable result was confirmed.

Do not expose real secret values or provider identifiers in the verification report.

Use controlled synthetic/test facts and clean up temporary test artifacts where practical.

If deliberate replay, redelivery, duplicate send, destructive action, or other provider-side side effect is unnecessary because the same invariant is already covered safely by automated tests, do not perform it merely to make the report look stronger. State exactly what was and was not live-tested.

Never invent provider evidence.

---

## 18. Documentation discipline

Documentation is part of the source of truth.

Update documentation only to reflect verified reality.

Do not mark planned work as implemented.

Do not mark an iteration `DONE`, `COMPLETE`, or `LIVE VERIFIED` merely because code exists.

When implementation status changes, update the applicable source-of-truth documents requested by the task or required by the active contract so they remain mutually consistent.

Do not silently rewrite approved product/architecture contracts during an implementation task. Contract changes require an explicit decision.

Do not place secrets, temporary credentials, provider IDs, private test identities, temporary public hostnames, or other sensitive runtime evidence in committed documentation.

Use exact, bounded wording:
- `DONE` only for completed and sufficiently verified implementation;
- `LIVE VERIFIED` only for actual live-provider verification;
- `IMPLEMENTED / NOT LIVE-VERIFIED` (or equivalent) when implementation exists but external verification remains blocked.

---

## 19. Git/change discipline

Prefer minimal, reviewable changes.

Do not:
- delete unrelated files;
- reformat the whole repository unnecessarily;
- rename/move large areas without approval;
- modify ignored/local user files unless the task requires it;
- commit secrets;
- rewrite Git history.

Inspect the final diff for unintended changes.

Run `git diff --check` for substantial implementation/documentation iterations where practical.

Do not create commits, push branches, open pull requests, or perform destructive Git operations unless explicitly requested.

---

## 20. Required completion report

After every substantial implementation task, provide the full report directly in Cursor chat and save the same substantive report in a new `history/ANSWER_XX.md` file.

A short summary is not sufficient.

Use this structure:

```text
TASK COMPLETED

1. Scope implemented
2. Summary of implementation
3. Files created
4. Files modified
5. Database/migrations changed
6. API endpoints added/changed
7. Authorization/security impact
8. Dependencies added/changed
9. i18n/UI impact
10. Tests/checks actually run and exact results
11. Runtime/browser/provider verification actually performed
12. Known issues, limitations, blockers, or checks not run
13. Deviations from applicable requirements/architecture/contracts
14. Documentation/status files updated
15. Recommended next step
```

If a section has no changes, explicitly say `None`.

The Cursor-chat report and `history/ANSWER_XX.md` must substantively match.

The report must distinguish:
- implementation from verification;
- automated verification from browser verification;
- mocked/fake provider verification from real-provider verification;
- `PASS` from `NOT RUN`/`BLOCKED`;
- current-task changes from pre-existing conditions.

Never include secrets or unsafe credential/provider evidence in the report.

---

## 21. Development status updates

When the task requires status closure, update `docs/DEVELOPMENT_STATUS.md` only after the relevant verification supports the new status.

Do not mark work complete based solely on:
- code presence;
- migration presence;
- tests that do not cover the claimed behavior;
- mocked provider behavior when live verification is required.

Preserve historically accurate limitations. If a later verification resolves an earlier blocker, record that the blocker is resolved rather than pretending it never existed.

---

## 22. Local history directory

`history/` is a temporary local technical directory used for full Codex completion reports.

It is:
- ignored by Git;
- not a delivery artifact;
- intended to preserve implementation-session reports during development.

Do not delete it during development without explicit instruction.

Before final project delivery it may be removed when explicitly requested.

---

## 23. Default behavior when the task prompt is short

A task prompt does not need to repeat these rules.

When a prompt says, for example:

> Follow `docs/CODEX_RULES.md` and all applicable source-of-truth documents.

Codex must apply this entire file automatically.

The task prompt remains authoritative for:
- the exact iteration being implemented;
- task-specific scope;
- explicit exclusions;
- task-specific acceptance criteria;
- task-specific verification/live-provider steps.

Do not interpret the absence of repeated global rules in a task prompt as permission to ignore them.

---

## 24. Final decision rule

When uncertain, prefer:
1. the approved source of truth;
2. the smallest safe change;
3. preservation of existing verified behavior;
4. explicit reporting instead of guessing;
5. honest verification status instead of optimistic claims.

Codex implements the approved task. Codex does not decide the project's product rules or architecture.
