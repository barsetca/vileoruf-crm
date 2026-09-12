# Day 7 — QA / Delivery Contract

## Purpose and status

Day 7 adds no business feature. Its purpose is release QA, reproducibility, clean-start verification, final delivery artifacts, repository readiness, and honest MVP closure.

Status after D7.0: **Day 7 — QA / Delivery: IN PROGRESS**; **D7.0 — APPROVED / CLOSED**. MVP is not yet complete or ready for delivery.

## Minimal sequence

1. **D7.0 — QA / Delivery Contract + Release Readiness Audit.** Documentation/readiness only.
2. **D7.1 — Isolated Clean-start + Representative Release Acceptance.** In a new isolated environment/fresh database, prove repository/configuration → migrations at head → required system bootstrap → first ADMIN bootstrap → services start → a small representative browser/API business flow.
3. **D7.2 — Delivery Package.** Finalize README, final technical specification `.docx`, screenshots/screencast preparation, and public GitHub repository readiness. Separate repository-owner manual actions from repository-preparable artifacts.
4. **D7.3 — Final Release Gate + Documentation Closure.** Run one final proportional regression/release gate and close MVP.

No additional large phase is introduced unless a concrete need is found.

## D7.1 isolation and representative acceptance

Clean-start must never destroy or clear the existing working development database/runtime. It uses a separate fresh environment, database, or another repository-supported safe isolation method; `docker compose down -v` against the active environment is not an acceptable clean-start procedure.

The bounded representative E2E flow will be selected in D7.1 after inspecting existing harness patterns. It will cover public request, employee login, Client/Deal existence, a Deal/Pipeline action, Task or Communication, Analytics reflection of business data, and ADMIN/MANAGER authorization sanity. It must not invoke real AI or provider operations without a separately justified need.

## Evidence to reuse proportionally

Unless the affected product area changes, Day 7 does not repeat the D6.3 full RU/EN/ES `16 × 3` browser matrix, D6.4 full responsive matrix, or D6.5 loading/empty/error matrix. It also does not replay real OpenAI, Gmail, Telegram, Google Calendar create/update/cancel, or already-proven Day 5 replay/idempotency live operations.

The verified baseline is Day 1–4 COMPLETE; Day 5 COMPLETE WITH DEFERRED TECHNICAL DEBT; Day 6 COMPLETE; canonical PostgreSQL regression `291 passed`; Alembic head `20260909_0016`; production frontend build/runtime health; ADMIN/MANAGER smoke; D6.3/D6.4/D6.5 browser evidence.

## Delivery and final gate

Required delivery artifacts from `REQUIREMENTS.md` are a final technical specification `.docx`, public GitHub repository readiness, final `README.md`, screenshots, and screencast. D7.2 records what is created/prepared in the repository and what requires a project-owner manual action.

D7.3 expects canonical full PostgreSQL regression; Alembic head/current/check; frontend production build; relevant static/import/locale checks; runtime health; final repository/diff/secret hygiene; delivery-artifact existence/readability; source-of-truth consistency; and retention of deferred debt. A full browser matrix is not repeated if D7.1 does not change product UI.

## Deferred debt and invariants

The following remain non-blocking post-MVP debt: expandable deterministic Commercial Value breakdown; enhanced MANAGER AI ownership state; and WhatsApp Business Cloud API. WhatsApp is **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ**, not cancelled; its approved Business Platform / Cloud API architecture remains mandatory, and consumer/personal workarounds remain forbidden.
