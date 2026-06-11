"""
MCP server tool unit tests.

Calls the tool functions directly as Python functions — no MCP protocol
overhead, no API key required. Verifies JSON schema of every tool return value.

Run:  pytest tests/test_mcp_servers.py -v
"""

import json
import pytest

# Import tool functions directly from server modules
from mcp_servers.profile_server import (
    analyze_income_stability,
    assess_employment_risk,
    check_application_completeness,
    summarize_credit_history,
)
from mcp_servers.risk_server import (
    assess_credit_score_risk,
    assess_loan_amount_risk,
    calculate_debt_to_income,
    run_anomaly_detection,
)
from mcp_servers.decision_server import (
    classify_application,
    compute_composite_risk_score,
    compute_decision_confidence,
)
from mcp_servers.compliance_server import (
    determine_action,
    generate_case_id,
    get_current_timestamp,
    send_notification,
)


# ── Profile server ─────────────────────────────────────────────────────────────

def test_analyze_income_stability_returns_score():
    result = json.loads(analyze_income_stability(90_000, "salaried", 35))
    assert "income_stability_score" in result
    assert 0 <= result["income_stability_score"] <= 100


def test_assess_employment_risk_salaried():
    result = json.loads(assess_employment_risk("salaried"))
    assert result["employment_risk"] == "Low"


def test_check_completeness_flags_missing_fields():
    incomplete = json.dumps({"applicant_id": "APP-001", "income": 50000})
    result = json.loads(check_application_completeness(incomplete))
    assert "application_completeness_flags" in result
    assert len(result["application_completeness_flags"]) > 0


def test_check_completeness_clean_application():
    complete = json.dumps({
        "applicant_id": "APP-002", "age": 35, "income": 80000,
        "employment_type": "salaried", "credit_score": 720,
        "loan_amount": 200000, "loan_tenure_months": 120,
        "existing_liabilities": 10000, "location": "NYC",
    })
    result = json.loads(check_application_completeness(complete))
    assert result["application_completeness_flags"] == []


def test_summarize_credit_history_excellent():
    result = json.loads(summarize_credit_history(800))
    assert "credit_history_summary" in result
    assert "800" in result["credit_history_summary"]


# ── Risk server ────────────────────────────────────────────────────────────────

def test_calculate_dti_returns_float():
    result = json.loads(calculate_debt_to_income(60_000, 5_000, 60_000, 60))
    assert "debt_to_income_ratio" in result
    assert result["debt_to_income_ratio"] >= 0


def test_assess_credit_score_risk_valid_levels():
    for score, expected in [(800, "Low"), (700, "Medium"), (600, "High"), (450, "Very High")]:
        result = json.loads(assess_credit_score_risk(score))
        assert result["credit_score_risk_level"] == expected


def test_run_anomaly_detection_clean_case():
    result = json.loads(run_anomaly_detection(80_000, 35, 720, 200_000, 10_000))
    assert result["anomaly_detected"] is False
    assert result["anomaly_details"] is None


def test_run_anomaly_detection_high_liabilities():
    result = json.loads(run_anomaly_detection(50_000, 35, 700, 100_000, 40_000))
    assert result["anomaly_detected"] is True
    assert result["anomaly_details"] is not None


# ── Decision server ────────────────────────────────────────────────────────────

def test_compute_risk_score_range():
    result = json.loads(compute_composite_risk_score(75.0, 0.35, 720, False))
    assert "risk_score" in result
    assert 0 <= result["risk_score"] <= 100


def test_classify_application_approved():
    result = json.loads(classify_application(25.0, False, 0.30, "Low"))
    assert result["classification"] == "Approved"


def test_classify_application_anomaly_triggers_review():
    result = json.loads(classify_application(40.0, True, 0.35, "Medium"))
    assert result["classification"] == "Requires Manual Review"


# ── Compliance server ──────────────────────────────────────────────────────────

def test_generate_case_id_format():
    result = json.loads(generate_case_id("APP-001"))
    case_id = result["case_id"]
    assert case_id.startswith("LOAN-")
    # Last segment is always the 8-char UUID suffix
    assert len(case_id.split("-")[-1]) == 8


def test_determine_action_includes_risk_score():
    result = json.loads(determine_action("Approved", 28.5))
    assert "action_taken" in result
    # Verify the risk_score fix — score should appear in the action string
    assert "28.5" in result["action_taken"]


def test_determine_action_all_classifications():
    for classification in ["Approved", "Rejected", "Requires Manual Review"]:
        result = json.loads(determine_action(classification, 50.0))
        assert len(result["action_taken"]) > 0


def test_get_current_timestamp_iso_format():
    result = json.loads(get_current_timestamp())
    ts = result["timestamp"]
    assert "T" in ts  # ISO 8601 format
    assert "+" in ts or "Z" in ts or ts.endswith("+00:00")  # Has timezone


def test_send_notification_returns_sent_true():
    result = json.loads(send_notification("APP-001", "Approved", "LOAN-APP001-ABCD1234"))
    assert result["notification_sent"] is True
    assert len(result["notification_message"]) > 0
    assert "email" in result["channels"]
