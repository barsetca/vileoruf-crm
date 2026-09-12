# VILEORUF CRM — сценарий короткого screencast

Цель: показать MVP за **3–5 минут** без credentials, реальных персональных данных, live OpenAI calls или provider mutations. Основной язык записи — RU; рекомендуемый desktop viewport — `1440 × 900`.

## Подготовка до записи

1. Работать только в локальном development/demo environment, не в production.
2. Поднять приложение по [README](../../README.md). Для воспроизводимого CRM примера допустим documented development-only `seed_demo`; после записи при необходимости выполнить его documented `--clean`. Не использовать реальные контакты, сообщения, токены или пароли в кадре.
3. Войти под отдельным demo ADMIN account. Пароль не записывать, не показывать и не включать в сценарий.
4. Заранее открыть в отдельных tabs: `/`, `/login`, `/crm`, `/crm/clients`, `/crm/deals`, `/crm/pipeline`, `/crm/tasks`, `/crm/ai-history`, `/crm/inbox`, `/crm/settings/integrations`, `/crm/analytics`.
5. Подготовить только safe demo Client/Deal/Task/Communication. Для AI показать уже сохранённый/demo result либо AI History; не нажимать controls, которые запускают генерацию. Для integrations не нажимать Connect, Sync, Send, Check Bot либо Calendar mutation controls.

## Последовательность записи

| Время | Экран и действие | Короткий комментарий |
| --- | --- | --- |
| 0:00–0:30 | `/` — public request page | Посетитель оставляет обращение. Нормальный публичный flow создаёт CRM Client и Deal в системной стадии New Lead; customer portal не создаётся. Для записи можно показать заполненный demo form или уже созданный результат, без отправки нового обращения. |
| 0:30–0:50 | `/login` → `/crm` | Войти как employee. Показать Dashboard: задачи, последние коммуникации и быстрый переход к CRM areas. |
| 0:50–1:45 | `/crm/clients` → `/crm/deals` → deal detail | Открыть demo Client и связанную Deal. Показать поля карточки, responsible employee, бюджет/срок/вероятность и timeline. Не демонстрировать чужие или реальные записи. |
| 1:45–2:20 | `/crm/pipeline` → `/crm/tasks` → при наличии `/crm/inbox` | Показать Kanban по persisted stages и рабочую Task. Для Communication/Inbox показать только безопасную уже сохранённую demo запись; не выполнять отправку, linking или provider sync. |
| 2:20–3:05 | deal AI section или `/crm/ai-history` | Показать сохранённый advisory score/recommendation и историю. Подчеркнуть, что результат консультативный, а действия сотрудника контролируемы. Не запускать новый AI request. |
| 3:05–3:35 | `/crm/settings/integrations` | Показать безопасные status cards: Gmail, Telegram и Google Calendar реализованы и live verified ранее; WhatsApp — **отложено / технический долг**. Не запускать любые provider controls. |
| 3:35–4:10 | `/crm/analytics` | Показать CRM-wide KPI, pipeline breakdown и monthly charts. Не интерпретировать values как платежи или AI forecast. |
| 4:10–4:25 | language switch | Коротко показать RU/EN/ES selector либо сообщить, что CRM локализована в RU/EN/ES; оставить запись без credentials и technical tooling. |

## Безопасные границы записи

- Не записывать passwords, tokens, OAuth callback URLs, provider credentials, raw provider errors или browser developer tools.
- Не запускать OpenAI generation, Gmail send/sync, Telegram send, Google Calendar create/update/cancel или WhatsApp operation.
- Не использовать реальных клиентов либо личные контакты; сохранять только safe synthetic/demo fixtures.
- После временной demo preparation удалить fixture по её documented cleanup procedure. Не удалять shared development/production data или Docker volumes ради подготовки записи.

