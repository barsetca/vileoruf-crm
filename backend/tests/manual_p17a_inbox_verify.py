"""Narrow P1.7a Inbox-only Chromium smoke; synthetic data only."""
import secrets, shutil, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import delete, func, select
from backend.tests import manual_d63a_ru_browser_verify as base
from backend.app.db.session import SessionLocal
from backend.app.models import ExternalMessage, ExternalMessageStatus, IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider, User, UserRole
from backend.app.services.users import create_user

PREFIX = f"P17A_{secrets.token_hex(6)}_"; email=f"{PREFIX}admin@example.invalid"; password=secrets.token_urlsafe(18); ids={"users":[],"messages":[],"connections":[]}; profile=None; chrome=None
def setup():
    with SessionLocal() as s:
        u=create_user(s,email=email,display_name=PREFIX+"Admin",password=password,role=UserRole.ADMIN);ids["users"].append(u.id)
        g=s.scalar(select(IntegrationConnection).where(IntegrationConnection.provider==IntegrationProvider.GMAIL)) or IntegrationConnection(provider=IntegrationProvider.GMAIL,status=IntegrationConnectionStatus.CONNECTED,display_name="Gmail");t=s.scalar(select(IntegrationConnection).where(IntegrationConnection.provider==IntegrationProvider.TELEGRAM)) or IntegrationConnection(provider=IntegrationProvider.TELEGRAM,status=IntegrationConnectionStatus.CONNECTED,display_name="Telegram");s.add_all([g,t]);s.flush(); now=datetime.now(timezone.utc)
        a=ExternalMessage(integration_connection_id=g.id,provider=IntegrationProvider.GMAIL,provider_message_id=PREFIX+"mail",direction="INCOMING",status=ExternalMessageStatus.RECEIVED,sender_identifier="sender.p17a@example.test",recipient_identifier="crm",subject="P17A Subject",content="P17A email body",provider_created_at=now,received_at=now)
        b=ExternalMessage(integration_connection_id=t.id,provider=IntegrationProvider.TELEGRAM,provider_message_id=PREFIX+"telegram",direction="INCOMING",status=ExternalMessageStatus.RECEIVED,sender_identifier="RAW-P17A-ID-DO-NOT-SHOW",recipient_identifier="crm",content="P17A telegram body",sender_first_name="P17A First",sender_last_name="Last",sender_username="p17a_user",provider_created_at=now,received_at=now)
        s.add_all([a,b]);s.flush();ids["messages"] += [a.id,b.id];s.commit()
def cleanup():
    with SessionLocal() as s:
        for model,key in ((ExternalMessage,"messages"),(IntegrationConnection,"connections"),(User,"users")): s.execute(delete(model).where(model.id.in_(ids[key])))
        s.commit()
def main():
    global profile,chrome
    setup(); profile=Path(f"/tmp/p17a-{secrets.token_hex(6)}"); port=9337
    try:
        chrome=subprocess.Popen(["google-chrome","--headless=new","--no-sandbox","--disable-gpu","--remote-allow-origins=*",f"--remote-debugging-port={port}",f"--user-data-dir={profile}","about:blank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline=time.time()+20
        while True:
            try: target=next(x for x in base.http_json(f"http://127.0.0.1:{port}/json/list") if x["type"]=="page");break
            except Exception:
                if time.time()>deadline: raise
                time.sleep(.2)
        c=base.CDP(target["webSocketDebuggerUrl"]);c.call("Page.enable");c.call("Runtime.enable");base.nav(c,"/login");base.wait_for(c,"document.querySelector('#login-email')","login");base.set_input(c,"#login-email",email);base.set_input(c,"#login-password",password);c.evaluate("document.querySelector('form').requestSubmit()");base.wait_for(c,"location.pathname === '/crm'","auth");base.nav(c,"/crm/inbox");base.wait_for(c,"document.body.innerText.includes('P17A email body') && document.body.innerText.includes('P17A telegram body')","fixtures")
        text=c.evaluate("document.body.innerText"); assert "sender.p17a@example.test" in text and "P17A Subject" in text and "P17A First Last (@p17a_user)" in text and "RAW-P17A-ID-DO-NOT-SHOW" not in text
        assert all(c.evaluate(f"[...document.querySelectorAll('button')].some(x=>x.innerText==={v!r})") for v in ("Все","Email","Telegram")); c.evaluate("[...document.querySelectorAll('button')].find(x=>x.innerText==='Email').click()");base.wait_for(c,"document.body.innerText.includes('P17A email body') && !document.body.innerText.includes('P17A telegram body')","email filter");c.evaluate("[...document.querySelectorAll('button')].find(x=>x.innerText==='Telegram').click()");base.wait_for(c,"document.body.innerText.includes('P17A telegram body')","telegram filter"); assert c.evaluate("document.querySelectorAll('select').length >= 2 && document.body.innerText.includes('Удалить отмеченные')")
        print("P17A INBOX BROWSER PASS")
    finally:
        if chrome: chrome.terminate();chrome.wait(timeout=5)
        if profile: shutil.rmtree(profile,ignore_errors=True)
        cleanup()
        with SessionLocal() as s: assert all(s.scalar(select(func.count()).select_from(m).where(m.id.in_(ids[k])))==0 for m,k in ((ExternalMessage,"messages"),(IntegrationConnection,"connections"),(User,"users")))
if __name__=="__main__": main()
