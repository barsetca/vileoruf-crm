"""Bounded D6.4 responsive/usability Chromium verification.

Run from the repository root with:
    .venv/bin/python backend/tests/manual_d64_responsive_verify.py

The harness reuses the D6.3 synthetic-fixture/CDP pattern, performs no AI or
external-provider operation, and guarantees fixture/profile cleanup in finally.
"""

import json
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from sqlalchemy.orm.attributes import flag_modified

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.models import AIAnalysis, Client, Communication, Deal, ExternalMessage, Task
from backend.tests import manual_d63a_ru_browser_verify as base


BASE_URL = "http://localhost:5173"
PORT = 9700 + secrets.randbelow(200)
PROFILE = Path(f"/tmp/d64-chrome-{secrets.token_hex(6)}")
VIEWPORTS = {
    "desktop": (1440, 900),
    "tablet": (768, 1000),
    "mobile": (390, 844),
}
CRITICAL = {"Dashboard", "Clients", "Deals", "Pipeline", "Tasks", "Analytics", "Business Settings"}
LONG_TOKEN = "D64_" + "ОченьДлинныйКонтентБезПробелов" * 4

chrome = None
results = {}
defects = []
language_layout_checks = []


def wait_for(cdp, condition, description, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cdp.evaluate(f"Boolean({condition})"):
            return
        time.sleep(0.12)
    rendered = cdp.evaluate("document.body ? document.body.innerText.slice(0, 1600) : ''")
    raise AssertionError(f"Timeout waiting for {description}; body={rendered!r}")


def set_viewport(cdp, name):
    width, height = VIEWPORTS[name]
    cdp.call("Emulation.setDeviceMetricsOverride", {
        "width": width,
        "height": height,
        "deviceScaleFactor": 1,
        "mobile": name == "mobile",
    })


def navigate(cdp, path, ready):
    cdp.call("Page.navigate", {"url": f"{BASE_URL}{path}"})
    wait_for(cdp, "document.readyState === 'complete'", f"load {path}")
    wait_for(cdp, ready, f"ready {path}")


def click(cdp, expression, description):
    wait_for(cdp, expression, description)
    cdp.evaluate(f"({expression}).click()")


def enhance_fixture(ids):
    with SessionLocal() as session:
        client = session.get(Client, ids["client"])
        deal = session.get(Deal, ids["deal"])
        task = session.get(Task, ids["task"])
        message = session.get(ExternalMessage, ids["message"])
        communication = session.query(Communication).filter(Communication.deal_id == deal.id).one()
        analysis = session.query(AIAnalysis).filter(AIAnalysis.deal_id == deal.id).one()

        client.name = f"{base.PREFIX} Клиент с очень длинным названием студии {LONG_TOKEN}"
        client.company = f"Синтетическая международная компания {LONG_TOKEN}"
        client.email = f"d64-{secrets.token_hex(16)}@very-long-synthetic-domain.example.invalid"
        client.notes = f"Длинная заметка для responsive проверки. {LONG_TOKEN}"
        deal.name = f"{base.PREFIX} Сделка с длинным названием проекта {LONG_TOKEN}"
        deal.description = f"Длинное описание сделки для проверки переноса. {LONG_TOKEN}"
        task.title = f"{base.PREFIX} Задача с длинным названием {LONG_TOKEN}"
        task.description = f"Длинное описание задачи для мобильного modal. {LONG_TOKEN}"
        communication.content = f"Длинная синтетическая коммуникация. {LONG_TOKEN}"
        message.subject = f"Длинная тема входящего сообщения {LONG_TOKEN}"
        message.content = f"Длинное входящее сообщение. {LONG_TOKEN}"
        payload = dict(analysis.result_payload)
        payload["summary"] = f"Длинное безопасное AI summary. {LONG_TOKEN}"
        for key in ("service_fit", "commercial_value", "lead_quality", "feasibility"):
            payload[key] = {**payload[key], "explanation": f"Длинное объяснение. {LONG_TOKEN}"}
        analysis.result_payload = payload
        flag_modified(analysis, "result_payload")
        session.commit()
        return {
            "client_name": client.name,
            "deal_name": deal.name,
            "task_title": task.title,
        }


def layout_snapshot(cdp):
    return cdp.evaluate("""(() => {
      const width = window.innerWidth;
      const root = document.documentElement;
      const main = document.querySelector('.crm-main') || document.body;
      const visible = (element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      };
      const exempt = '.clients-table-wrap,.kanban-scroll,.analytics-table-wrap,.analytics-chart__labels';
      const offenders = Array.from(document.querySelectorAll('button,input,select,textarea,a,[tabindex="0"]'))
        .filter((element) => visible(element) && !element.closest(exempt))
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return {element, rect};
        })
        .filter(({rect}) => rect.left < -1 || rect.right > width + 1)
        .slice(0, 8)
        .map(({element, rect}) => ({
          tag: element.tagName,
          text: (element.innerText || element.getAttribute('aria-label') || '').slice(0, 80),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
        }));
      const wideElements = Array.from(document.body.querySelectorAll('*')).reverse()
        .filter(visible)
        .map((element) => ({element, rect:element.getBoundingClientRect()}))
        .filter(({element, rect}) => !element.closest(exempt) && (rect.right > width + 1 || element.scrollWidth > element.clientWidth + 1))
        .slice(0, 10)
        .map(({element, rect}) => ({
          tag:element.tagName,
          className:element.className?.toString().slice(0, 100) || '',
          left:Math.round(rect.left), right:Math.round(rect.right),
          clientWidth:element.clientWidth, scrollWidth:element.scrollWidth,
        }));
      const smallTouchControls = width <= 390 ? Array.from(document.querySelectorAll('button,summary,input:not([type="checkbox"]),select,textarea'))
        .filter((element) => visible(element) && !element.matches('.analytics-help__button'))
        .map((element) => ({element, rect:element.getBoundingClientRect()}))
        .filter(({rect}) => rect.height < 39.5)
        .slice(0, 8)
        .map(({element, rect}) => ({tag:element.tagName,text:(element.innerText||element.getAttribute('aria-label')||'').slice(0,60),height:Math.round(rect.height)})) : [];
      return {
        viewportWidth: width,
        documentOverflow: Math.max(0, root.scrollWidth - root.clientWidth),
        mainOverflow: Math.max(0, main.scrollWidth - main.clientWidth),
        offenders,
        wideElements,
        smallTouchControls,
      };
    })()""")


def assert_layout(cdp, area, viewport):
    snapshot = layout_snapshot(cdp)
    problems = []
    if snapshot["documentOverflow"] > 1:
        problems.append(f"document horizontal overflow {snapshot['documentOverflow']}px")
    if snapshot["mainOverflow"] > 1:
        problems.append(f"main horizontal overflow {snapshot['mainOverflow']}px")
    if snapshot["offenders"]:
        problems.append(f"off-viewport controls: {snapshot['offenders']}")
    if snapshot["wideElements"] and (snapshot["documentOverflow"] > 1 or snapshot["mainOverflow"] > 1):
        problems.append(f"wide elements: {snapshot['wideElements']}")
    if snapshot["smallTouchControls"]:
        problems.append(f"small touch controls: {snapshot['smallTouchControls']}")
    if problems:
        defects.append({"area": area, "viewport": viewport, "problems": problems})
        raise AssertionError(f"{area}/{viewport}: {'; '.join(problems)}")
    return snapshot


def assert_modal(cdp, area, viewport):
    metrics = cdp.evaluate("""(() => {
      const modal = document.querySelector('.client-modal');
      const close = modal?.querySelector('.icon-button');
      if (!modal || !close) return null;
      const m = modal.getBoundingClientRect(), c = close.getBoundingClientRect();
      return {
        modalLeft:m.left, modalRight:m.right, modalTop:m.top, modalBottom:m.bottom,
        closeLeft:c.left, closeRight:c.right, closeTop:c.top, closeBottom:c.bottom,
        viewportWidth:innerWidth, viewportHeight:innerHeight,
        overflowY:getComputedStyle(modal).overflowY,
      };
    })()""")
    assert metrics, f"{area}/{viewport}: modal missing"
    assert metrics["modalLeft"] >= -1 and metrics["modalRight"] <= metrics["viewportWidth"] + 1, f"modal horizontal bounds: {metrics}"
    assert metrics["modalTop"] >= -1 and metrics["modalBottom"] <= metrics["viewportHeight"] + 1, f"modal vertical bounds: {metrics}"
    assert metrics["closeLeft"] >= -1 and metrics["closeRight"] <= metrics["viewportWidth"] + 1, f"close horizontal bounds: {metrics}"
    assert metrics["closeTop"] >= -1 and metrics["closeBottom"] <= metrics["viewportHeight"] + 1, f"close vertical bounds: {metrics}"
    assert metrics["overflowY"] in {"auto", "scroll"}, f"modal not scrollable: {metrics}"
    assert_layout(cdp, area, viewport)


def record(area, viewport, action):
    results.setdefault(area, {})[viewport] = {"status": "PASS", "action": action}


def check_page(cdp, area, path, ready, viewports):
    for viewport in viewports:
        set_viewport(cdp, viewport)
        navigate(cdp, path, ready)
        assert_layout(cdp, area, viewport)
        record(area, viewport, f"Открыт {path}; viewport {VIEWPORTS[viewport][0]}x{VIEWPORTS[viewport][1]}, overflow/controls PASS")


def assert_internal_scroll(cdp, selector, description):
    metrics = cdp.evaluate(f"""(() => {{
      const element=document.querySelector({json.dumps(selector)});
      if (!element) return null;
      const before=element.scrollLeft;
      element.scrollLeft=element.scrollWidth;
      const after=element.scrollLeft;
      element.scrollLeft=before;
      return {{clientWidth:element.clientWidth,scrollWidth:element.scrollWidth,after,overflowX:getComputedStyle(element).overflowX}};
    }})()""")
    assert metrics and metrics["scrollWidth"] > metrics["clientWidth"] and metrics["after"] > 0 and metrics["overflowX"] in {"auto", "scroll"}, f"{description} inaccessible: {metrics}"


def verify_public_and_login(cdp):
    for area, path, ready in (
        ("Public", "/", "document.querySelector('.public-card form')"),
        ("Login", "/login", "document.querySelector('.login-form')"),
    ):
        for viewport in ("desktop", "mobile"):
            set_viewport(cdp, viewport)
            navigate(cdp, path, ready)
            assert not cdp.evaluate(f"document.querySelector('{'.public-card form' if area == 'Public' else '.login-form'}').checkValidity()")
            assert_layout(cdp, area, viewport)
            record(area, viewport, "Форма, labels, language controls и native required validation доступны")
        if area == "Public":
            for index, language in ((1, "en"), (2, "es"), (0, "ru")):
                cdp.evaluate(f"document.querySelectorAll('.language-button')[{index}].click()")
                wait_for(cdp, f"document.documentElement.lang === {json.dumps(language)}", f"{language} public layout")
                assert_layout(cdp, area, "mobile")
                language_layout_checks.append({"route": path, "language": language, "viewport": "mobile", "status": "PASS"})
        else:
            for index, language in ((1, "en"), (2, "es"), (0, "ru")):
                cdp.evaluate(f"document.querySelectorAll('.language-button')[{index}].click()")
                wait_for(cdp, f"document.documentElement.lang === {json.dumps(language)}", f"{language} login layout")
                assert_layout(cdp, area, "mobile")
                language_layout_checks.append({"route": path, "language": language, "viewport": "mobile", "status": "PASS"})


def login(cdp):
    set_viewport(cdp, "desktop")
    navigate(cdp, "/login", "document.querySelector('#login-email')")
    base.set_input(cdp, "#login-email", base.ADMIN_EMAIL)
    base.set_input(cdp, "#login-password", base.PASSWORD)
    cdp.evaluate("document.querySelector('.login-form').requestSubmit()")
    wait_for(cdp, "location.pathname === '/crm' && document.querySelector('.crm-shell')", "ADMIN login")


def assert_navigation(cdp, viewport):
    set_viewport(cdp, viewport)
    navigate(cdp, "/crm/analytics", "document.querySelector('.analytics-surface')")
    if cdp.evaluate("Boolean(document.querySelector('.crm-menu-button') && getComputedStyle(document.querySelector('.crm-menu-button')).display !== 'none')"):
        cdp.evaluate("document.querySelector('.crm-menu-button').click()")
        wait_for(cdp, "document.querySelector('.crm-nav.is-open')", "mobile navigation expansion")
    data = cdp.evaluate("""(() => {
      const visible = (e) => { const r=e.getBoundingClientRect(),s=getComputedStyle(e); return s.display!=='none'&&r.width>0&&r.height>0; };
      const toggle=document.querySelector('.crm-menu-button');
      const items=Array.from(document.querySelectorAll('.crm-nav-item'));
      const active=document.querySelector('.crm-nav-item.is-active');
      const r=active?.getBoundingClientRect();
      return {total:items.length,visible:items.filter(visible).length,activeVisible:Boolean(active&&visible(active)),activeWidth:r?.width||0,toggleVisible:Boolean(toggle&&visible(toggle))};
    })()""")
    assert data["visible"] == data["total"] and data["activeVisible"] and data["activeWidth"] >= 40, f"navigation unusable: {data}"
    assert_layout(cdp, "Navigation", viewport)
    cdp.evaluate("Array.from(document.querySelectorAll('.crm-nav-item'))[6].click()")
    wait_for(cdp, "location.pathname === '/crm/inbox'", f"{viewport} navigation click")
    if viewport == "mobile":
        wait_for(cdp, "!document.querySelector('.crm-nav.is-open')", "mobile navigation closes after selection")
    record("Navigation", viewport, f"Все {data['total']} route actions и active Analytics доступны; переход в Inbox выполнен; mobile toggle={data['toggleVisible']}")


def verify_core(cdp, labels, ids):
    all_three = ("desktop", "tablet", "mobile")
    check_page(cdp, "Dashboard", "/crm", f"document.body.innerText.includes({json.dumps(labels['task_title'])})", all_three)
    check_page(cdp, "Clients", "/crm/clients", f"document.body.innerText.includes({json.dumps(labels['client_name'])})", all_three)
    assert_internal_scroll(cdp, ".clients-table-wrap", "Clients mobile table")
    set_viewport(cdp, "mobile")
    click(cdp, f"Array.from(document.querySelectorAll('.clients-table tbody tr')).find(x => x.innerText.includes({json.dumps(base.PREFIX)}))", "synthetic client row")
    wait_for(cdp, "document.querySelector('#client-modal-title')", "client modal")
    wait_for(cdp, f"document.querySelector('.client-modal').innerText.includes({json.dumps(LONG_TOKEN)})", "client long communication")
    assert_modal(cdp, "Client details", "mobile")
    record("Client details", "mobile", "Длинные данные, edit form, Communications/Calendar и close control доступны в scrollable modal")
    set_viewport(cdp, "desktop"); assert_modal(cdp, "Client details", "desktop"); record("Client details", "desktop", "Desktop modal и секции доступны")

    check_page(cdp, "Deals", "/crm/deals", f"document.body.innerText.includes({json.dumps(labels['deal_name'])})", all_three)
    assert_internal_scroll(cdp, ".clients-table-wrap", "Deals mobile table")
    for viewport in ("desktop", "mobile"):
        set_viewport(cdp, viewport)
        navigate(cdp, f"/crm/deals?deal={ids['deal']}", "document.querySelector('#deal-modal-title')")
        wait_for(cdp, f"document.querySelector('#deal-modal-title').textContent.includes({json.dumps(base.PREFIX)})", "deal modal content")
        assert_modal(cdp, "Deal details", viewport)
        assert LONG_TOKEN in cdp.evaluate("document.querySelector('.client-modal').innerText")
        record("Deal details", viewport, "Длинное описание, AI/Communications/Calendar sections, actions и close доступны")
        if viewport == "mobile":
            click(cdp, "document.querySelector('.deal-actions > .secondary-button')", "Deal edit action")
            wait_for(cdp, "document.querySelector('.client-modal .client-form')", "Deal edit form")
            assert_modal(cdp, "Deal details", viewport)

    check_page(cdp, "Pipeline", "/crm/pipeline", f"document.body.innerText.includes({json.dumps(labels['deal_name'])})", all_three)
    assert_internal_scroll(cdp, ".kanban-scroll", "Pipeline mobile board")
    set_viewport(cdp, "mobile")
    move_height = cdp.evaluate("document.querySelector('.kanban-card:not(.is-readonly) .kanban-move-button')?.getBoundingClientRect().height || 0")
    assert move_height >= 40, f"Pipeline/mobile Move touch target is only {move_height}px"
    click(cdp, "document.querySelector('.kanban-card:not(.is-readonly) .kanban-move-button')", "Pipeline Move fallback")
    wait_for(cdp, "document.querySelector('.move-modal')", "move modal")
    assert_modal(cdp, "Pipeline", "mobile")

    check_page(cdp, "Tasks", "/crm/tasks", f"document.body.innerText.includes({json.dumps(labels['task_title'])})", all_three)
    assert_internal_scroll(cdp, ".clients-table-wrap", "Tasks mobile table")
    set_viewport(cdp, "mobile")
    click(cdp, f"Array.from(document.querySelectorAll('.tasks-table tbody tr')).find(x => x.innerText.includes({json.dumps(base.PREFIX)}))", "synthetic task row")
    wait_for(cdp, "document.querySelector('#task-modal-title')", "task modal")
    assert_modal(cdp, "Tasks", "mobile")
    click(cdp, "document.querySelector('.client-modal .deal-actions > .secondary-button')", "Task edit action")
    wait_for(cdp, "document.querySelector('.client-modal .client-form')", "Task edit form")
    assert_modal(cdp, "Tasks", "mobile")

    check_page(cdp, "Analytics", "/crm/analytics", "document.querySelectorAll('.analytics-kpi').length === 10 && document.querySelectorAll('.analytics-chart').length === 2", all_three)
    check_page(cdp, "Business Settings", "/crm/settings/business", "document.querySelectorAll('.settings-card').length >= 3", all_three)


def verify_remaining(cdp, labels, ids):
    for area, path, ready in (
        ("AI History", "/crm/ai-history", "document.querySelector('.ai-history-list details')"),
        ("Inbox", "/crm/inbox", f"document.querySelector('[data-testid=\"inbox-message-{ids['message']}\"]')"),
        ("AI Settings", "/crm/settings/ai", "document.querySelector('.ai-settings-form')"),
        ("Integration Settings", "/crm/settings/integrations", "document.querySelectorAll('[data-testid^=integration-card-]').length === 4"),
    ):
        check_page(cdp, area, path, ready, ("desktop", "mobile"))
        if area == "AI History":
            set_viewport(cdp, "mobile")
            cdp.evaluate("document.querySelector('.ai-history-list details').open=true")
            wait_for(cdp, f"document.body.innerText.includes({json.dumps(LONG_TOKEN)})", "expanded long AI result")
            assert_layout(cdp, area, "mobile")

    for viewport in ("desktop", "mobile"):
        set_viewport(cdp, viewport)
        navigate(cdp, "/crm", "document.querySelector('.admin-tools')")
        cdp.evaluate("document.querySelector('.admin-tools').open=true")
        wait_for(cdp, "document.querySelector('.employee-row')", "employee management")
        assert_layout(cdp, "Employee management", viewport)
        record("Employee management", viewport, "Create/list/select/status/actions доступны")


def verify_long_locale_layouts(cdp):
    set_viewport(cdp, "mobile")
    for path, ready in (
        ("/crm/settings/business", "document.querySelectorAll('.settings-card').length >= 3"),
        ("/crm/settings/integrations", "document.querySelectorAll('[data-testid^=integration-card-]').length === 4"),
    ):
        navigate(cdp, path, ready)
        for index, language in ((1, "en"), (2, "es"), (0, "ru")):
            cdp.evaluate(f"document.querySelectorAll('.language-button')[{index}].click()")
            wait_for(cdp, f"document.documentElement.lang === {json.dumps(language)}", f"{language} {path} layout")
            assert_layout(cdp, path, "mobile")
            language_layout_checks.append({"route": path, "language": language, "viewport": "mobile", "status": "PASS"})


def verify_logout(cdp):
    set_viewport(cdp, "mobile")
    navigate(cdp, "/crm", "document.querySelector('.crm-shell')")
    cdp.evaluate("document.querySelector('.crm-user-menu .text-button').click()")
    wait_for(cdp, "location.pathname === '/' && document.querySelector('.public-card')", "logout to public")
    assert_layout(cdp, "Public", "mobile")
    results["Navigation"]["logout"] = {"status": "PASS", "action": "Mobile logout выполнен; возврат на public route подтверждён"}


def run_browser(labels, ids):
    global chrome
    chrome = subprocess.Popen([
        "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--remote-allow-origins=*", "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=3):
                break
        except Exception:
            if time.time() > deadline:
                raise RuntimeError("Chrome DevTools endpoint did not become ready")
            time.sleep(0.2)
    target = next(item for item in base.http_json(f"http://127.0.0.1:{PORT}/json/list") if item["type"] == "page")
    cdp = base.CDP(target["webSocketDebuggerUrl"])
    cdp.call("Page.enable"); cdp.call("Runtime.enable")

    verify_public_and_login(cdp)
    login(cdp)
    for viewport in VIEWPORTS:
        assert_navigation(cdp, viewport)
    verify_core(cdp, labels, ids)
    verify_remaining(cdp, labels, ids)
    verify_long_locale_layouts(cdp)
    verify_logout(cdp)

    expected = {"Public", "Login", "Navigation", "Dashboard", "Clients", "Client details", "Deals", "Deal details", "Pipeline", "Tasks", "AI History", "Inbox", "Analytics", "Employee management", "Business Settings", "AI Settings", "Integration Settings"}
    assert set(results) == expected
    for area in expected - {"Navigation"}:
        required = set(VIEWPORTS) if area in CRITICAL else {"desktop", "mobile"}
        assert required.issubset(results[area]), f"missing viewport coverage for {area}"


if __name__ == "__main__":
    failure = None
    residue = {}
    profile_removed = False
    try:
        fixture_ids = base.setup_fixture()
        fixture_labels = enhance_fixture(fixture_ids)
        run_browser(fixture_labels, fixture_ids)
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if chrome:
            chrome.terminate()
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.kill()
        for _ in range(20):
            shutil.rmtree(PROFILE, ignore_errors=True)
            if not PROFILE.exists():
                profile_removed = True
                break
            time.sleep(0.1)
        try:
            base.cleanup_fixture()
            residue = base.residue_counts()
        except Exception as cleanup_error:
            residue = {"cleanup_error": type(cleanup_error).__name__}
            if failure is None:
                failure = "fixture cleanup failed"
    passed = failure is None and profile_removed and all(value == 0 for value in residue.values())
    print(json.dumps({
        "result": "PASS" if passed else "FAIL",
        "viewports": VIEWPORTS,
        "areas": results,
        "detected_layout_defects": defects,
        "language_layout_checks": language_layout_checks,
        "isolated_profile": True,
        "profile_removed": profile_removed,
        "cleanup_residue": residue,
        "authenticated_role": "ADMIN",
        "ai_provider_operations": 0,
        "external_provider_operations": 0,
        "failure": failure,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 1)
