"""
MCP Server: Loan Decision

Exposes deterministic tools for computing the final loan decision.
Run standalone:  python -m mcp_servers.decision_server
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from core import rules

mcp = FastMCP("Loan Decision Server")


@mcp.tool()
def compute_composite_risk_score(
    income_stability_score: float,
    debt_to_income_ratio: float,
    credit_score: int,
    anomaly_detected: bool,
) -> str:
    """Compute a composite risk score (0-100) from prior analysis outputs."""
    score = rules.compute_risk_score(
        income_stability_score,
        debt_to_income_ratio,
        credit_score,
        anomaly_detected,
    )
    return json.dumps({"risk_score": score})


@mcp.tool()
def classify_application(
    risk_score: float,
    anomaly_detected: bool,
    debt_to_income_ratio: float,
    credit_score_risk_level: str,
) -> str:
    """Classify loan as Approved, Rejected, or Requires Manual Review."""
    classification = rules.classify_loan(
        risk_score, anomaly_detected, debt_to_income_ratio, credit_score_risk_level
    )
    return json.dumps({"classification": classification})


@mcp.tool()
def compute_decision_confidence(
    risk_score: float,
    anomaly_detected: bool,
    completeness_flags_json: str,
) -> str:
    """Compute confidence level (0-100) for the loan decision."""
    try:
        flags = json.loads(completeness_flags_json)
    except Exception:
        flags = []
    confidence = rules.compute_confidence(risk_score, anomaly_detected, flags)
    return json.dumps({"confidence_level": confidence})


if __name__ == "__main__":
    mcp.run()
