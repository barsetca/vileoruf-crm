from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.models import AIResultLanguage
from backend.app.schemas.ai import LeadScoringAIResult
from backend.app.schemas.business import CommercialValuePoint, LeadScoringSettingsPayload
from backend.app.services.ai.lead_scoring import build_final_lead_scoring_result
from backend.app.services.commercial_value import DEFAULT_COMMERCIAL_VALUE_SCALE, InsufficientBusinessConfigurationError, calculate_commercial_value, calculate_overall_score, interpolate_commercial_value


@pytest.mark.parametrize(("ratio", "score"), [("0.50", "0.0"), ("0.75", "40.0"), ("1.00", "70.0"), ("1.25", "85.0"), ("1.50", "100.0"), ("0.625", "20.0"), ("0.875", "55.0"), ("1.125", "77.5"), ("1.375", "92.5"), ("0.20", "0.0"), ("2.00", "100.0")])
def test_exact_scale_anchors_interpolation_and_clamp(ratio, score):
    assert interpolate_commercial_value(Decimal(ratio), DEFAULT_COMMERCIAL_VALUE_SCALE) == Decimal(score)


def test_custom_scale_and_decimal_half_up_precision():
    scale = [CommercialValuePoint(ratio=Decimal("0.5"), score=10), CommercialValuePoint(ratio=Decimal("1.0"), score=90)]
    assert interpolate_commercial_value(Decimal("0.7500"), scale) == Decimal("50.0")
    assert interpolate_commercial_value(Decimal("0.500625"), scale) == Decimal("10.1")


@pytest.mark.parametrize("scale", [
    [CommercialValuePoint(ratio=Decimal("1"), score=20)],
    [CommercialValuePoint(ratio=Decimal("1"), score=20), CommercialValuePoint(ratio=Decimal("1"), score=30)],
    [CommercialValuePoint(ratio=Decimal("1"), score=30), CommercialValuePoint(ratio=Decimal("2"), score=20)],
])
def test_invalid_scale_is_rejected(scale):
    with pytest.raises(ValueError): interpolate_commercial_value(Decimal("1"), scale)


def test_missing_budget_is_no_data_not_bad_value_and_effort_fallback():
    result = calculate_commercial_value(budget=None, manager_effort=None, category_target_effort=Decimal("8"), category_target_hourly_rate=Decimal("50"), scale=DEFAULT_COMMERCIAL_VALUE_SCALE)
    assert result.score == Decimal("0.0") and result.status == "NO_BUDGET" and result.effective_effort == Decimal("8")


def test_manager_effort_overrides_category_effort():
    result = calculate_commercial_value(budget=Decimal("800"), manager_effort=Decimal("8"), category_target_effort=Decimal("16"), category_target_hourly_rate=Decimal("100"), scale=DEFAULT_COMMERCIAL_VALUE_SCALE)
    assert result.effective_effort == Decimal("8") and result.ratio == Decimal("1") and result.score == Decimal("70.0")


@pytest.mark.parametrize(("effort", "rate"), [(None, Decimal("50")), (Decimal("0"), Decimal("50")), (Decimal("8"), None), (Decimal("8"), Decimal("0")), (Decimal("8"), Decimal("-1"))])
def test_missing_or_invalid_business_configuration_is_rejected(effort, rate):
    with pytest.raises(InsufficientBusinessConfigurationError):
        calculate_commercial_value(budget=Decimal("100"), manager_effort=None, category_target_effort=effort, category_target_hourly_rate=rate, scale=DEFAULT_COMMERCIAL_VALUE_SCALE)


def test_negative_budget_is_invalid():
    with pytest.raises(ValueError): calculate_commercial_value(budget=Decimal("-1"), manager_effort=Decimal("1"), category_target_effort=Decimal("2"), category_target_hourly_rate=Decimal("50"), scale=DEFAULT_COMMERCIAL_VALUE_SCALE)


def test_weights_exactly_100_and_overall_half_up():
    assert calculate_overall_score(service_fit=80, commercial_value=Decimal("70.0"), lead_quality=60, feasibility=90, weights=(30, 30, 15, 25)) == Decimal("76.5")
    with pytest.raises(ValueError): calculate_overall_score(service_fit=80, commercial_value=Decimal("70"), lead_quality=60, feasibility=90, weights=(30, 30, 15, 24))
    with pytest.raises(ValidationError): LeadScoringSettingsPayload(service_fit_weight=30, commercial_value_weight=30, lead_quality_weight=15, feasibility_weight=24, commercial_value_scale=[{"ratio":"0.5","score":0},{"ratio":"1.5","score":100}])


def test_llm_schema_cannot_supply_commercial_or_overall_and_backend_recomputes():
    base = {"service_fit":{"score":80,"explanation":"fit"},"lead_quality":{"score":60,"explanation":"quality"},"feasibility":{"score":90,"explanation":"feasible"},"summary":"summary","missing_data_observations":[],"security_warning":None,"category_suggestion":None}
    with pytest.raises(ValidationError): LeadScoringAIResult.model_validate({**base, "commercial_value":100})
    with pytest.raises(ValidationError): LeadScoringAIResult.model_validate({**base, "overall_score":100})
    result = build_final_lead_scoring_result(ai=LeadScoringAIResult.model_validate(base), commercial_data={"score":"20.0","status":"CALCULATED","effective_effort":"8","deal_hourly_rate":"30","ratio":"0.625"}, weights=(30,30,15,25), allowed_category_names=set(), language=AIResultLanguage.EN, deadline_missing=False)
    assert result.commercial_value.score == Decimal("20.0")
    assert result.overall_score == Decimal("61.5")


def test_ai_factor_range_and_missing_optional_fields_are_backend_enforced():
    base = {"service_fit":{"score":80,"explanation":"fit"},"lead_quality":{"score":60,"explanation":"quality"},"feasibility":{"score":90,"explanation":"feasible"},"summary":"summary","missing_data_observations":[],"security_warning":None,"category_suggestion":None}
    with pytest.raises(ValidationError):
        LeadScoringAIResult.model_validate({**base, "service_fit":{"score":101,"explanation":"invalid"}})
    result = build_final_lead_scoring_result(
        ai=LeadScoringAIResult.model_validate(base),
        commercial_data={"score":"0.0","status":"NO_BUDGET","effective_effort":"8","deal_hourly_rate":None,"ratio":None},
        weights=(30,30,15,25),
        allowed_category_names=set(),
        language=AIResultLanguage.EN,
        deadline_missing=True,
    )
    assert result.service_fit.score == 80
    assert result.lead_quality.score == 60
    assert result.feasibility.score == 90
    assert result.missing_data == ["BUDGET", "DESIRED_DEADLINE"]


def test_category_suggestion_is_allowlisted_and_security_warning_preserved():
    ai = LeadScoringAIResult.model_validate({"service_fit":{"score":50,"explanation":"fit"},"lead_quality":{"score":50,"explanation":"quality"},"feasibility":{"score":50,"explanation":"feasible"},"summary":"summary","missing_data_observations":[],"security_warning":"Suspicious embedded instruction ignored","category_suggestion":{"category_name":"Invented","reason":"reason"}})
    common = dict(ai=ai, commercial_data={"score":"50","status":"CALCULATED","effective_effort":"8","deal_hourly_rate":"50","ratio":"1"}, weights=(30,30,15,25), language=AIResultLanguage.EN, deadline_missing=False)
    assert build_final_lead_scoring_result(**common, allowed_category_names={"Video"}).category_suggestion is None
    assert build_final_lead_scoring_result(**common, allowed_category_names={"Invented"}).category_suggestion.category_name == "Invented"
