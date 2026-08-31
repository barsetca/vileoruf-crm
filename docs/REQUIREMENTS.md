# VILEORUF CRM — Requirements

## 1. Product goal
Create a full-stack CRM with AI automation throughout the sales process: scoring, prediction, recommendations, and automation.

## 2. Business tasks
The source specification requires:
- sales-cycle automation;
- revenue forecasting;
- smart recommendations for managers;
- integrations with communication channels.

## 3. CRM web interface

### 3.1 Sales pipeline
- Kanban-style sales funnel.
- Drag & drop deals between stages.
- Persist stage changes in the database.
- Pipeline stages must be represented as data rather than hard-coded UI-only state.

Initial proposed stages:
1. New Lead
2. Contact
3. Qualification
4. Proposal
5. Negotiation
6. Won
7. Lost

Stage names/configuration may be refined during implementation.

### 3.2 Clients
Client records should support the CRM workflow. Proposed MVP fields:
- name / company name;
- contact person;
- email;
- phone;
- Telegram identifier/username (optional);
- WhatsApp identifier/phone/contact (optional);
- company;
- lead source;
- notes;
- created/updated timestamps.

Each Client has a business lifecycle status, distinct from authentication roles:
- `CUSTOMER` (`Заказчик` in Russian UI): a person/company in the CRM with no successfully completed deal;
- `CLIENT` (`Клиент` in Russian UI): a person/company with at least one deal completed as `Won`.

The first successful `Won` transition changes `CUSTOMER` to `CLIENT`. Later lost deals do not automatically reverse `CLIENT` to `CUSTOMER`.

### 3.3 Deals
A deal belongs to a client. Proposed MVP fields:
- project/deal name;
- description;
- estimated budget;
- deadline;
- pipeline stage;
- probability;
- responsible user;
- timestamps.

Estimated budget is CRM deal information and is NOT payment processing.

### 3.4 Communication history
Maintain communication history for clients/deals. Proposed channels:
- email;
- Telegram;
- WhatsApp;
- manual/other communication where useful.

Proposed communication data:
- channel;
- incoming/outgoing direction;
- content;
- timestamp;
- client;
- optional deal;
- status.

### 3.5 Tasks
Tasks are an MVP extension supporting manager recommendations/workflow:
- title/description;
- due date;
- completion status;
- client/deal association where applicable.

## 4. AI requirements

### 4.1 Lead scoring
Generate a lead score and useful explanation.

### 4.2 Deal prediction
Estimate the probability/outlook of a deal using available CRM context.

### 4.3 Next best action
Recommend the next useful manager action based on client, deal and communication context.

### 4.4 Email generation
Generate an email draft from CRM context.
AI must not automatically send an AI-generated email without an explicit user action.

## 5. Integrations
Required by the source specification:
- Gmail API / email;
- Telegram;
- WhatsApp;
- Calendar.

Implementation priority for the 7-day MVP:
1. Gmail
2. Telegram
3. Calendar
4. WhatsApp

External API limitations, credentials, verification or provider access may constrain live integration. Do not fake a successful live integration. If blocked externally, implement the adapter/interface and document the limitation.

## 6. Analytics and reporting
MVP analytics should cover useful sales metrics such as:
- lead/deal counts;
- deals by pipeline stage;
- pipeline value;
- conversion;
- won/lost deals;
- revenue/deal forecast where supported by available data.

## 7. Internationalization (mandatory)
Languages:
- Russian (`ru`) — default and fallback;
- English (`en`);
- Spanish (`es`).

Requirements:
- language switching from the UI;
- selected language persists between sessions;
- all user-facing navigation, buttons, forms, statuses, messages, errors, analytics labels and settings are translatable;
- no hard-coded user-facing strings in React components where translation keys should be used;
- translation architecture must allow additional languages later;
- localize dates, times and numeric formatting.

## 8. Privacy / data
The source specification states:
- test data;
- database encryption;
- GDPR compliance.

Because the source specification does not define concrete encryption/GDPR acceptance criteria, implementation details must be documented rather than silently assumed.

### 8.1 Authentication / authorization

Authentication and authorization are required for the internal CRM interface. Backend/frontend authentication and ADMIN-only employee management are implemented. ADMIN can list/create/update employees, including role, name and active state; MANAGER is forbidden. Email/password changes and physical deletion are absent. Self-deactivation/self-downgrade and removal of the last active ADMIN are rejected. CRM role/ownership authorization remains pending.

#### Users and roles

An authenticated `User` is only a VILEORUF Studio employee. MVP roles are:
- `ADMIN`;
- `MANAGER`.

External customers are `Client` records, not `User` accounts or authentication roles. They receive no CRM login or customer portal in the current scope.

The minimum `User` model contains `id`, unique login `email`, `password_hash`, `display_name`, `role`, `is_active`, `created_at`, and `updated_at`. The implemented backend foundation uses a UUID primary key, a native PostgreSQL role enum, and timezone-aware timestamps. Employee offboarding uses `is_active = false`; physical deletion is not the primary mechanism because historical CRM records may reference the user.

#### Authentication mechanism

Login uses email and password. Passwords must never be stored in plaintext and must be hashed with Argon2id. The MVP password policy is 12–128 characters, with no mandatory character-class combination and no periodic forced password change.

Authentication uses JWT without server-side session storage:
- access JWT: approximately 30 minutes, stored only in React memory, never in `localStorage` or `sessionStorage`, and sent as `Authorization: Bearer <access-jwt>`;
- refresh JWT: approximately 7 days, stored/transmitted through an `HttpOnly` cookie inaccessible to frontend JavaScript; `Secure=true` is required in production and cookie attributes must match the deployment environment securely;
- refresh issues a new access JWT, which remains only in React memory.

MVP refresh is stateless until token `exp`: no refresh-token table, blacklist, server-side refresh session store, or complex rotation/reuse-detection infrastructure. Refresh and authenticated API requests must validate the current user, including `is_active`; authenticated requests must also enforce the current role and ownership rules. Logout removes the in-memory access token and clears the refresh cookie. A previously issued stateless JWT cannot be centrally revoked without server-side state, so the access JWT remains short-lived.

The MVP does not include OAuth/Google login, SSO, LDAP, magic links, 2FA, email verification, or password reset by email without a separate requirements decision.

#### First ADMIN bootstrap

There is no public employee registration. The implemented secure CLI/bootstrap mechanism creates the first `ADMIN` from email, display name, and an interactively supplied/confirmed password that is hashed. It is creation-only and refuses repeated bootstrap when any active or inactive ADMIN exists. Hard-coded/default/master credentials, credentials in Git or `.env.example`, and development seed data as a production ADMIN bootstrap are forbidden.

#### Authorization

Backend authorization is authoritative; frontend hiding/disabling controls is only a UX measure.

`ADMIN` may view, create, and edit all Clients and Deals; change the pipeline stage of any Deal; assign/change the responsible user; and has full CRM Core access within the approved MVP scope.

`MANAGER` may view all Clients and Deals, create Clients and Deals, and edit the common card of any Client. A manager may edit or move only their own Deals and may not modify other managers' Deals. Deal ownership is determined by `Deal.responsible_user_id` or an equivalent foreign-key relationship to `User`.

#### Public requests

Public visitors do not authenticate and may submit a future public request without an employee login. The internal CRM remains protected for `ADMIN`/`MANAGER`. External customers remain `Client` records, never `User` accounts: the public area is not a customer portal and provides no password, personal cabinet, order-history login, customer JWT, or customer role.

Once implemented during Day 2, a public request maps to `Client(status=CUSTOMER)` plus a Deal in the initial pipeline stage. The exact API/form contract remains deferred to a separate controlled Day 2 iteration; neither the public route/form nor request endpoint exists yet, and no new `Lead`, `Inquiry`, or `Request` entity is approved by this principle alone.

#### Authentication internationalization

Future login, authentication errors, logout, access-denied messages, user-management and role labels, and Client lifecycle status labels must follow the mandatory `ru` default/fallback plus `en` and `es` i18n rules.

## 9. Explicitly out of current scope
Unless requirements are changed explicitly:
- payment processing;
- payment gateways;
- invoices/accounting;
- inventory;
- HR;
- ERP modules;
- mobile native application;
- microservice decomposition.
- customer portal/personal account;
- multi-tenancy or multiple organizations;
- custom dynamic roles or an enterprise permission matrix;
- OAuth/SSO, 2FA, or Redis-backed authentication state.

## 10. Delivery artifacts
Required:
- technical specification document (`.docx`);
- public GitHub repository;
- `README.md` explaining setup and operation;
- screenshots and screencasts demonstrating functionality.

## 11. Acceptance principle
A feature is considered complete only when it works through the relevant frontend/backend/database flow, can be reproduced, and does not knowingly break existing completed functionality.
