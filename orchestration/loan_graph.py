"""
LangGraph orchestration pipeline.

Graph topology (fan-out / fan-in for parallelism):
  START → profile_node ──┐
  START → risk_node    ──┤ (run concurrently — both need only LoanApplication)
                         ↓ fan-in: decision_node waits for both
                    decision_node → compliance_node → END

Why profile_node ∥ risk_node is safe:
  All tools in risk_server.py take only LoanApplication fields.
  profile_result.income_stability_score is first needed by
  decision_server.compute_composite_risk_score, which runs after the fan-in.
"""

from __future__ import annotations

import logging
import time
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from core.models import (
    ApplicantProfileResult,
    ComplianceResult,
    FinancialRiskResult,
    LoanApplication,
    LoanApplicationResponse,
    LoanDecisionResult,
)
from agents.applicant_profile_agent import ApplicantProfileAgent
from agents.compliance_agent import ComplianceAgent
from agents.financial_risk_agent import FinancialRiskAgent
from agents.loan_decision_agent import LoanDecisionAgent

logger = logging.getLogger(__name__)


# ── State schema ───────────────────────────────────────────────────────────────

class LoanState(TypedDict):
    application: LoanApplication
    profile_result: Optional[ApplicantProfileResult]
    risk_result: Optional[FinancialRiskResult]
    decision_result: Optional[LoanDecisionResult]
    compliance_result: Optional[ComplianceResult]
    error: Annotated[Optional[str], lambda a, b: a or b]


# ── Node functions (return only changed keys for clean parallel merging) ────────

async def profile_node(state: LoanState) -> dict:
    logger.info("[Graph] Running Applicant Profile Agent")
    try:
        agent = ApplicantProfileAgent()
        result = await agent.analyze(state["application"])
        return {"profile_result": result}
    except Exception as exc:
        logger.error("[Graph] profile_node failed: %s", exc, exc_info=True)
        return {"error": f"profile_node failed: {exc}"}


async def risk_node(state: LoanState) -> dict:
    # Runs in parallel with profile_node — profile_result is not yet available
    logger.info("[Graph] Running Financial Risk Agent (parallel with Profile Agent)")
    try:
        agent = FinancialRiskAgent()
        result = await agent.analyze(state["application"])  # profile=None intentionally
        return {"risk_result": result}
    except Exception as exc:
        logger.error("[Graph] risk_node failed: %s", exc, exc_info=True)
        return {"error": f"risk_node failed: {exc}"}


async def decision_node(state: LoanState) -> dict:
    logger.info("[Graph] Running Loan Decision Agent")
    if state.get("error"):
        logger.warning("[Graph] Skipping decision_node — upstream error: %s", state["error"])
        return {}
    try:
        agent = LoanDecisionAgent()
        result = await agent.decide(
            state["application"],
            state["profile_result"],
            state["risk_result"],
        )
        return {"decision_result": result}
    except Exception as exc:
        logger.error("[Graph] decision_node failed: %s", exc, exc_info=True)
        return {"error": f"decision_node failed: {exc}"}


async def compliance_node(state: LoanState) -> dict:
    logger.info("[Graph] Running Compliance & Action Orchestrator Agent")
    if state.get("error"):
        logger.warning("[Graph] Skipping compliance_node — upstream error: %s", state["error"])
        return {}
    try:
        agent = ComplianceAgent()
        result = await agent.process(
            state["application"],
            state["profile_result"],
            state["risk_result"],
            state["decision_result"],
        )
        return {"compliance_result": result}
    except Exception as exc:
        logger.error("[Graph] compliance_node failed: %s", exc, exc_info=True)
        return {"error": f"compliance_node failed: {exc}"}


# ── Graph definition ───────────────────────────────────────────────────────────

def build_loan_graph():
    graph = StateGraph(LoanState)

    graph.add_node("profile_node", profile_node)
    graph.add_node("risk_node", risk_node)
    graph.add_node("decision_node", decision_node)
    graph.add_node("compliance_node", compliance_node)

    # Fan-out: both profile_node and risk_node start from START (run concurrently)
    graph.add_edge(START, "profile_node")
    graph.add_edge(START, "risk_node")

    # Fan-in: decision_node waits for both profile_node and risk_node to complete
    graph.add_edge(["profile_node", "risk_node"], "decision_node")

    graph.add_edge("decision_node", "compliance_node")
    graph.add_edge("compliance_node", END)

    return graph.compile()


# Compiled once at import time — not rebuilt per request
_LOAN_GRAPH = build_loan_graph()


# ── Public entry point ─────────────────────────────────────────────────────────

async def process_loan_application(application: LoanApplication) -> LoanApplicationResponse:
    """Run the full 4-agent pipeline and return a structured response."""
    start_ms = time.monotonic()

    graph = _LOAN_GRAPH
    initial_state: LoanState = {
        "application": application,
        "profile_result": None,
        "risk_result": None,
        "decision_result": None,
        "compliance_result": None,
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)

    elapsed_ms = (time.monotonic() - start_ms) * 1000

    if final_state.get("error"):
        raise RuntimeError(f"Pipeline failed: {final_state['error']}")

    return LoanApplicationResponse(
        case_id=final_state["compliance_result"].case_id,
        applicant_id=application.applicant_id,
        profile=final_state["profile_result"],
        risk_analysis=final_state["risk_result"],
        decision=final_state["decision_result"],
        compliance=final_state["compliance_result"],
        processing_time_ms=round(elapsed_ms, 1),
    )
