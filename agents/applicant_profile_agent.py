"""
Agent A: Applicant Profile Agent

Produces: income stability score, employment risk, credit history summary,
          application completeness flags.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from core.models import ApplicantProfileResult, LoanApplication
from mcp_servers.profile_server import mcp as profile_mcp
from agents.base import MCPAgent

logger = logging.getLogger(__name__)

_SYSTEM = """You are the Applicant Profile Agent in a bank's loan approval system.

Your job is to assess the applicant's profile by calling the available tools in this order:
1. check_application_completeness — always call this first
2. analyze_income_stability
3. assess_employment_risk
4. summarize_credit_history

After calling all tools, respond with a JSON object (and nothing else) matching this schema:
{{
  "income_stability_score": <float 0-100>,
  "employment_risk": "<Low|Medium|High>",
  "credit_history_summary": "<string>",
  "application_completeness_flags": [<list of strings, empty if complete>]
}}

Do not include any explanation outside the JSON block."""

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


class ApplicantProfileAgent:
    def __init__(self) -> None:
        self._agent = MCPAgent(profile_mcp, _SYSTEM)

    async def analyze(self, application: LoanApplication) -> ApplicantProfileResult:
        app_dict = application.model_dump(mode="json")
        app_dict["application_timestamp"] = str(app_dict.get("application_timestamp", ""))

        user_input = (
            "Analyze the following loan application and return the profile assessment.\n\n"
            f"Application data:\n{json.dumps(app_dict, indent=2)}"
        )
        formatted = _PROMPT_TEMPLATE.format_messages(user_input=user_input)
        prompt = formatted[1].content

        raw = await self._agent.run(prompt)
        logger.debug("ApplicantProfileAgent raw response: %s", raw)

        data = _extract_json(raw)
        return ApplicantProfileResult(**data)
