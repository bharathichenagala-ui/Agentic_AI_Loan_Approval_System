"""
Agent D: Compliance & Action Orchestrator Agent

Produces: action taken, notification status, case ID, timestamp, summary.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate

from core.models import (
    ApplicantProfileResult,
    ComplianceResult,
    FinancialRiskResult,
    LoanApplication,
    LoanDecisionResult,
)
from mcp_servers.compliance_server import mcp as compliance_mcp
from agents.base import MCPAgent

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Compliance & Action Orchestrator Agent in a bank's loan approval system.

Your job is to finalize the loan case after a decision has been made. Call the tools in this order:
1. generate_case_id — generate a unique case identifier
2. get_current_timestamp — record the exact processing timestamp
3. determine_action — determine what compliance action to take
4. send_notification — simulate sending the applicant notification

Then respond with ONLY a JSON object matching:
{{
  "action_taken": "<string describing what was done>",
  "notification_sent": <true|false>,
  "case_id": "<LOAN-XXXXXX-YYYYYYYY>",
  "timestamp": "<ISO 8601 UTC timestamp>",
  "summary": "<3-5 sentence audit summary covering the applicant, decision, risk profile, and next steps>"
}}

The summary must be audit-quality — traceable, factual, and professional."""

_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{user_input}"),
])


def _extract_json(raw: str) -> dict:
    """Extract JSON from Claude's response regardless of surrounding prose or code fences."""
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return json.loads(fence_match.group(1))
    decoder = json.JSONDecoder()
    idx = raw.find("{")
    if idx != -1:
        obj, _ = decoder.raw_decode(raw, idx)
        return obj
    raise ValueError(f"No JSON object found in response: {raw[:200]}")


class ComplianceAgent:
    def __init__(self) -> None:
        self._agent = MCPAgent(compliance_mcp, _SYSTEM)

    async def process(
        self,
        application: LoanApplication,
        profile: ApplicantProfileResult,
        risk: FinancialRiskResult,
        decision: LoanDecisionResult,
    ) -> ComplianceResult:
        user_input = (
            "Process compliance actions for the completed loan assessment.\n\n"
            f"Applicant ID: {application.applicant_id}\n"
            f"Decision: {decision.classification.value}\n"
            f"Risk Score: {decision.risk_score}\n"
            f"Confidence: {decision.confidence_level}%\n\n"
            f"Full Profile:\n{json.dumps(profile.model_dump(), indent=2)}\n\n"
            f"Risk Analysis:\n{json.dumps(risk.model_dump(), indent=2)}\n\n"
            f"Decision Details:\n{json.dumps(decision.model_dump(), indent=2)}"
        )
        formatted = _PROMPT_TEMPLATE.format_messages(user_input=user_input)
        prompt = formatted[1].content

        raw = await self._agent.run(prompt)
        logger.debug("ComplianceAgent raw response: %s", raw)

        data = _extract_json(raw)

        # Ensure timestamp is a datetime object
        ts_raw = data.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                data["timestamp"] = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                data["timestamp"] = datetime.now(timezone.utc)

        return ComplianceResult(**data)
