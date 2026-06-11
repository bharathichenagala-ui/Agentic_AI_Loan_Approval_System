"""
Agent integration tests (requires ANTHROPIC_API_KEY).

Uses small, deterministic inputs to verify agent output schemas.

Run:  pytest tests/test_agents.py -v -s
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio

from core.models import (
    ApplicantProfileResult,
    DecisionClassification,
    EmploymentType,
    FinancialRiskResult,
    LoanApplication,
    LoanDecisionResult,
)


@pytest.fixture
def sample_application():
    return LoanApplication(
        applicant_id="TEST-001",
        age=35,
        income=90_000.0,
        employment_type=EmploymentType.SALARIED,
        credit_score=740,
        loan_amount=200_000.0,
        loan_tenure_months=120,
        existing_liabilities=8_000.0,
        location="Seattle, WA",
    )


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
async def test_applicant_profile_agent(sample_application):
    from agents.applicant_profile_agent import ApplicantProfileAgent
    agent = ApplicantProfileAgent()
    result = await agent.analyze(sample_application)

    assert isinstance(result, ApplicantProfileResult)
    assert 0 <= result.income_stability_score <= 100
    assert result.employment_risk in ("Low", "Medium", "High")
    assert isinstance(result.credit_history_summary, str)
    assert isinstance(result.application_completeness_flags, list)


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
async def test_financial_risk_agent(sample_application):
    from agents.applicant_profile_agent import ApplicantProfileAgent
    from agents.financial_risk_agent import FinancialRiskAgent

    profile_agent = ApplicantProfileAgent()
    profile = await profile_agent.analyze(sample_application)

    risk_agent = FinancialRiskAgent()
    result = await risk_agent.analyze(sample_application, profile)

    assert isinstance(result, FinancialRiskResult)
    assert result.debt_to_income_ratio >= 0
    assert result.credit_score_risk_level in ("Low", "Medium", "High", "Very High")
    assert result.loan_amount_risk in ("Low", "Medium", "High")
    assert isinstance(result.anomaly_detected, bool)
    assert isinstance(result.reasoning, str) and len(result.reasoning) > 10


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
async def test_full_pipeline(sample_application):
    from orchestration.loan_graph import process_loan_application

    response = await process_loan_application(sample_application)

    assert response.case_id.startswith("LOAN-")
    assert response.applicant_id == "TEST-001"
    assert response.decision.classification in list(DecisionClassification)
    assert 0 <= response.decision.risk_score <= 100
    assert 0 <= response.decision.confidence_level <= 100
    assert len(response.decision.key_decision_factors) >= 1
    assert response.compliance.notification_sent is True
    assert response.processing_time_ms > 0
