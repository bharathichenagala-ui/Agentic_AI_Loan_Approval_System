"""
Rule engine unit tests.

Run:  pytest tests/test_rules.py -v
"""

import pytest
from core import rules


def test_income_stability_salaried_high_income():
    # income_pts=30 + emp_pts=40 + age_pts=20 = 90
    score = rules.compute_income_stability_score(150_000, "salaried", 40)
    assert score == 90.0


def test_income_stability_unemployed():
    # income_pts=0 + emp_pts=0 + age_pts=20 (age 30 in sweet spot) = 20
    score = rules.compute_income_stability_score(0, "unemployed", 30)
    assert score == 20.0


def test_income_stability_self_employed_young():
    score = rules.compute_income_stability_score(50_000, "self_employed", 22)
    assert 0 < score < 100


def test_employment_risk_levels():
    assert rules.compute_employment_risk("salaried") == "Low"
    assert rules.compute_employment_risk("self_employed") == "Medium"
    assert rules.compute_employment_risk("unemployed") == "High"


def test_dti_basic():
    # monthly income = 5000, monthly existing = 416.67, monthly new = 1000 => DTI = 1416.67/5000 = 0.2833
    dti = rules.compute_dti(60_000, 5_000, 60_000, 60)
    assert abs(dti - 0.2917) < 0.01


def test_dti_zero_income():
    dti = rules.compute_dti(0, 1000, 50_000, 60)
    assert dti == 999.0


def test_credit_score_risk_levels():
    assert rules.compute_credit_score_risk(800) == "Low"
    assert rules.compute_credit_score_risk(700) == "Medium"
    assert rules.compute_credit_score_risk(600) == "High"
    assert rules.compute_credit_score_risk(450) == "Very High"


def test_loan_amount_risk():
    assert rules.compute_loan_amount_risk(100_000, 200_000) == "Low"    # 2x
    assert rules.compute_loan_amount_risk(100_000, 500_000) == "Medium"  # 5x
    assert rules.compute_loan_amount_risk(100_000, 900_000) == "High"    # 9x


def test_anomaly_high_liabilities():
    detected, details = rules.detect_anomalies(50_000, 35, 700, 100_000, 40_000)
    assert detected is True
    assert "liabilities" in details.lower()


def test_anomaly_no_flags():
    detected, details = rules.detect_anomalies(80_000, 35, 720, 200_000, 10_000)
    assert detected is False
    assert details is None


def test_classify_loan_approved():
    result = rules.classify_loan(30.0, False, 0.35, "Medium")
    assert result == "Approved"


def test_classify_loan_rejected_high_risk():
    result = rules.classify_loan(70.0, False, 0.50, "High")
    assert result == "Rejected"


def test_classify_loan_rejected_very_high_credit():
    result = rules.classify_loan(50.0, False, 0.40, "Very High")
    assert result == "Rejected"


def test_classify_loan_manual_review_anomaly():
    result = rules.classify_loan(40.0, True, 0.40, "Medium")
    assert result == "Requires Manual Review"


def test_risk_score_range():
    score = rules.compute_risk_score(75.0, 0.35, 720, False)
    assert 0 <= score <= 100


def test_confidence_high_for_clear_case():
    confidence = rules.compute_confidence(20.0, False, [])
    assert confidence >= 80


def test_confidence_lower_for_anomaly():
    confidence_clean = rules.compute_confidence(20.0, False, [])
    confidence_anomaly = rules.compute_confidence(20.0, True, [])
    assert confidence_anomaly < confidence_clean
