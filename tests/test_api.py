"""
FastAPI endpoint tests.

Run:  pytest tests/test_api.py -v
"""

import os
import pytest
from fastapi.testclient import TestClient

# TestClient handles async endpoints synchronously
from api.main import app

client = TestClient(app)


def test_health_check():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_loan_apply_approved_profile():
    payload = {
        "applicant_id": "API-TEST-001",
        "age": 38,
        "income": 120_000,
        "employment_type": "salaried",
        "credit_score": 780,
        "loan_amount": 150_000,
        "loan_tenure_months": 120,
        "existing_liabilities": 5_000,
        "location": "San Francisco, CA",
    }
    resp = client.post("/api/v1/loan/apply", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"].startswith("LOAN-")
    assert data["decision"]["classification"] in [
        "Approved", "Rejected", "Requires Manual Review"
    ]
    assert "profile" in data
    assert "risk_analysis" in data
    assert "compliance" in data


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_loan_apply_then_retrieve():
    payload = {
        "applicant_id": "API-TEST-002",
        "age": 45,
        "income": 55_000,
        "employment_type": "contract",
        "credit_score": 620,
        "loan_amount": 300_000,
        "loan_tenure_months": 240,
        "existing_liabilities": 20_000,
        "location": "Houston, TX",
    }
    post_resp = client.post("/api/v1/loan/apply", json=payload)
    assert post_resp.status_code == 200
    case_id = post_resp.json()["case_id"]

    get_resp = client.get(f"/api/v1/loan/{case_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["case_id"] == case_id


def test_loan_retrieve_not_found():
    resp = client.get("/api/v1/loan/LOAN-NOTREAL-00000000")
    assert resp.status_code == 404


def test_loan_apply_invalid_payload():
    payload = {
        "applicant_id": "BAD-001",
        "age": 15,          # below 18
        "income": -1000,    # negative
        "employment_type": "salaried",
        "credit_score": 700,
        "loan_amount": 100_000,
        "loan_tenure_months": 60,
        "existing_liabilities": 0,
        "location": "NYC",
    }
    resp = client.post("/api/v1/loan/apply", json=payload)
    assert resp.status_code == 422  # Validation error
