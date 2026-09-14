# VILEORUF CRM — требования

## 1. Цель продукта

Полнофункциональная CRM с AI-автоматизацией процесса продаж: оценкой, прогнозированием, рекомендациями и автоматизацией.

## 2. Бизнес-задачи

Исходная спецификация предусматривает:

- автоматизацию цикла продаж;
- прогнозирование выручки;
- умные рекомендации для менеджеров;
- интеграции с каналами коммуникации.

## 3. Веб-интерфейс CRM

### 3.1 Воронка продаж

- Воронка продаж в стиле Kanban.
- Перетаскивание сделок между стадиями.
- Сохранение изменений стадий в базе данных.
- Стадии Pipeline представлены данными, а не жёстко заданным состоянием только UI.

Используются стадии:

1. New Lead
2. Contact
3. Qualification
4. Proposal
5. Negotiation
6. Won
7. Lost

### 3.2 Клиенты

Записи Client поддерживают рабочий процесс CRM и содержат:

- имя / название компании;
- контактное лицо;
- email;
- телефон;
- идентификатор/username Telegram (необязательно);
- идентификатор/телефон/контакт WhatsApp (необязательно);
- компанию;
- источник лида;
- заметки;
- временные метки создания/обновления.

Каждый Client имеет бизнес-статус жизненного цикла, отдельный от ролей аутентификации:

- `CUSTOMER` (`Заказчик` в русском UI): человек/компания в CRM без успешно завершённой сделки;
- `CLIENT` (`Клиент` в русском UI): человек/компания хотя бы с одной сделкой, завершённой как `Won`.

Первый успешный переход в `Won` меняет `CUSTOMER` на `CLIENT`. Последующие проигранные сделки не возвращают `CLIENT` в `CUSTOMER` автоматически.

### 3.3 Сделки

Сделка принадлежит клиенту и содержит:

- название проекта/сделки;
- описание;
- оценочный бюджет;
- срок;
- стадию Pipeline;
- вероятность;
- ответственного пользователя;
- временные метки.

Оценочный бюджет — информация CRM о сделке, а не обработка платежей.

### 3.4 Communication history — Day 3 contract
`Communication` is an append-oriented CRM history record, not a live provider integration. It has `id`, required `client_id`, optional `deal_id`, `channel`, `direction`, `content`, actual communication timestamp, and `status`.

- Channels are `EMAIL`, `TELEGRAM`, `WHATSAPP`, `MANUAL`, and `OTHER`; they classify a CRM record only and do not imply a live integration.
- Directions are `INCOMING` and `OUTGOING`.
- The sole Day 3 status is `RECORDED`, meaning the communication fact is registered in CRM.
- If `deal_id` is present, that Deal must belong to the specified Client; the backend is authoritative for this invariant.
- Day 3 provides create and get/list/read only. DELETE and arbitrary edits are excluded.
- Both employee roles may read history. ADMIN may create for any Client/Deal. MANAGER may create client-level history for any existing Client and Deal-linked history only for Deals for which the manager is responsible.

Квитанции о доставке провайдера, идентификаторы сообщений провайдера, `SENT`/`DELIVERED`/`READ`, повторные попытки, ошибки провайдера, состояние синхронизации и реальные интеграции Gmail/Telegram/WhatsApp определяются финальным контрактом интеграций Day 5.

### 3.5 Tasks — Day 3 contract
`Task` is an internal CRM task with `id`, `title`, optional `description`, `due_at`, persisted completion `status`, `responsible_user_id`, and optional `client_id` and `deal_id`.

- Persisted statuses are only `OPEN` and `COMPLETED`. `OVERDUE`, if needed, is derived from an open task whose `due_at` is in the past; it is not stored.
- The responsible employee must be an active existing User with role ADMIN or MANAGER.
- General tasks without Client or Deal are allowed. If both relations are supplied, the Deal must belong to the Client. A task linked only to a Deal need not duplicate its Client; the backend enforces these relationship invariants.
- ADMIN can view all Tasks, create for any active ADMIN/MANAGER, update any Task, and reassign responsibility. MANAGER can view all Tasks, create only for themself, and update/complete only Tasks assigned to themself; a MANAGER cannot reassign a Task.
- Доступны создание, list/get, обновление и завершение через `status`; DELETE исключён.

## 4. Требования к AI

### 4.1 Lead scoring
Генерировать оценку лида и полезное пояснение.

### 4.2 Deal prediction
Оценивать вероятность/перспективу сделки на основе доступного контекста CRM.

### 4.3 Next best action
Рекомендовать следующее полезное действие менеджера на основе контекста клиента, сделки и коммуникаций.

### 4.4 Email generation
Генерировать черновик email из контекста CRM. AI не должен автоматически отправлять созданное AI письмо без явного действия пользователя.

## 5. Интеграции

Исходная спецификация предусматривает:
- Gmail API / email;
- Telegram;
- WhatsApp;
- Calendar.

Приоритет интеграций MVP:
1. Gmail
2. Telegram
3. Calendar
4. WhatsApp

Ограничения внешних API, учётные данные, верификация или доступ к провайдеру могут ограничивать работу реальной интеграции. Нельзя имитировать успешную реальную интеграцию. При внешней блокировке реализуется адаптер/интерфейс и документируется ограничение.

## 6. Analytics and reporting

Контракт MVP Analytics для Day 6 — [`ANALYTICS_CONTRACT.md`](ANALYTICS_CONTRACT.md). Он утверждает защищённый `/crm/analytics` для всей CRM, детерминированную агрегацию PostgreSQL во время чтения, количества клиентов/сделок, разбивку по сохраняемым стадиям, стоимость активного Pipeline, бюджет выигранных сделок, конверсию закрытых сделок и два месячных графика Deal. В этот MVP не входят взвешенный прогноз AI, выручка платежей/бухгалтерии, настраиваемая отчётность и BI.

## 7. Интернационализация (обязательно)

Языки:

- русский (`ru`) — по умолчанию и резервный;
- английский (`en`);
- испанский (`es`).

Требования:

- переключение языка из UI;
- выбранный язык сохраняется между сессиями;
- все пользовательские навигация, кнопки, формы, статусы, сообщения, ошибки, метки аналитики и настройки переводимы;
- в React-компонентах не должно быть жёстко заданных пользовательских строк там, где должны использоваться ключи перевода;
- архитектура переводов допускает добавление языков;
- локализуются даты, время и числовое форматирование.

## 8. Приватность / данные

Исходная спецификация устанавливает:

- тестовые данные;
- шифрование базы данных;
- соответствие GDPR.

Поскольку исходная спецификация не задаёт конкретных критериев приёмки для шифрования/GDPR, детали реализации должны быть документированы, а не неявно предполагаемы.

### 8.1 Аутентификация / авторизация

Аутентификация и авторизация обязательны для внутреннего интерфейса CRM. Реализованы аутентификация бэкенда/фронтенда, управление сотрудниками только для ADMIN и авторизация CRM по ролям/владению. ADMIN может просматривать/создавать/обновлять сотрудников, включая роль, имя и состояние активности; MANAGER это запрещено. Изменение email/пароля и физическое удаление отсутствуют. Самодеактивация/самопонижение роли и удаление последнего активного ADMIN отклоняются.

#### Пользователи и роли

Аутентифицированный `User` — только сотрудник VILEORUF Studio. Роли MVP:
- `ADMIN`;
- `MANAGER`.

Внешние заказчики — записи `Client`, а не учётные записи `User` или роли аутентификации. Они не получают вход в CRM или клиентский портал.

Минимальная модель `User` содержит `id`, уникальный логин `email`, `password_hash`, `display_name`, `role`, `is_active`, `created_at` и `updated_at`. Бэкенд использует UUID-первичный ключ, нативное PostgreSQL-перечисление ролей и временные метки с часовым поясом. Для увольнения сотрудника используется `is_active = false`; физическое удаление не является основным механизмом, поскольку на пользователя могут ссылаться исторические записи CRM.

#### Механизм аутентификации

Для входа используются email и пароль. Пароли никогда не хранятся в открытом виде и хешируются Argon2id. Политика паролей MVP: 12–128 символов, без обязательного сочетания классов символов и периодической принудительной смены.

Аутентификация использует JWT без серверного хранения сессий:
- access JWT: примерно 30 минут, хранится только в памяти React, никогда не в `localStorage` или `sessionStorage`, передаётся как `Authorization: Bearer <access-jwt>`;
- refresh JWT: примерно 7 дней, хранится/передаётся через недоступную JavaScript фронтенда cookie `HttpOnly`; в production обязателен `Secure=true`, а атрибуты cookie должны безопасно соответствовать окружению развёртывания;
- refresh выпускает новый access JWT, который остаётся только в памяти React.

Refresh MVP не имеет состояния до истечения `exp`: нет таблицы refresh-токенов, чёрного списка, серверного хранилища refresh-сессий или сложной инфраструктуры ротации/обнаружения повторного использования. Refresh и аутентифицированные API-запросы валидируют текущего пользователя, включая `is_active`; аутентифицированные запросы также применяют текущие правила ролей и владения. Выход удаляет access-токен из памяти и очищает refresh-cookie. Ранее выданный JWT без состояния нельзя централизованно отозвать без серверного состояния, поэтому access JWT остаётся краткоживущим.

MVP не включает вход OAuth/Google, SSO, LDAP, magic links, 2FA, верификацию email или сброс пароля по email без отдельного изменения требований.

#### Первоначальный bootstrap ADMIN

Публичной регистрации сотрудников нет. Защищённый CLI/bootstrap-механизм создаёт первого `ADMIN` из email, отображаемого имени и интерактивно введённого/подтверждённого хешируемого пароля. Он предназначен только для создания и отказывает в повторном bootstrap при существовании любого активного или неактивного ADMIN. Жёстко заданные/стандартные/master-учётные данные, учётные данные в Git или `.env.example` и development seed-данные как production-bootstrap ADMIN запрещены.

#### Авторизация

Авторизация бэкенда является источником истины; скрытие/отключение элементов на фронтенде — только UX-мера.

`ADMIN` may view, create, and edit all Clients and Deals; change the pipeline stage of any Deal; assign/change the responsible user; and has full CRM Core access within the approved MVP scope.

`MANAGER` may view all Clients and Deals, create Clients and Deals, and edit the common card of any Client. A manager may edit or move only their own Deals and may not modify other managers' Deals. Deal ownership is determined by `Deal.responsible_user_id` or an equivalent foreign-key relationship to `User`.

#### Публичные заявки

Публичные посетители не аутентифицируются и могут отправить публичную заявку без входа сотрудника. Внутренняя CRM остаётся защищённой для `ADMIN`/`MANAGER`. Внешние заказчики остаются записями `Client`, а не учётными записями `User`: публичная зона не является клиентским порталом и не предоставляет пароль, личный кабинет, вход для истории заказов, клиентский JWT или роль клиента.

Публичная заявка атомарно создаёт `Client(status=CUSTOMER)` и неназначенный Deal в системной стадии `New Lead`. Этот поток не создаёт новых сущностей `Lead`, `Inquiry` или `Request`.

#### Интернационализация аутентификации

Строки входа, ошибок аутентификации, выхода, отказа в доступе, управления пользователями и ролей, а также метки статуса жизненного цикла Client соответствуют обязательным правилам i18n: `ru` по умолчанию/резервный, `en` и `es`.

## 9. Явно вне текущего объёма

Если требования не изменены явно:
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

## 10. Артефакты поставки

Состав поставки:
- technical specification document (`.docx`);
- public GitHub repository;
- `README.md` explaining setup and operation;
- screenshots and screencasts demonstrating functionality.

## 11. Принцип приёмки

Функция считается завершённой только когда работает через релевантный поток фронтенд/бэкенд/база данных, воспроизводима и заведомо не нарушает существующую завершённую функциональность.
