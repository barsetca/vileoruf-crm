# VILEORUF CRM

VILEORUF CRM — полнофункциональная CRM для VILEORUF Studio: публичный сбор заявок, внутренняя работа с клиентами и продажами, AI-поддержка менеджеров и интеграции с корпоративными каналами. Проект реализован как модульный монолит и предназначен для локального запуска через Docker Compose.

## Статус MVP

Реализация MVP и техническая проверка завершены; проект **ТЕХНИЧЕСКИ ГОТОВ К ПЕРЕДАЧЕ**.

Архитектура системы описана в [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Возможности

### Пользователи и доступ

- Вход сотрудников по email/password; хеширование пароля с помощью Argon2id.
- JWT access token хранится только в памяти фронтенда; refresh token передаётся через cookie `HttpOnly`.
- Две роли: `ADMIN` и `MANAGER`.
- `ADMIN` управляет сотрудниками и настройками, работает со всеми CRM-записями.
- `MANAGER` видит Clients/Deals/Tasks, но изменяет чувствительные к владельцу данные Deal/AI/Task только в пределах действующих серверных правил.
- Внешние заказчики — записи `Client`, а не пользователи системы; клиентский портал отсутствует.



### CRM Core

- Публичная заявка требует корректный Email и отдельное согласие на обработку персональных данных, создаёт `Client(status=CUSTOMER)` с серверной датой и версиями документов, а также неназначенную Deal в системной стадии `New Lead`.
- Публичная форма ссылается на поддерживаемые владельцем русскоязычные PDF: [personal-data-consent.pdf](frontend/public/legal/personal-data-consent.pdf) и [privacy-policy.pdf](frontend/public/legal/privacy-policy.pdf). Текущие версии документов в приложении — `2026-09-10`; они заданы в `backend/app/services/public_requests.py`. При замене любого юридического PDF назначьте новую версию, обновите эту константу приложения и архивируйте предыдущую редакцию. Это описание реализации, а не юридическая консультация или общее заявление о соответствии российскому законодательству/GDPR.
- Clients: контактные данные, источник, заметки, предпочтительный язык общения и жизненный цикл `CUSTOMER → CLIENT` после первого успешного `Won`.
- Deals: Service/Category, бюджет, срок, вероятность, трудозатраты, ответственный сотрудник и сохраняемая стадия Pipeline.
- Pipeline: семь начальных стадий, перетаскивание Kanban и доступная альтернатива Move.
- Tasks: `OPEN`/`COMPLETED`, срок, ответственный и необязательные связи с Client/Deal.
- Communications: история с добавлением записей в контексте Client/Deal; `MANUAL` используется для ручной фиксации факта общения.
- Dashboard: компактный список ближайших открытых Tasks, последние Communications и быстрые переходы. Это операционный обзор, а не Analytics.



### AI

- Lead Scoring / «Привлекательность» 0–100 с детерминированным Commercial Value.
- Deal Prediction 0–100% с confidence, сигналами и рисками.
- Next Best Action: 1–3 advisory-рекомендации без автоматического исполнения.
- AI Email Draft: ручная генерация, редактирование и сохранение; автоматическая отправка запрещена.
- Начальная оркестрация новой Deal: параллельные Lead Scoring и Deal Prediction, затем NBA.
- Единая AI History, семантика актуальности/устаревания, валидация структурированного вывода, предупреждение о prompt injection, ADMIN AI Settings и ограничение частоты запросов Redis.
- AI-вызовы проходят через внутреннюю границу провайдера OpenAI и очередь Celery `ai`. Отсутствие `OPENAI_API_KEY` не блокирует обычную CRM.



### Интеграции

- Gmail: одно корпоративное подключение Google OAuth, явная отправка EmailDraft, ограниченная синхронизация входящих, сопоставление/устранение дублей и Communication только после подтверждённого факта от провайдера.
- Telegram: один корпоративный Bot, аутентифицированный webhook, жизненный цикл входящих/исходящих сообщений, несопоставленные записи Inbox и стабильное сопоставление пользователя провайдера.
- Google Calendar: отдельный `CalendarEvent`, явные операции create/update/cancel из контекста Client/Deal/Task, сохранение исторического состояния.
- Integration Settings доступны только `ADMIN`; секреты и OAuth tokens не возвращаются в UI/API.
- WhatsApp Business Platform / Cloud API не входит в поставленный MVP. Автоматизация потребительского/личного WhatsApp не допускается.



### Analytics и интерфейс

- Защищённая `/crm/analytics` использует синхронную агрегацию PostgreSQL по всей CRM: KPI Client/Deal, стоимость активного Pipeline, стоимость Won, конверсию закрытых сделок, разбивку по сохраняемым стадиям и две месячные серии Deal.
- UI поддерживает `ru` (по умолчанию/резервный), `en` и `es`; выбор языка сохраняется, даты/время/числа локализуются.
- Адаптивный интерфейс Modern Minimal Light проверен на desktop/tablet/mobile.



## Технологический стек


| Область         | Реализация                                                               |
| --------------- | ------------------------------------------------------------------------ |
| Фронтенд        | JavaScript, React 19, Vite 8, i18next/react-i18next                      |
| Бэкенд          | Python 3.10, FastAPI, Uvicorn, Pydantic Settings                         |
| Хранение данных | PostgreSQL 16, SQLAlchemy 2, Psycopg 3, Alembic                          |
| Фоновые задачи  | Celery 5, Redis 7; логические очереди `ai` и `integrations`              |
| Безопасность    | Argon2id, PyJWT/HS256, зашифрованные Fernet данные токенов Google        |
| Провайдеры      | OpenAI Responses API, Gmail API, Telegram Bot API, Google Calendar API   |
| Среда запуска   | Docker, Docker Compose                                                   |
| Проверка        | pytest, интеграционные тесты PostgreSQL, локальные CDP/Chromium-сценарии |


Точные закреплённые версии находятся в `backend/requirements.txt` и `frontend/package.json`.

## Архитектура

```text
Браузер / React
       |
       | REST/JSON
       v
Модульный монолит FastAPI -----> PostgreSQL
       |
       +---- постановка в очередь --> Redis --> воркер Celery
                                    |             |
                                  очередь ai   очередь integrations
                                    |             |
                                  OpenAI     Gmail / Telegram / Calendar
```

Бизнес-правила находятся в серверных сервисах; обработчики маршрутов остаются тонкими. AI и внешние провайдеры доступны только через собственные границы сервисов/адаптеров. `ExternalMessage` хранит жизненный цикл провайдера, `Communication` — подтверждённый CRM-факт; `Task` и `CalendarEvent` остаются разными сущностями. Подробнее: [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Структура репозитория

```text
backend/               приложение FastAPI, доменные сервисы, воркеры, Alembic, тесты
frontend/              приложение React/Vite и ресурсы локалей RU/EN/ES
docs/                  требования, архитектура, контракты этапов, документы передачи
docker-compose.yml     локальная среда PostgreSQL/Redis/backend/worker/frontend
.env.example           публичный шаблон конфигурации без секретов
.nvmrc                 поддерживаемая основная версия Node.js
README.md
```



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
- не добавляйте учётные данные провайдера, пока соответствующая операция не нужна.

`.env` игнорируется Git и не должен попадать в commit, логи или отчёты.

### 3. Запуск среды и миграций

```bash
docker compose up -d --build
docker compose ps
```

Backend ждёт готовности PostgreSQL и при старте автоматически выполняет `alembic upgrade head`. Текущая проверенная головная ревизия Alembic: `20260909_0016`. Затем запускаются FastAPI, Redis, воркер Celery с очередями `ai,integrations` и фронтенд Vite.

### 4. Обязательные начальные системные данные

После миграций выполните обе идемпотентные команды:

```bash
docker compose exec backend python -m backend.app.scripts.bootstrap_pipeline
docker compose exec backend python -m backend.app.scripts.bootstrap_business_catalog
```

Первая создаёт семь системных PipelineStage. Вторая создаёт минимальные Category и Service с фиксированными UUID: `Другое / Other / Otro` и `Общий запрос / General request / Solicitud general`. Это обязательные системные данные, а не демонстрационное заполнение; команды допустимы во всех окружениях и не создают пользователей.

### 5. Первый ADMIN

```bash
docker compose exec backend python -m backend.app.scripts.create_admin
```

CLI интерактивно запрашивает email, отображаемое имя и скрытый пароль с подтверждением. Он создаёт только первого `ADMIN`, использует единую политику Argon2id и отказывается от повторной инициализации, если ADMIN уже существует. Учётные данные по умолчанию отсутствуют.

### 6. Доступ

- Frontend: [http://localhost:5173](http://localhost:5173)
- Public request: [http://localhost:5173/](http://localhost:5173/)
- Employee login: [http://localhost:5173/login](http://localhost:5173/login)
- Backend: [http://localhost:8000](http://localhost:8000)
- Health: [http://localhost:8000/health](http://localhost:8000/health)
- PostgreSQL host port: `55432`
- Redis host port: `56379`

Для согласованной работы cookie/CORS используйте hostname `localhost` и для фронтенда, и для бэкенда.

### 7. Остановка

Остановить сервисы, сохранив данные:

```bash
docker compose down
```

Команда ниже удаляет тома PostgreSQL/Redis/frontend. Используйте её только для явно одноразового окружения после проверки, что данные не нужны:

```bash
docker compose down -v
```

Не выполняйте `down -v` в рабочем или близком к production окружении ради проверки чистого запуска; создайте отдельные проект Compose и тома.

## Необязательное демонстрационное заполнение

Демонстрационные данные отделены от системной инициализации и запрещены при `APP_ENV=production`:

```bash
docker compose exec backend python -m backend.app.scripts.seed_demo
docker compose exec backend python -m backend.app.scripts.seed_demo --clean
```

Сценарий заполнения идемпотентно создаёт только три вымышленных Clients и пять Deals, не создаёт учётные данные и удаляет через `--clean` только собственные детерминированные записи. См. [DEVELOPMENT_SEED_STRATEGY.md](docs/DEVELOPMENT_SEED_STRATEGY.md).

## Конфигурация


| Группа             | Основные переменные                                                                    | Назначение                                      |
| ------------------ | -------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Среда/база данных  | `APP_ENV`, `POSTGRES_*`, `POSTGRES_HOST_PORT`, `DATABASE_URL`                          | Режим среды и подключение PostgreSQL            |
| Источники/auth     | `FRONTEND_ORIGIN`, `VITE_API_BASE_URL`, `JWT_*`, `AUTH_COOKIE_SECURE`                  | CORS, URL API, срок/подпись JWT, refresh cookie |
| Очередь            | `REDIS_HOST_PORT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, флаги eager           | Транспорт Celery/хранилище результатов          |
| AI                 | `OPENAI_API_KEY`, model/default/allowlist, переменные timeout/retry/context/rate-limit | Провайдер OpenAI и ограниченное выполнение AI   |
| Google             | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, redirect/TTL                   | Корпоративный OAuth Gmail/Calendar              |
| Шифрование токенов | `INTEGRATION_TOKEN_ENCRYPTION_KEY`                                                     | Ключ шифрования Fernet; только в окружении      |
| Telegram           | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`                                        | Корпоративный Bot и подлинность webhook         |


Ключи/токены провайдеров необязательны для обычного запуска CRM. Реальные значения должны находиться только в локальных механизмах секретов или механизмах секретов развёртывания. После изменения их окружения пересоздайте `backend` и `celery_worker`:

```bash
docker compose up -d --force-recreate backend celery_worker
```

Локальный обратный вызов Google OAuth по умолчанию `http://localhost:8000/settings/integrations/google/callback`. Для веб-клиента OAuth в Google Cloud необходимо зарегистрировать точный URI перенаправления и включить API Gmail и Google Календаря. Для входящих сообщений Telegram требуется доступный для провайдера HTTPS-вебхук и соответствующая настройка секретного ключа.

### Telegram webhook — локальная разработка

Для доставки вебхуков Telegram требуется общедоступная HTTPS-конечная точка; Telegram не может получить доступ к `localhost`. В процессе локальной разработки уже установленный Cloudflare Quick Tunnel используется исключительно для временного тестирования владельцем или разработчиком.

1. Запустите CRM и убедитесь, что бэкенд доступен:
  ```bash
   docker compose up -d
   curl http://localhost:8000/health
  ```
2. Указывайте реальные значения только в файле `.env`, который игнорируется системой контроля версий (никогда не помещайте их в README или коммит):
  ```bash
   TELEGRAM_BOT_TOKEN=<bot-token>
   TELEGRAM_WEBHOOK_SECRET=<opaque-random-secret>
  ```
   Пересоздайте `backend`, если изменилось любое из значений.
3. В отдельном терминале запустите HTTPS-туннель к фактическому локальному порту бэкенда и не останавливайте этот процесс:
  ```bash
   cloudflared tunnel --url http://127.0.0.1:8000
  ```
   Скопируйте временный URL вида `https://<random>.trycloudflare.com`, выведенный `cloudflared`.
4. В оболочке, где доступны обе переменные, проверьте текущую регистрацию Telegram, установите новый webhook с существующим секретом, затем проверьте регистрацию снова:
  ```bash
   curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

   curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H 'Content-Type: application/json' \
     -d "{\"url\":\"https://<random>.trycloudflare.com/webhooks/telegram\",\"secret_token\":\"${TELEGRAM_WEBHOOK_SECRET}\"}"

   curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
  ```
   Итоговый ответ должен содержать точный временный URL и не содержать немедленного `last_error_message`. Не выводите, не сохраняйте и не передавайте ни одну из переменных. **Временный URL туннеля может измениться после перезапуска. Если это произошло, зарегистрируйте webhook Telegram повторно.**
5. Отправьте одно обычное новое текстовое сообщение Bot от реального пользователя Telegram. Убедитесь, что сопоставленное сообщение появилось в истории Communication соответствующих Client/Deal; если сопоставление невозможно, убедитесь, что оно отображается в `/crm/inbox`, и свяжите его с существующим Client. Если сообщение отсутствует в обоих местах, не перезапускайте бэкенд или туннель до сбора доказательств.



### Telegram webhook — примечание для production

В production нельзя использовать временный туннель. Production-путь:

```text
Telegram → стабильный публичный HTTPS-домен → обратный прокси TLS → backend /webhooks/telegram
```

Для него требуются стабильный публичный HTTPS URL, действующий TLS, обратный прокси к бэкенду, управляемый окружением `TELEGRAM_WEBHOOK_SECRET` и явный вызов Telegram `setWebhook` для production URL. Репозиторий не предоставляет развёртывание production или подсистему автоматической регистрации webhook.

## Основные маршруты

- `/` — публичная заявка.
- `/login` — вход сотрудника.
- `/crm` — операционный Dashboard.
- `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks` — основная часть CRM.
- `/crm/ai-history`, `/crm/inbox`, `/crm/analytics` — история AI, несопоставленные входящие от провайдеров, аналитика.
- `/crm/settings/business`, `/crm/settings/ai`, `/crm/settings/integrations` — настройки только для ADMIN.
- Управление сотрудниками находится в инструментах ADMIN внутри защищённой оболочки CRM; отдельного маршрута регистрации заказчика/сотрудника нет.



## Проверка

Проверка состояния/среды:

```bash
docker compose ps
curl http://localhost:8000/health
docker compose exec celery_worker celery -A backend.app.workers.celery_app:celery_app inspect active_queues
```

Тесты бэкенда из локального окружения Python:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pytest backend/tests
RUN_DATABASE_TESTS=1 APP_ENV=test .venv/bin/python -m pytest backend/tests
```

Тесты с PostgreSQL используют настроенный `DATABASE_URL`; не направляйте их на БД с данными, которые нельзя использовать для тестирования.

Проверка миграций:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini current
.venv/bin/python -m alembic -c backend/alembic.ini heads
.venv/bin/python -m alembic -c backend/alembic.ini check
```

Production-сборка фронтенда:

```bash
nvm use
cd frontend
npm install
npm run build
```

Сценарии lint/test фронтенда сейчас не настроены. Ручные CDP-сценарии браузера в `backend/tests/manual_*.py` — это инструменты проверки релиза, а не замена unit/integration tests.

## Примечания по безопасности

- Авторизация бэкенда является источником истины; скрытые элементы управления фронтенда не являются границей безопасности.
- Access/refresh JWT содержат только claims идентификации и времени; роль и активный статус повторно считываются из PostgreSQL.
- Данные OAuth token хранятся зашифрованными; ключ шифрования остаётся вне БД.
- Необработанные ошибки провайдеров, prompts, responses, учётные данные и tokens не должны попадать в API/UI/history.
- Сгенерированный AI клиентский контент отправляется только после явного действия сотрудника и подтверждения провайдера.
- Для fixtures/demo/проверки провайдеров используются только синтетические данные.
- Заявленная исходная спецификация не определяет достаточные критерии приёмки для общего шифрования базы данных/сертификации GDPR; проект не заявляет неподтверждённое соответствие требованиям.



## Известные ограничения и отложенная область работ

- WhatsApp Business Cloud API не входит в поставленный MVP; утверждённая архитектура сохраняется.
- В MVP не входят расширяемая детерминированная разбивка Commercial Value и улучшенное отображение состояния/сообщения AI о владельце для MANAGER.
- Автоматическое редактирование PII в свободном тексте Deal/Communication не реализовано.
- Нет клиентского портала, мультиарендности, платёжного/бухгалтерского функционала, полноценных клиентов email/мессенджера/календаря, платформы развёртывания/облака/CI.



## Документация

- [REQUIREMENTS.md](docs/REQUIREMENTS.md) — утверждённая область работ.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — подробная архитектура и проверенная реализация.
- [AI_CONTRACT.md](docs/AI_CONTRACT.md), [INTEGRATIONS_CONTRACT.md](docs/INTEGRATIONS_CONTRACT.md), [ANALYTICS_CONTRACT.md](docs/ANALYTICS_CONTRACT.md), [QA_DELIVERY_CONTRACT.md](docs/QA_DELIVERY_CONTRACT.md) — финальные продуктовые и QA-контракты.



## Демонстрационные материалы / материалы передачи

- [Манифест передачи](docs/delivery/README_DELIVERY.md) — итоговый перечень скриншотов и статус их подготовки владельцем.
- [Скринкаст](https://drive.google.com/file/d/1pS8ik4P3Qj6cuYkF0jxl8GjFR0NKSxt6/view?usp=sharing).
- [Техническое задание (RU)](docs/VILEORUF_CRM_TECHNICAL_ASSIGNMENT_RU.docx).
- [Техническая спецификация](docs/VILEORUF_CRM_TECHNICAL_SPECIFICATION.docx).
- [Руководство пользователя (RU)](docs/VILEORUF_CRM_USER_GUIDE_RU.docx).



## Логирование

Для локальных операционных журналов используйте Docker Compose без вывода значений окружения:

```bash
docker compose logs --tail=200 backend celery_worker frontend
docker compose logs -f backend celery_worker
```

Проект использует стандартные журналы Uvicorn/FastAPI и Celery/Docker, а также ограниченные сообщения аудита сервисов; централизованная платформа мониторинга или наблюдаемости не предусмотрена. В журналы, API-ответы и отчёты не должны попадать секреты, OAuth-токены, учётные данные, необработанные ответы провайдеров или персональные данные сверх необходимого для безопасной диагностики.

## Обработка ошибок

Обработка ошибок внешних интеграций, безопасные категории ошибок, повторные попытки и правила сокрытия необработанных ответов провайдеров описаны в разделе [«Retry and failure semantics»](docs/INTEGRATIONS_CONTRACT.md#16-retry-and-failure-semantics) файла [INTEGRATIONS_CONTRACT.md](docs/INTEGRATIONS_CONTRACT.md). Ошибки AI и политика повторных попыток описаны в [AI_CONTRACT.md](docs/AI_CONTRACT.md).

## Лицензия и публикация

Лицензия в репозитории пока не добавлена. Перед публикацией владелец должен выбрать лицензию либо явно оставить репозиторий без предоставления open-source лицензии, проверить итоговый diff, создать commits и самостоятельно выполнить публикацию на GitHub. Техническая готовность MVP не означает, что публичный репозиторий уже опубликован.