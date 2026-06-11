"""
Agent B: Financial Risk Analysis Agent

Produces: DTI ratio, credit score risk, loan amount risk,
          anomaly detection, and natural-language reasoning.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from core.models import (
    ApplicantProfileResult,
    FinancialRiskResult,
    LoanApplication,
)
from mcp_servers.risk_server import mcp as risk_mcp
from agents.base import MCPAgent

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Financial Risk Analysis Agent in a bank's loan approval system.

Your job is to assess financial risk by calling the available tools:
1. calculate_debt_to_income — always call first
2. assess_credit_score_risk
3. assess_loan_amount_risk
4. run_anomaly_detection

After calling all tools, respond with a JSON object (and nothing else) matching:
{{
  "debt_to_income_ratio": <float>,
  "credit_score_risk_level": "<Low|Medium|High|Very High>",
  "loan_amount_risk": "<Low|Medium|High>",
  "anomaly_detected": <true|false>,
  "anomaly_details": "<string or null>",
  "reasoning": "<2-3 sentence explanation of the key financial risk factors>"
}}

Return ONLY the JSON object — no extra text before or after."""

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


class FinancialRiskAgent:
    def __init__(self) -> None:
        self._agent = MCPAgent(risk_mcp, _SYSTEM)

    async def analyze(
        self,
        application: LoanApplication,
        profile: ApplicantProfileResult | None = None,
    ) -> FinancialRiskResult:
        profile_section = (
            f"\nProfile Assessment (for reasoning context):\n{json.dumps(profile.model_dump(), indent=2)}"
            if profile else ""
        )
        user_input = (
            "Perform financial risk analysis for the following applicant.\n\n"
            f"Loan Application:\n{json.dumps(application.model_dump(mode='json'), indent=2, default=str)}"
            f"{profile_section}"
        )
        formatted = _PROMPT_TEMPLATE.format_messages(user_input=user_input)
        prompt = formatted[1].content

        raw = await self._agent.run(prompt)
        logger.debug("FinancialRiskAgent raw response: %s", raw)

        data = _extract_json(raw)
        return FinancialRiskResult(**data)
