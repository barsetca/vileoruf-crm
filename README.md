# VILEORUF CRM

VILEORUF CRM — full-stack CRM для VILEORUF Studio: публичный сбор заявок, внутренняя работа с клиентами и продажами, AI-поддержка менеджеров и интеграции с корпоративными каналами. Проект реализован как модульный монолит и предназначен для локального запуска через Docker Compose.

## Статус MVP

- Day 1–4 — COMPLETE.
- Day 5 — COMPLETE WITH DEFERRED TECHNICAL DEBT: Gmail, Telegram и Google Calendar реализованы и live-verified; WhatsApp Business Cloud API — **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ**.
- Day 6 — COMPLETE: Analytics, RU/EN/ES, responsive UX и основные loading/empty/error states проверены.
- D7.1 — DONE / VERIFIED: isolated clean-start и representative browser acceptance прошли.
- Day 7 — DONE / VERIFIED; MVP implementation и technical verification завершены и **TECHNICALLY READY FOR DELIVERY**.

Подробный текущий статус хранится в [DEVELOPMENT_STATUS.md](docs/DEVELOPMENT_STATUS.md), архитектура — в [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Возможности

### Пользователи и доступ

- Employee login по email/password; Argon2id password hashing.
- JWT access token хранится только в памяти frontend; refresh token передаётся через `HttpOnly` cookie.
- Две роли: `ADMIN` и `MANAGER`.
- `ADMIN` управляет сотрудниками и настройками, работает со всеми CRM-записями.
- `MANAGER` видит Clients/Deals/Tasks, но изменяет ownership-sensitive Deal/AI/Task данные только в пределах действующих backend-правил.
- Внешние заказчики — записи `Client`, а не пользователи системы; customer portal отсутствует.

### CRM Core

- Публичная заявка требует отдельного согласия на обработку персональных данных, создаёт `Client(status=CUSTOMER)` с backend-authoritative датой и версиями документов и неназначенную Deal в системной стадии `New Lead`.
- Public form links to the owner-maintained Russian PDFs [`personal-data-consent.pdf`](frontend/public/legal/personal-data-consent.pdf) and [`privacy-policy.pdf`](frontend/public/legal/privacy-policy.pdf). Current application document versions are both `2026-09-10` in `backend/app/services/public_requests.py`; when either legal PDF is replaced, assign a new version, update that application constant, and archive the prior document revision. This is an implementation record, not legal advice or a general Russian/GDPR compliance claim.
- Clients: контактные данные, источник, заметки, preferred communication language и lifecycle `CUSTOMER → CLIENT` после первого успешного `Won`.
- Deals: Service/Category, бюджет, срок, вероятность, трудозатраты, ответственный сотрудник и persisted Pipeline stage.
- Pipeline: семь bootstrap-стадий, Kanban drag-and-drop и доступная Move-альтернатива.
- Tasks: `OPEN`/`COMPLETED`, срок, ответственный и необязательные связи с Client/Deal.
- Communications: append-oriented история в Client/Deal context; `MANUAL` используется для ручной фиксации факта общения.
- Dashboard: компактные ближайшие открытые Tasks, последние Communications и быстрые переходы. Это operational overview, не Analytics.

### AI

- Lead Scoring / «Привлекательность» 0–100 с детерминированным Commercial Value.
- Deal Prediction 0–100% с confidence, сигналами и рисками.
- Next Best Action: 1–3 advisory-рекомендации без автоматического исполнения.
- AI Email Draft: ручная генерация, редактирование и сохранение; автоматическая отправка запрещена.
- Initial new-Deal orchestration: Lead Scoring и Deal Prediction параллельно, затем NBA.
- Unified AI History, freshness/outdated semantics, structured output validation, prompt-injection warning, ADMIN AI Settings и Redis rate limit.
- AI-вызовы проходят через внутренний OpenAI provider boundary и Celery queue `ai`. Отсутствие `OPENAI_API_KEY` не блокирует обычную CRM.

### Интеграции

- Gmail: один corporate Google OAuth connection, explicit EmailDraft send, bounded inbound sync, matching/deduplication и Communication только после подтверждённого provider-факта.
- Telegram: один corporate Bot, authenticated webhook, inbound/outbound lifecycle, unmatched Inbox и stable provider-user matching.
- Google Calendar: отдельный `CalendarEvent`, explicit create/update/cancel из Client/Deal/Task context, сохранение исторического состояния.
- Integration Settings доступны только `ADMIN`; секреты и OAuth tokens не возвращаются в UI/API.
- WhatsApp Business Platform / Cloud API — **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ**. Consumer/personal WhatsApp automation не допускается.

### Analytics и интерфейс

- Защищённая `/crm/analytics` использует синхронную CRM-wide PostgreSQL aggregation: Client/Deal KPI, active Pipeline value, Won value, closed-deal conversion, breakdown по persisted stages и две monthly Deal series.
- UI поддерживает `ru` (default/fallback), `en` и `es`; выбор языка сохраняется, даты/время/числа локализуются.
- Responsive Modern Minimal Light интерфейс проверен на desktop/tablet/mobile в рамках Day 6.

## Технологический стек

| Область | Реализация |
|---|---|
| Frontend | JavaScript, React 19, Vite 8, i18next/react-i18next |
| Backend | Python 3.10, FastAPI, Uvicorn, Pydantic Settings |
| Persistence | PostgreSQL 16, SQLAlchemy 2, Psycopg 3, Alembic |
| Background work | Celery 5, Redis 7; logical queues `ai` и `integrations` |
| Security | Argon2id, PyJWT/HS256, Fernet-encrypted Google token payload |
| Providers | OpenAI Responses API, Gmail API, Telegram Bot API, Google Calendar API |
| Runtime | Docker, Docker Compose |
| Verification | pytest, PostgreSQL integration tests, local CDP/Chromium harnesses |

Точные pinned версии находятся в `backend/requirements.txt` и `frontend/package.json`.

## Архитектура

```text
Browser / React
       |
       | REST/JSON
       v
FastAPI modular monolith --------> PostgreSQL
       |
       +---- enqueue ----> Redis ----> Celery worker
                                    |             |
                                  ai queue   integrations queue
                                    |             |
                                  OpenAI     Gmail / Telegram / Calendar
```

Business rules находятся в backend services; route handlers остаются тонкими. AI и внешние providers доступны только через свои service/adapter boundaries. `ExternalMessage` хранит provider lifecycle, `Communication` — подтверждённый CRM-факт; `Task` и `CalendarEvent` остаются разными сущностями. Подробнее: [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Структура репозитория

```text
backend/               FastAPI app, domain services, workers, Alembic, tests
frontend/              React/Vite app and RU/EN/ES locale resources
docs/                  requirements, architecture, phase contracts, delivery docs
docker-compose.yml     local PostgreSQL/Redis/backend/worker/frontend runtime
.env.example           public non-secret configuration template
.nvmrc                 supported Node.js major version
README.md
```

`history/` — локальный ignored-каталог отчётов разработки, не delivery artifact.

## Быстрый локальный запуск

### 1. Требования

- Git.
- Docker Engine/Desktop с Docker Compose v2.

Python 3.10 и Node.js 24 нужны только для запуска команд вне контейнеров.

### 2. Получение и конфигурация

```bash
git clone <repository-url>
cd vileoruf-crm
cp .env.example .env
```

Отредактируйте `.env`:

- замените `POSTGRES_PASSWORD` и тот же пароль внутри `DATABASE_URL`;
- задайте сильный локальный `JWT_SECRET_KEY`;
- оставьте `AUTH_COOKIE_SECURE=false` только для локального HTTP;
- не добавляйте provider credentials, пока соответствующая операция не нужна.

`.env` игнорируется Git и не должен попадать в commit, логи или отчёты.

### 3. Запуск runtime и migrations

```bash
docker compose up -d --build
docker compose ps
```

Backend ждёт healthy PostgreSQL и при старте автоматически выполняет `alembic upgrade head`. Текущий verified Alembic head: `20260909_0016`. Затем запускаются FastAPI, Redis, Celery worker с queues `ai,integrations` и frontend Vite.

### 4. Обязательные system bootstrap data

После migrations выполните обе idempotent-команды:

```bash
docker compose exec backend python -m backend.app.scripts.bootstrap_pipeline
docker compose exec backend python -m backend.app.scripts.bootstrap_business_catalog
```

Первая создаёт семь системных PipelineStage. Вторая создаёт минимальные fixed-UUID Category `Другое / Other / Otro` и Service `Общий запрос / General request / Solicitud general`. Это обязательные system data, а не demo seed; команды допустимы во всех окружениях и не создают пользователей.

### 5. Первый ADMIN

```bash
docker compose exec backend python -m backend.app.scripts.create_admin
```

CLI интерактивно запрашивает email, display name и скрытый password с подтверждением. Он создаёт только первого `ADMIN`, использует общий Argon2id policy и отказывается от повторного bootstrap, если ADMIN уже существует. Default credentials отсутствуют.

### 6. Доступ

- Frontend: <http://localhost:5173>
- Public request: <http://localhost:5173/>
- Employee login: <http://localhost:5173/login>
- Backend: <http://localhost:8000>
- Health: <http://localhost:8000/health>
- PostgreSQL host port: `55432`
- Redis host port: `56379`

Для cookie/CORS consistency используйте именно hostname `localhost` для frontend и backend.

### 7. Остановка

Остановить сервисы, сохранив данные:

```bash
docker compose down
```

Команда ниже удаляет PostgreSQL/Redis/frontend volumes. Используйте её только для явно disposable окружения после проверки, что данные не нужны:

```bash
docker compose down -v
```

Не выполняйте `down -v` против working или production-like окружения ради clean-start проверки; создайте отдельный Compose project/volumes.

## Optional demo seed

Demo data отделены от system bootstrap и запрещены при `APP_ENV=production`:

```bash
docker compose exec backend python -m backend.app.scripts.seed_demo
docker compose exec backend python -m backend.app.scripts.seed_demo --clean
```

Seed idempotently создаёт только три fictitious Clients и пять Deals, не создаёт credentials и удаляет через `--clean` только собственные deterministic записи. См. [DEVELOPMENT_SEED_STRATEGY.md](docs/DEVELOPMENT_SEED_STRATEGY.md).

## Конфигурация

| Группа | Основные variables | Назначение |
|---|---|---|
| Runtime/database | `APP_ENV`, `POSTGRES_*`, `POSTGRES_HOST_PORT`, `DATABASE_URL` | Environment mode и PostgreSQL connection |
| Origins/auth | `FRONTEND_ORIGIN`, `VITE_API_BASE_URL`, `JWT_*`, `AUTH_COOKIE_SECURE` | CORS, API URL, JWT lifetime/signing, refresh cookie |
| Queue | `REDIS_HOST_PORT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, eager flags | Celery transport/result backend |
| AI | `OPENAI_API_KEY`, model/default/allowlist, timeout/retry/context/rate-limit variables | OpenAI provider и bounded AI execution |
| Google | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, redirect/TTL | Corporate Gmail/Calendar OAuth |
| Token encryption | `INTEGRATION_TOKEN_ENCRYPTION_KEY` | Fernet encryption key; environment-only |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` | Corporate Bot and webhook authenticity |

Provider keys/tokens are optional for ordinary CRM startup. Real values belong only in local/deployment secret mechanisms. Recreate `backend` and `celery_worker` after changing their environment:

```bash
docker compose up -d --force-recreate backend celery_worker
```

Google OAuth local callback defaults to `http://localhost:8000/settings/integrations/google/callback`. The Google Cloud Web OAuth client must register the exact redirect URI and enable Gmail plus Google Calendar APIs. Telegram inbound requires a provider-reachable HTTPS webhook and matching secret configuration.

### Telegram webhook — local development

Telegram webhook delivery needs a public HTTPS endpoint; `localhost` is not reachable by Telegram. The local development path uses the already installed Cloudflare Quick Tunnel only for a temporary owner/developer test.

1. Start the CRM and confirm the backend is available:

   ```bash
   docker compose up -d
   curl http://localhost:8000/health
   ```

2. Put real values only in the ignored `.env` file (never in README or a commit):

   ```bash
   TELEGRAM_BOT_TOKEN=<bot-token>
   TELEGRAM_WEBHOOK_SECRET=<opaque-random-secret>
   ```

   Recreate `backend` if either value changed:

   ```bash
   docker compose up -d --force-recreate backend
   ```

3. In a separate terminal, start the HTTPS tunnel to the actual local backend port and keep this terminal/process running:

   ```bash
   cloudflared tunnel --url http://127.0.0.1:8000
   ```

   Copy the temporary `https://<random>.trycloudflare.com` URL printed by `cloudflared` and form:

   ```text
   https://<random>.trycloudflare.com/webhooks/telegram
   ```

4. From a shell where the two variables are available, inspect the current Telegram registration, set the new webhook with the existing secret, then inspect it again:

   ```bash
   curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

   curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H 'Content-Type: application/json' \
     -d "{\"url\":\"https://<random>.trycloudflare.com/webhooks/telegram\",\"secret_token\":\"${TELEGRAM_WEBHOOK_SECRET}\"}"

   curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
   ```

   The final response must show the exact temporary URL and no immediate `last_error_message`. Do not print, save, or share either variable. **A temporary tunnel URL can change after a tunnel restart. If it changes, register Telegram webhook again.**

5. Send one ordinary new text message to the Bot from a real Telegram user. Confirm a matched message in that Client/Deal Communication history; if it cannot be matched, confirm it in `/crm/inbox` and link it to an existing Client. Do not restart backend or the tunnel before collecting evidence if the message is absent from both locations.

### Telegram webhook — production note

Production must not use a temporary tunnel. The production path is:

```text
Telegram → stable public HTTPS domain → TLS reverse proxy → backend /webhooks/telegram
```

It requires a stable public HTTPS URL, valid TLS, a reverse proxy to the backend, an environment-managed `TELEGRAM_WEBHOOK_SECRET`, and an explicit Telegram `setWebhook` call for the production URL. No production deployment or automatic webhook-registration subsystem is provided by this repository.

## Основные routes

- `/` — public request.
- `/login` — employee login.
- `/crm` — operational Dashboard.
- `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks` — CRM Core.
- `/crm/ai-history`, `/crm/inbox`, `/crm/analytics` — AI history, unmatched provider inbox, Analytics.
- `/crm/settings/business`, `/crm/settings/ai`, `/crm/settings/integrations` — ADMIN-only settings.
- Employee management находится в ADMIN tools внутри protected CRM shell; отдельного customer/employee registration route нет.

## Проверка

Health/runtime:

```bash
docker compose ps
curl http://localhost:8000/health
docker compose exec celery_worker celery -A backend.app.workers.celery_app:celery_app inspect active_queues
```

Backend tests из локального Python environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pytest backend/tests
RUN_DATABASE_TESTS=1 APP_ENV=test .venv/bin/python -m pytest backend/tests
```

PostgreSQL-backed tests используют настроенный `DATABASE_URL`; не направляйте их на БД с данными, которые нельзя использовать для тестирования.

Migration checks:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini current
.venv/bin/python -m alembic -c backend/alembic.ini heads
.venv/bin/python -m alembic -c backend/alembic.ini check
```

Frontend production build:

```bash
nvm use
cd frontend
npm install
npm run build
```

Frontend lint/test scripts сейчас не настроены. Manual CDP browser harnesses в `backend/tests/manual_*.py` являются release-verification tooling, а не заменой unit/integration tests.

## Security notes

- Backend authorization authoritative; скрытые frontend controls не являются security boundary.
- Access/refresh JWT содержат только identity/timing claims; role и active state перечитываются из PostgreSQL.
- OAuth token payload хранится encrypted; ключ шифрования остаётся вне БД.
- Raw provider errors, prompts, responses, credentials и tokens не должны попадать в API/UI/history.
- AI-generated client content отправляется только после explicit employee action и provider confirmation.
- Для fixtures/demo/provider verification используются только synthetic data.
- Заявленная source specification не определяет достаточных acceptance criteria для общей database encryption/GDPR certification; проект не делает неподтверждённых compliance claims.

## Известные ограничения и deferred scope

- WhatsApp Business Cloud API — **ОТЛОЖЕНО / ТЕХНИЧЕСКИЙ ДОЛГ** после MVP; approved architecture сохраняется.
- Expandable deterministic Commercial Value breakdown — deferred UX enhancement.
- Enhanced MANAGER AI ownership state/message — deferred role-aware UX enhancement.
- Automatic free-text PII redaction для Deal/Communication content не реализован.
- Нет customer portal, multi-tenancy, payment/accounting, full email/messenger/calendar clients, deployment/cloud/CI platform.

## Документация

- [REQUIREMENTS.md](docs/REQUIREMENTS.md) — approved scope.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — detailed architecture and verified implementation.
- [PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) — compact current context.
- [DEVELOPMENT_STATUS.md](docs/DEVELOPMENT_STATUS.md) — operational progress.
- [DAY4_AI_CONTRACT.md](docs/DAY4_AI_CONTRACT.md), [DAY5_INTEGRATIONS_CONTRACT.md](docs/DAY5_INTEGRATIONS_CONTRACT.md), [DAY6_ANALYTICS_CONTRACT.md](docs/DAY6_ANALYTICS_CONTRACT.md), [DAY7_QA_DELIVERY_CONTRACT.md](docs/DAY7_QA_DELIVERY_CONTRACT.md) — phase contracts.

## License and publication

Лицензия в репозитории пока не добавлена. Перед publication владелец должен выбрать лицензию либо явно оставить repository без предоставления open-source license, проверить итоговый diff, создать commits и самостоятельно выполнить GitHub publication. Техническая готовность MVP не означает, что public repository уже опубликован.
