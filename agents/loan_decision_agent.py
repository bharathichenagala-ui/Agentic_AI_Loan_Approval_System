"""
Agent C: Loan Decision Agent

Produces: classification, risk score, confidence level,
          key decision factors, and explanation.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from core.models import (
    ApplicantProfileResult,
    DecisionClassification,
    FinancialRiskResult,
    LoanApplication,
    LoanDecisionResult,
)
from mcp_servers.decision_server import mcp as decision_mcp
from agents.base import MCPAgent

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Loan Decision Agent in a bank's automated loan approval system.

You receive the outputs of profile and risk analysis. Your job is to make a final loan decision
by calling the available tools in order:
1. compute_composite_risk_score — always call first
2. classify_application
3. compute_decision_confidence

After calling all tools, respond with ONLY a JSON object matching:
{{
  "classification": "<Approved|Rejected|Requires Manual Review>",
  "risk_score": <float 0-100>,
  "confidence_level": <float 0-100>,
  "key_decision_factors": [<list of 3-5 short factor strings>],
  "explanation": "<2-4 sentence plain-English explanation of the decision>"
}}

Rules:
- key_decision_factors must be concrete (e.g. "DTI ratio of 0.52 exceeds 0.43 threshold")
- explanation must be clear enough for the applicant to understand
- Do not include any text outside the JSON block"""

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


class LoanDecisionAgent:
    def __init__(self) -> None:
        self._agent = MCPAgent(decision_mcp, _SYSTEM)

    async def decide(
        self,
        application: LoanApplication,
        profile: ApplicantProfileResult,
        risk: FinancialRiskResult,
    ) -> LoanDecisionResult:
        user_input = (
            "Make a loan decision based on the following analysis results.\n\n"
            f"Application:\n{json.dumps(application.model_dump(mode='json'), indent=2, default=str)}\n\n"
            f"Profile Result:\n{json.dumps(profile.model_dump(), indent=2)}\n\n"
            f"Risk Analysis:\n{json.dumps(risk.model_dump(), indent=2)}"
        )
        formatted = _PROMPT_TEMPLATE.format_messages(user_input=user_input)
        prompt = formatted[1].content

        raw = await self._agent.run(prompt)
        logger.debug("LoanDecisionAgent raw response: %s", raw)

        data = _extract_json(raw)
        data["classification"] = DecisionClassification(data["classification"])
        return LoanDecisionResult(**data)
