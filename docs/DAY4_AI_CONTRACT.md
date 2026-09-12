# DAY4_AI_CONTRACT.md

## VILEORUF Studio CRM — Day 4 AI Architecture & Product Contract

**Status:** APPROVED / CLOSED  
**Gate:** D4.0 Architecture / Product Contract  
**Purpose:** Source-of-truth contract for implementation of Day 4 AI functionality.  
**Implementation sequence:** D4.1 → D4.7.

> This document contains the final consolidated Day 4 decisions. Where an earlier discussion or idea conflicts with this document, this document takes precedence for Day 4 implementation. Existing project-wide architecture, security, authorization, migration, i18n, and Codex rules remain in force unless explicitly refined here.

---

## 1. Day 4 scope and boundaries

Day 4 extends the existing **modular monolith**. Do not introduce microservices.

Day 4 adds:

- AI service layer;
- OpenAI provider abstraction;
- Celery + Redis for background AI processing only;
- `AIAnalysis` history/audit entity;
- `EmailDraft` working-draft entity;
- business dictionaries for Categories and Services;
- AI Settings and Business/CRM Settings required by this contract;
- Lead Scoring;
- Deal Prediction;
- Next Best Action;
- AI Email Draft;
- AI history UI;
- Deal-page AI UI;
- required authorization, i18n, validation, failure handling, audit metadata, and tests.

Day 4 does **not** add:

- microservices;
- real email sending;
- Telegram/WhatsApp provider integrations;
- capacity planning / actual team workload planning;
- AI cost dashboard;
- monetary OpenAI cost calculation;
- global CRM-wide predictive statistics;
- automatic PII redaction of free text;
- retrospective bulk AI analysis of existing Deals;
- complex EmailDraft versioning;
- automatic execution of AI recommendations.

---

## 2. Business-facing AI metrics

There are two independent Deal-level metrics.

### 2.1 Lead Scoring / Привлекательность

Range: **0–100**.

Business question:

> How commercially attractive is this specific Deal for VILEORUF Studio? / Насколько мы хотим получить эту сделку?

Stable labels:

- RU: **Привлекательность**
- EN: **Lead Scoring**
- ES: **Atractivo**

Lead Scoring is independent from Deal Prediction. Do not combine them into one opaque Deal Score.

### 2.2 Deal Prediction / Вероятность успеха

Range: **0–100%**.

Business question:

> How likely is this Deal to end as `Won`? / Насколько вероятно, что мы действительно получим эту сделку?

Stable labels:

- RU: **Вероятность успеха**
- EN: **Deal Prediction**
- ES: **Probabilidad de éxito**

Lead Scoring is **not** an input to Deal Prediction.

---

## 3. Lead Scoring contract

Lead Scoring consists of four factors, each scored from 0 to 100.

Initial weights:

| Factor | Initial weight |
|---|---:|
| Service Fit | 30% |
| Commercial Value | 30% |
| Lead Quality | 15% |
| Feasibility | 25% |

ADMIN can change weights at runtime through Business/CRM Settings.

Constraint:

> The four weights must always total exactly 100%.

Weights are not redistributed when a factor cannot be evaluated.

### 3.1 Service Fit

AI evaluates how well the Deal fits VILEORUF Studio's available services.

Inputs may include:

- selected Service;
- actual Deal Category;
- Deal description/requirements;
- active Services in the relevant Category.

No separate category capability-description field is required for MVP.

### 3.2 Commercial Value

Commercial Value is **deterministic CRM math**, not subjective LLM reasoning.

The LLM must not calculate or override this factor.

Inputs:

- Deal budget;
- effective effort;
- Category Target hourly rate.

Effective effort:

1. use Deal manager effort estimate when present;
2. otherwise use Category Target effort.

Calculated Deal hourly rate:

`budget / effective_effort_hours`

Commercial ratio:

`calculated_deal_hourly_rate / category_target_hourly_rate`

Initial configurable score scale:

| Ratio to Target hourly rate | Commercial Value score |
|---:|---:|
| ≤ 50% | 0 |
| 75% | 40 |
| 100% | 70 |
| 125% | 85 |
| ≥ 150% | 100 |

Rules:

- smoothly interpolate between configured points;
- clamp score to 0–100;
- ≥150% is capped at 100;
- ADMIN can change the scale without code changes.

If Budget is absent:

> **Commercial Value = 0/100 — no data / нет данных.**

This means the factor cannot be calculated because required data is absent. It must not be presented as a conclusion that the Deal is commercially bad.

The UI must explain the missing input.

If a Category lacks required Target hourly rate configuration, the system must not invent it. Report insufficient configuration/data for full commercial calculation.

### 3.3 Lead Quality

AI score: **0–100**.

Lead Quality measures how well the available information allows VILEORUF to understand the task and expected result.

It is contextual to the selected service and may consider:

- goal;
- expected result;
- major functions/scope;
- constraints;
- other relevant request details.

Do not impose a universal rigid checklist.

Missing optional Budget or Desired deadline alone must not lower Lead Quality automatically.

### 3.4 Feasibility

AI score: **0–100**.

Business meaning:

> How realistic is it for VILEORUF to execute this project given the known requirements, budget, desired deadline, and Category norms?

Inputs may include:

- Service/Category;
- Deal description;
- Budget when provided;
- Desired deadline when provided;
- Category Target effort;
- Category Target hourly rate;
- manager effort estimate when present.

Missing optional Budget or Desired deadline does not automatically make Feasibility zero.

Zero is appropriate only when the information is genuinely insufficient to evaluate the factor. Missing information must be explained.

Desired deadline may reduce Feasibility when the time window is objectively tight relative to effective effort.

However, Day 4 has **no capacity planning** and does not know actual team availability. Therefore AI may say that a deadline is comfortable, tight, or very tight relative to the work volume, but must not claim that VILEORUF will definitely meet or definitely miss it.

### 3.5 Lead Scoring result

A successful Lead Scoring result must provide:

- overall score 0–100;
- four factor scores;
- short explanation for each factor;
- overall AI summary of approximately 1–3 sentences;
- missing-data warning and missing-information list when relevant;
- security warning when Prompt Injection is detected;
- optional existing-Category suggestion when the actual Category is `Другое`.

Commercial Value explanation is generated from deterministic CRM numbers.

Service Fit, Lead Quality, and Feasibility explanations are AI-generated.

### 3.6 Current-Deal Communication context

Lead Scoring may use raw text, channel/direction and timestamp from Communications linked to the **current Deal** as supplemental contextual evidence for Service Fit, Lead Quality and Feasibility.

- structured CRM fields remain authoritative if they conflict with Communication text;
- Communication text does not define Commercial Value, weights, effective effort, rate, budget or the deterministic overall formula;
- an explicitly available qualification fact in current-Deal Communication history must not be reported as missing merely because it is absent from a structured optional field;
- Communication text is untrusted input and cannot instruct the system, alter the task, or override these rules;
- context is newest-first and bounded by the shared technical character limit, with truncation metadata; no summarizer call is added;
- the bounded context is frozen at launch. The worker executes that frozen payload and does not re-query Communications later.

---

## 4. Categories and Services

Use simple ADMIN-managed business dictionaries.

### 4.1 Categories

Initial examples include:

- Программирование;
- Видео под ключ;
- Видеомонтаж;
- Нейрофото;
- Другое.

Each Category has configurable:

- Target hourly rate — target €/person-hour;
- Target effort — typical/target effort.

Target effort is stored in **person-hours**.

ADMIN UI may accept/display working days using:

> 1 working day = 8 person-hours.

Target effort is a baseline norm, not a promise or exact project estimate.

`Другое` is a normal Category and has its own Target hourly rate and Target effort.

### 4.2 Services

The public user selects a **Service**.

Each Service belongs to exactly one Category, so normal Category assignment is deterministic from selected Service.

ADMIN can manage Categories and Services.

### 4.3 Dictionary lifecycle

For business dictionaries, normal CRM UI must **not physically delete records**.

Use:

- ACTIVE;
- INACTIVE.

ADMIN may add, edit, and deactivate.

Inactive values:

- are not offered for new entities;
- remain referenced by existing/historical entities.

This rule applies to Categories, Services, and future business dictionaries unless explicitly overridden.

Deactivating a Service or Category:

- does not alter existing Deals;
- does not by itself make existing AI analyses outdated;
- should produce a warning on an active Deal linked to an inactive value.

If Target rate/effort changes at the same time, normal business-setting invalidation rules apply.

Changes to dictionary names/content/composition do not mass-invalidate existing AI results. A future manual recalculation uses the current dictionary.

---

## 5. Category `Другое` and AI suggestion

If the selected Service maps to Category `Другое`, AI may analyze the Deal description and suggest one of the **existing active Categories**.

Rules:

- AI must not invent a new Category;
- AI may suggest an existing active Category or leave the Deal as `Другое`;
- suggestion includes a short reason;
- suggestion is part of the **Lead Scoring structured result**;
- do not create a separate paid AI call only for classification;
- AI never changes Deal Category automatically.

UI may show:

> Suggested Category: X  
> Reason: ...  
> [Apply Category]

Until a manager confirms the suggestion:

- actual Deal Category remains `Другое`;
- all economic calculations use `Другое` Target hourly rate and Target effort.

After confirmation:

- Deal Category changes;
- dependent AI results may become outdated according to this contract;
- no automatic recalculation is triggered.

General principle:

> AI suggestion ≠ CRM business-data mutation.

---

## 6. Deal fields relevant to Day 4

### 6.1 Budget

Public field:

> **Бюджет (опционально)** / Budget (optional)

Do not force predefined budget ranges for MVP.

Budget participates in:

1. deterministic Commercial Value;
2. AI Feasibility context.

AI does not calculate Commercial Value.

### 6.2 Desired deadline

Public field:

> **Желаемый срок выполнения (опционально)** / Desired deadline (optional)

Store as a concrete calendar **DATE**, not as a number of days.

Desired deadline and effort are separate concepts.

Never convert:

> 10 days → 80 person-hours.

For a new public request, a date before the current date must not be selectable/accepted.

If an existing Deal has a Desired deadline that is now in the past:

- preserve it;
- show a warning;
- allow Feasibility to treat it as a significant schedule risk;
- do not automatically change it;
- do not automatically declare the entire Deal infeasible.

Desired deadline does not participate in Commercial Value.

### 6.3 Manager effort estimate

Add an optional Deal-level field:

> **Оценка трудозатрат, чел.-ч.** / Manager effort estimate, person-hours.

When present, it takes priority over Category Target effort.

When absent, effective effort falls back to Category Target effort.

A historical AIAnalysis snapshot records the values actually used, e.g.:

- target effort;
- manager effort;
- effective effort.

AI does not invent effort for Commercial Value.

---

## 7. Deal Prediction contract

Deal Prediction estimates the probability that the current Deal ends as `Won`.

Result:

- probability 0–100%;
- confidence: `LOW`, `MEDIUM`, or `HIGH`;
- short summary;
- positive signals;
- risks / negative signals;
- missing/limited-context information when relevant;
- security warning when Prompt Injection is detected.

Confidence represents **data sufficiency/reliability**, not Deal quality.

### 7.1 Inputs

Deal Prediction may use:

1. current Deal state/data;
2. Communications for the current Deal;
3. structured Tasks for the current Deal;
4. CRM-computed time/activity indicators;
5. anonymized/structured aggregate commercial history for the same Client.

Useful time/activity indicators include:

- days Deal open;
- time since last Communication;
- Communication count;
- time on current Pipeline Stage, if reliable data exists.

### 7.2 Communications

For MVP, Deal Prediction may receive the text content of current Deal Communications plus useful metadata such as:

- channel/type;
- direction;
- timestamp.

Do not add a separate AI summarization call for old Communications in MVP.

### 7.3 Same-Client commercial history

Use only anonymized/structured aggregates such as:

- prior Deal count;
- Won count;
- Lost count;
- historical win rate;
- recency of last Won;
- similar structured signals.

Do not send Client identity or the contents of old Deals.

This history is a signal, not a hard rule.

Do not add global CRM-wide historical win statistics to Deal Prediction in Day 4.

---

## 8. Next Best Action contract

Next Best Action (NBA) returns **1–3 ranked recommended actions**.

Each action contains:

- priority;
- action;
- reason;
- recommended timing/moment.

The first action is the primary recommendation.

AI does not execute any action automatically.

A future feature may allow a manager to create a Task from a selected recommendation, but Day 4 does not make AI recommendations autonomous.

### 8.1 NBA inputs

Primary inputs:

- Deal;
- Communications;
- Tasks;
- time/activity indicators;
- same-Client aggregate Deal history.

Auxiliary inputs:

- latest Lead Scoring, if available;
- latest Deal Prediction, if available;
- explicit indication of whether either auxiliary result is outdated.

Lead Scoring and Deal Prediction are **not mandatory prerequisites** for manual NBA.

If they are missing, failed, or outdated:

- NBA may still run;
- do not auto-trigger missing/recalculated LS or DP;
- use primary data plus whatever auxiliary context is available.

If outdated LS/DP values are passed, they must be explicitly marked as outdated so the model treats them with reduced trust.

---

## 9. AI Email Draft contract

AI Email Draft is **manual only**.

Manager specifies the purpose of the email.

Examples:

- follow-up;
- request/clarify information;
- reply;
- discuss proposal/terms;
- custom purpose.

An optional selected NBA recommendation may be used as the purpose/context.

Manager may also provide:

> **Additional AI instructions**

### 9.1 Inputs

Email Draft may use:

- current Deal;
- selected purpose;
- current Deal Communications subject to context limits;
- selected NBA recommendation when applicable;
- manager Additional AI instructions.

### 9.2 Output

AI returns:

- Subject;
- editable Body.

### 9.3 Writing style

Base VILEORUF email style:

- professional;
- friendly;
- natural;
- concrete;
- no bureaucracy;
- no pushy sales tone;
- no obvious generic AI style.

Mandatory writing behavior:

- avoid generic AI introductions;
- do not unnecessarily recap the entire Deal;
- avoid unnecessary headings/lists;
- avoid verbose, over-polished constructions and repetition;
- avoid promotional/pompous wording;
- use natural length;
- use the style of prior correspondence when there is enough evidence;
- never invent facts, agreements, prices, deadlines, promises, or commitments;
- manager instructions have priority only within known CRM facts and safety/business rules.

Do not claim guaranteed AI-detector evasion.

### 9.4 Client communication language

Add Client field:

> **Preferred communication language: RU / EN / ES**

It is the default language for Email Draft.

Manager may change the language before generation.

Preferred communication language is independent from CRM UI language.

### 9.5 Client name

Do not intentionally send the structured Client name to the LLM.

Use:

`{{client_name}}`

CRM substitutes the real name after generation.

---

## 10. EmailDraft persistence and workflow

`EmailDraft` is a real persisted working entity, separate from AI history.

Day 4 workflow:

> AI generate → manager edit → Save as Draft → reopen/edit → copy externally.

No real email send action in Day 4.

Minimum EmailDraft data:

- Deal;
- Subject;
- Body;
- language;
- purpose;
- creator;
- created timestamp;
- updated timestamp;
- optional source AIAnalysis when the draft originated from an AI generation.

Rules:

- a draft may be created by AI or entirely manually;
- one Deal may have multiple independent EmailDraft records;
- no complex versioning of a single draft in MVP;
- repeat AI generation never silently overwrites a saved/edited draft;
- a new generation creates a new AI-generated variant;
- manager decides whether to save/use it;
- normal manual saves/edits of EmailDraft do not create new AIAnalysis records.

Deletion:

- MANAGER may delete a working EmailDraft for own Deal;
- ADMIN may delete a working EmailDraft for any Deal;
- deleting a working draft does not delete historical AIAnalysis;
- future sent Communications must not be deleted through EmailDraft deletion.

Day 5 target workflow may later become:

> AI → edit → Save Draft → edit → Send → Communication.

When real email sending exists, the final actually sent text belongs in Communication.

Principle:

> AIAnalysis = what AI proposed.  
> EmailDraft = current working document.  
> Communication = what actually went to the client.

---

## 11. AIAnalysis persistence

Use one common `AIAnalysis` entity/table for the history/audit of AI operations.

It covers at least:

- Lead Scoring;
- Deal Prediction;
- Next Best Action;
- Email Draft generation.

Do not create one unrelated history table per AI function.

### 11.1 Common metadata

Store common metadata as normal columns where appropriate, including:

- Deal reference;
- AI function/type;
- technical status;
- model actually used;
- language;
- prompt version;
- start/end timestamps;
- duration;
- token/usage information when provider supplies it;
- input fingerprint;
- compact structured snapshot;
- safe normalized error category for failures;
- other required audit metadata.

### 11.2 Business result

Store the type-specific business result as **validated structured JSON**.

Each AI function has its own strict backend schema.

JSON does not mean arbitrary unvalidated LLM content.

### 11.3 No raw provider storage

Do not store in DB:

- full raw prompt;
- full raw OpenAI response;
- raw provider error text.

Technical details may go to application logs subject to secret/privacy rules.

---

## 12. AI operation lifecycle

Technical status and business freshness are separate concepts.

Technical statuses:

- `QUEUED`
- `RUNNING`
- `SUCCESS`
- `FAILED`

Do **not** use `OUTDATED` as the main technical status.

A successful result may have:

- `status = SUCCESS`
- `is_outdated = true`

`is_outdated` is meaningful for successful business results, not for failed calls.

Do not add a separate `is_current` flag.

The current result for a Deal/function is:

> the latest successfully completed AIAnalysis of that function type for that Deal,

subject to closed-Deal rules below.

A later failed attempt does not erase or replace the previous successful business result.

Example history:

> 52% SUCCESS  
> 64% SUCCESS / outdated  
> FAILED

The main Deal UI still shows the latest successful 64% result, clearly marks it as potentially outdated, and may separately report that the latest recalculation attempt failed.

---

## 13. Failed AI operations

Never fabricate fallback business scores/results.

If AI is unavailable, times out, returns invalid structured data, or otherwise fails:

- CRM/Deal creation and editing continue to work;
- operation ends as FAILED after applicable retries;
- old successful results remain intact;
- existing EmailDraft remains untouched when regeneration fails;
- user receives a clear localized retry-friendly message;
- do not expose stack traces, API keys, or raw provider responses.

Failed logical AI operations are saved in AI history with:

- function type;
- FAILED status;
- model where known;
- timing/audit metadata;
- safe normalized error category;
- usage if available.

Examples of normalized categories:

- `PROVIDER_TIMEOUT`
- `PROVIDER_UNAVAILABLE`
- `INVALID_STRUCTURED_RESPONSE`
- `CONFIGURATION_ERROR`

A FAILED operation has no fabricated business result.

Detailed provider error information belongs only in application logs.

---

## 14. Structured outputs and backend validation

Every AI function must have a strict result schema.

Flow:

> LLM structured response → backend validation → only then SUCCESS/business persistence.

Invalid or incomplete output must not become a successful CRM result.

Examples:

- probability above 100 is invalid;
- invalid confidence enum is invalid;
- missing mandatory fields are invalid.

Commercial Value remains authoritative backend math and cannot be overridden by LLM output.

---

## 15. Background processing: Celery + Redis

Day 4 explicitly introduces:

- Celery;
- Redis.

Use them for **background AI operations** so Deal create/edit does not wait for the LLM.

Do not move ordinary CRUD to Celery without a separate architectural reason.

---

## 16. Retry policy

For transient technical failures:

> 1 initial provider attempt + maximum 2 retries.

Use increasing backoff.

Retry transient failures such as:

- provider timeout;
- temporary provider unavailability;
- temporary network failure;
- similar retryable provider errors.

Do not automatically retry errors that are clearly non-transient, such as:

- configuration errors;
- invalid authentication/API key;
- other errors where repeating the same request cannot reasonably succeed.

All retries belong to **one logical AI operation**.

Do not create separate business-history entries for each internal retry.

`timeout`, retry count, and backoff are technical env/config parameters.

Do not expose them in ADMIN UI for MVP.

---

## 17. Frozen input context during background execution

At the start of a logical AI operation, capture the significant input state/fingerprint and the prepared operation context needed for deterministic retry behavior.

All retries of that logical operation use the **same original input context**.

A retry must not silently pick up newer Deal data and thereby become a different analysis.

If significant data changes while the operation is running:

- save a successful result historically;
- compare original fingerprint with current significant state;
- mark the result immediately outdated when they differ;
- do not silently present that result as current/fresh.

For Email Draft, a completed generated variant may still be shown, but warn that the Deal context changed since generation began.

---

## 18. Fingerprint and snapshot

### 18.1 Fingerprint

Fingerprint/hash contains only significant input data that existed **before** the AI operation.

Do not include:

- outputs produced by the same operation;
- values derived from that operation's output.

An AI operation must never make its own result outdated merely by producing the result.

### 18.2 Snapshot

Store a compact structured snapshot of important business/calculation parameters actually used.

Examples for Lead Scoring:

- Service/Category identifiers or stable business references as appropriate;
- Budget;
- Desired deadline;
- Target hourly rate;
- Target effort;
- manager effort estimate;
- effective effort;
- Lead Scoring weights;
- Commercial Value scale.

Examples for Prediction/NBA:

- Pipeline Stage;
- relevant counts/time indicators;
- aggregate Client history;
- for NBA, auxiliary LS/DP values and freshness flags.

Do not duplicate in snapshot:

- full Deal description;
- full Communications;
- system prompt;
- raw OpenAI request;
- raw OpenAI response.

Purpose:

- fingerprint = freshness/change detection;
- snapshot = auditability of important structured conditions used for the historical result.

---

## 19. Duplicate in-flight protection

For one Deal, allow only **one active (`QUEUED`/`RUNNING`) logical AI operation per function type**.

Different function types may run in parallel.

Examples:

- Lead Scoring + Deal Prediction in parallel: allowed;
- two simultaneous Lead Scoring operations for the same Deal: not allowed.

UI disables the same action while active and shows a localized state such as:

> Рассчитывается…

Email Draft follows the same rule for generation. After completion, a manager may deliberately generate another variant.

---

## 20. Initial automatic AI pipeline

Add setting:

> **Автоматический AI-анализ новых сделок** / Automatic AI analysis for new Deals

Default: **ON**.

If:

- global AI is Enabled;
- automatic new-Deal analysis is ON;
- a new active Deal is created,

then:

1. Lead Scoring starts;
2. Deal Prediction starts **in parallel**;
3. NBA waits until both initial operations reach a final state (`SUCCESS` or final `FAILED` after retries);
4. NBA then runs using available primary data plus whichever auxiliary results succeeded.

One AI failure must not kill the entire initial chain.

If both LS and DP fail, NBA may still run from primary data.

Automatic AI applies to new Deal creation from:

- public request;
- MANAGER manual creation;
- ADMIN manual creation.

Initial analysis language:

- employee-created Deal → creator's current CRM UI language;
- public request → Russian default.

Turning automatic analysis ON later is **not retrospective**.

Do not mass-analyze Deals that were created while the setting was OFF.

---

## 21. Manual AI independence

After initial creation, AI functions are independently runnable.

Manual actions include:

- recalculate Lead Scoring;
- recalculate Deal Prediction;
- update NBA recommendations;
- generate Email Draft.

Manual recalculation of one function does **not** automatically recalculate another.

Manual NBA is allowed when LS/DP:

- were never calculated;
- failed;
- are outdated.

If outdated LS/DP are supplied to NBA, pass explicit freshness/outdated flags.

Do not auto-trigger LS/DP merely because NBA is requested.

This independence also prevents hidden unnecessary paid AI calls.

---

## 22. Global AI kill switch

AI Settings include:

> **AI Enabled / Disabled**

Default: **Enabled**.

When Disabled:

- do not start new automatic AI operations;
- do not allow new manual AI analyses;
- do not allow new AI Email Draft generation;
- existing AI results remain viewable;
- existing EmailDraft records remain manually editable;
- CRM otherwise continues functioning;
- already-running AI operations are not forcibly canceled.

UI must clearly state that AI is temporarily disabled by an administrator.

---

## 23. OpenAI provider abstraction

First real provider: **OpenAI**.

Business services must not call OpenAI SDK directly.

Use a small internal provider abstraction/service boundary.

This is **not** a multi-provider platform in MVP.

The abstraction exists so provider-specific implementation does not leak into business services and can be replaced later without rewriting CRM business logic.

API key and technical provider configuration come from environment/config and are never persisted/logged as normal business data.

---

## 24. OpenAI model settings

Maintain two independent runtime model settings:

1. **Analysis model**
   - Lead Scoring
   - Deal Prediction
   - Next Best Action

2. **Email model**
   - AI Email Draft

Initial default for both:

> `gpt-5.4-mini`

Initial configured allowlist:

- `gpt-5.4-mini`
- `gpt-5.4`
- `gpt-5.4-nano`

ADMIN selects only from the configured allowlist, never an arbitrary free-text model identifier.

The allowlist is configurable and must not be hardcoded into business logic.

Environment/config supplies default/fallback models.

ADMIN runtime override is persisted in DB and takes precedence over default config.

Changes apply to **new AI calls only** and do not rewrite historical results.

AI Settings UI should show:

- current model;
- default model;
- reset-to-default action.

**Reset to default** removes the DB override rather than copying the current default into DB.

The actual model used for each call is stored in AIAnalysis.

---

## 25. AI Settings

ADMIN-manageable AI Settings include at least:

- AI Enabled;
- Automatic AI analysis for new Deals;
- Analysis model;
- Email model;
- Deal Prediction validity;
- NBA validity.

Business/runtime settings that are explicitly ADMIN-manageable should apply without backend restart.

Technical settings such as provider timeout/backoff/rate-limit defaults remain env/config and do not require an MVP ADMIN UI.

---

## 26. Business/CRM Settings

Keep business rules separate from provider/AI settings.

Business/CRM Settings include:

- Categories;
- Services;
- Target hourly rate;
- Target effort;
- Lead Scoring factor weights;
- Commercial Value scale.

Changing business calculation settings may affect freshness of existing analyses according to the rules below.

---

## 27. Freshness / outdated rules

User-facing wording should prefer:

> **устаревший результат / возможно не соответствует текущим данным**

rather than exposing technical jargon such as `stale`.

No automatic OpenAI recalculation is triggered merely because a result becomes outdated.

Manager decides when to recalculate, except for the initial new-Deal pipeline.

### 27.1 Lead Scoring becomes outdated when significant inputs change

Relevant changes include:

- Service;
- Category;
- Deal description/requirements;
- Budget;
- Desired deadline;
- Category Target hourly rate;
- Category Target effort;
- manager effort estimate;
- Lead Scoring weights;
- Commercial Value scale.
- new, substantive edit, or deletion of a Communication linked to the current Deal.

Pipeline Stage change alone does **not** make Lead Scoring outdated.

Lead Scoring has **no time-based expiration**.

### 27.2 Deal Prediction becomes outdated when relevant inputs change

Relevant changes include:

- significant Deal data;
- Pipeline Stage;
- Communications;
- Tasks;
- same-Client aggregate commercial history;
- time-based validity expiration.

### 27.3 NBA becomes outdated when relevant inputs change

Relevant changes include:

- Deal data;
- Pipeline Stage;
- Communications;
- Tasks;
- same-Client aggregate history;
- new Lead Scoring result;
- new Deal Prediction result;
- time-based validity expiration.

### 27.4 Email Draft

Saved EmailDraft is **not automatically marked outdated**.

If Deal context changes while an AI Email generation is in flight, show a warning on the generated variant that context changed during generation.

---

## 28. Time-based validity

Time-based validity applies only to **active Deals**.

Initial defaults:

- Deal Prediction validity: **7 days**;
- NBA validity: **7 days**.

These are two independent ADMIN-configurable settings.

Each supports reset-to-default behavior.

After validity expires:

- show a recommend-refresh/outdated warning;
- do not auto-call OpenAI.

Freshness may be checked when Deal is accessed; no nightly background process is required for MVP.

Lead Scoring has no time expiration.

Won/Lost historical results do not age into outdated state due solely to time.

---

## 29. Tasks and freshness

For MVP, Tasks affect:

- Deal Prediction;
- NBA.

Tasks do not affect Lead Scoring.

Significant Task changes include:

- creation;
- status;
- due date;
- Deal relation;
- assignee.

A Task becoming overdue may also make DP/NBA outdated.

This may be detected on Deal access; no nightly job is required.

Existing Day 3 Task authorization semantics remain authoritative.

---

## 30. Communications and freshness

For an active Deal, any:

- new Communication;
- substantive Communication edit;
- Communication deletion

makes:

- Lead Scoring potentially outdated;
- Deal Prediction potentially outdated;
- NBA potentially outdated.

Do not automatically call AI after Communication changes.

Existing Day 3 Communications remain CRM history records, not provider-confirmed delivery events.

---

## 31. Business-setting changes and historical Deals

Changes to:

- Lead Scoring weights;
- Commercial Value scale;
- Target hourly rate;
- Target effort

make affected latest analyses outdated **only for active Deals**.

Do not automatically recalculate them.

Closed Won/Lost Deal history remains unchanged.

Technical AI settings such as:

- selected model;
- model allowlist;
- context limits

do not by themselves invalidate historical business results.

---

## 32. Active and closed Deals

A Deal is active until it reaches terminal status:

- `Won`;
- `Lost`.

After a Deal is closed:

- do not allow new Lead Scoring;
- do not allow new Deal Prediction;
- do not allow new NBA;
- preserve all existing AI history;
- future business-setting changes do not mark closed-Deal historical analyses outdated.

EmailDraft is still available after closure:

- existing drafts may be viewed/edited/deleted according to authorization;
- new AI Email Drafts may still be generated when global AI is enabled;
- future Day 5 email sending may still use them.

The analytics restriction on closed Deals does not apply to communication drafting.

---

## 33. Deal closes while AI is running

Do not forcibly cancel already-running LS/DP/NBA operations merely because Deal becomes Won/Lost.

When such an operation finishes:

- save the result historically;
- do not make it the new current active analysis;
- do not launch follow-on NBA after closure.

Preserving the historical result may later allow comparison of the last prediction with actual Won/Lost outcome.

---

## 34. Sparse new Deal data

Automatic initial AI analysis runs for **any valid newly created active Deal**, even if information is sparse.

Missing optional Budget, Desired deadline, or limited description does not block the initial pipeline.

Insufficiency is represented through:

- factor scores;
- missing-data warnings;
- Deal Prediction Confidence;
- NBA recommendations such as gathering additional information.

Do not require artificially complete data before AI can run.

---

## 35. Communications context limits

For Lead Scoring, Deal Prediction, NBA, and Email Draft, limit Communication context by **text volume**, not a fixed number of messages.

When history exceeds the configured limit:

- prioritize recent Communications;
- set structured context flag such as `communication_history_truncated = true`.

Deal Prediction may account for truncation when determining Confidence.

The context limit is a technical configuration parameter.

Do not add a separate old-history LLM summarizer in MVP.

---

## 36. Privacy/data minimization for MVP

Intentionally send only business data required by the specific AI function.

Do **not** intentionally add structured:

- Client name;
- email;
- phone;
- Client company;
- internal Client/User identifiers;
- other technical identifiers that are unnecessary for the AI task.

Allowed business context may include:

- Service/Category;
- Deal description;
- Budget;
- Desired deadline;
- Pipeline Stage;
- Target rate;
- Target effort;
- manager effort;
- Tasks as required;
- Communications as required;
- time/activity indicators;
- anonymized aggregate Client commercial history.

### 36.1 Free-text PII

For MVP, do **not** build automatic PII redaction/anonymization of Deal description or Communication free text.

Therefore free text may incidentally contain personal information entered by the client.

This is a consciously deferred privacy/security enhancement.

Do not create a second LLM call just to anonymize free text in Day 4.

The special `{{client_name}}` rule for Email Draft still applies to the structured Client name.

---

## 37. Prompt Injection protection

Prompt Injection protection is mandatory for all four AI functions.

Treat:

- Deal description;
- Communications;
- other client/user-supplied free text

as **untrusted data**, never as instructions to the model.

System/business instructions must have priority.

The model must ignore embedded instructions that attempt to:

- force particular scores;
- override CRM rules;
- reveal system instructions/data;
- alter required output format;
- otherwise manipulate the AI operation.

Use two layers:

1. architecture/prompt construction clearly separates trusted instructions from untrusted business data;
2. the existing AI call also detects suspicious embedded instructions and returns a structured security warning.

Do not create a separate extra AI call solely for Prompt Injection detection.

When potential Prompt Injection is detected:

- ignore the embedded instruction;
- continue the legitimate CRM analysis;
- return a structured warning;
- identify the source when practical without unnecessarily reproducing the malicious instruction;
- save the warning in AI history;
- show a localized warning to the user.

Example user-facing meaning:

> В данных сделки обнаружен текст, который может быть попыткой повлиять на инструкции AI. Он был проигнорирован при формировании результата.

---

## 38. Authorization

Backend remains authoritative.

ADMIN:

- may view/run all four AI functions for any Deal;
- may manage AI/Business settings according to existing admin rules.

MANAGER:

- may view/run AI functions only for own Deals;
- may manage EmailDraft only for own Deals.

Frontend role-aware behavior is UX only and must not replace backend authorization.

Existing project role semantics remain in force:

- ADMIN is a sales-capable employee plus admin privileges;
- MANAGER is a CRM employee.

---

## 39. Rate limiting

Add a general technical rate limit to AI launch endpoints.

Purpose:

- protect against accidental loops/spam;
- reduce uncontrolled provider usage.

Do not add personal daily/monthly quotas for ADMIN/MANAGER in MVP.

Exact default is a technical configurable value via env/config.

Do not expose rate-limit configuration in ADMIN UI for MVP.

---

## 40. AI audit metadata

For each logical AI call, save technical audit information including:

- function type;
- actual model;
- prompt version;
- language;
- status;
- start/end time;
- duration;
- token/usage information when available.

Do not store full raw prompt or raw provider response.

Do not calculate monetary OpenAI cost in Day 4.

Token/usage data collected in Day 4 may later support Day 6 usage/cost analytics.

---

## 41. ADMIN setting-change audit

Do not create a dedicated DB history table for ADMIN setting changes in MVP.

Log relevant changes in application logs:

- who changed it;
- what changed;
- old value;
- new value;
- timestamp.

Examples:

- Category Target hourly rate;
- Service deactivation;
- Analysis model.

Never log secrets or API keys.

DB stores current setting state.

Historical AIAnalysis snapshot/audit metadata records the actual relevant values/model used for a given AI operation.

---

## 42. i18n

CRM UI supports:

- Russian — default;
- English;
- Spanish.

UI labels, statuses, headings, warnings, and errors must follow the existing i18n architecture.

For Lead Scoring, Deal Prediction, and NBA:

- explanation/content is generated in the UI language of the employee who launched the analysis;
- the AIAnalysis saves the language code;
- historical AI content is not automatically translated when viewed by another user in a different UI language.

For public-form automatic initial AI analysis:

- use Russian default.

Email Draft uses Client Preferred communication language by default, independently from CRM UI language.

---

## 43. UI placement

On Deal Page, use one logical AI area containing four sections:

1. Lead Scoring;
2. Deal Prediction;
3. Next Best Action;
4. AI Email Draft.

The main Deal view shows:

- latest successful result where applicable;
- freshness/outdated warning;
- active calculation status;
- relevant primary action such as Recalculate / Update recommendations / Generate email;
- latest failure notice without destroying previous success.

Do not dump full AI history onto the main Deal view.

Provide a separate **AI History / История AI** view/section accessible from the Deal AI area.

ADMIN settings are separated into:

### AI Settings

- AI Enabled;
- Automatic AI analysis;
- Analysis model;
- Email model;
- DP validity;
- NBA validity.

### Business/CRM Settings

- Categories;
- Services;
- Target hourly rate;
- Target effort;
- Lead Scoring weights;
- Commercial Value scale.

Do not mix provider/runtime settings with business calculation rules unnecessarily.

---

## 44. Day 4 implementation sequence

Day 4 is implemented and accepted incrementally.

### D4.1 — AI Foundation

Scope:

- foundation data model required by Day 4;
- migrations;
- AIAnalysis/EmailDraft foundation;
- required Deal/Client/settings foundation fields/entities;
- Celery + Redis;
- provider abstraction;
- OpenAI configuration foundation;
- model/default/allowlist foundation;
- common statuses/lifecycle;
- retry/failure foundation;
- structured-validation foundation;
- background-processing foundation;
- tests and docs required for this infrastructure.

**Do not implement full Lead Scoring, Deal Prediction, NBA, or Email Draft business functionality in D4.1.**

### D4.2 — Business Configuration + Lead Scoring

Implement:

- Categories/Services business configuration required by Lead Scoring;
- Target rate/Target effort;
- manager effort estimate;
- Budget/Desired deadline support as required;
- scoring weights;
- Commercial Value scale/math;
- Lead Scoring AI;
- `Другое` Category suggestion;
- Lead Scoring UI/freshness behavior.

### D4.3 — Deal Prediction

Implement:

- Prediction structured result;
- Communications/Tasks/time indicators;
- same-Client aggregate history;
- Confidence/signals/risks;
- freshness/manual recalculation;
- relevant UI/tests.

### D4.4 — Next Best Action

Implement:

- 1–3 ranked actions;
- primary context;
- auxiliary LS/DP context with freshness flags;
- independent manual NBA;
- initial LS + DP → NBA orchestration;
- relevant UI/tests.

### D4.5 — AI Email Draft

Implement:

- purpose/instructions;
- Client preferred communication language;
- generation;
- variants;
- EmailDraft persistence;
- manual editing/reopening/deleting;
- `{{client_name}}` substitution;
- no real sending;
- relevant UI/tests.

### D4.6 — AI History + Settings + Hardening

Complete/integrate:

- AI History UI;
- ADMIN AI Settings;
- Business/CRM Settings UI as needed;
- runtime toggles;
- model selection/reset;
- Prompt Injection warning integration;
- permissions hardening;
- rate limiting;
- i18n RU/EN/ES;
- remaining freshness/hardening behavior.

### D4.7 — Final Regression & Documentation

Perform:

- backend regression tests;
- frontend build/tests;
- migration verification;
- Celery/Redis runtime smoke;
- controlled real OpenAI smoke with minimal provider calls;
- browser smoke;
- authorization/security checks;
- i18n validation;
- documentation synchronization;
- final Day 4 report.

---

## 45. Codex execution/reporting contract

Existing `CODEX_RULES.md` remains authoritative.

For each substantial Day 4 iteration Codex must:

1. read the project source-of-truth docs;
2. read this `DAY4_AI_CONTRACT.md`;
3. read the latest `history/ANSWER_XX.md`;
4. stay strictly inside the requested iteration scope;
5. preserve modular-monolith architecture and existing security rules;
6. create new DB migrations rather than modifying old migrations;
7. run the required verification;
8. fully form a completion report;
9. save it as the next new `history/ANSWER_XX.md`;
10. send the same full report in the current Codex chat.

History reports are never overwritten.

At the close of D4.0, the latest baseline report is:

> `history/ANSWER_43.md`

Therefore the next substantial implementation report is expected to be:

> `history/ANSWER_44.md`

unless repository state shows a newer report.

Each iteration is accepted separately:

> Codex implementation → report → architectural/regression review → DONE or rework → only then next iteration.

---

## 46. Explicit superseding/refinement notes

The following final rules supersede earlier intermediate ideas.

### 46.1 Effort estimation

AI does **not** invent effort for Commercial Value.

Use:

1. manager Deal effort estimate when present;
2. otherwise Category Target effort.

### 46.2 Free-text PII redaction

Automatic PII redaction of Deal/Communication free text is **not part of Day 4 MVP**.

Structured PII is intentionally excluded where not required, but free-text anonymization is deferred.

### 46.3 Category suggestion

For Category `Другое`, AI only suggests an existing active Category as part of Lead Scoring.

AI does not mutate Deal Category.

Manager confirmation is mandatory.

### 46.4 Communications

Existing Communications remain CRM history records. Day 4 does not turn semantic EMAIL/TELEGRAM/WHATSAPP labels into real provider delivery integrations.

### 46.5 Capacity planning

Desired deadline may inform Feasibility, but Day 4 does not model real employee/team availability and cannot guarantee delivery capacity.

---

## 47. Architecture invariants

Throughout D4.1–D4.7 preserve these invariants:

- modular monolith;
- AI calls isolated behind AI service/provider layer;
- ordinary CRUD remains synchronous unless there is a specific approved reason otherwise;
- background LLM work uses Celery/Redis;
- backend authorization is authoritative;
- AI never silently mutates core Deal business data;
- AI never fabricates a fallback score on provider failure;
- AI results are validated before becoming successful CRM business results;
- historical AI records are not silently overwritten;
- manual AI functions remain independent after the initial new-Deal pipeline;
- no automatic email sending in Day 4;
- no secrets in source, DB business records, or logs;
- all schema changes use new migrations;
- RU/EN/ES i18n remains mandatory;
- existing Day 1–3 behavior must not regress.

---

## 48. D4.0 closure

D4.0 Architecture / Product Contract is **APPROVED and CLOSED**.

No further product redesign is required before D4.1.

If implementation reveals a genuine conflict with existing repository/source-of-truth state:

1. do not silently choose a different behavior;
2. report the conflict explicitly;
3. preserve existing project invariants;
4. obtain an architectural decision before materially changing this contract.

Next implementation stage:

> **D4.1 — AI Foundation**
