# VILEORUF CRM — Day 5 Integrations Architecture / Product Contract

## 1. Purpose and status

This document is the approved architecture/product contract for **Day 5 — Integrations**.

It defines the Day 5 scope before implementation and is intended to prevent provider-specific code, credential handling, background jobs, persistence, and UI from expanding beyond the agreed MVP.

Day 1 — Foundation, Day 2 — CRM Core, Day 3 — Communications/Tasks, and Day 4 — AI Automation are complete. Day 5 implementation has not started at the time this contract is created.

The required integration priority remains:

1. Gmail
2. Telegram
3. Google Calendar
4. WhatsApp

External credentials, provider verification, public webhook reachability, account approval, or provider policy may constrain live verification. The application must never fake successful live integration behavior.

---

## 2. Day 5 principles

1. Preserve the modular-monolith architecture.
2. External providers are accessed only through integration services/adapters.
3. Backend authorization remains authoritative.
4. Existing CRM history remains durable when an integration is disconnected or unavailable.
5. Provider failure must degrade the integration, not the CRM as a whole.
6. AI-generated content is never automatically sent to a client.
7. User-facing Day 5 UI is localized in Russian, English, and Spanish; Russian remains default/fallback.
8. Do not create a generic integration platform or multi-account subsystem for this MVP.
9. Reuse the existing Celery/Redis infrastructure where asynchronous provider work is justified; do not introduce another broker or integration microservice.
10. Do not claim a provider operation succeeded until the provider result is confirmed.

---

## 3. Approved corporate-account model

The MVP has exactly one corporate connection per integration type:

- one corporate Gmail account;
- one corporate Telegram Bot;
- one corporate Google Calendar;
- one corporate WhatsApp Business account through WhatsApp Business Platform / Cloud API.

Per-employee Gmail accounts, per-employee calendars, multiple bots, multiple WhatsApp accounts, tenant-level connection ownership, and generic multi-account connection management are outside Day 5.

Only `ADMIN` may connect, reconnect, disconnect, or manage integration configuration. `MANAGER` may use an already configured integration only where existing CRM authorization permits the underlying Client/Deal/Task operation.

---

## 4. Existing domain contracts that Day 5 must preserve

### 4.1 Communication remains CRM business history

`Communication` remains the normalized append-oriented CRM record of a communication fact.

Day 5 does **not** turn `Communication` into a provider transport entity.

It continues to represent:

- a Client;
- an optional Deal;
- channel;
- direction;
- actual content;
- actual communication timestamp;
- the existing CRM recording semantics.

Provider message IDs, provider lifecycle, retries, provider errors, synchronization state, and deduplication belong to the integration layer, not to the core `Communication` lifecycle.

The central rule is:

```text
Provider message != Communication
```

For live provider channels, `Communication` is created only after a real inbound message has been accepted and matched to CRM context, or after a real outbound operation has been confirmed successful by the provider.

### 4.2 Existing Communication authorization remains the baseline

- `ADMIN` may create/use communications for any valid Client/Deal context.
- `MANAGER` may create/use client-level communication for an existing Client and Deal-linked communication only for a Deal for which the manager is responsible.
- Backend Client/Deal consistency checks remain authoritative.

Day 5 must not weaken these rules merely because a provider adapter is involved.

### 4.3 Task remains an internal CRM task

`Task` remains an internal CRM work item with responsibility, due time, optional Client/Deal context, and `OPEN`/`COMPLETED` lifecycle.

A calendar event is a different business object.

Approved relationship:

```text
Task != CalendarEvent
Task <-> CalendarEvent (optional explicit link)
```

A user may explicitly create a calendar event from a Task. Completing a Task must not automatically delete/cancel its calendar event, and changing/cancelling a calendar event must not automatically complete the Task.

### 4.4 EmailDraft remains a working document until successful send

The existing Day 4 distinction remains:

```text
AIAnalysis = AI proposal/history
EmailDraft = employee-controlled working document
ExternalMessage = provider operation/lifecycle
Communication = actual CRM communication history
```

An AI-generated or manually created EmailDraft is never automatically sent.

After a confirmed successful Gmail send, the sent EmailDraft becomes historical and **read-only**. Its subject/body must remain copyable (for example Copy subject / Copy body / Copy all), but its historical sent content must not be editable. A new follow-up email requires a new draft.

If sending fails, the EmailDraft remains editable and unsent. An uncertain provider outcome must not be falsely marked `SENT`.

---

## 5. Integration boundaries by provider

## 5.1 Gmail

### Approved MVP behavior

- One corporate Gmail account connected through Google OAuth.
- Outbound email from CRM.
- Inbound synchronization of new relevant email.
- Exact Client matching by normalized email address.
- Deterministic Deal association for replies only where provider thread correlation makes the Deal unambiguous.
- Successful outbound email creates `Communication(channel=EMAIL, direction=OUTGOING)`.
- Matched inbound email creates `Communication(channel=EMAIL, direction=INCOMING)`.
- Existing EmailDraft is the primary employee-controlled draft workflow.

### Outbound flow

```text
EmailDraft(DRAFT)
      -> explicit Send action
      -> authorization/contact validation
      -> ExternalMessage(PENDING)
      -> Gmail adapter/background job
      -> provider confirms success
      -> ExternalMessage(SENT)
      -> Communication(EMAIL, OUTGOING)
      -> EmailDraft(SENT, read-only, copyable)
```

The `Communication` content is the text actually sent, not a later-edited copy.

### Inbound flow

```text
Gmail sync/provider event
      -> authenticity/provider validation where applicable
      -> provider-message deduplication
      -> ExternalMessage(RECEIVED)
      -> exact Client match by normalized email
      -> optional deterministic Deal match by known provider thread
      -> Communication(EMAIL, INCOMING)
```

If no Client can be safely matched, keep the `ExternalMessage` unmatched; do not create a Client automatically.

### Explicit Gmail non-goals

- full Gmail client;
- folder/label management;
- mailbox administration;
- import of the entire historical mailbox;
- AI guessing of Deal association from email text;
- automatic sending of AI drafts.

---

## 5.2 Telegram

### Approved MVP behavior

- One corporate Telegram Bot.
- Incoming client messages through the Bot integration.
- Outbound employee replies through the Bot API.
- Webhook-based inbound architecture.
- Telegram provider user ID is the preferred stable matching identifier after a Client has been linked; username is not treated as immutable identity.
- Matched inbound/outbound messages become `Communication` records only after the corresponding real provider event/success.

### Inbound flow

```text
Client -> Telegram Bot -> webhook
      -> Telegram adapter
      -> webhook authenticity validation
      -> deduplication
      -> ExternalMessage(RECEIVED)
      -> Client match
      -> Communication(TELEGRAM, INCOMING)
```

If Client matching is unavailable or ambiguous, the message remains unmatched for manual linking.

### Outbound flow

```text
CRM employee -> explicit Send
      -> authorization/contact validation
      -> ExternalMessage(PENDING)
      -> Telegram adapter/background job
      -> provider confirms success
      -> ExternalMessage(SENT)
      -> Communication(TELEGRAM, OUTGOING)
```

### Explicit Telegram non-goals

- employee personal Telegram accounts;
- Telegram groups/channels management;
- a full Telegram client inside CRM;
- automatic AI replies;
- automatic Client creation from arbitrary inbound Telegram users.

---

## 5.3 Google Calendar

### Approved MVP behavior

- One corporate Google Calendar connection through Google OAuth.
- A dedicated CRM `CalendarEvent` entity.
- Explicit creation of events from Client, Deal, or Task context.
- Create/update/cancel synchronization for CRM-created events.
- Store provider event identity and external Google Calendar URL when available.
- Display linked event state in the relevant CRM context.
- Allow opening the synchronized event in Google Calendar.

### Approved relationship model

A `CalendarEvent` may have optional links to:

- Client;
- Deal;
- Task.

Client/Deal consistency must remain backend-authoritative.

### Creation flow

```text
Client / Deal / Task
      -> explicit Create/Add to calendar
      -> CalendarEvent(PENDING)
      -> Google Calendar adapter/background job
      -> provider confirms success
      -> CalendarEvent(SYNCED)
      -> provider_event_id + external_url stored
```

Provider failure produces a safe error state without changing unrelated Task/Deal/Client lifecycle.

### Explicit Calendar non-goals

- replacing Google Calendar with a CRM calendar UI;
- `/crm/calendar` month/week/day calendar in Day 5;
- importing the user's complete calendar history;
- treating every Task as a calendar event;
- automatically completing Tasks from calendar state;
- complex recurrence workflows.

---

## 5.4 WhatsApp

### Target integration

WhatsApp Business Platform / Cloud API is the approved target. Consumer/personal WhatsApp automation is not part of the contract.

### Approved MVP behavior when provider configuration is available

- one corporate WhatsApp Business account;
- inbound messages through provider webhook;
- outbound employee messages through the approved adapter/API path;
- Client matching by normalized WhatsApp/phone identity where safe;
- matched successful messages become `Communication(WHATSAPP, ...)`;
- webhook/provider operations are deduplicated.

### External limitation rule

If Meta Business verification, credentials, phone configuration, templates/policies, public callback requirements, or other provider prerequisites prevent live operation, the implementation may complete the approved adapter/interface, persistence, validation, tests, and setup documentation but must report the provider as **not live-verified**. It must never display or document a fake successful live integration.

### Explicit WhatsApp non-goals

- consumer WhatsApp automation;
- multiple WhatsApp accounts;
- campaign/broadcast marketing subsystem;
- general template-management platform beyond any minimum strictly required for an approved provider operation;
- automatic AI replies.

---

## 6. Persistence model

Day 5 introduces a minimal integration persistence boundary. Exact SQLAlchemy naming may follow repository conventions, but the semantic contract below is fixed.

## 6.1 IntegrationConnection

Purpose: safe non-secret metadata and lifecycle for one corporate provider connection.

Minimum semantic fields:

```text
id
provider
status
display_name
external_account_id / safe external identifier (optional)
external_account_email / provider-safe display identifier (optional)
connected_at (optional)
last_success_at (optional)
last_error_at (optional)
last_error_code (optional)
created_at
updated_at
```

Provider values:

```text
GMAIL
TELEGRAM
GOOGLE_CALENDAR
WHATSAPP
```

Connection status values:

```text
DISCONNECTED
CONNECTING
CONNECTED
ERROR
```

The database must enforce the single-corporate-connection-per-provider MVP invariant.

`IntegrationConnection` must not expose plaintext credentials through normal API schemas.

## 6.2 ExternalMessage

Purpose: provider/integration lifecycle for Gmail, Telegram, and WhatsApp messages.

Minimum semantic fields:

```text
id
integration_connection_id
provider
provider_message_id (nullable until known for outbound)
provider_thread_id (optional)
client_id (optional)
deal_id (optional)
communication_id (optional)
direction
status
sender_identifier
recipient_identifier
subject (optional)
content
provider_created_at (optional)
received_at (optional)
sent_at (optional)
last_error_code (optional)
created_at
updated_at
```

Approved lifecycle status values:

```text
PENDING
SENT
RECEIVED
FAILED
UNKNOWN
```

`UNKNOWN` means the provider may have accepted an outbound operation but CRM cannot safely confirm the result. It must not be silently retried or represented as sent.

The implementation must provide a provider-scoped uniqueness/idempotency rule equivalent to preventing duplicate processing of the same provider message for the same connection.

Do not create separate GmailMessage, TelegramMessage, and WhatsAppMessage domain tables for the MVP.

## 6.3 CalendarEvent

Purpose: CRM representation and provider synchronization lifecycle for an explicitly created calendar event.

Minimum semantic fields:

```text
id
integration_connection_id
client_id (optional)
deal_id (optional)
task_id (optional)
provider_event_id (optional until synchronized)
title
description (optional)
start_at
end_at
timezone
status
external_url (optional)
last_synced_at (optional)
last_error_code (optional)
created_by_user_id
created_at
updated_at
```

Approved status values:

```text
PENDING
SYNCED
CANCELLED
ERROR
```

A provider cancellation must preserve the CRM historical record rather than physically deleting it.

## 6.4 EmailDraft send-state extension

Day 5 may minimally extend the existing `EmailDraft` persistence to distinguish at least:

```text
DRAFT
SENT
```

and to correlate a successfully sent draft to the resulting actual communication/provider operation as needed by the implementation.

A `SENT` EmailDraft is immutable as historical content but remains readable and copyable.

No Day 5 feature may rewrite a sent draft so that it no longer matches what was actually sent.

---

## 7. Idempotency and Communication creation rules

### 7.1 Global invariant

One external provider message/event must create at most one corresponding `ExternalMessage` and at most one resulting `Communication` for that provider fact.

Repeated webhook delivery, repeated Gmail synchronization, worker retry, browser retry, or duplicate provider callback must not duplicate CRM communication history.

### 7.2 Outbound

```text
explicit user action
      -> ExternalMessage(PENDING)
      -> provider operation
```

On confirmed success:

```text
ExternalMessage(SENT)
      -> create exactly one Communication(OUTGOING)
      -> link records
```

On confirmed failure:

```text
ExternalMessage(FAILED)
      -> no Communication
```

On uncertain outcome:

```text
ExternalMessage(UNKNOWN)
      -> no false SENT state
      -> no automatic duplicate resend
      -> no false Communication success record
```

### 7.3 Inbound

```text
provider event
      -> authenticity check
      -> deduplication
      -> ExternalMessage(RECEIVED)
      -> safe Client matching
```

If Client matching succeeds, create exactly one `Communication(INCOMING)`.

If matching does not succeed, preserve the unmatched `ExternalMessage` and do not create a fake Client or guess a Deal.

---

## 8. Client and Deal matching

### 8.1 Gmail

Client match: exact normalized email address.

Deal match for inbound email is allowed only when deterministic provider-thread correlation links the reply to an earlier Deal-associated outbound message. Otherwise use Client-level communication.

### 8.2 Telegram

Prefer stored provider Telegram user ID. Username may assist UI/setup but must not be treated as immutable provider identity.

### 8.3 WhatsApp

Use normalized approved WhatsApp/phone identity where safe.

### 8.4 Ambiguity

- zero matches -> unmatched inbox;
- one safe exact match -> Client-level processing;
- ambiguous/multiple matches -> unmatched inbox;
- do not use AI to guess Client or Deal from message content in Day 5.

For Telegram and WhatsApp inbound messages, do not automatically select a Deal merely because the Client has active Deals.

---

## 9. Unmatched integration inbox

Day 5 may add a protected route such as:

```text
/crm/inbox
```

Its purpose is **not** to become a complete unified messenger. It is primarily an operational queue for inbound `ExternalMessage` records that require manual Client association or attention.

Approved workflow:

```text
unmatched ExternalMessage
      -> employee selects an existing Client
      -> backend validates link
      -> optional Deal remains unset unless explicitly and validly selected
      -> create exactly one Communication(INCOMING)
```

Day 5 must not automatically create a Client from arbitrary inbound email, Telegram, or WhatsApp traffic.

---

## 10. User-facing messaging workflows

### 10.1 Deal EmailDraft

Existing Deal EmailDraft UI is extended with explicit provider send behavior.

Before send, show a clear confirmation containing at least the recipient and subject. The UI must not say “Sent” while the operation is merely queued/pending.

After success:

- draft shows `SENT`;
- content is read-only;
- Copy subject / Copy body / Copy all remain available;
- the actual `Communication` appears in the Deal/Client communication history.

### 10.2 Telegram and WhatsApp

Use the existing Client/Deal communication context rather than creating separate full messenger applications.

A live-channel send action must call the provider integration. The UI must not directly create a fake outgoing live-channel `Communication` before provider success.

`MANUAL` remains the way to record an external/offline communication fact manually where appropriate.

### 10.3 Integration availability

The UI must clearly distinguish:

- connected and usable;
- pending/connecting;
- disconnected/not configured;
- provider/configuration error.

Missing integration configuration must not crash or block ordinary CRM functionality.

---

## 11. Calendar user workflows

Approved entry points:

- Client context: Create event;
- Deal context: Create event;
- Task context: Add to calendar.

Minimum form semantics:

```text
title *
date/start *
end *
timezone
description (optional)
Client (contextual/optional)
Deal (contextual/optional)
Task (contextual/optional)
```

After synchronization, show the event state and an `Open in Google Calendar` action when an external URL exists.

A synchronized event may be updated or cancelled through the approved CRM flow. Cancellation preserves the CRM record.

---

## 12. Credentials, OAuth, encryption, and secrets

## 12.1 General rule

Secrets are never source code, ordinary business fields, logs, completion reports, test assertions, browser-visible API payloads, or committed documentation values.

`.env.example` may contain only non-secret placeholders.

### 12.2 Telegram / WhatsApp

For the MVP, static provider credentials such as Telegram Bot token and WhatsApp access/configuration secrets are environment/deployment-secret backed. `IntegrationConnection` stores only safe metadata/status.

### 12.3 Google OAuth

Gmail and Google Calendar use interactive OAuth for the single corporate Google account/calendar.

Approved model:

```text
Google OAuth client credentials -> environment/deployment secrets
OAuth callback -> access/refresh token payload
              -> application-level encryption
              -> ciphertext persisted in PostgreSQL
Encryption key -> environment/deployment secret only
```

The encryption key must never be stored alongside the encrypted token payload.

Plaintext OAuth tokens may exist only transiently in process memory as required for provider calls/refresh. They must never be returned to the frontend or written to logs/reports.

Day 5 must not introduce a general secret-management platform. Use a minimal justified encryption implementation and document any new dependency before/when it is added.

### 12.4 ADMIN-only connection management

Only ADMIN may:

- initiate Google OAuth connection;
- reconnect/disconnect Google;
- manage/activate Telegram integration configuration;
- manage/activate WhatsApp integration configuration;
- view integration connection health/settings.

MANAGER must receive backend denial for management endpoints even if frontend navigation is bypassed.

---

## 13. Integration Settings UI

Add an ADMIN-only route:

```text
/crm/settings/integrations
```

It presents four provider cards:

- Gmail;
- Telegram;
- Google Calendar;
- WhatsApp.

Each card may expose only safe metadata such as:

- connection status;
- safe account/bot/calendar display identifier;
- last successful activity;
- safe normalized error state;
- Connect/Reconnect/Disconnect actions where applicable.

Never provide a “show token/secret” UI.

All strings and states must be localized in `ru`, `en`, and `es`.

---

## 14. Webhook contract

A webhook is an inbound provider callback to the CRM integration boundary. Telegram and WhatsApp use webhook-based inbound architecture where provider capabilities/configuration allow it.

Webhook route handlers must remain thin:

1. validate provider authenticity using the provider-supported verification/signature/secret mechanism;
2. minimally validate payload shape;
3. apply/persist enough provider identity for idempotency;
4. enqueue or dispatch heavier processing when appropriate;
5. return an appropriate response promptly.

An unauthenticated/unverified provider callback must not create an `ExternalMessage`, `Communication`, Client, or other CRM business record.

Repeated valid webhook delivery must be safe and idempotent.

If local development cannot receive a provider-required public HTTPS webhook, this is an external/live-verification constraint to document. Do not silently change the approved production architecture to an unrelated polling design merely to claim a live pass.

---

## 15. Background processing

Reuse the existing Celery + Redis infrastructure.

Provider operations that should not block an HTTP request may use a dedicated logical queue, for example `integrations`, separate from the existing `ai` queue but within the same Celery/Redis deployment.

Approved asynchronous candidates include:

- outbound Gmail send;
- outbound Telegram send;
- outbound WhatsApp send;
- Google Calendar create/update/cancel synchronization;
- heavier inbound provider processing after fast webhook acceptance;
- bounded Gmail inbound synchronization where implemented.

Ordinary integration settings CRUD/status reads remain synchronous unless a provider operation itself requires background work.

The frontend must distinguish accepted/pending work from confirmed provider success.

---

## 16. Retry and failure semantics

Provider errors must be normalized behind safe application error categories rather than exposing raw provider bodies or credentials.

Representative safe categories include:

```text
AUTH_REQUIRED
INVALID_CONFIGURATION
PERMISSION_DENIED
INVALID_RECIPIENT
RATE_LIMITED
PROVIDER_UNAVAILABLE
PROVIDER_ERROR
```

The exact internal enum may be refined during implementation without exposing secrets.

### 16.1 Retry classes

**SAFE_RETRY**

Automatic retry is allowed only when the adapter can establish that retry will not cause an unsafe duplicate provider action. Use bounded retry with increasing backoff; Day 5 should not introduce unbounded retries.

**NO_RETRY**

Permanent/configuration failures such as invalid credentials, permission denial, or invalid recipient must not be blindly retried.

**UNCERTAIN**

If the provider may have accepted an outbound operation but CRM cannot safely confirm the result, mark the `ExternalMessage` `UNKNOWN`. Do not automatically resend.

### 16.2 User-visible semantics

Pending work: localized equivalent of `Sending...` / `Synchronizing...`.

Confirmed success: localized confirmed sent/synchronized state.

Confirmed failure: localized safe failure with a retry action only where the backend declares retry safe.

Unknown outcome: clearly state that the result could not be confirmed and must be checked before another send.

Do not show raw provider response bodies.

---

## 17. Disconnect and provider outage behavior

Disconnecting an integration stops future provider operations but must not delete historical data.

Preserve:

- existing `Communication` records;
- `ExternalMessage` history;
- `CalendarEvent` history;
- sent EmailDraft history.

A provider outage or invalid credential must not make Clients, Deals, Tasks, Pipeline, AI history, or other unrelated CRM areas unavailable.

Existing communication history remains readable when a provider is disconnected or degraded.

---

## 18. Testing strategy

A Day 5 subtask is not complete merely because provider-facing code exists.

### 18.1 Unit/service coverage

As applicable, cover:

- adapter boundary behavior;
- provider error normalization;
- retry classification;
- idempotency logic;
- Client matching;
- deterministic Deal thread correlation;
- authorization;
- state transitions;
- secret redaction/non-exposure.

### 18.2 PostgreSQL integration coverage

As applicable, verify:

- schema constraints and migrations;
- one connection per provider;
- provider-message uniqueness/deduplication;
- Client/Deal/Task relationship invariants;
- exactly-once Communication creation for a provider fact;
- unmatched inbound persistence/linking;
- sent EmailDraft immutability;
- historical preservation after disconnect/cancel.

### 18.3 API coverage

As applicable, verify:

- ADMIN/MANAGER authorization;
- integration settings protection;
- webhook authenticity rejection/acceptance boundaries;
- send/create/update/cancel endpoints;
- safe error responses;
- no secret-bearing response fields.

### 18.4 Frontend/browser verification

As applicable, verify:

- production build;
- RU/EN/ES keys/localized states;
- ADMIN integration settings access and MANAGER denial;
- pending/success/error UI semantics;
- EmailDraft send/read-only/copy behavior;
- unmatched inbox linking;
- CalendarEvent create/open/update/cancel flow;
- ordinary CRM remains usable with providers disconnected/unavailable.

Never claim a check passed unless it was actually run.

---

## 19. Live-provider verification gates

Mocks/fakes validate application behavior but do not prove a live provider integration.

### 19.1 Gmail live verification

When credentials/account access are available, target at least:

- real corporate Google OAuth connection;
- one real outbound test email;
- confirmed provider success -> exactly one outgoing Communication;
- one real inbound test email;
- repeat processing does not duplicate the inbound Communication.

### 19.2 Telegram live verification

When bot/public callback configuration is available, target at least:

- real Bot configuration;
- one real inbound message;
- one real outbound reply;
- confirmed Communication creation and deduplication.

If a public webhook endpoint is unavailable, report the live inbound verification blocker explicitly.

### 19.3 Google Calendar live verification

When Google OAuth is available, target at least:

- real OAuth connection;
- real test event creation;
- persisted provider event ID;
- usable external URL where provider supplies one;
- at least one real update/cancel verification.

### 19.4 WhatsApp live verification

Perform live verification only when valid Meta Business / Cloud API configuration is actually available.

If unavailable, the acceptable status is explicitly similar to:

```text
IMPLEMENTED / NOT LIVE-VERIFIED — external provider setup required
```

Do not mark it live-verified based only on mocks, adapter tests, or fabricated credentials.

All live tests must use synthetic/test data and must clean up temporary test data/provider artifacts where practical.

---

## 20. Explicit Day 5 non-goals

The following are outside the approved Day 5 MVP unless separately authorized:

- multi-account integration platform;
- per-employee Gmail/Calendar connections;
- full Gmail/email client;
- Gmail folder/label administration;
- full historical mailbox import;
- unified messenger containing all conversations;
- Telegram personal accounts, groups, or channel management;
- consumer WhatsApp automation;
- WhatsApp marketing/campaign/broadcast subsystem;
- broad WhatsApp template-management product;
- full Google Calendar import;
- CRM month/week/day calendar application;
- complex recurrence workflows;
- automatic Task completion/cancellation based on CalendarEvent state;
- automatic Client creation from arbitrary inbound provider traffic;
- AI-based Client/Deal guessing from message text;
- automatic AI replies;
- automatic AI EmailDraft sending;
- provider delivery/read analytics as a Day 5 reporting feature;
- generic event-sourcing architecture;
- separate provider-specific message domain tables;
- integration microservices;
- a second Redis/broker infrastructure;
- a new generic secret-management platform;
- Day 6 Analytics/Reporting work;
- payment functionality.

---

## 21. Planned Day 5 implementation sequence

This contract approves the following incremental plan. Each implementation iteration must remain independently verified and leave the project runnable.

### D5.0 — Integration Architecture/Product Contract

- approve this contract;
- reconcile source-of-truth documentation;
- no Day 5 product implementation code.

### D5.1 — Integration Foundation

Expected scope:

- shared integration persistence/lifecycle foundation;
- `IntegrationConnection`;
- `ExternalMessage`;
- `CalendarEvent` foundation;
- EmailDraft sent-state foundation if required by schema design;
- provider adapter interfaces;
- encryption/token-storage foundation;
- integration Celery queue/tasks infrastructure as minimally required;
- ADMIN integration-settings API/UI foundation;
- tests/migration/runtime verification;
- no premature provider-specific business flow beyond foundation needs.

### D5.2 — Gmail

- Google OAuth connection flow;
- encrypted runtime token handling/refresh;
- EmailDraft explicit send;
- outbound provider lifecycle -> Communication;
- bounded inbound relevant-email synchronization;
- email Client matching and deterministic thread-based Deal correlation;
- Gmail UI states and verification.

### D5.3 — Telegram

- Bot configuration boundary;
- authenticated/verified webhook boundary;
- inbound/outbound messaging;
- Client matching/manual unmatched linking;
- Communication creation;
- live verification where public/provider setup permits.

### D5.4 — Google Calendar

- Google Calendar use of approved corporate OAuth connection;
- CalendarEvent create/update/cancel;
- Client/Deal/Task entry points;
- external link/status UI;
- live verification.

### D5.5 — WhatsApp

- WhatsApp Business Cloud API adapter;
- verified webhook/provider boundary;
- inbound/outbound lifecycle where credentials permit;
- Client matching/unmatched flow;
- honest documented external limitation if live verification is unavailable.

### D5.6 — Unified Integration UX + Hardening

- `/crm/inbox` unmatched operational flow;
- integration status/error UX reconciliation;
- authorization/security hardening;
- retry/idempotency regression;
- RU/EN/ES completion for Day 5;
- no Day 6 analytics expansion.

### D5.7 — Final Day 5 Regression / Runtime / Provider / Browser Verification + Documentation Closure

- full backend PostgreSQL regression;
- Alembic head/current/check;
- frontend production build;
- integration runtime health/degradation checks;
- live-provider gates actually possible with available credentials/configuration;
- authenticated ADMIN/MANAGER browser smoke;
- public/CRM regression as appropriate;
- cleanup of temporary synthetic data;
- source-of-truth documentation closure;
- explicitly record any provider that is implemented but not live-verified.

---

## 22. Definition of Day 5 complete

Day 5 may be marked COMPLETE only when:

1. approved integration functionality is implemented according to this contract;
2. backend authorization is verified;
3. provider secrets are not exposed through source, logs, API responses, browser UI, tests, or reports;
4. idempotency prevents duplicate Communication creation for repeated provider facts;
5. EmailDraft is sent only by explicit employee action and becomes immutable/copyable after confirmed send;
6. Task and CalendarEvent remain separate but explicitly linkable;
7. disconnected/degraded providers do not break ordinary CRM operation;
8. required RU/EN/ES user-facing strings are present;
9. PostgreSQL migrations and relevant automated tests pass;
10. frontend production build and relevant browser smoke pass;
11. each live provider is either actually live-verified or explicitly documented as not live-verified because of a concrete external blocker;
12. source-of-truth documentation accurately reflects what was actually verified.

---

## 23. Architecture decisions fixed by this contract

- One corporate connection per provider for the MVP.
- Gmail + Google Calendar use Google OAuth.
- Google runtime OAuth tokens are encrypted at application level before PostgreSQL persistence; encryption key remains environment/deployment-secret only.
- Telegram/WhatsApp static credentials are environment/deployment-secret backed for the MVP.
- Only ADMIN manages integration connections.
- Provider calls go through adapters/services.
- Messaging provider lifecycle is persisted in `ExternalMessage`; CRM history remains `Communication`.
- `Communication` is created only for actual confirmed outbound or accepted/matched inbound communication facts.
- Inbound unmatched traffic does not automatically create Clients.
- Gmail Deal correlation may use deterministic provider-thread history; AI/text guessing is prohibited.
- `Task != CalendarEvent`; optional explicit linking is approved.
- Calendar does not become a full CRM calendar application.
- EmailDraft becomes read-only but copyable after confirmed successful send.
- Celery/Redis are reused; a logical integrations queue is permitted without new broker infrastructure.
- `UNKNOWN` outbound state prevents unsafe blind retries after an uncertain provider outcome.
- Disconnect never deletes historical CRM/provider records.
- WhatsApp live verification depends on real Meta provider setup and may be honestly documented as externally blocked.

