from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from backend.app.schemas.business import CommercialValuePoint


SCORE_QUANTUM = Decimal("0.1")
DEFAULT_COMMERCIAL_VALUE_SCALE = (
    CommercialValuePoint(ratio=Decimal("0.50"), score=0),
    CommercialValuePoint(ratio=Decimal("0.75"), score=40),
    CommercialValuePoint(ratio=Decimal("1.00"), score=70),
    CommercialValuePoint(ratio=Decimal("1.25"), score=85),
    CommercialValuePoint(ratio=Decimal("1.50"), score=100),
)


class InsufficientBusinessConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class CommercialValueResult:
    score: Decimal
    status: str
    effective_effort: Decimal
    deal_hourly_rate: Decimal | None
    ratio: Decimal | None


def interpolate_commercial_value(ratio: Decimal, scale: tuple[CommercialValuePoint, ...] | list[CommercialValuePoint]) -> Decimal:
    _validate_scale(scale)
    if ratio <= scale[0].ratio:
        return Decimal(scale[0].score).quantize(SCORE_QUANTUM)
    if ratio >= scale[-1].ratio:
        return Decimal(scale[-1].score).quantize(SCORE_QUANTUM)
    for left, right in zip(scale, scale[1:]):
        if left.ratio <= ratio <= right.ratio:
            score = Decimal(left.score) + ((ratio - left.ratio) / (right.ratio - left.ratio)) * Decimal(right.score - left.score)
            return min(Decimal(100), max(Decimal(0), score)).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
    raise AssertionError("Scale interpolation segment was not found")


def calculate_commercial_value(*, budget: Decimal | None, manager_effort: Decimal | None, category_target_effort: Decimal | None, category_target_hourly_rate: Decimal | None, scale: tuple[CommercialValuePoint, ...] | list[CommercialValuePoint]) -> CommercialValueResult:
    effective_effort = manager_effort if manager_effort is not None else category_target_effort
    if effective_effort is None or effective_effort <= 0:
        raise InsufficientBusinessConfigurationError("effective effort must be positive")
    if category_target_hourly_rate is None or category_target_hourly_rate <= 0:
        raise InsufficientBusinessConfigurationError("target hourly rate must be positive")
    _validate_scale(scale)
    if budget is None:
        return CommercialValueResult(score=Decimal("0.0"), status="NO_BUDGET", effective_effort=effective_effort, deal_hourly_rate=None, ratio=None)
    if budget < 0:
        raise ValueError("budget must be non-negative")
    deal_hourly_rate = budget / effective_effort
    ratio = deal_hourly_rate / category_target_hourly_rate
    return CommercialValueResult(score=interpolate_commercial_value(ratio, scale), status="CALCULATED", effective_effort=effective_effort, deal_hourly_rate=deal_hourly_rate, ratio=ratio)


def calculate_overall_score(*, service_fit: int, commercial_value: Decimal, lead_quality: int, feasibility: int, weights: tuple[int, int, int, int]) -> Decimal:
    if sum(weights) != 100:
        raise ValueError("weights must total exactly 100")
    for score in (service_fit, lead_quality, feasibility):
        if not 0 <= score <= 100:
            raise ValueError("factor score must be between 0 and 100")
    if not Decimal(0) <= commercial_value <= Decimal(100):
        raise ValueError("commercial value must be between 0 and 100")
    weighted = Decimal(service_fit * weights[0]) + commercial_value * weights[1] + Decimal(lead_quality * weights[2]) + Decimal(feasibility * weights[3])
    return (weighted / Decimal(100)).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def _validate_scale(scale) -> None:
    if len(scale) < 2:
        raise ValueError("scale requires at least two points")
    ratios = [point.ratio for point in scale]
    scores = [point.score for point in scale]
    if ratios != sorted(ratios) or len(set(ratios)) != len(ratios):
        raise ValueError("scale ratios must be unique and strictly increasing")
    if scores != sorted(scores) or any(score < 0 or score > 100 for score in scores):
        raise ValueError("scale scores must be non-decreasing within 0..100")
