"""
MCP Server: Financial Risk Analysis

Exposes deterministic tools for calculating financial risk metrics.
Run standalone:  python -m mcp_servers.risk_server
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from core import rules

mcp = FastMCP("Financial Risk Server")


@mcp.tool()
def calculate_debt_to_income(
    income: float,
    existing_liabilities: float,
    loan_amount: float,
    loan_tenure_months: int,
) -> str:
    """Compute the Debt-to-Income (DTI) ratio. Values above 0.43 indicate elevated risk."""
    dti = rules.compute_dti(income, existing_liabilities, loan_amount, loan_tenure_months)
    return json.dumps({"debt_to_income_ratio": dti})


@mcp.tool()
def assess_credit_score_risk(credit_score: int) -> str:
    """Classify credit score risk as Low, Medium, High, or Very High."""
    level = rules.compute_credit_score_risk(credit_score)
    return json.dumps({"credit_score_risk_level": level})


@mcp.tool()
def assess_loan_amount_risk(income: float, loan_amount: float) -> str:
    """Classify loan-to-income risk as Low, Medium, or High."""
    risk = rules.compute_loan_amount_risk(income, loan_amount)
    return json.dumps({"loan_amount_risk": risk})


@mcp.tool()
def run_anomaly_detection(
    income: float,
    age: int,
    credit_score: int,
    loan_amount: float,
    existing_liabilities: float,
) -> str:
    """Detect statistical anomalies in the application that may indicate data errors or fraud."""
    detected, details = rules.detect_anomalies(income, age, credit_score, loan_amount, existing_liabilities)
    return json.dumps({
        "anomaly_detected": detected,
        "anomaly_details": details,
    })


if __name__ == "__main__":
    mcp.run()
