"""Bounded D7.1b browser release acceptance.

Run with an isolated database URL and frontend URL. Reuses the D6.3 CDP pattern,
creates only synthetic ADMIN/MANAGER data, and guarantees cleanup in finally.
"""

import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.db.session import SessionLocal
from backend.app.models import AIAnalysis, Client, ClientStatus, Communication, Deal, InitialAIAnalysisPipeline, PipelineStage, Service, Task, TaskStatus, User, UserRole
from backend.app.services.users import create_user
from backend.tests.manual_d63a_ru_browser_verify import CDP

BASE_URL = os.environ.get("D71B_BASE_URL", "http://localhost:15174")
PORT = 10100 + secrets.randbelow(200)
PREFIX = f"D71B_{secrets.token_hex(6)}_"
ADMIN_EMAIL = f"d71b-admin-{secrets.token_hex(8)}@example.invalid"
MANAGER_EMAIL = f"d71b-manager-{secrets.token_hex(8)}@example.invalid"
ADMIN_PASSWORD = secrets.token_urlsafe(24)
MANAGER_PASSWORD = secrets.token_urlsafe(24)
PROFILE = Path(f"/tmp/d71b-chrome-{secrets.token_hex(6)}")

created = {"users": [], "clients": [], "deals": [], "tasks": [], "communications": [], "analyses": []}
ids, chrome = {}, None
results = {}


def http_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def wait(cdp, expression, name, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cdp.evaluate(f"Boolean({expression})"):
            return
        time.sleep(.12)
    body = cdp.evaluate("document.body ? document.body.innerText.slice(0, 1800) : ''")
    controls = cdp.evaluate("JSON.stringify(Array.from(document.querySelectorAll('.modal-backdrop input,.modal-backdrop select,.modal-backdrop textarea')).map(e=>[e.tagName,e.name,e.type,e.value]))")
    modal_html = cdp.evaluate("document.querySelector('.modal-backdrop')?.innerHTML.slice(0, 5000) || ''")
    raise AssertionError(f"Timeout {name}: controls={controls}; modal_html={modal_html!r}; body={body!r}")


def nav(cdp, path):
    cdp.call("Page.navigate", {"url": f"{BASE_URL}{path}"})
    wait(cdp, "document.readyState === 'complete'", f"load {path}")


def set_value(cdp, selector, value):
    cdp.evaluate(f"""(() => {{
      const e=document.querySelector({json.dumps(selector)}); if (!e) throw new Error('missing '+{json.dumps(selector)});
      const p=e instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : e instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(p,'value').set.call(e,{json.dumps(value)});
      e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}}));
    }})()""")


def click(cdp, expression, name):
    wait(cdp, expression, name)
    cdp.evaluate(f"({expression}).click()")


def setup_users():
    with SessionLocal() as session:
        admin = create_user(session, email=ADMIN_EMAIL, display_name=f"{PREFIX}ADMIN", password=ADMIN_PASSWORD, role=UserRole.ADMIN)
        manager = create_user(session, email=MANAGER_EMAIL, display_name=f"{PREFIX}MANAGER", password=MANAGER_PASSWORD, role=UserRole.MANAGER)
        created["users"] += [admin.id, manager.id]
        ids.update(admin=str(admin.id), manager=str(manager.id))


def db_public_result():
    with SessionLocal() as session:
        matching_clients = list(session.scalars(select(Client).where(Client.name == f"{PREFIX}Public client")))
        assert len(matching_clients) == 1, f"expected exactly one public client, got {len(matching_clients)}"
        client = matching_clients[0]
        assert client and client.status is ClientStatus.CUSTOMER and client.lead_source == "Website"
        deal = session.scalar(select(Deal).where(Deal.client_id == client.id))
        stage = session.get(PipelineStage, deal.stage_id)
        service = session.get(Service, deal.service_id)
        next_stage = session.scalar(select(PipelineStage).where(PipelineStage.name == "Contact"))
        assert deal and stage.name == "New Lead" and deal.responsible_user_id is None
        assert service and service.category_id and next_stage
        created["clients"].append(client.id); created["deals"].append(deal.id)
        ids.update(client=str(client.id), deal=str(deal.id), service=str(service.id), category=str(service.category_id), next_stage=str(next_stage.id))


def assert_stage(name):
    with SessionLocal() as session:
        deal = session.get(Deal, ids["deal"]); stage = session.get(PipelineStage, deal.stage_id)
        assert stage.name == name, f"expected stage {name}, got {stage.name}"
        return str(stage.id)


def wait_stage(name, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return assert_stage(name)
        except AssertionError:
            time.sleep(.15)
    return assert_stage(name)


def db_task_and_communication():
    with SessionLocal() as session:
        task = session.scalar(select(Task).where(Task.title == f"{PREFIX}Task"))
        communication = session.scalar(select(Communication).where(Communication.content == f"{PREFIX}Manual communication"))
        assert task and task.status is TaskStatus.COMPLETED and str(task.deal_id) == ids["deal"]
        assert communication and str(communication.client_id) == ids["client"] and str(communication.deal_id) == ids["deal"]
        created["tasks"].append(task.id); created["communications"].append(communication.id)


def login(cdp, email, password, role):
    nav(cdp, "/login"); wait(cdp, "document.querySelector('#login-email')", f"{role} login form")
    set_value(cdp, "#login-email", email); set_value(cdp, "#login-password", password)
    cdp.evaluate("document.querySelector('.login-form').requestSubmit()")
    wait(cdp, "location.pathname === '/crm' && document.querySelector('.crm-shell')", f"{role} login")


def logout(cdp):
    click(cdp, "Array.from(document.querySelectorAll('.crm-header .text-button')).find(x=>x.textContent.includes('Выйти'))", "logout")
    wait(cdp, "location.pathname === '/' && document.querySelector('.public-card')", "public after logout")


def run_browser():
    global chrome
    chrome = subprocess.Popen(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--remote-allow-origins=*", "--remote-debugging-address=127.0.0.1", f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while True:
        try: http_json(f"http://127.0.0.1:{PORT}/json/version"); break
        except Exception:
            if time.time() > deadline: raise RuntimeError("Chrome CDP unavailable")
            time.sleep(.2)
    target = next(item for item in http_json(f"http://127.0.0.1:{PORT}/json/list") if item["type"] == "page")
    cdp = CDP(target["webSocketDebuggerUrl"]); cdp.call("Page.enable"); cdp.call("Runtime.enable")
    cdp.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": """(() => { const original=window.fetch.bind(window); window.fetch=async (...args)=>{ const options=args[1]||{}; if(options.headers && options.headers.Authorization) window.__d71b_auth=options.headers.Authorization; return original(...args); }; })()"""})

    nav(cdp, "/")
    wait(cdp, "document.documentElement.lang === 'ru' && document.querySelector('.public-card form') && document.querySelectorAll('.public-card select')[0]?.options.length > 0", "RU public form")
    set_value(cdp, "input[name=name]", f"{PREFIX}Public client")
    set_value(cdp, "input[name=contact_person]", "Synthetic Contact")
    set_value(cdp, "input[name=email]", f"{PREFIX.lower()}public@example.invalid")
    set_value(cdp, "input[name=deal_name]", f"{PREFIX}Public deal")
    set_value(cdp, "input[name=estimated_budget]", "321.00")
    set_value(cdp, "textarea", "Synthetic public request")
    service_id = cdp.evaluate("document.querySelector('.public-card select').options[0].value")
    assert service_id, "required system Service did not render"
    set_value(cdp, ".public-card select", service_id)
    assert cdp.evaluate("document.querySelector('.public-card form').checkValidity()"), cdp.evaluate("Array.from(document.querySelector('.public-card form').elements).map(x=>[x.name,x.value,x.validationMessage])")
    cdp.evaluate("document.querySelector('.public-card form').requestSubmit()")
    wait(cdp, "document.querySelector('.public-success')", "public request success")
    db_public_result(); results["public"] = "PASS"

    login(cdp, ADMIN_EMAIL, ADMIN_PASSWORD, "ADMIN")
    nav(cdp, "/crm/clients"); wait(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + 'Public client')})", "public client visible")
    click(cdp, f"Array.from(document.querySelectorAll('.clients-table tbody tr')).find(x=>x.innerText.includes({json.dumps(PREFIX + 'Public client')}))", "open public client")
    wait(cdp, "document.querySelector('#client-modal-title')", "client detail")
    results["admin_client"] = "PASS"

    nav(cdp, "/crm/deals"); wait(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + 'Public deal')})", "public deal visible")
    click(cdp, f"Array.from(document.querySelectorAll('.deals-table tbody tr')).find(x=>x.innerText.includes({json.dumps(PREFIX + 'Public deal')}))", "open public deal")
    wait(cdp, "document.querySelector('#deal-modal-title') && document.querySelector('.transition-form')", "deal detail/action")
    assert cdp.evaluate(f"document.body.innerText.includes({json.dumps(PREFIX + 'Public client')})")
    const_next = ids["next_stage"]
    set_value(cdp, ".transition-form select", const_next); cdp.evaluate("document.querySelector('.transition-form').requestSubmit()")
    wait_stage("Contact"); results["deal_pipeline"] = "PASS"

    nav(cdp, "/crm/tasks"); wait(cdp, "document.querySelector('.page-action') && !document.querySelector('.page-action').disabled", "tasks page ready")
    results["task_ui"] = "opened"
    click(cdp, "document.querySelector('.page-action')", "create task")
    wait(cdp, "document.querySelector('.modal-backdrop input[name=title]')", "task form")
    results["task_ui"] = "form"
    set_value(cdp, ".modal-backdrop input[name=title]", f"{PREFIX}Task")
    set_value(cdp, ".modal-backdrop select[name=clientId]", ids["client"]); time.sleep(.2)
    set_value(cdp, ".modal-backdrop select[name=dealId]", ids["deal"])
    cdp.evaluate("document.querySelector('.modal-backdrop input[name=title]').closest('form').requestSubmit()")
    wait(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + 'Task')}) && !document.querySelector('.modal-backdrop')", "task created")
    results["task_ui"] = "created"
    click(cdp, f"Array.from(document.querySelectorAll('.tasks-table tbody tr')).find(x=>x.innerText.includes({json.dumps(PREFIX + 'Task')}))", "open task")
    wait(cdp, "document.querySelector('#task-modal-title')", "task detail")
    click(cdp, "Array.from(document.querySelectorAll('.deal-actions button')).find(x=>x.textContent.includes('Завершить'))", "complete task")
    wait(cdp, "document.body.innerText.includes('Завершена')", "completed task UI")
    results["task"] = "PASS"

    nav(cdp, f"/crm/deals?deal={ids['deal']}")
    wait(cdp, "document.querySelector('.communication-form textarea[name=content]')", "communication form")
    set_value(cdp, ".communication-form textarea[name=content]", f"{PREFIX}Manual communication")
    cdp.evaluate("document.querySelector('.communication-form').requestSubmit()")
    wait(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + 'Manual communication')})", "manual communication timeline")
    db_task_and_communication(); results["communication"] = "PASS"

    nav(cdp, "/crm/analytics"); wait(cdp, "document.querySelectorAll('.analytics-kpi').length === 10", "analytics API UI")
    assert cdp.evaluate("performance.getEntriesByType('resource').some(x=>x.name.includes('/analytics/summary'))"), "analytics summary resource not observed"
    kpis = cdp.evaluate("JSON.stringify(Array.from(document.querySelectorAll('.analytics-kpi')).map(x=>x.innerText))")
    assert cdp.evaluate("Array.from(document.querySelectorAll('.analytics-kpi')).some(x=>x.innerText.includes('CRM-записи') && x.innerText.includes('1'))"), f"analytics CRM-record total was not one synthetic client: {kpis}"
    assert cdp.evaluate("Array.from(document.querySelectorAll('.analytics-kpi')).some(x=>x.innerText.includes('Всего сделок') && x.innerText.includes('1'))"), "analytics deal total did not include the synthetic deal"
    assert cdp.evaluate("document.querySelectorAll('.analytics-table-wrap tbody tr').length >= 7"), "analytics pipeline breakdown did not render configured stages"
    results["analytics"] = "PASS"

    nav(cdp, "/crm/ai-history"); wait(cdp, "document.querySelector('.ai-history-list') || document.querySelector('.state-panel')", "AI History without launch")
    results["ai_route"] = "PASS"

    logout(cdp); login(cdp, MANAGER_EMAIL, MANAGER_PASSWORD, "MANAGER")
    nav(cdp, "/crm/settings/business")
    wait(cdp, "location.pathname === '/crm' && document.querySelector('.dashboard-grid')", "manager admin settings denied")
    results["manager_settings"] = "PASS"
    nav(cdp, "/crm/deals"); wait(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + 'Public deal')})", "manager sees deal")
    click(cdp, f"Array.from(document.querySelectorAll('.deals-table tbody tr')).find(x=>x.innerText.includes({json.dumps(PREFIX + 'Public deal')}))", "manager opens foreign deal")
    wait(cdp, "document.querySelector('.readonly-note')", "manager foreign deal readonly")
    assert not cdp.evaluate("document.querySelector('.transition-form')")
    auth = cdp.evaluate("window.__d71b_auth")
    assert auth, "manager auth header was not observed"
    # The real backend boundary is invoked with the captured Bearer token and must reject the foreign transition.
    response = cdp.call("Runtime.evaluate", {"expression": f"""(async()=>{{const r=await fetch('http://localhost:18001/deals/{ids['deal']}/transition',{{method:'POST',headers:{{Authorization:window.__d71b_auth,'Content-Type':'application/json'}},body:JSON.stringify({{stage_id:{json.dumps(const_next)}}})}}); return r.status;}})()""", "awaitPromise": True, "returnByValue": True})
    response_status = response["result"]["value"]
    assert response_status == 403, f"foreign manager transition returned {response_status}"
    assert_stage("Contact"); results["manager_authorization"] = "PASS"
    return results


def cleanup():
    with SessionLocal() as session:
        public_deals = created["deals"]
        if public_deals:
            session.execute(delete(InitialAIAnalysisPipeline).where(InitialAIAnalysisPipeline.deal_id.in_(public_deals)))
            session.execute(delete(AIAnalysis).where(AIAnalysis.deal_id.in_(public_deals)))
            session.execute(delete(Communication).where(Communication.deal_id.in_(public_deals)))
            session.execute(delete(Task).where(Task.deal_id.in_(public_deals)))
        if created["users"]:
            session.execute(delete(Task).where(Task.responsible_user_id.in_(created["users"])))
        for model, key in ((Communication, "communications"), (Task, "tasks"), (Deal, "deals"), (Client, "clients"), (User, "users")):
            if created[key]: session.execute(delete(model).where(model.id.in_(created[key])))
        session.commit()
    residue = {}
    with SessionLocal() as session:
        for model, key in ((User,"users"),(Client,"clients"),(Deal,"deals"),(Task,"tasks"),(Communication,"communications")):
            residue[key] = session.scalar(select(func.count()).select_from(model).where(model.id.in_(created[key]))) if created[key] else 0
        public_deals = created["deals"]
        residue["analyses"] = session.scalar(select(func.count()).select_from(AIAnalysis).where(AIAnalysis.deal_id.in_(public_deals))) if public_deals else 0
        residue["pipelines"] = session.scalar(select(func.count()).select_from(InitialAIAnalysisPipeline).where(InitialAIAnalysisPipeline.deal_id.in_(public_deals))) if public_deals else 0
    return residue


def main():
    failure = None; residue = {}; profile_removed = False
    try:
        setup_users(); run_browser()
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if chrome:
            chrome.terminate()
            try: chrome.wait(timeout=5)
            except subprocess.TimeoutExpired: chrome.kill()
        for _ in range(20):
            shutil.rmtree(PROFILE, ignore_errors=True)
            if not PROFILE.exists(): break
            time.sleep(.1)
        profile_removed = not PROFILE.exists()
        residue = cleanup()
    output = {"result": "PASS" if failure is None and not any(residue.values()) and profile_removed else "FAIL", "checks": results, "cleanup": residue, "profile_removed": profile_removed, "failure": failure, "provider_operations": 0}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
