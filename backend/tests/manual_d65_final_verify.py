"""Bounded D6.5 state and final Day 6 Chromium verification.

Run from the repository root with:
    .venv/bin/python backend/tests/manual_d65_final_verify.py

Only synthetic database fixtures and browser-local fetch interception are used.
No AI or external-provider mutation is invoked. Cleanup is guaranteed in finally.
"""

import json
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from sqlalchemy import delete, func, select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.db.session import SessionLocal
from backend.app.models import User, UserRole
from backend.app.services.users import create_user
from backend.tests import manual_d63a_ru_browser_verify as base
from backend.tests import manual_d64_responsive_verify as responsive

BASE_URL = "http://localhost:5173"
PORT = 9900 + secrets.randbelow(90)
PROFILE = Path(f"/tmp/d65-chrome-{secrets.token_hex(6)}")
MANAGER_EMAIL = f"d65-manager-{secrets.token_hex(8)}@example.invalid"
MANAGER_PASSWORD = secrets.token_urlsafe(24)
RAW_MARKER = "RAW_BACKEND_STACKTRACE_D65_MUST_NOT_RENDER"

chrome = None
manager_id = None
results = {
    "loading": {}, "empty": {}, "error_retry": {}, "mutation_error": {},
    "ai_states": {}, "integration_states": {}, "analytics": {},
    "responsive": {}, "i18n": {}, "admin_smoke": {}, "manager_smoke": {},
}


def wait_for(cdp, condition, description, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cdp.evaluate(f"Boolean({condition})"):
            return
        time.sleep(0.1)
    body = cdp.evaluate("document.body ? document.body.innerText.slice(0, 2000) : ''")
    raise AssertionError(f"Timeout waiting for {description}; body={body!r}")


def navigate(cdp, path):
    cdp.call("Page.navigate", {"url": f"{BASE_URL}{path}"})
    wait_for(cdp, "document.readyState === 'complete'", f"document load {path}")


def rendered(cdp):
    return cdp.evaluate("document.body.innerText")


def set_intercepts(cdp, rules):
    cdp.evaluate(f"localStorage.setItem('__d65_intercepts', {json.dumps(json.dumps(rules))})")


def clear_intercepts(cdp):
    cdp.evaluate("localStorage.removeItem('__d65_intercepts')")


def rule(path, *, method="GET", mode="error", body=None, delay_ms=1400):
    value = {"path": path, "method": method, "mode": mode, "delayMs": delay_ms}
    if body is not None:
        value["body"] = body
    return value


def set_value(cdp, selector, value):
    cdp.evaluate(f"""(() => {{
      const element=document.querySelector({json.dumps(selector)});
      if (!element) throw new Error('missing form control');
      const prototype=element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(prototype,'value').set.call(element,{json.dumps(value)});
      element.dispatchEvent(new Event('input',{{bubbles:true}}));
      element.dispatchEvent(new Event('change',{{bubbles:true}}));
    }})()""")


def click(cdp, expression, description):
    wait_for(cdp, expression, description)
    cdp.evaluate(f"({expression}).click()")


def assert_safe_error(cdp, expected_text):
    text = rendered(cdp)
    assert expected_text in text, f"missing localized error {expected_text!r}"
    assert RAW_MARKER not in text, "raw backend body reached UI"
    assert cdp.evaluate("Boolean(document.querySelector('.crm-shell'))"), "CRM shell was replaced by state error"


def verify_loading(cdp):
    cases = [
        ("Clients", "/crm/clients", "/clients", "Загружаем клиентов"),
        ("Deals", "/crm/deals", "/deals", "Загружаем сделки"),
        ("Tasks", "/crm/tasks", "/tasks", "Загружаем задачи"),
        ("AI History", "/crm/ai-history", "/ai-history", "Загрузка истории AI"),
        ("Inbox", "/crm/inbox", "/inbox/external-messages", "Загружаем входящие сообщения"),
        ("Analytics", "/crm/analytics", "/analytics/summary", "Загружаем аналитику"),
        ("Business Settings", "/crm/settings/business", "/business/categories", "Загружаем бизнес-настройки"),
        ("Integration Settings", "/crm/settings/integrations", "/settings/integrations", "Загружаем настройки интеграций"),
    ]
    for name, route, path, text in cases:
        set_intercepts(cdp, [rule(path, mode="delay")])
        navigate(cdp, route)
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(text)})", f"{name} loading")
        assert cdp.evaluate("Boolean(document.querySelector('.crm-shell'))")
        assert RAW_MARKER not in rendered(cdp)
        clear_intercepts(cdp)
        results["loading"][name] = "PASS — локализованный state внутри работающего CRM shell"
        time.sleep(1.5)


def zero_analytics():
    return {
        "clients": {"total": 0, "customer": 0, "client": 0},
        "deals": {"total": 0, "active": 0, "won": 0, "lost": 0},
        "active_pipeline_estimated_value": "0", "won_deals_estimated_value": "0",
        "closed_deal_conversion_percent": None,
        "pipeline_stages": [{"stage_id": "00000000-0000-0000-0000-000000000001", "stage_name": "New Lead", "position": 1, "deal_count": 0, "estimated_value": "0"}],
        "created_deals_by_month": [], "first_won_deals_by_month": [],
    }


def verify_empty(cdp, ids):
    cases = [
        ("Clients", "/crm/clients", [rule("/clients", mode="json", body=[])], "Клиентов пока нет"),
        ("Deals", "/crm/deals", [rule("/deals", mode="json", body=[])], "Сделок пока нет"),
        ("Tasks", "/crm/tasks", [rule("/tasks", mode="json", body=[])], "Задачи не найдены"),
        ("AI History", "/crm/ai-history", [rule("/ai-history", mode="json", body={"items": [], "total": 0, "limit": 20, "offset": 0})], "Подходящих AI-операций нет"),
        ("Inbox", "/crm/inbox", [rule("/inbox/external-messages", mode="json", body=[])], "Очередь пуста"),
        ("Analytics", "/crm/analytics", [rule("/analytics/summary", mode="json", body=zero_analytics())], "Для графика пока недостаточно"),
    ]
    for name, route, rules, text in cases:
        set_intercepts(cdp, rules); navigate(cdp, route)
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(text)})", f"{name} empty")
        assert "Не удалось" not in rendered(cdp)
        results["empty"][name] = "PASS — controlled API empty response"
        clear_intercepts(cdp)

    navigate(cdp, "/crm/pipeline")
    wait_for(cdp, "document.querySelectorAll('.kanban-column').length >= 7", "pipeline stages")
    wait_for(cdp, "document.querySelector('.kanban-stage-empty')", "empty pipeline stage")
    results["empty"]["Pipeline stage"] = "PASS — отдельное объяснение внутри пустой persisted stage"

    empty_deal_rules = [
        rule("/communications", mode="json", body=[]),
        rule("/calendar-events", mode="json", body=[]),
        rule(f"/deals/{ids['deal']}/email-drafts", mode="json", body=[]),
        rule(f"/deals/{ids['deal']}/email-draft", mode="json", body={"active": None, "current": None, "latest_attempt": None}),
        rule(f"/deals/{ids['deal']}/next-best-action", mode="json", body={"active": None, "current": None, "history": []}),
    ]
    set_intercepts(cdp, empty_deal_rules); navigate(cdp, f"/crm/deals?deal={ids['deal']}")
    wait_for(cdp, "document.querySelector('#deal-modal-title')", "deal modal empty sections")
    wait_for(cdp, "document.body.innerText.includes('Коммуникаций пока нет') && document.body.innerText.includes('Связанных событий календаря пока нет') && document.body.innerText.includes('Сохранённых черновиков пока нет')", "timeline/calendar/draft empty states")
    for name in ("Communications/Timeline", "Calendar", "Email drafts/history"):
        results["empty"][name] = "PASS — controlled empty section in Deal details"
    clear_intercepts(cdp)


def verify_error_retry(cdp):
    cases = [
        ("Clients read", "/crm/clients", "/clients", "Не удалось загрузить клиентов", ".state-panel .secondary-button", ".clients-table"),
        ("Deals read", "/crm/deals", "/deals", "Не удалось загрузить сделки", ".state-panel .secondary-button", ".deals-table"),
        ("Tasks", "/crm/tasks", "/tasks", "Не удалось загрузить задачи", ".state-panel .secondary-button", ".tasks-table"),
        ("AI History", "/crm/ai-history", "/ai-history", "Не удалось загрузить историю AI", ".state-panel .secondary-button", ".ai-history-list"),
        ("Inbox", "/crm/inbox", "/inbox/external-messages", "Не удалось загрузить очередь входящих", ".state-panel .secondary-button", ".inbox-list"),
        ("Analytics", "/crm/analytics", "/analytics/summary", "Не удалось безопасно загрузить аналитику", ".state-panel .secondary-button", ".analytics-kpis"),
        ("Business Settings", "/crm/settings/business", "/business/categories", "Не удалось загрузить или сохранить бизнес-настройки", ".state-panel .secondary-button", ".settings-grid"),
        ("AI Settings", "/crm/settings/ai", "/settings/ai", "Не удалось загрузить или сохранить настройки AI", ".state-panel .secondary-button", ".ai-settings-form"),
        ("Integration Settings", "/crm/settings/integrations", "/settings/integrations", "Не удалось загрузить настройки интеграций", ".state-panel .secondary-button", ".settings-grid"),
    ]
    for name, route, path, text, retry_selector, recovered_selector in cases:
        set_intercepts(cdp, [rule(path)])
        navigate(cdp, route)
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(text)})", f"{name} safe error")
        assert_safe_error(cdp, text)
        clear_intercepts(cdp)
        cdp.evaluate(f"document.querySelector({json.dumps(retry_selector)}).click()")
        wait_for(cdp, f"document.querySelector({json.dumps(recovered_selector)})", f"{name} retry recovery")
        results["error_retry"][name] = "PASS — synthetic 503, raw body hidden, Retry recovered without page reload"


def verify_mutations(cdp, ids):
    # Client create error preserves entered data.
    navigate(cdp, "/crm/clients"); wait_for(cdp, "document.querySelector('.clients-table')", "clients ready")
    click(cdp, "document.querySelector('.page-action')", "client create")
    marker = "D65 сохранённый клиент"
    set_value(cdp, ".client-modal input[name='name']", marker)
    set_intercepts(cdp, [rule("/clients", method="POST")]); cdp.evaluate("document.querySelector('.client-modal form').requestSubmit()")
    wait_for(cdp, "document.querySelector('.client-modal .form-error')", "client mutation error")
    assert cdp.evaluate("document.querySelector('.client-modal input[name=name]').value") == marker
    assert RAW_MARKER not in rendered(cdp); clear_intercepts(cdp)
    results["mutation_error"]["Client save"] = "PASS — localized error, value retained, no false success"

    # Deal create error preserves entered data.
    cdp.evaluate("document.querySelector('.client-modal .icon-button').click()")
    navigate(cdp, "/crm/deals"); wait_for(cdp, "document.querySelector('.deals-table')", "deals ready")
    click(cdp, "document.querySelector('.page-action')", "deal create")
    marker = "D65 сохранённая сделка"; set_value(cdp, ".client-modal input[name='name']", marker)
    set_intercepts(cdp, [rule("/deals", method="POST")]); cdp.evaluate("document.querySelector('.client-modal form').requestSubmit()")
    wait_for(cdp, "document.querySelector('.client-modal .form-error')", "deal mutation error")
    assert cdp.evaluate("document.querySelector('.client-modal input[name=name]').value") == marker
    clear_intercepts(cdp); results["mutation_error"]["Deal save"] = "PASS — localized error, value retained, no false success"

    # Task completion failure leaves task OPEN and exposes safe error.
    navigate(cdp, "/crm/tasks"); wait_for(cdp, "document.querySelector('.tasks-table')", "tasks ready")
    click(cdp, f"Array.from(document.querySelectorAll('.tasks-table tbody tr')).find(x=>x.innerText.includes({json.dumps(base.PREFIX)}))", "task row")
    set_intercepts(cdp, [rule(f"/tasks/{ids['task']}/complete", method="POST")])
    click(cdp, "Array.from(document.querySelectorAll('.client-modal .deal-actions button')).find(x=>x.textContent.includes('Завершить'))", "complete task")
    wait_for(cdp, "document.querySelector('.client-modal .form-error')", "task complete error")
    assert "Открыта" in rendered(cdp); clear_intercepts(cdp)
    results["mutation_error"]["Task complete"] = "PASS — task remained OPEN, localized error, no false success"

    # Manual Communication error preserves message.
    navigate(cdp, f"/crm/deals?deal={ids['deal']}"); wait_for(cdp, "document.querySelector('.communication-form textarea[name=content]')", "communication form")
    marker = "D65 несохранённая коммуникация"; set_value(cdp, ".communication-form textarea[name='content']", marker)
    set_intercepts(cdp, [rule("/communications", method="POST")]); cdp.evaluate("document.querySelector('.communication-form').requestSubmit()")
    wait_for(cdp, "document.querySelector('.communication-form .form-error')", "communication mutation error")
    assert cdp.evaluate("document.querySelector('.communication-form textarea[name=content]').value") == marker
    clear_intercepts(cdp); results["mutation_error"]["Communication create"] = "PASS — safe error and entered content retained"

    # Settings save error stays inline and preserves changed field.
    navigate(cdp, "/crm/settings/business"); wait_for(cdp, "document.querySelector('.settings-card--wide form')", "business settings")
    selector = ".settings-card--wide input[type=number]"; old = cdp.evaluate(f"document.querySelector({json.dumps(selector)}).value")
    changed = "31" if old != "31" else "32"; set_value(cdp, selector, changed)
    wait_for(cdp, f"document.querySelector({json.dumps(selector)}).value === {json.dumps(changed)}", "settings changed value")
    set_intercepts(cdp, [rule("/business/lead-scoring-settings", method="PUT")]); cdp.evaluate("document.querySelector('.settings-card--wide form').requestSubmit()")
    wait_for(cdp, "document.body.innerText.includes('Введённые данные сохранены')", "settings mutation error")
    actual = cdp.evaluate(f"document.querySelector({json.dumps(selector)}).value")
    assert actual == changed, f"settings value was not preserved: expected={changed!r}, actual={actual!r}"
    assert cdp.evaluate("document.querySelectorAll('.settings-card').length >= 3"), "settings cards disappeared after mutation failure"
    clear_intercepts(cdp); results["mutation_error"]["Settings save"] = "PASS — screen/data retained and no false success"


def verify_ai_and_integrations(cdp, ids):
    now = "2026-09-09T10:00:00Z"
    def item(suffix, function_type, status, *, outdated=False, payload=None, error=None):
        return {"id": f"00000000-0000-0000-0000-0000000000{suffix}", "deal_id": ids["deal"], "deal_name": f"{base.PREFIX} state deal", "function_type": function_type, "status": status, "language": "RU", "actual_model": "synthetic-no-provider" if status == "SUCCESS" else None, "created_at": now, "started_at": None if status == "QUEUED" else now, "finished_at": now if status in ("SUCCESS", "FAILED") else None, "duration_ms": 1 if status in ("SUCCESS", "FAILED") else None, "attempt_count": 1, "provider_usage": None, "is_current": status == "SUCCESS", "is_outdated": outdated, "result_valid": status == "SUCCESS", "result_payload": payload, "error_category": error}
    prediction = {"probability_won": 65, "confidence": "MEDIUM", "summary": "Синтетический исторический результат", "positive_signals": [], "risks": [], "missing_context": []}
    items = [
        item("21", "LEAD_SCORING", "QUEUED"),
        item("22", "NEXT_BEST_ACTION", "RUNNING"),
        item("23", "DEAL_PREDICTION", "SUCCESS", outdated=True, payload=prediction),
        item("24", "EMAIL_DRAFT", "FAILED", error="PROVIDER_UNAVAILABLE"),
    ]
    set_intercepts(cdp, [rule("/ai-history", mode="json", body={"items": items, "total": 4, "limit": 20, "offset": 0})])
    navigate(cdp, "/crm/ai-history"); wait_for(cdp, "document.querySelectorAll('.ai-history-list details').length === 4", "AI states")
    text = rendered(cdp)
    for label in ("В очереди", "Выполняется", "Успешно", "Ошибка", "Возможно устарело"):
        assert label in text
    cdp.evaluate("document.querySelectorAll('.ai-history-list details')[3].open=true")
    wait_for(cdp, "document.body.innerText.includes('Провайдер недоступен')", "safe AI failure")
    assert RAW_MARKER not in rendered(cdp); clear_intercepts(cdp)
    results["ai_states"] = {"QUEUED/PENDING": "PASS", "RUNNING": "PASS", "SUCCESS historical": "PASS", "FAILED safe": "PASS", "outdated": "PASS", "provider_calls": 0}

    connections = [
        {"id": None, "provider": "GMAIL", "status": "CONNECTED", "display_name": "Gmail", "external_account_email": "synthetic@example.invalid", "last_success_at": now, "last_error_code": None, "inbound_sync_status": "ERROR", "inbound_sync_error_code": "PROVIDER_UNAVAILABLE"},
        {"id": None, "provider": "TELEGRAM", "status": "ERROR", "display_name": "Telegram", "external_account_id": None, "last_error_code": "INVALID_CONFIGURATION", "inbound_sync_status": "IDLE"},
        {"id": None, "provider": "GOOGLE_CALENDAR", "status": "CONNECTED", "display_name": "Google Calendar", "external_account_email": "synthetic@example.invalid", "last_success_at": now, "inbound_sync_status": "IDLE"},
        {"id": None, "provider": "WHATSAPP", "status": "DISCONNECTED", "display_name": "WhatsApp", "inbound_sync_status": "IDLE"},
    ]
    set_intercepts(cdp, [rule("/settings/integrations", mode="json", body=connections)])
    navigate(cdp, "/crm/settings/integrations"); wait_for(cdp, "document.querySelectorAll('[data-testid^=integration-card-]').length === 4", "integration states")
    text = rendered(cdp)
    missing = [label for label in ("Подключено", "Требуется повторное подключение", "Провайдер временно недоступен", "Отложено / технический долг") if label not in text]
    assert not missing and RAW_MARKER not in text, f"integration state labels missing={missing}; body={text[:1800]!r}"
    clear_intercepts(cdp)

    calendar = [{"id": f"00000000-0000-0000-0000-00000000003{i}", "title": title, "description": "Synthetic only", "start_at": now, "end_at": "2026-09-09T11:00:00Z", "timezone": "Europe/Madrid", "status": status, "external_url": "https://calendar.google.com/" if status == "SYNCED" else None} for i, (title, status) in enumerate((("Pending", "PENDING"), ("Synced", "SYNCED"), ("Error", "ERROR"), ("Cancelled", "CANCELLED")), 1)]
    set_intercepts(cdp, [rule("/calendar-events", mode="json", body=calendar)])
    navigate(cdp, "/crm/tasks"); wait_for(cdp, "document.querySelector('.tasks-table')", "task list for calendar states")
    click(cdp, f"Array.from(document.querySelectorAll('.tasks-table tbody tr')).find(x=>x.innerText.includes({json.dumps(base.PREFIX)}))", "calendar task")
    wait_for(cdp, "document.querySelectorAll('[data-testid^=calendar-event-]').length >= 4", "calendar lifecycle states")
    text = rendered(cdp)
    for label in ("Ожидает синхронизации", "Синхронизировано", "Ошибка синхронизации", "Отменено"):
        assert label in text
    clear_intercepts(cdp)
    results["integration_states"] = {"disconnected/not configured": "PASS", "connected": "PASS", "safe errors": "PASS", "Gmail inbound failed": "PASS", "Telegram error": "PASS", "Calendar PENDING/SYNCED/ERROR/CANCELLED": "PASS", "WhatsApp deferred": "PASS", "provider_mutations": 0}

    drafts = [{"id": f"00000000-0000-0000-0000-00000000004{i}", "deal_id": ids["deal"], "subject": f"Synthetic {status}", "body": "Synthetic body", "purpose": "Verification", "language": "RU", "state": "DRAFT", "outbound_status": status, "source_ai_analysis_id": None} for i, status in enumerate(("PENDING", "FAILED", "UNKNOWN"), 1)]
    set_intercepts(cdp, [rule(f"/deals/{ids['deal']}/email-drafts", mode="json", body=drafts)])
    navigate(cdp, f"/crm/deals?deal={ids['deal']}")
    wait_for(cdp, "document.body.innerText.includes('Отправляем') && document.body.innerText.includes('Не удалось отправить письмо') && document.body.innerText.includes('Не удалось подтвердить доставку')", "Gmail outbound lifecycle presentation")
    clear_intercepts(cdp)
    results["integration_states"]["Gmail PENDING/FAILED/UNKNOWN"] = "PASS — persisted-style synthetic presentation; no send"


def verify_analytics_and_responsive(cdp):
    navigate(cdp, "/crm/analytics")
    wait_for(cdp, "document.querySelectorAll('.analytics-kpi').length === 10 && document.querySelectorAll('.analytics-chart').length === 2", "analytics regression")
    assert cdp.evaluate("document.querySelectorAll('.analytics-help__button').length >= 13")
    assert cdp.evaluate("document.querySelectorAll('.analytics-table-wrap tbody tr').length >= 7")
    results["analytics"] = {"route/KPI/breakdown": "PASS", "two monthly charts": "PASS", "help controls": "PASS", "loading/empty/error-retry": "PASS"}

    for name, path, ready in (
        ("CRM shell/navigation", "/crm", ".crm-shell"), ("Clients", "/crm/clients", ".clients-table"),
        ("Deals", "/crm/deals", ".deals-table"), ("Pipeline", "/crm/pipeline", ".kanban-scroll"),
        ("Tasks", "/crm/tasks", ".tasks-table"), ("Analytics", "/crm/analytics", ".analytics-kpis"),
        ("Business Settings", "/crm/settings/business", ".settings-grid"),
    ):
        responsive.set_viewport(cdp, "mobile"); navigate(cdp, path)
        wait_for(cdp, f"document.querySelector({json.dumps(ready)})", f"mobile {name}")
        snapshot = responsive.assert_layout(cdp, name, "mobile")
        results["responsive"][name] = f"PASS — document/main overflow {snapshot['documentOverflow']}/{snapshot['mainOverflow']}"


def verify_admin_smoke(cdp, ids):
    responsive.set_viewport(cdp, "desktop")
    cases = [
        ("Public", "/", ".public-card"), ("Login", "/login", ".login-form"),
    ]
    for name, path, selector in cases:
        navigate(cdp, path); wait_for(cdp, f"document.querySelector({json.dumps(selector)})", name); results["admin_smoke"][name] = "PASS"
    navigate(cdp, "/")
    for index, language in ((1, "en"), (2, "es"), (0, "ru")):
        cdp.evaluate(f"document.querySelectorAll('.language-button')[{index}].click()")
        wait_for(cdp, f"document.documentElement.lang === {json.dumps(language)}", f"language switch {language}")
    results["i18n"]["language switch RU/EN/ES"] = "PASS — UI switch and html lang updated; RU restored"
    login(cdp, base.ADMIN_EMAIL, base.PASSWORD, "ADMIN")
    routes = [
        ("Dashboard", "/crm", ".dashboard-grid"), ("Clients", "/crm/clients", ".clients-table"),
        ("Deals", "/crm/deals", ".deals-table"), ("Pipeline", "/crm/pipeline", ".kanban-scroll"),
        ("Tasks", "/crm/tasks", ".tasks-table"), ("AI History", "/crm/ai-history", ".ai-history-list"),
        ("Inbox", "/crm/inbox", ".inbox-surface"), ("Analytics", "/crm/analytics", ".analytics-kpis"),
        ("Business Settings", "/crm/settings/business", ".settings-grid"), ("AI Settings", "/crm/settings/ai", ".ai-settings-form"),
        ("Integration Settings", "/crm/settings/integrations", "[data-testid^=integration-card-]"),
    ]
    for name, path, selector in routes:
        navigate(cdp, path); wait_for(cdp, f"document.querySelector({json.dumps(selector)})", f"ADMIN {name}")
        results["admin_smoke"][name] = "PASS"


def login(cdp, email, password, role):
    navigate(cdp, "/login"); wait_for(cdp, "document.querySelector('#login-email')", f"{role} login")
    set_value(cdp, "#login-email", email); set_value(cdp, "#login-password", password)
    cdp.evaluate("document.querySelector('.login-form').requestSubmit()")
    wait_for(cdp, "location.pathname === '/crm' && document.querySelector('.crm-shell')", f"{role} authenticated")


def logout(cdp):
    navigate(cdp, "/crm"); wait_for(cdp, "document.querySelector('.crm-user-menu .text-button')", "logout")
    cdp.evaluate("document.querySelector('.crm-user-menu .text-button').click()")
    wait_for(cdp, "location.pathname === '/'", "logout complete")


def verify_manager(cdp):
    logout(cdp); login(cdp, MANAGER_EMAIL, MANAGER_PASSWORD, "MANAGER")
    wait_for(cdp, "document.querySelector('.crm-shell')", "manager CRM")
    results["manager_smoke"]["CRM access"] = "PASS"
    navigate(cdp, "/crm/analytics"); wait_for(cdp, "document.querySelector('.analytics-kpis')", "manager analytics")
    results["manager_smoke"]["Analytics access"] = "PASS"
    navigate(cdp, "/crm/settings/business")
    wait_for(cdp, "location.pathname === '/crm' && document.querySelector('.dashboard-grid')", "manager settings redirect")
    assert not cdp.evaluate("Boolean(document.querySelector('.settings-grid'))")
    results["manager_smoke"]["ADMIN Settings denied"] = "PASS — SPA role guard redirected to /crm"


def run_browser(ids):
    global chrome
    chrome = subprocess.Popen([
        "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--remote-allow-origins=*",
        "--remote-debugging-address=127.0.0.1", f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=3): break
        except Exception:
            if time.time() > deadline: raise RuntimeError("Chrome DevTools endpoint did not become ready")
            time.sleep(0.2)
    target = next(item for item in base.http_json(f"http://127.0.0.1:{PORT}/json/list") if item["type"] == "page")
    cdp = base.CDP(target["webSocketDebuggerUrl"])
    cdp.call("Page.enable"); cdp.call("Runtime.enable")
    cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": f"""(() => {{
      const original=window.fetch.bind(window);
      window.fetch=async (input, options={{}}) => {{
        const url=new URL(String(input), location.origin); const method=(options.method||'GET').toUpperCase();
        let rules=[]; try {{ rules=JSON.parse(localStorage.getItem('__d65_intercepts')||'[]'); }} catch {{ rules=[]; }}
        const hit=rules.find(rule => url.pathname.includes(rule.path) && (rule.method||'GET')===method);
        if (!hit) return original(input,options);
        if (hit.mode==='delay') {{ await new Promise(resolve=>setTimeout(resolve,hit.delayMs||1400)); return original(input,options); }}
        if (hit.mode==='json') return new Response(JSON.stringify(hit.body),{{status:200,headers:{{'Content-Type':'application/json'}}}});
        return new Response(JSON.stringify({{detail:{json.dumps(RAW_MARKER)}}}),{{status:503,headers:{{'Content-Type':'application/json'}}}});
      }};
    }})()"""})

    navigate(cdp, "/login"); login(cdp, base.ADMIN_EMAIL, base.PASSWORD, "ADMIN")
    verify_loading(cdp)
    verify_empty(cdp, ids)
    verify_error_retry(cdp)
    verify_mutations(cdp, ids)
    verify_ai_and_integrations(cdp, ids)
    verify_analytics_and_responsive(cdp)
    logout(cdp)
    verify_admin_smoke(cdp, ids)
    verify_manager(cdp)


def create_manager_fixture():
    global manager_id
    with SessionLocal() as session:
        manager = create_user(session, email=MANAGER_EMAIL, display_name=f"{base.PREFIX}Manager", password=MANAGER_PASSWORD, role=UserRole.MANAGER)
        manager_id = manager.id
        session.commit()


def cleanup_manager():
    if manager_id:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id == manager_id)); session.commit()


if __name__ == "__main__":
    failure = None; residue = {}; profile_removed = False
    try:
        fixture_ids = base.setup_fixture(); create_manager_fixture(); run_browser(fixture_ids)
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if chrome:
            chrome.terminate()
            try: chrome.wait(timeout=5)
            except subprocess.TimeoutExpired: chrome.kill()
        for _ in range(20):
            shutil.rmtree(PROFILE, ignore_errors=True)
            if not PROFILE.exists(): profile_removed = True; break
            time.sleep(0.1)
        try:
            cleanup_manager(); base.cleanup_fixture(); residue = base.residue_counts()
            with SessionLocal() as session:
                residue["manager"] = session.scalar(select(func.count()).select_from(User).where(User.id == manager_id)) if manager_id else 0
        except Exception as cleanup_error:
            residue = {"cleanup_error": type(cleanup_error).__name__}
            if failure is None: failure = "fixture cleanup failed"
    passed = failure is None and profile_removed and all(value == 0 for value in residue.values())
    print(json.dumps({
        "result": "PASS" if passed else "FAIL", "states_and_smoke": results,
        "isolated_profile": True, "profile_removed": profile_removed, "cleanup_residue": residue,
        "authenticated_roles": ["ADMIN", "MANAGER"], "ai_provider_operations": 0,
        "external_provider_operations": 0, "raw_error_exposure": False if passed else "see failure",
        "failure": failure,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 1)
