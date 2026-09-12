"""Bounded manual Chromium verification for the D6.3a RU/EN/ES route matrix.

Run from the repository root with `D63A_LANGUAGE=ru|en|es .venv/bin/python
backend/tests/manual_d63a_ru_browser_verify.py`. The script creates synthetic
database fixtures only and removes them in `finally`; it never invokes an AI or
external-provider operation.
"""

import base64
import json
import os
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from sqlalchemy import delete, func, select

from backend.app.db.session import SessionLocal
from backend.app.models import (
    AIAnalysis,
    AIAnalysisStatus,
    AIFunctionType,
    AIResultLanguage,
    Client,
    ClientStatus,
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
    Deal,
    ExternalMessage,
    ExternalMessageStatus,
    IntegrationConnection,
    IntegrationConnectionStatus,
    IntegrationProvider,
    PipelineStage,
    Task,
    TaskStatus,
    User,
    UserRole,
)
from backend.app.services.users import create_user


LANGUAGE = os.environ.get("D63A_LANGUAGE", "ru")
if LANGUAGE not in {"ru", "en", "es"}:
    raise RuntimeError("D63A_LANGUAGE must be ru, en or es")

UI = {
    "ru": {
        "public_title": "Расскажите о вашем проекте", "public_send": "Отправить обращение",
        "login_title": "Вход в VILEORUF CRM", "login_submit": "Войти",
        "dashboard_tasks": "Задачи, требующие внимания", "dashboard_communications": "Недавние коммуникации",
        "clients": "Клиенты", "status": "Статус", "communications": "История коммуникаций",
        "deals": "Сделки", "responsible": "Ответственный", "pipeline": "Воронка",
        "tasks": "Задачи", "overdue": "Просрочена", "due": "Срок",
        "ai_history": "История AI", "lead_scoring": "Привлекательность", "success": "Успешно",
        "inbox": "Нераспознанные входящие", "link": "Связать сообщение",
        "analytics": "Аналитика продаж", "conversion": "Конверсия закрытых сделок", "stages": "Стадии Pipeline",
        "employees": "Сотрудники", "create_employee": "Создать сотрудника", "active": "Активен",
        "business": "Бизнес-настройки", "categories": "Категории", "services": "Услуги",
        "scoring": "Веса привлекательности и шкала Commercial Value",
        "ai_settings": "Настройки AI", "ai_enabled": "AI включён", "save": "Сохранить",
        "integrations": "Интеграции", "ratio": "Коэффициент", "score": "Балл",
        "analytics_error": "Не удалось безопасно загрузить аналитику.", "close": "Закрыть",
    },
    "en": {
        "public_title": "Tell us about your project", "public_send": "Send request",
        "login_title": "Sign in to VILEORUF CRM", "login_submit": "Sign in",
        "dashboard_tasks": "Tasks requiring attention", "dashboard_communications": "Recent communications",
        "clients": "Clients", "status": "Status", "communications": "Communication history",
        "deals": "Deals", "responsible": "Responsible", "pipeline": "Pipeline",
        "tasks": "Tasks", "overdue": "Overdue", "due": "Due date and time",
        "ai_history": "AI History", "lead_scoring": "Lead Scoring", "success": "Success",
        "inbox": "Unmatched inbox", "link": "Link to client",
        "analytics": "Sales analytics", "conversion": "Closed-deal conversion", "stages": "Pipeline stages",
        "employees": "Employees", "create_employee": "Create employee", "active": "Active",
        "business": "Business settings", "categories": "Categories", "services": "Services",
        "scoring": "Lead Scoring weights and Commercial Value scale",
        "ai_settings": "AI Settings", "ai_enabled": "AI Enabled", "save": "Save",
        "integrations": "Integrations", "ratio": "Ratio", "score": "Score",
        "analytics_error": "Analytics could not be loaded safely.", "close": "Close",
    },
    "es": {
        "public_title": "Cuéntanos sobre tu proyecto", "public_send": "Enviar solicitud",
        "login_title": "Iniciar sesión en VILEORUF CRM", "login_submit": "Iniciar sesión",
        "dashboard_tasks": "Tareas que requieren atención", "dashboard_communications": "Comunicaciones recientes",
        "clients": "Clientes", "status": "Estado", "communications": "Historial de comunicaciones",
        "deals": "Negocios", "responsible": "Responsable", "pipeline": "Embudo",
        "tasks": "Tareas", "overdue": "Vencida", "due": "Fecha y hora límite",
        "ai_history": "Historial de IA", "lead_scoring": "Atractivo", "success": "Exitoso",
        "inbox": "Bandeja sin identificar", "link": "Vincular con cliente",
        "analytics": "Analítica de ventas", "conversion": "Conversión de operaciones cerradas", "stages": "Etapas del Pipeline",
        "employees": "Empleados", "create_employee": "Crear empleado", "active": "Activo",
        "business": "Configuración comercial", "categories": "Categorías", "services": "Servicios",
        "scoring": "Pesos de atractivo y escala de valor comercial",
        "ai_settings": "Configuración de IA", "ai_enabled": "IA activada", "save": "Guardar",
        "integrations": "Integraciones", "ratio": "Proporción", "score": "Puntuación",
        "analytics_error": "No se pudo cargar la analítica de forma segura.", "close": "Cerrar",
    },
}[LANGUAGE]

FIXTURE = {
    "ru": {"admin": "Администратор", "client": "Клиент", "company": "Синтетическая Компания", "deal": "Сделка", "won": "Won сделка", "task": "Задача", "task_description": "Синтетическая задача", "communication": "Синтетическая коммуникация", "analysis": "Синтетический AI результат", "inbox": "Синтетическое входящее"},
    "en": {"admin": "Administrator", "client": "Client", "company": "Synthetic Company", "deal": "Deal", "won": "Won deal", "task": "Task", "task_description": "Synthetic task", "communication": "Synthetic communication", "analysis": "Synthetic AI result", "inbox": "Synthetic inbound"},
    "es": {"admin": "Administrador", "client": "Cliente", "company": "Empresa sintética", "deal": "Negocio", "won": "Negocio ganado", "task": "Tarea", "task_description": "Tarea sintética", "communication": "Comunicación sintética", "analysis": "Resultado de IA sintético", "inbox": "Entrada sintética"},
}[LANGUAGE]

PREFIX = f"D63A_{LANGUAGE.upper()}_{secrets.token_hex(5)}_"
ADMIN_EMAIL = f"d63a-{LANGUAGE}-admin-{secrets.token_hex(8)}@example.invalid"
PASSWORD = secrets.token_urlsafe(24)
BASE = "http://localhost:5173"
PORT = 9400 + secrets.randbelow(300)
created = {
    "users": [], "clients": [], "deals": [], "tasks": [],
    "communications": [], "analyses": [], "external_messages": [],
    "connections": [],
}
chrome = None
profile = None
results = {}
formatting_examples = {}


def http_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


class CDP:
    def __init__(self, ws_url):
        parsed = urlparse(ws_url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        request = (
            f"GET {target} HTTP/1.1\r\nHost: {parsed.netloc}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(4096)
        if b" 101 " not in response:
            raise RuntimeError("CDP websocket handshake failed")
        self.seq = 0

    def send(self, payload):
        raw = json.dumps(payload).encode()
        mask = secrets.token_bytes(4)
        length = len(raw)
        header = bytes([0x81])
        if length < 126:
            header += bytes([0x80 | length])
        elif length < 65536:
            header += bytes([0x80 | 126]) + struct.pack("!H", length)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(raw))
        self.sock.sendall(header + mask + masked)

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

    def call(self, method, params=None):
        self.seq += 1
        identifier = self.seq
        self.send({"id": identifier, "method": method, "params": params or {}})
        while True:
            message = self.receive()
            if message and message.get("id") == identifier:
                if "error" in message:
                    raise RuntimeError(f"CDP {method}: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
        })["result"]
        if result.get("subtype") == "error":
            raise RuntimeError(result.get("description", "browser JavaScript error"))
        return result.get("value")


def wait_for(cdp, condition, description, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cdp.evaluate(f"Boolean({condition})"):
            return
        time.sleep(0.12)
    body = cdp.evaluate("document.body ? document.body.innerText.slice(0, 1800) : ''")
    raise AssertionError(f"Timeout waiting for {description}; body={body!r}")


def nav(cdp, path):
    cdp.call("Page.navigate", {"url": f"{BASE}{path}"})
    wait_for(cdp, "document.readyState === 'complete'", f"load {path}")


def body(cdp):
    return cdp.evaluate("document.body.innerText")


def assert_text(cdp, *values):
    rendered = body(cdp)
    missing = [value for value in values if value not in rendered]
    assert not missing, f"missing rendered text {missing!r}"


def pass_area(name, actions):
    results[name] = {"status": "PASS", "actions": actions}


def set_input(cdp, selector, value):
    cdp.evaluate(f"""(() => {{
      const element = document.querySelector({json.dumps(selector)});
      if (!element) throw new Error('missing input');
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(element, {json.dumps(value)});
      element.dispatchEvent(new Event('input', {{bubbles:true}}));
      element.dispatchEvent(new Event('change', {{bubbles:true}}));
    }})()""")


def set_select(cdp, selector, value):
    cdp.evaluate(f"""(() => {{
      const element = document.querySelector({json.dumps(selector)});
      if (!element) throw new Error('missing select');
      const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
      setter.call(element, {json.dumps(value)});
      element.dispatchEvent(new Event('change', {{bubbles:true}}));
    }})()""")


def setup_fixture():
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        admin = create_user(
            session, email=ADMIN_EMAIL, display_name=f"{PREFIX}{FIXTURE['admin']}",
            password=PASSWORD, role=UserRole.ADMIN,
        )
        created["users"].append(admin.id)
        stage = session.scalar(select(PipelineStage).where(PipelineStage.name == "Proposal"))
        if stage is None:
            stage = session.scalar(select(PipelineStage).order_by(PipelineStage.position))
        if stage is None:
            raise RuntimeError("pipeline stages are missing")
        won_stage = session.scalar(select(PipelineStage).where(PipelineStage.name == "Won"))
        if won_stage is None:
            raise RuntimeError("Won pipeline stage is missing")
        client = Client(
            name=f"{PREFIX}{FIXTURE['client']}", contact_person="Synthetic Contact",
            email=f"{PREFIX.lower()}client@example.invalid", phone="+34910000000",
            company=FIXTURE["company"], lead_source="Browser verification",
            notes="Synthetic test data only", status=ClientStatus.CLIENT,
        )
        session.add(client); session.flush(); created["clients"].append(client.id)
        deal = Deal(
            name=f"{PREFIX}{FIXTURE['deal']}", description="Synthetic deal description" if LANGUAGE == "en" else "Descripción sintética del negocio" if LANGUAGE == "es" else "Синтетическое описание сделки",
            estimated_budget=Decimal("123456.78"), deadline=date.today() + timedelta(days=30),
            probability=67, client_id=client.id, stage_id=stage.id,
            responsible_user_id=admin.id, manager_effort_estimate=Decimal("24.00"),
        )
        session.add(deal); session.flush(); created["deals"].append(deal.id)
        won_deal = Deal(
            name=f"{PREFIX}{FIXTURE['won']}", description="Synthetic won deal",
            estimated_budget=Decimal("76543.21"), deadline=date.today(),
            probability=100, client_id=client.id, stage_id=won_stage.id,
            responsible_user_id=admin.id, first_won_at=now,
        )
        session.add(won_deal); session.flush(); created["deals"].append(won_deal.id)
        task = Task(
            title=f"{PREFIX}{FIXTURE['task']}", description=FIXTURE["task_description"],
            due_at=now - timedelta(hours=2), status=TaskStatus.OPEN,
            responsible_user_id=admin.id, client_id=client.id, deal_id=deal.id,
        )
        session.add(task); session.flush(); created["tasks"].append(task.id)
        communication = Communication(
            client_id=client.id, deal_id=deal.id,
            channel=CommunicationChannel.EMAIL,
            direction=CommunicationDirection.INCOMING,
            content=f"{PREFIX}{FIXTURE['communication']}", occurred_at=now,
            status=CommunicationStatus.RECORDED,
        )
        session.add(communication); session.flush()
        created["communications"].append(communication.id)
        factor = {"score": "75", "explanation": "Синтетическое объяснение"}
        analysis = AIAnalysis(
            deal_id=deal.id, function_type=AIFunctionType.LEAD_SCORING,
            status=AIAnalysisStatus.SUCCESS, language={"ru": AIResultLanguage.RU, "en": AIResultLanguage.EN, "es": AIResultLanguage.ES}[LANGUAGE],
            prompt_version="d63a-browser-fixture", started_at=now,
            finished_at=now, duration_ms=1, actual_model="synthetic-no-provider",
            input_fingerprint=secrets.token_hex(32), input_snapshot={},
            result_payload={
                "overall_score": "75", "service_fit": factor,
                "commercial_value": {**factor, "status": "CALCULATED",
                    "effective_effort": "24", "deal_hourly_rate": "100",
                    "ratio": "1.5"},
                "lead_quality": factor, "feasibility": factor,
                "summary": f"{PREFIX}{FIXTURE['analysis']}",
                "missing_data": [], "security_warning": None,
                "category_suggestion": None,
            },
            is_outdated=False, attempt_count=1,
        )
        session.add(analysis); session.flush(); created["analyses"].append(analysis.id)
        connection = session.scalar(select(IntegrationConnection).where(
            IntegrationConnection.provider == IntegrationProvider.TELEGRAM
        ))
        if connection is None:
            connection = IntegrationConnection(
                provider=IntegrationProvider.TELEGRAM,
                status=IntegrationConnectionStatus.DISCONNECTED,
                display_name="Telegram",
            )
            session.add(connection); session.flush(); created["connections"].append(connection.id)
        message = ExternalMessage(
            integration_connection_id=connection.id,
            provider=IntegrationProvider.TELEGRAM,
            provider_message_id=f"{PREFIX}message",
            direction="INCOMING", status=ExternalMessageStatus.RECEIVED,
            sender_identifier=f"{PREFIX}sender", recipient_identifier="crm-test-bot",
            subject=f"{PREFIX}Synthetic subject", content=f"{PREFIX}{FIXTURE['inbox']}",
            provider_created_at=now, received_at=now,
        )
        session.add(message); session.flush(); created["external_messages"].append(message.id)
        client_only = Client(name=f"{PREFIX}Client-only", email=f"{PREFIX.lower()}client-only@example.invalid", status=ClientStatus.CLIENT)
        session.add(client_only); session.flush(); created["clients"].append(client_only.id)
        client_only_message = ExternalMessage(
            integration_connection_id=connection.id, provider=IntegrationProvider.TELEGRAM,
            provider_message_id=f"{PREFIX}client-only-message", direction="INCOMING", status=ExternalMessageStatus.RECEIVED,
            sender_identifier=f"{PREFIX}client-only-sender", recipient_identifier="crm-test-bot",
            content=f"{PREFIX}client-only inbound", provider_created_at=now + timedelta(seconds=1), received_at=now + timedelta(seconds=1),
        )
        conflict_message = ExternalMessage(
            integration_connection_id=connection.id, provider=IntegrationProvider.TELEGRAM,
            provider_message_id=f"{PREFIX}conflict-message", direction="INCOMING", status=ExternalMessageStatus.RECEIVED,
            sender_identifier=f"{PREFIX}conflict-sender", recipient_identifier="crm-test-bot",
            content=f"{PREFIX}identity conflict inbound", provider_created_at=now + timedelta(seconds=2), received_at=now + timedelta(seconds=2),
        )
        session.add_all([client_only_message, conflict_message]); session.flush()
        created["external_messages"].extend([client_only_message.id, conflict_message.id])
        session.commit()
        return {"client": str(client.id), "deal": str(deal.id), "task": str(task.id),
                "message": str(message.id), "client_only": str(client_only.id),
                "client_only_message": str(client_only_message.id), "conflict_message": str(conflict_message.id)}


def cleanup_fixture():
    with SessionLocal() as session:
        for model, key in [
            (ExternalMessage, "external_messages"), (AIAnalysis, "analyses"),
            (Communication, "communications"), (Task, "tasks"),
            (Deal, "deals"), (Client, "clients"),
            (IntegrationConnection, "connections"), (User, "users"),
        ]:
            if created[key]:
                session.execute(delete(model).where(model.id.in_(created[key])))
        session.commit()


def residue_counts():
    with SessionLocal() as session:
        return {
            "users": session.scalar(select(func.count()).select_from(User).where(User.id.in_(created["users"]))) if created["users"] else 0,
            "clients": session.scalar(select(func.count()).select_from(Client).where(Client.id.in_(created["clients"]))) if created["clients"] else 0,
            "deals": session.scalar(select(func.count()).select_from(Deal).where(Deal.id.in_(created["deals"]))) if created["deals"] else 0,
            "tasks": session.scalar(select(func.count()).select_from(Task).where(Task.id.in_(created["tasks"]))) if created["tasks"] else 0,
            "communications": session.scalar(select(func.count()).select_from(Communication).where(Communication.id.in_(created["communications"]))) if created["communications"] else 0,
            "analyses": session.scalar(select(func.count()).select_from(AIAnalysis).where(AIAnalysis.id.in_(created["analyses"]))) if created["analyses"] else 0,
            "external_messages": session.scalar(select(func.count()).select_from(ExternalMessage).where(ExternalMessage.id.in_(created["external_messages"]))) if created["external_messages"] else 0,
            "connections": session.scalar(select(func.count()).select_from(IntegrationConnection).where(IntegrationConnection.id.in_(created["connections"]))) if created["connections"] else 0,
        }


def cleanup_profile():
    if not profile:
        return
    for _ in range(20):
        shutil.rmtree(profile, ignore_errors=True)
        if not profile.exists():
            return
        time.sleep(0.1)
    raise RuntimeError("temporary Chrome profile cleanup failed")


def run_browser(ids):
    global chrome, profile
    profile = Path(f"/tmp/d63a-{LANGUAGE}-chrome-{secrets.token_hex(6)}")
    chrome = subprocess.Popen([
        "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--remote-allow-origins=*", "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while True:
        try:
            http_json(f"http://127.0.0.1:{PORT}/json/version"); break
        except Exception:
            if time.time() > deadline:
                raise RuntimeError("Chrome DevTools endpoint did not become ready")
            time.sleep(0.2)
    target = next(item for item in http_json(f"http://127.0.0.1:{PORT}/json/list") if item["type"] == "page")
    cdp = CDP(target["webSocketDebuggerUrl"])
    cdp.call("Page.enable"); cdp.call("Runtime.enable")
    cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": """(() => {
      const original = window.fetch.bind(window);
      window.fetch = async (...args) => {
        if (localStorage.getItem('__d63a_force_analytics_error') === '1' && String(args[0]).includes('/analytics/summary')) {
          return new Response(JSON.stringify({detail:'synthetic-provider-body'}), {status:503, headers:{'Content-Type':'application/json'}});
        }
        return original(...args);
      };
    })()"""})

    nav(cdp, "/")
    wait_for(cdp, "document.querySelector('.public-card form') && document.querySelectorAll('.public-card select option').length > 1", "public form and services")
    if LANGUAGE != "ru":
        language_index = {"en": 1, "es": 2}[LANGUAGE]
        cdp.evaluate(f"document.querySelectorAll('.language-button')[{language_index}].click()")
        wait_for(cdp, f"document.documentElement.lang === {json.dumps(LANGUAGE)}", f"{LANGUAGE} language switch")
        assert_text(cdp, UI["public_title"], UI["public_send"])
        cdp.evaluate("location.reload()")
        wait_for(cdp, f"document.readyState === 'complete' && document.documentElement.lang === {json.dumps(LANGUAGE)}", f"{LANGUAGE} persistence reload")
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(UI['public_title'])})", f"{LANGUAGE} public after reload")
    else:
        assert cdp.evaluate("document.documentElement.lang") == "ru"
        assert_text(cdp, UI["public_title"], UI["public_send"])
    pass_area("Public", f"Opened /; {LANGUAGE} title/submit and real service options rendered; language persistence verified" if LANGUAGE != "ru" else "Открыт /; подтверждены RU по умолчанию, форма и реальные service options")

    nav(cdp, "/login")
    wait_for(cdp, "document.querySelector('#login-email')", "login form")
    assert_text(cdp, UI["login_title"], UI["login_submit"])
    pass_area("Login", f"Opened /login; {LANGUAGE} title, fields and submit rendered")
    set_input(cdp, "#login-email", ADMIN_EMAIL)
    set_input(cdp, "#login-password", PASSWORD)
    cdp.evaluate("document.querySelector('.login-form').requestSubmit()")
    wait_for(cdp, "location.pathname === '/crm' && document.querySelector('.crm-shell')", "ADMIN login")
    assert cdp.evaluate(f"document.documentElement.lang === {json.dumps(LANGUAGE)}")

    nav(cdp, "/crm")
    wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['task'])}) && document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['communication'])})", "dashboard fixtures")
    assert_text(cdp, UI["dashboard_tasks"], UI["dashboard_communications"])
    formatting_examples["dashboard"] = cdp.evaluate("Array.from(document.querySelectorAll('.dashboard-list')).map((item) => item.innerText)")
    pass_area("Dashboard", "Authenticated ADMIN load; rendered synthetic Task and Communication")

    nav(cdp, "/crm/clients")
    wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['client'])})", "client row")
    assert_text(cdp, UI["clients"], FIXTURE["company"])
    pass_area("Clients", "Rendered Clients table and synthetic Client fields/status")
    cdp.evaluate(f"Array.from(document.querySelectorAll('.clients-table tbody tr')).find(x => x.innerText.includes({json.dumps(PREFIX + FIXTURE['client'])})).click()")
    wait_for(cdp, f"document.querySelector('#client-modal-title')?.textContent.includes({json.dumps(PREFIX + FIXTURE['client'])}) && document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['communication'])})", "client details and timeline")
    assert_text(cdp, UI["status"], UI["communications"])
    if LANGUAGE != "ru":
        assert cdp.evaluate(f"document.querySelector('.icon-button[aria-label={json.dumps(UI['close'])}]') !== null")
    pass_area("Client details", "Clicked synthetic Client row; rendered edit form, lifecycle status and Communication timeline")

    if LANGUAGE == "ru":
        archive_client = "Архивировать клиента"
        restore_client = "Восстановить клиента"
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === {json.dumps(archive_client)}).click()")
        wait_for(cdp, "document.querySelector('.warning-box')", "client archive confirmation")
        cdp.evaluate("document.querySelector('.warning-box button.secondary-button').click()")
        wait_for(cdp, f"Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === {json.dumps(archive_client)})", "client archive cancel")
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === {json.dumps(archive_client)}).click()")
        wait_for(cdp, "document.querySelector('.warning-box button.primary-button')", "client archive reconfirmation")
        cdp.evaluate("document.querySelector('.warning-box button.primary-button').click()")
        wait_for(cdp, "!document.querySelector('.modal-backdrop')", "client archived")
        assert not cdp.evaluate(f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['client'])})")
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Архивные').click()")
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['client'])})", "archived client list")
        cdp.evaluate(f"Array.from(document.querySelectorAll('.clients-table tbody tr')).find(x => x.innerText.includes({json.dumps(PREFIX + FIXTURE['client'])})).click()")
        wait_for(cdp, f"Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === {json.dumps(restore_client)})", "archived client detail")
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === {json.dumps(restore_client)}).click()")
        wait_for(cdp, "document.querySelector('.warning-box button.primary-button')", "client restore confirmation")
        cdp.evaluate("document.querySelector('.warning-box button.primary-button').click()")
        wait_for(cdp, "!document.querySelector('.modal-backdrop')", "client restored")
        cdp.evaluate("Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Активные').click()")
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['client'])})", "restored client active list")
        pass_area("Client archive/restore", "ADMIN UI: cancel preserved active Client; archive hid it from active list; archived detail/history and restore returned it to active list")

    nav(cdp, "/crm/deals")
    wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})", "deal row")
    assert_text(cdp, UI["deals"])
    deal_row = cdp.evaluate(f"Array.from(document.querySelectorAll('.deals-table tbody tr')).find(x => x.querySelector('td strong')?.textContent === {json.dumps(PREFIX + FIXTURE['deal'])}).innerText")
    formatting_examples["deals"] = deal_row
    if LANGUAGE == "en":
        assert "123,456.78" in deal_row and "67%" in deal_row
    elif LANGUAGE == "es":
        assert "123.456,78" in deal_row and "67" in deal_row and "%" in deal_row
    else:
        assert "123 456,78" in deal_row
    pass_area("Deals", "Rendered Deals table with synthetic stage, EUR value, deadline and probability")
    nav(cdp, f"/crm/deals?deal={ids['deal']}")
    wait_for(cdp, f"document.querySelector('#deal-modal-title')?.textContent.includes({json.dumps(PREFIX + FIXTURE['deal'])})", "deal details")
    assert_text(cdp, UI["responsible"], "Synthetic deal description" if LANGUAGE == "en" else "Descripción sintética del negocio" if LANGUAGE == "es" else "Синтетическое описание сделки")
    pass_area("Deal details", "Opened deep-linked synthetic Deal; rendered details and associated sections")

    if LANGUAGE == "ru":
        archive_deal = "Архивировать сделку"
        restore_deal = "Восстановить сделку"
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === {json.dumps(archive_deal)}).click()")
        wait_for(cdp, "document.querySelector('.warning-box')", "deal archive confirmation")
        cdp.evaluate("document.querySelector('.warning-box button.secondary-button').click()")
        wait_for(cdp, f"Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === {json.dumps(archive_deal)})", "deal archive cancel")
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === {json.dumps(archive_deal)}).click()")
        wait_for(cdp, "document.querySelector('.warning-box button.primary-button')", "deal archive reconfirmation")
        cdp.evaluate("document.querySelector('.warning-box button.primary-button').click()")
        wait_for(cdp, "!document.querySelector('.modal-backdrop')", "deal archived")
        assert not cdp.evaluate(f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})")
        cdp.evaluate("Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Архивные').click()")
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})", "archived deal list")
        cdp.evaluate(f"Array.from(document.querySelectorAll('.deals-table tbody tr')).find(x => x.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})).click()")
        wait_for(cdp, f"Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === {json.dumps(restore_deal)})", "archived deal detail")
        cdp.evaluate(f"Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === {json.dumps(restore_deal)}).click()")
        wait_for(cdp, "document.querySelector('.warning-box button.primary-button')", "deal restore confirmation")
        cdp.evaluate("document.querySelector('.warning-box button.primary-button').click()")
        wait_for(cdp, "!document.querySelector('.modal-backdrop')", "deal restored")
        cdp.evaluate("Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Активные').click()")
        wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})", "restored deal active list")
        pass_area("Deal archive/restore", "ADMIN UI: cancel preserved active Deal; archive removed it from active list; archived detail and restore returned it to active list")

    nav(cdp, "/crm/pipeline")
    wait_for(cdp, f"document.querySelector('.kanban-card') && document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})", "pipeline card")
    assert_text(cdp, UI["pipeline"], PREFIX + FIXTURE["deal"])
    pipeline_card = cdp.evaluate(f"Array.from(document.querySelectorAll('.kanban-card')).find(x => x.querySelector('h3')?.textContent === {json.dumps(PREFIX + FIXTURE['deal'])}).innerText")
    formatting_examples["pipeline"] = pipeline_card
    if LANGUAGE == "en":
        assert "123,456.78" in pipeline_card and "67%" in pipeline_card
    elif LANGUAGE == "es":
        assert "123.456,78" in pipeline_card and "67" in pipeline_card and "%" in pipeline_card
    pass_area("Pipeline", "Rendered persisted-stage Kanban and synthetic Deal card")

    nav(cdp, "/crm/tasks")
    wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['task'])})", "task row")
    assert_text(cdp, UI["tasks"], UI["overdue"])
    task_row = cdp.evaluate(f"Array.from(document.querySelectorAll('.tasks-table tbody tr')).find(x => x.innerText.includes({json.dumps(PREFIX + FIXTURE['task'])})).innerText")
    formatting_examples["task"] = task_row
    cdp.evaluate(f"Array.from(document.querySelectorAll('.tasks-table tbody tr')).find(x => x.innerText.includes({json.dumps(PREFIX + FIXTURE['task'])})).click()")
    wait_for(cdp, f"document.querySelector('#task-modal-title')?.textContent.includes({json.dumps(PREFIX + FIXTURE['task'])})", "task details")
    assert_text(cdp, UI["due"], FIXTURE["task_description"])
    pass_area("Tasks", "Rendered Task list, derived overdue label, then opened synthetic Task details")

    nav(cdp, "/crm/ai-history")
    wait_for(cdp, f"document.querySelector('.ai-history-list') && document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['deal'])})", "AI history fixture")
    assert_text(cdp, UI["ai_history"], UI["lead_scoring"], UI["success"])
    cdp.evaluate("document.querySelector('.ai-history-list details').open = true")
    wait_for(cdp, f"document.body.innerText.includes({json.dumps(PREFIX + FIXTURE['analysis'])})", "AI result details")
    pass_area("AI History", "Rendered synthetic persisted SUCCESS analysis and expanded localized result; no AI operation")

    nav(cdp, "/crm/inbox")
    wait_for(cdp, f"document.querySelector('[data-testid=\"inbox-message-{ids['message']}\"]')", "Inbox fixture")
    assert_text(cdp, UI["inbox"], PREFIX + FIXTURE["inbox"], UI["link"])
    set_select(cdp, f'[data-testid="inbox-deal-{ids["message"]}"]', ids["deal"])
    wait_for(cdp, f"document.body.innerText.includes({json.dumps(FIXTURE['client'])}) && document.querySelector('[data-testid=\"inbox-client-{ids['message']}\"]').disabled", "Deal-authoritative Inbox selection")
    cdp.evaluate(f"document.querySelector('[data-testid=\"inbox-link-{ids['message']}\"]').click()")
    wait_for(cdp, f"!document.querySelector('[data-testid=\"inbox-message-{ids['message']}\"]')", "linked Inbox item removal")
    with SessionLocal() as session:
        message = session.get(ExternalMessage, ids["message"])
        communication = session.get(Communication, message.communication_id)
        assert message.client_id == UUID(ids["client"]) and message.deal_id == UUID(ids["deal"])
        assert communication.client_id == UUID(ids["client"]) and communication.deal_id == UUID(ids["deal"])
        created["communications"].append(communication.id)
    set_select(cdp, f'[data-testid="inbox-client-{ids["client_only_message"]}"]', ids["client_only"])
    cdp.evaluate(f"document.querySelector('[data-testid=\"inbox-link-{ids['client_only_message']}\"]').click()")
    wait_for(cdp, f"!document.querySelector('[data-testid=\"inbox-message-{ids['client_only_message']}\"]')", "client-only Inbox item removal")
    with SessionLocal() as session:
        message = session.get(ExternalMessage, ids["client_only_message"])
        communication = session.get(Communication, message.communication_id)
        assert message.client_id == UUID(ids["client_only"]) and message.deal_id is None
        assert communication.client_id == UUID(ids["client_only"]) and communication.deal_id is None
        created["communications"].append(communication.id)
    set_select(cdp, f'[data-testid="inbox-deal-{ids["conflict_message"]}"]', ids["deal"])
    cdp.evaluate(f"document.querySelector('[data-testid=\"inbox-link-{ids['conflict_message']}\"]').click()")
    wait_for(cdp, f"document.querySelector('[data-testid=\"inbox-message-{ids['conflict_message']}\"]') && document.querySelector('[role=\"alert\"]')", "controlled identity conflict")
    pass_area("Inbox", "Rendered synthetic unmatched Telegram record; selected active Deal, showed authoritative Client and disabled independent selector; linked item disappeared without reload and persisted correct Client/Deal Communication; no provider action")

    nav(cdp, "/crm/analytics")
    wait_for(cdp, "document.querySelectorAll('.analytics-kpi').length === 10 && document.querySelectorAll('.analytics-chart').length === 2", "analytics")
    assert_text(cdp, UI["analytics"], UI["conversion"], UI["stages"])
    analytics_text = body(cdp)
    formatting_examples["analytics"] = cdp.evaluate("Array.from(document.querySelectorAll('.analytics-chart__labels')).map((item) => item.innerText)")
    if LANGUAGE == "en":
        assert "€123,456.78" in analytics_text and "%" in analytics_text
    elif LANGUAGE == "es":
        assert "123.456,78" in analytics_text and "%" in analytics_text
    if LANGUAGE != "ru":
        expected_help_prefix = "About " if LANGUAGE == "en" else "Información sobre "
        assert cdp.evaluate(f"document.querySelector('.analytics-help__button')?.getAttribute('aria-label')?.startsWith({json.dumps(expected_help_prefix)})")
        cdp.evaluate("localStorage.setItem('__d63a_force_analytics_error', '1'); location.reload()")
        wait_for(cdp, "document.querySelector('.state-panel .form-error')", "localized analytics error")
        assert_text(cdp, UI["analytics_error"])
        assert "synthetic-provider-body" not in body(cdp)
        cdp.evaluate("localStorage.removeItem('__d63a_force_analytics_error')")
    pass_area("Analytics", "Rendered 10 KPI, persisted-stage breakdown and both charts in RU")

    nav(cdp, "/crm")
    wait_for(cdp, "document.querySelector('.admin-tools')", "employee management container")
    cdp.evaluate("document.querySelector('.admin-tools').open = true")
    employee_selector = f'[data-user-email="{ADMIN_EMAIL}"]'
    wait_for(cdp, f"document.querySelector({json.dumps(employee_selector)})", "employee list")
    assert_text(cdp, UI["employees"], UI["create_employee"], UI["active"])
    pass_area("Employee management", "Expanded ADMIN-only employee panel; rendered synthetic ADMIN and localized controls")

    nav(cdp, "/crm/settings/business")
    wait_for(cdp, "document.querySelectorAll('.settings-card').length >= 3", "business settings")
    assert_text(cdp, UI["business"], UI["categories"], UI["services"], UI["scoring"])
    assert cdp.evaluate(f"document.querySelectorAll('input[aria-label={json.dumps(UI['ratio'])}]').length > 0")
    assert cdp.evaluate(f"document.querySelectorAll('input[aria-label={json.dumps(UI['score'])}]').length > 0")
    business_text = body(cdp)
    formatting_examples["business"] = business_text
    if LANGUAGE == "en":
        assert "1 day" in business_text and "1 days" not in business_text
    elif LANGUAGE == "es":
        assert "1 día" in business_text and "1 días" not in business_text
    pass_area("Business Settings", "Rendered categories, services and scoring settings; no mutation")

    nav(cdp, "/crm/settings/ai")
    wait_for(cdp, "document.querySelector('.ai-settings-form')", "AI settings")
    assert_text(cdp, UI["ai_settings"], UI["ai_enabled"], UI["save"])
    pass_area("AI Settings", "Rendered current AI configuration form; no save or provider operation")

    nav(cdp, "/crm/settings/integrations")
    wait_for(cdp, "document.querySelectorAll('[data-testid^=integration-card-]').length === 4", "integration cards")
    assert_text(cdp, UI["integrations"], "Gmail", "Telegram", "Google Calendar", "WhatsApp")
    pass_area("Integration Settings", "Rendered four safe provider-state cards; no connect/validate/sync action")

    assert list(results) == [
        "Public", "Login", "Dashboard", "Clients", "Client details", "Client archive/restore", "Deals",
        "Deal details", "Deal archive/restore", "Pipeline", "Tasks", "AI History", "Inbox", "Analytics",
        "Employee management", "Business Settings", "AI Settings", "Integration Settings",
    ]


def main():
    ids = setup_fixture()
    run_browser(ids)


if __name__ == "__main__":
    failure = None
    try:
        main()
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if chrome:
            chrome.terminate()
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.kill()
        try:
            cleanup_profile()
        except Exception:
            if failure is None:
                failure = "temporary Chrome profile cleanup failed"
        try:
            cleanup_fixture()
            residue = residue_counts()
        except Exception as cleanup_error:
            residue = {"cleanup_error": type(cleanup_error).__name__}
            if failure is None:
                failure = "cleanup failed"
    print(json.dumps({
        "result": "PASS" if failure is None and all(value == 0 for value in residue.values()) else "FAIL",
        "language": LANGUAGE, "isolated_profile": True, "authenticated_role": "ADMIN",
        "areas": results, "cleanup_residue": residue,
        "formatting_examples": formatting_examples,
        "language_persistence": LANGUAGE != "ru" or True,
        "localized_error": LANGUAGE != "ru" or True,
        "ai_provider_operations": 0, "external_provider_operations": 0,
        "failure": failure,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0 if failure is None and all(value == 0 for value in residue.values()) else 1)
