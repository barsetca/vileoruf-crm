from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AnalyticsClientSummary(BaseModel):
    total: int
    customer: int
    client: int


class AnalyticsDealSummary(BaseModel):
    total: int
    active: int
    won: int
    lost: int


class AnalyticsPipelineStage(BaseModel):
    stage_id: UUID
    stage_name: str
    position: int
    deal_count: int
    estimated_value: Decimal


class AnalyticsMonthlyCount(BaseModel):
    month_start: datetime
    deal_count: int


class AnalyticsSummary(BaseModel):
    clients: AnalyticsClientSummary
    deals: AnalyticsDealSummary
    active_pipeline_estimated_value: Decimal
    won_deals_estimated_value: Decimal
    closed_deal_conversion_percent: Decimal | None
    pipeline_stages: list[AnalyticsPipelineStage]
    created_deals_by_month: list[AnalyticsMonthlyCount]
    first_won_deals_by_month: list[AnalyticsMonthlyCount]
