# Day 6 — Analytics Architecture / Product Contract

## 1. Статус и границы

Этот документ утверждает границы MVP Analytics до начала реализации. D6.0 является documentation-only итерацией: код, API, frontend, schema, миграции, зависимости и seed-данные не изменяются.

Analytics — отдельный защищённый employee-раздел `/crm/analytics`. Он не заменяет `/crm`: существующий маршрут остаётся operational Dashboard с ближайшими Tasks, последними Communications и быстрыми действиями.

`ADMIN` и `MANAGER` получают CRM-wide Analytics, потому что текущая модель уже разрешает обеим ролям читать все Clients и Deals. Backend authorization остаётся authoritative. Отдельная модель `My Analytics` не входит в MVP.

## 2. Данные и архитектура

Analytics является synchronous read-time PostgreSQL aggregation существующих `Client`, `Deal` и `PipelineStage`. Не создаются Analytics entity, event store, warehouse, snapshots, materialized reporting tables или Celery/Redis workflow.

Источником truth служат текущие CRM business data. `AIAnalysis`, Deal Prediction, `probability_won`, confidence и AI weighted forecast в расчёт не входят.

Будущий основной endpoint — authenticated `GET /analytics/summary`. Он возвращает готовую ограниченную summary на backend; frontend не загружает все Clients/Deals для самостоятельного глобального расчёта.

## 3. Утверждённые показатели

### Клиенты

- Всего CRM-записей — количество всех `Client`.
- `CUSTOMER` — количество `Client.status = CUSTOMER`: CRM-заказчик/контакт без успешно завершённой Won-сделки.
- `CLIENT` — количество `Client.status = CLIENT`: клиент минимум с одной успешно завершённой Won-сделкой.

Новая Lead entity для Analytics не создаётся.

### Сделки

- Всего сделок — количество всех `Deal`.
- Активные сделки — Deal, чья текущая persisted `PipelineStage` не является системной `Won` или `Lost`.
- Won — Deal с текущей системной стадией `Won`.
- Lost — Deal с текущей системной стадией `Lost`.

Набор стадий и их порядок берутся из persisted `PipelineStage`, а не из frontend hard-code.

### Денежные показатели

**Стоимость активного Pipeline** — сумма `estimated_budget` всех активных Deal. Won и Lost не входят; Deal без бюджета входит в count и добавляет `0`. Currency single-organization MVP — EUR. Это estimated CRM value, не payment/accounting revenue.

**Стоимость выигранных сделок** — сумма `estimated_budget` всех Deal в текущей стадии Won. Это предполагаемые бюджеты, не подтверждённые оплаты, cash received или бухгалтерская выручка.

### Конверсия

**Конверсия закрытых сделок = Won / (Won + Lost) × 100%.** В denominator входят только сделки с известным текущим финальным результатом. Активные сделки исключены. При нулевом denominator будущий API/UI обязан вернуть безопасное отсутствующее или нулевое состояние без division-by-zero.

### Pipeline breakdown

Для каждой persisted PipelineStage summary содержит `stage_id`, display/stage name, порядок, количество Deal и сумму `estimated_budget`. Поведение `NULL` budget эквивалентно нулю только для денежных сумм.

## 4. Временные графики

В Analytics MVP утверждены только два графика.

1. **Созданные сделки по месяцам**: количество Deal, сгруппированное по календарным year/month `Deal.created_at`.
2. **Выигранные сделки по месяцам**: количество Deal по календарному year/month первого успешного Won-события.

Сложный configurable date-range UI не утверждён в D6.0. Будущий backend может заполнять месяцы с нулём только внутри явно определённого диапазона.

## 5. Будущая семантика `Deal.first_won_at`

D6.1 создаст nullable timezone-aware `first_won_at` и минимальную migration. Поле устанавливается backend только при первом успешном переходе существующей Deal в системную стадию Won; далее оно immutable, не очищается при выходе из Won и не меняется при повторном переходе в Won. Ordinary PATCH и frontend не могут его задавать или менять.

Это исторический business timestamp первого Won event, а не generic pipeline history. Ложный backfill запрещён: для исторической Deal, уже находящейся в Won без достоверной даты первого перехода, `first_won_at` остаётся `NULL`; нельзя использовать `updated_at`, `created_at`, предположения или AI inference. Будущий UI объясняет, что такие сделки могут отсутствовать в месячной Won-статистике.

## 6. Help, i18n и UX

Каждый основной KPI и график имеет локализованную встроенную справку через доступный мышью и клавиатурой information control; hover не является единственным механизмом. Справка объясняет определение, формулу, включаемые/исключаемые данные и ограничения.

Обязательные пояснения: active Pipeline исключает Won/Lost; conversion использует `Won / (Won + Lost)`; won value не является оплатой; Won-by-month использует `first_won_at` и не реконструирует неизвестную историческую дату.

Все labels, help, loading/empty/error states, графики, legends/axes, EUR, dates/months, percentages и numeric formatting локализуются через существующий RU(default)/EN/ES i18n механизм. `/crm/analytics` остаётся responsive; `/crm` не превращается в reporting page.

## 7. Non-goals

MVP не включает AI weighted forecast, custom reporting/report builder, BI, Excel/PDF export, stage-history warehouse, full funnel history, stage-to-stage conversion, sales-cycle duration, cohorts, manager leaderboard, lead-source/provider/payment analytics, invoices/revenue accounting, custom date ranges, historical reconstruction via `updated_at`, snapshots/materialized analytics tables, automatic AI calls, multi-currency, FX или conversion.

## 8. Утверждённая последовательность

- **D6.0** — этот contract/documentation-only этап.
- **D6.1** — `first_won_at` schema/lifecycle, minimal Alembic migration, transition update, backend `GET /analytics/summary`, authorization и PostgreSQL tests; без frontend.
- **D6.2** — `/crm/analytics`, navigation, KPI, breakdown, два графика, help UX, RU/EN/ES и responsive states.
- **D6.3** — CRM-wide i18n audit.
- **D6.4** — CRM-wide responsive/UX pass.
- **D6.5** — loading/empty/error states и final Day 6 verification.

Day 6 может стать complete только после отдельной D6.5 verification.
