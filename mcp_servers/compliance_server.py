"""
MCP Server: Compliance & Action

Exposes tools for case management, notifications, and audit logging.
Run standalone:  python -m mcp_servers.compliance_server
"""

import json
import sys
import os
import uuid
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP

mcp = FastMCP("Compliance Server")
logger = logging.getLogger(__name__)


@mcp.tool()
def generate_case_id(applicant_id: str) -> str:
    """Generate a unique, traceable case ID for the loan application."""
    short_uuid = str(uuid.uuid4()).replace("-", "")[:8].upper()
    case_id = f"LOAN-{applicant_id[:6].upper()}-{short_uuid}"
    return json.dumps({"case_id": case_id})


@mcp.tool()
def determine_action(classification: str, risk_score: float) -> str:
    """Determine the compliance action to take based on the loan decision."""
    actions = {
        "Approved": "Loan file forwarded to disbursement team. Offer letter queued.",
        "Rejected": "Application rejected. Adverse action notice prepared per ECOA.",
        "Requires Manual Review": "Case escalated to credit underwriting desk for manual review.",
    }
    action = actions.get(classification, "Case flagged for supervisor review.")
    action = f"{action} [Risk score: {risk_score:.1f}/100]"
    return json.dumps({"action_taken": action})


@mcp.tool()
def send_notification(applicant_id: str, classification: str, case_id: str) -> str:
    """Simulate sending notification to applicant and internal teams. Returns notification status."""
    # In production this would call an email/SMS service
    logger.info("Notification sent for case %s — decision: %s", case_id, classification)
    messages = {
        "Approved": f"Congratulations! Your loan application {case_id} has been approved.",
        "Rejected": f"We regret to inform you that loan application {case_id} could not be approved at this time.",
        "Requires Manual Review": f"Your loan application {case_id} is under review. Our team will contact you within 2 business days.",
    }
    message = messages.get(classification, f"Update available for case {case_id}.")
    return json.dumps({
        "notification_sent": True,
        "notification_message": message,
        "channels": ["email", "in-app"],
    })


@mcp.tool()
def get_current_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    ts = datetime.now(timezone.utc).isoformat()
    return json.dumps({"timestamp": ts})


if __name__ == "__main__":
    mcp.run()
