"""Bounded P1.0 public-consent browser verification with guaranteed cleanup.

Runs against the local Compose runtime. It uses an isolated Chrome profile and one
synthetic public request. AI automation is temporarily disabled only for that
fixture, then the exact prior runtime setting is restored in ``finally``.
"""

import base64
import json
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_URL = "http://localhost:5173"
PORT = 10300 + secrets.randbelow(300)
PREFIX = f"P10_{secrets.token_hex(6)}"
PROFILE = Path(f"/tmp/p10-consent-chrome-{secrets.token_hex(6)}")
PERSONAL_DATA_CONSENT_VERSION = "2026-09-10"
PRIVACY_POLICY_VERSION = "2026-09-10"


class CDP:
    def __init__(self, ws_url: str):
        parsed = urlparse(ws_url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        self.sock.sendall((f"GET {target} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(4096)
        if b" 101 " not in response:
            raise RuntimeError("CDP websocket handshake failed")
        self.seq = 0

    def send(self, payload):
        raw, mask = json.dumps(payload).encode(), secrets.token_bytes(4)
        length = len(raw)
        header = bytes([0x81])
        header += bytes([0x80 | length]) if length < 126 else bytes([0x80 | 126]) + struct.pack("!H", length) if length < 65536 else bytes([0x80 | 127]) + struct.pack("!Q", length)
        self.sock.sendall(header + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(raw)))

    def receive(self):
        def exact(count):
            value = b""
            while len(value) < count:
                part = self.sock.recv(count - len(value))
                if not part:
                    raise RuntimeError("CDP websocket closed")
                value += part
            return value
        first, second = exact(2)
        opcode, length = first & 15, second & 127
        if length == 126:
            length = struct.unpack("!H", exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", exact(8))[0]
        mask = exact(4) if second & 128 else None
        body = exact(length)
        if mask:
            body = bytes(value ^ mask[index % 4] for index, value in enumerate(body))
        if opcode == 9:
            self.sock.sendall(bytes([0x8A, len(body)]) + body)
            return self.receive()
        if opcode == 8:
            raise RuntimeError("CDP websocket closed")
        return json.loads(body) if opcode == 1 else None

    def call(self, method: str, params=None):
        self.seq += 1
        identifier = self.seq
        self.send({"id": identifier, "method": method, "params": params or {}})
        while True:
            message = self.receive()
            if message and message.get("id") == identifier:
                if "error" in message:
                    raise RuntimeError(f"CDP {method}: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression: str):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})["result"]
        if result.get("subtype") == "error":
            raise RuntimeError(result.get("description", "browser JavaScript error"))
        return result.get("value")


def container_python(code: str) -> str:
    completed = subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "python", "-c", code],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def http_json(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def wait(cdp: CDP, expression: str, name: str, timeout: float = 20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cdp.evaluate(f"Boolean({expression})"):
            return
        time.sleep(0.1)
    raise AssertionError(f"Timeout waiting for {name}: {cdp.evaluate('document.body.innerText.slice(0,1200)')!r}")


def nav(cdp: CDP, path: str):
    cdp.call("Page.navigate", {"url": f"{BASE_URL}{path}"})
    wait(cdp, "document.readyState === 'complete'", f"load {path}")


def set_value(cdp: CDP, selector: str, value: str):
    cdp.evaluate(
        f"""(() => {{
          const element = document.querySelector({json.dumps(selector)});
          if (!element) throw new Error('missing {selector}');
          const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, {json.dumps(value)});
          element.dispatchEvent(new Event('input', {{bubbles: true}}));
          element.dispatchEvent(new Event('change', {{bubbles: true}}));
        }})()"""
    )


def disable_ai_for_fixture():
    return json.loads(container_python("""
import json
from decimal import Decimal
from backend.app.db.session import SessionLocal
from backend.app.models import AIModelSettings, Category, PipelineStage, Service
with SessionLocal() as session:
    row = session.get(AIModelSettings, 1)
    snapshot = None if row is None else {
        field: getattr(row, field) for field in (
            'analysis_model_override', 'email_model_override',
            'deal_prediction_validity_days', 'next_best_action_validity_days',
            'ai_enabled', 'automatic_new_deal_analysis',
        )
    }
    if row is None:
        session.add(AIModelSettings(id=1, ai_enabled=False, automatic_new_deal_analysis=False))
    else:
        row.ai_enabled = False
        row.automatic_new_deal_analysis = False
    category = Category(name_ru='P10 category', name_en='P10 category', name_es='P10 category', target_hourly_rate=Decimal('1.00'), target_effort=Decimal('1.00'), is_active=True)
    session.add(category)
    session.flush()
    service = Service(category_id=category.id, name_ru='P10 service', name_en='P10 service', name_es='P10 service', is_active=True)
    session.add(service)
    stage = session.query(PipelineStage).filter(PipelineStage.name == 'New Lead').one_or_none()
    created_stage_id = None
    if stage is None:
        stage = PipelineStage(name='New Lead', position=0)
        session.add(stage)
        session.flush()
        created_stage_id = str(stage.id)
    session.commit()
    print(json.dumps({'ai_snapshot': snapshot, 'category_id': str(category.id), 'service_id': str(service.id), 'created_stage_id': created_stage_id}))
"""))


def inspect_fixture():
    return json.loads(container_python(f"""
import json
from sqlalchemy import select
from backend.app.db.session import SessionLocal
from backend.app.models import Client, Deal, PipelineStage
with SessionLocal() as session:
    client = session.scalar(select(Client).where(Client.name == {PREFIX!r}))
    assert client is not None
    deal = session.scalar(select(Deal).where(Deal.client_id == client.id))
    stage = session.get(PipelineStage, deal.stage_id)
    print(json.dumps({{
        'client_id': str(client.id), 'deal_id': str(deal.id), 'status': client.status.value,
        'lead_source': client.lead_source, 'consent': client.personal_data_consent,
        'consent_at': client.personal_data_consent_at.isoformat() if client.personal_data_consent_at else None,
        'consent_version': client.personal_data_consent_version,
        'privacy_version': client.privacy_policy_version, 'stage': stage.name,
        'responsible_user_id': str(deal.responsible_user_id) if deal.responsible_user_id else None,
    }}))
"""))


def cleanup(fixture):
    snapshot_literal = repr(fixture["ai_snapshot"])
    category_id_literal = repr(fixture["category_id"])
    service_id_literal = repr(fixture["service_id"])
    created_stage_literal = repr(fixture["created_stage_id"])
    return json.loads(container_python(f"""
import json
from sqlalchemy import delete, func, select
from backend.app.db.session import SessionLocal
from backend.app.models import AIAnalysis, AIModelSettings, Category, Client, Deal, InitialAIAnalysisPipeline, PipelineStage, Service
with SessionLocal() as session:
    clients = list(session.scalars(select(Client).where(Client.name == {PREFIX!r})))
    client_ids = [row.id for row in clients]
    deal_ids = list(session.scalars(select(Deal.id).where(Deal.client_id.in_(client_ids)))) if client_ids else []
    if deal_ids:
        session.execute(delete(InitialAIAnalysisPipeline).where(InitialAIAnalysisPipeline.deal_id.in_(deal_ids)))
        session.execute(delete(AIAnalysis).where(AIAnalysis.deal_id.in_(deal_ids)))
        session.execute(delete(Deal).where(Deal.id.in_(deal_ids)))
    if client_ids:
        session.execute(delete(Client).where(Client.id.in_(client_ids)))
    service = session.get(Service, {service_id_literal})
    if service is not None:
        session.delete(service)
    category = session.get(Category, {category_id_literal})
    if category is not None:
        session.delete(category)
    if {created_stage_literal} is not None:
        stage = session.get(PipelineStage, {created_stage_literal})
        if stage is not None:
            session.delete(stage)
    snapshot = {snapshot_literal}
    row = session.get(AIModelSettings, 1)
    if snapshot is None:
        if row is not None:
            session.delete(row)
    else:
        if row is None:
            row = AIModelSettings(id=1)
            session.add(row)
        for field, value in snapshot.items():
            setattr(row, field, value)
    session.commit()
    residue = session.scalar(select(func.count()).select_from(Client).where(Client.name == {PREFIX!r}))
    print(json.dumps({{
        'client_residue': residue,
        'deal_residue': 0 if not client_ids else session.scalar(select(func.count()).select_from(Deal).where(Deal.client_id.in_(client_ids))),
        'service_residue': session.scalar(select(func.count()).select_from(Service).where(Service.id == {service_id_literal})),
        'category_residue': session.scalar(select(func.count()).select_from(Category).where(Category.id == {category_id_literal})),
        'stage_residue': 0 if {created_stage_literal} is None else session.scalar(select(func.count()).select_from(PipelineStage).where(PipelineStage.id == {created_stage_literal})),
    }}))
"""))


def main():
    chrome = None
    snapshot = None
    checks = {}
    failure = None
    cleanup_result = None
    try:
        snapshot = disable_ai_for_fixture()
        chrome = subprocess.Popen([
            "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
            "--remote-allow-origins=*", "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 20
        while True:
            try:
                http_json(f"http://127.0.0.1:{PORT}/json/version")
                break
            except Exception:
                if time.time() > deadline:
                    raise RuntimeError("Chrome CDP unavailable")
                time.sleep(0.2)
        target = next(item for item in http_json(f"http://127.0.0.1:{PORT}/json/list") if item["type"] == "page")
        cdp = CDP(target["webSocketDebuggerUrl"])
        cdp.call("Page.enable"); cdp.call("Runtime.enable")
        cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": """(() => { const original = window.fetch.bind(window); window.__p10_post_count = 0; window.fetch = (...args) => { if (String(args[0]).includes('/public/requests') && (args[1] || {}).method === 'POST') window.__p10_post_count += 1; return original(...args); }; })()"""})
        cdp.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
        nav(cdp, "/")
        wait(cdp, "document.documentElement.lang === 'ru' && document.querySelector('.public-card form') && document.querySelectorAll('.public-card select')[0]?.options.length > 0", "Russian public form")
        checkbox = "input[name=personal_data_consent]"
        assert cdp.evaluate(f"document.querySelector({checkbox!r}) && !document.querySelector({checkbox!r}).checked"), "consent checkbox is not unchecked by default"
        for href in ("/legal/personal-data-consent.pdf", "/legal/privacy-policy.pdf"):
            selector = f'a[href="{href}"]'
            assert cdp.evaluate(f"document.querySelector({json.dumps(selector)})?.target === '_blank'"), f"missing new-tab link {href}"
            with urllib.request.urlopen(f"{BASE_URL}{href}", timeout=10) as response:
                assert response.status == 200 and response.headers.get_content_type() == "application/pdf", href
        cdp.call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        assert cdp.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "mobile public form overflows horizontally"
        checks["public_form_desktop_mobile_and_pdfs"] = "PASS"
        cdp.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
        set_value(cdp, "input[name=name]", PREFIX)
        set_value(cdp, "input[name=deal_name]", f"{PREFIX} Deal")
        service_id = cdp.evaluate("document.querySelector('.public-card select').value")
        assert service_id, cdp.evaluate("document.querySelector('.public-card select').outerHTML")
        cdp.evaluate("document.querySelector('.public-card form').requestSubmit()")
        wait(cdp, "document.querySelector('.form-error[role=alert]')", "consent validation")
        assert cdp.evaluate("window.__p10_post_count === 0"), "unchecked consent sent a request"
        checks["unchecked_consent_blocks_submit"] = "PASS"
        cdp.evaluate(f"document.querySelector({checkbox!r}).click()")
        cdp.evaluate("document.querySelector('.public-card form').requestSubmit()")
        wait(cdp, "document.querySelector('.public-success')", "accepted public request")
        assert cdp.evaluate("window.__p10_post_count === 1"), "accepted consent did not send exactly one request"
        persisted = inspect_fixture()
        assert persisted == {
            **persisted, 'status': 'CUSTOMER', 'lead_source': 'Website', 'consent': True,
            'consent_version': PERSONAL_DATA_CONSENT_VERSION, 'privacy_version': PRIVACY_POLICY_VERSION,
            'stage': 'New Lead', 'responsible_user_id': None,
        } and persisted['consent_at'], persisted
        checks["accepted_request_and_server_metadata"] = "PASS"
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
                break
            time.sleep(0.1)
        try:
            cleanup_result = cleanup(snapshot) if snapshot is not None else {"not_started": True}
        except Exception as error:
            failure = failure or f"cleanup {type(error).__name__}: {error}"
    result = "PASS" if failure is None and not PROFILE.exists() and cleanup_result == {"client_residue": 0, "deal_residue": 0, "service_residue": 0, "category_residue": 0, "stage_residue": 0} else "FAIL"
    print(json.dumps({"result": result, "checks": checks, "cleanup": cleanup_result, "profile_removed": not PROFILE.exists(), "provider_operations": 0, "failure": failure}, ensure_ascii=False, indent=2))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
