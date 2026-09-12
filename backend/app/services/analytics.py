from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from backend.app.models import Client, ClientStatus, Deal, PipelineStage
from backend.app.schemas.analytics import (
    AnalyticsClientSummary,
    AnalyticsDealSummary,
    AnalyticsMonthlyCount,
    AnalyticsPipelineStage,
    AnalyticsSummary,
)


WON_STAGE_NAME = "Won"
LOST_STAGE_NAME = "Lost"
TERMINAL_STAGE_NAMES = (WON_STAGE_NAME, LOST_STAGE_NAME)


def get_analytics_summary(session: Session) -> AnalyticsSummary:
    client_counts = session.execute(
        select(
            func.count(Client.id),
            func.count(Client.id).filter(Client.status == ClientStatus.CUSTOMER),
            func.count(Client.id).filter(Client.status == ClientStatus.CLIENT),
        )
    ).one()
    effective_active = and_(Deal.archived_at.is_(None), Client.archived_at.is_(None))
    deal_counts = session.execute(
        select(
            func.count(Deal.id),
            func.count(Deal.id).filter(PipelineStage.name.not_in(TERMINAL_STAGE_NAMES), effective_active),
            func.count(Deal.id).filter(PipelineStage.name == WON_STAGE_NAME),
            func.count(Deal.id).filter(PipelineStage.name == LOST_STAGE_NAME),
            func.coalesce(func.sum(Deal.estimated_budget).filter(PipelineStage.name.not_in(TERMINAL_STAGE_NAMES), effective_active), 0),
            func.coalesce(func.sum(Deal.estimated_budget).filter(PipelineStage.name == WON_STAGE_NAME), 0),
        ).select_from(Deal).join(PipelineStage).join(Client)
    ).one()
    total, active, won, lost, active_value, won_value = deal_counts
    closed = won + lost
    conversion = None if closed == 0 else (Decimal(won) * Decimal("100") / Decimal(closed)).quantize(Decimal("0.01"))

    active_deals = (
        select(Deal.id, Deal.stage_id, Deal.estimated_budget)
        .join(Client)
        .where(Deal.archived_at.is_(None), Client.archived_at.is_(None))
        .subquery()
    )
    stages = session.execute(
        select(
            PipelineStage.id,
            PipelineStage.name,
            PipelineStage.position,
            func.count(active_deals.c.id),
            func.coalesce(func.sum(active_deals.c.estimated_budget), 0),
        ).outerjoin(active_deals, active_deals.c.stage_id == PipelineStage.id).group_by(PipelineStage.id).order_by(PipelineStage.position)
    ).all()

    return AnalyticsSummary(
        clients=AnalyticsClientSummary(total=client_counts[0], customer=client_counts[1], client=client_counts[2]),
        deals=AnalyticsDealSummary(total=total, active=active, won=won, lost=lost),
        active_pipeline_estimated_value=active_value,
        won_deals_estimated_value=won_value,
        closed_deal_conversion_percent=conversion,
        pipeline_stages=[AnalyticsPipelineStage(stage_id=row[0], stage_name=row[1], position=row[2], deal_count=row[3], estimated_value=row[4]) for row in stages],
        created_deals_by_month=_monthly_counts(session, Deal.created_at),
        first_won_deals_by_month=_monthly_counts(session, Deal.first_won_at),
    )


def _monthly_counts(session: Session, timestamp_column) -> list[AnalyticsMonthlyCount]:
    month = func.date_trunc("month", timestamp_column)
    rows = session.execute(
        select(month.label("month"), func.count(Deal.id))
        .where(timestamp_column.is_not(None))
        .group_by(month)
        .order_by(month)
    ).all()
    if not rows:
        return []
    counts = {row[0]: row[1] for row in rows}
    current = _month_start(rows[0][0])
    end = _month_start(datetime.now(timezone.utc))
    result = []
    while current <= end:
        result.append(AnalyticsMonthlyCount(month_start=current, deal_count=counts.get(current, 0)))
        current = _next_month(current)
    return result


def _month_start(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _next_month(value: datetime) -> datetime:
    return value.replace(year=value.year + 1, month=1) if value.month == 12 else value.replace(month=value.month + 1)
