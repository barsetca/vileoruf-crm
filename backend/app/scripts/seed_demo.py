import sys
from collections.abc import Callable
from typing import TextIO
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.config import AppEnvironment, Settings, get_settings
from backend.app.db.session import SessionLocal
from backend.app.models import Client, ClientStatus, Deal, PipelineStage


DEMO_CLIENT_IDS = [UUID(f"00000000-0000-0000-0000-d200000000{index:02d}") for index in range(1, 4)]
DEMO_DEAL_IDS = [UUID(f"00000000-0000-0000-0000-d200000000{index:02d}") for index in range(11, 16)]
DEMO_CLIENTS = [
    (DEMO_CLIENT_IDS[0], "Northstar Atelier", ClientStatus.CUSTOMER),
    (DEMO_CLIENT_IDS[1], "Blue Orchard Studio", ClientStatus.CLIENT),
    (DEMO_CLIENT_IDS[2], "Paper Kite Works", ClientStatus.CUSTOMER),
]
DEMO_DEALS = [
    (DEMO_DEAL_IDS[0], DEMO_CLIENT_IDS[0], "New Lead", "Northstar website refresh"),
    (DEMO_DEAL_IDS[1], DEMO_CLIENT_IDS[0], "Qualification", "Northstar discovery"),
    (DEMO_DEAL_IDS[2], DEMO_CLIENT_IDS[1], "Negotiation", "Blue Orchard identity"),
    (DEMO_DEAL_IDS[3], DEMO_CLIENT_IDS[1], "Won", "Blue Orchard launch"),
    (DEMO_DEAL_IDS[4], DEMO_CLIENT_IDS[2], "Lost", "Paper Kite campaign"),
]


class DemoSeedError(ValueError):
    pass


def seed_demo(session: Session, *, app_env: AppEnvironment) -> None:
    if app_env == "production":
        raise DemoSeedError("Demo seed is forbidden in production")
    stages = {stage.name: stage.id for stage in session.scalars(select(PipelineStage))}
    if any(name not in stages for _, _, name, _ in DEMO_DEALS):
        raise DemoSeedError("System pipeline must be bootstrapped before demo seed")
    for client_id, name, client_status in DEMO_CLIENTS:
        if session.get(Client, client_id) is None:
            session.add(Client(id=client_id, name=name, company=name, lead_source="Demo", status=client_status))
    session.flush()
    for deal_id, client_id, stage_name, name in DEMO_DEALS:
        if session.get(Deal, deal_id) is None:
            session.add(Deal(id=deal_id, client_id=client_id, stage_id=stages[stage_name], name=name, responsible_user_id=None))
    session.commit()


def clean_demo(session: Session, *, app_env: AppEnvironment) -> None:
    if app_env == "production":
        raise DemoSeedError("Demo cleanup is forbidden in production")
    session.execute(delete(Deal).where(Deal.id.in_(DEMO_DEAL_IDS)))
    session.execute(delete(Client).where(Client.id.in_(DEMO_CLIENT_IDS)))
    session.commit()


def main(*, session_factory: Callable[[], Session] = SessionLocal, settings_factory: Callable[[], Settings] = get_settings, argv: list[str] | None = None, stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    clean = "--clean" in (argv if argv is not None else sys.argv[1:])
    try:
        with session_factory() as session:
            operation = clean_demo if clean else seed_demo
            operation(session, app_env=settings_factory().app_env)
    except DemoSeedError as error:
        print(f"Demo seed failed: {error}", file=stderr)
        return 1
    print("Demo seed cleaned." if clean else "Demo seed ready: 3 clients, 5 deals.", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
