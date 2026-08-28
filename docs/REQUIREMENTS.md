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
- Telegram;
- WhatsApp;
- company;
- lead source;
- notes;
- created/updated timestamps.

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

Authentication and authorization are required architectural concerns but their acceptance criteria and mechanism are not yet defined. The architecture must be decided before Day 2 CRM Core implementation. Do not assume JWT, cookie sessions, roles or a password policy without an explicit requirements decision.

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

## 10. Delivery artifacts
Required:
- technical specification document (`.docx`);
- public GitHub repository;
- `README.md` explaining setup and operation;
- screenshots and screencasts demonstrating functionality.

## 11. Acceptance principle
A feature is considered complete only when it works through the relevant frontend/backend/database flow, can be reproduced, and does not knowingly break existing completed functionality.
