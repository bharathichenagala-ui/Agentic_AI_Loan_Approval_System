"""
MCP Server: Applicant Profile Analysis

Exposes deterministic tools for profiling the loan applicant.
Run standalone:  python -m mcp_servers.profile_server
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from core import rules

mcp = FastMCP("Applicant Profile Server")


@mcp.tool()
def analyze_income_stability(income: float, employment_type: str, age: int) -> str:
    """Compute income stability score (0-100) from income, employment type, and age."""
    score = rules.compute_income_stability_score(income, employment_type, age)
    return json.dumps({"income_stability_score": score})


@mcp.tool()
def assess_employment_risk(employment_type: str) -> str:
    """Classify employment risk as Low, Medium, or High."""
    risk = rules.compute_employment_risk(employment_type)
    return json.dumps({"employment_risk": risk})


@mcp.tool()
def summarize_credit_history(credit_score: int) -> str:
    """Generate a plain-language credit history summary from a credit score."""
    summary = rules.summarize_credit_history(credit_score)
    return json.dumps({"credit_history_summary": summary})


@mcp.tool()
def check_application_completeness(application_json: str) -> str:
    """Check the loan application for missing or flagged fields. Input must be a JSON string."""
    try:
        application = json.loads(application_json)
    except Exception:
        return json.dumps({"flags": ["Invalid application JSON"]})
    flags = rules.check_completeness(application)
    return json.dumps({"application_completeness_flags": flags})


if __name__ == "__main__":
    mcp.run()
