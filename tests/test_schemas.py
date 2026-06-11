"""
Schema validation tests.

Run:  pytest tests/test_schemas.py -v
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from core.models import (
    DecisionClassification,
    EmploymentType,
    LoanApplication,
    LoanApplicationRequest,
    ApplicantProfileResult,
    FinancialRiskResult,
    LoanDecisionResult,
    ComplianceResult,
)


# ── LoanApplication ────────────────────────────────────────────────────────────

def test_loan_application_valid():
    app = LoanApplication(
        applicant_id="APP-001",
        age=35,
        income=80000.0,
        employment_type=EmploymentType.SALARIED,
        credit_score=720,
        loan_amount=200000.0,
        loan_tenure_months=120,
        existing_liabilities=12000.0,
        location="Austin, TX",
    )
    assert app.applicant_id == "APP-001"
    assert app.employment_type == EmploymentType.SALARIED


def test_loan_application_invalid_age_too_low():
    with pytest.raises(ValidationError):
        LoanApplication(
            applicant_id="APP-002",
            age=17,  # below minimum
            income=50000.0,
            employment_type="salaried",
            credit_score=700,
            loan_amount=100000.0,
            loan_tenure_months=60,
            existing_liabilities=0.0,
            location="Dallas, TX",
        )


def test_loan_application_invalid_credit_score():
    with pytest.raises(ValidationError):
        LoanApplication(
            applicant_id="APP-003",
            age=30,
            income=60000.0,
            employment_type="salaried",
            credit_score=900,  # above maximum 850
            loan_amount=100000.0,
            loan_tenure_months=60,
            existing_liabilities=0.0,
            location="Chicago, IL",
        )


def test_loan_application_invalid_negative_income():
    with pytest.raises(ValidationError):
        LoanApplication(
            applicant_id="APP-004",
            age=30,
            income=-1000.0,
            employment_type="salaried",
            credit_score=700,
            loan_amount=100000.0,
            loan_tenure_months=60,
            existing_liabilities=0.0,
            location="Miami, FL",
        )


# ── ApplicantProfileResult ─────────────────────────────────────────────────────

def test_profile_result_valid():
    profile = ApplicantProfileResult(
        income_stability_score=78.5,
        employment_risk="Low",
        credit_history_summary="Good credit history.",
        application_completeness_flags=[],
    )
    assert profile.income_stability_score == 78.5
    assert profile.application_completeness_flags == []


def test_profile_result_invalid_score_out_of_range():
    with pytest.raises(ValidationError):
        ApplicantProfileResult(
            income_stability_score=150.0,  # > 100
            employment_risk="Low",
            credit_history_summary="Test",
            application_completeness_flags=[],
        )


# ── FinancialRiskResult ────────────────────────────────────────────────────────

def test_financial_risk_result_valid():
    risk = FinancialRiskResult(
        debt_to_income_ratio=0.35,
        credit_score_risk_level="Medium",
        loan_amount_risk="Low",
        anomaly_detected=False,
        anomaly_details=None,
        reasoning="Stable income with moderate DTI.",
    )
    assert risk.anomaly_detected is False


# ── LoanDecisionResult ─────────────────────────────────────────────────────────

def test_loan_decision_result_approved():
    decision = LoanDecisionResult(
        classification=DecisionClassification.APPROVED,
        risk_score=28.0,
        confidence_level=92.0,
        key_decision_factors=["Low DTI", "Good credit score"],
        explanation="Application meets all criteria.",
    )
    assert decision.classification == DecisionClassification.APPROVED


def test_loan_decision_result_rejected():
    decision = LoanDecisionResult(
        classification=DecisionClassification.REJECTED,
        risk_score=78.0,
        confidence_level=85.0,
        key_decision_factors=["Very High credit risk", "DTI exceeds 65%"],
        explanation="Application does not meet minimum credit requirements.",
    )
    assert decision.classification == DecisionClassification.REJECTED


# ── ComplianceResult ───────────────────────────────────────────────────────────

def test_compliance_result_valid():
    compliance = ComplianceResult(
        action_taken="Loan file forwarded to disbursement.",
        notification_sent=True,
        case_id="LOAN-APP001-ABCD1234",
        timestamp=datetime.now(timezone.utc),
        summary="Application approved with low risk.",
    )
    assert compliance.notification_sent is True
