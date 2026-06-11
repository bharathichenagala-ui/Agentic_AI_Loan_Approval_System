"""
FastAPI microservice — Loan Approval API

Endpoints:
  POST  /api/v1/loan/apply               — submit a loan application
  GET   /api/v1/loan/{case_id}           — retrieve result by case ID
  PATCH /api/v1/loan/{case_id}/resolve   — underwriter resolution for manual review cases
  GET   /api/v1/health                   — health check

Run:  uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.schemas import HealthResponse, LoanApplicationRequest, LoanApplicationResponse
from core.models import LoanApplication
from orchestration.loan_graph import process_loan_application

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ── SQLite persistence ─────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent.parent / "loan_cases.db"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_cases (
                case_id     TEXT PRIMARY KEY,
                payload     TEXT NOT NULL,
                resolved_by TEXT,
                resolved_at TEXT,
                resolution  TEXT
            )
        """)
        conn.commit()


def _save_case(case_id: str, result: LoanApplicationResponse) -> None:
    with _get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO loan_cases (case_id, payload) VALUES (?, ?)",
            (case_id, result.model_dump_json()),
        )
        conn.commit()


def _load_case(case_id: str) -> dict | None:
    with _get_db() as conn:
        row = conn.execute(
            "SELECT payload, resolved_by, resolved_at, resolution FROM loan_cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    if not row:
        return None
    data = json.loads(row["payload"])
    if row["resolved_by"]:
        data["resolution"] = {
            "resolved_by": row["resolved_by"],
            "resolved_at": row["resolved_at"],
            "resolution":  row["resolution"],
        }
    return data


# ── App lifecycle ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_db()
    logger.info("SQLite store initialised at %s", DB_PATH)
    yield


app = FastAPI(
    title="Agentic AI Loan Approval System",
    description="Multi-agent intelligent loan approval with LangGraph + Claude Sonnet",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/response models ────────────────────────────────────────────────────

class ResolveRequest(BaseModel):
    resolved_by: str
    resolution: str  # "Approved" | "Rejected" | free-text underwriter note


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )


@app.post(
    "/api/v1/loan/apply",
    response_model=LoanApplicationResponse,
    tags=["Loan"],
    summary="Submit a loan application for AI-driven assessment",
)
async def apply_for_loan(request: LoanApplicationRequest) -> LoanApplicationResponse:
    logger.info("Received loan application for applicant_id=%s", request.applicant_id)

    application = LoanApplication(**request.model_dump())
    result = await process_loan_application(application)

    _save_case(result.case_id, result)

    logger.info(
        "Loan decision complete: case_id=%s classification=%s",
        result.case_id,
        result.decision.classification,
    )
    return result


@app.get(
    "/api/v1/loan/{case_id}",
    tags=["Loan"],
    summary="Retrieve a previously processed loan decision by case ID",
)
async def get_loan_result(case_id: str) -> dict:
    data = _load_case(case_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return data


@app.patch(
    "/api/v1/loan/{case_id}/resolve",
    tags=["Loan"],
    summary="Underwriter resolution for a Requires Manual Review case",
)
async def resolve_manual_review(case_id: str, body: ResolveRequest) -> dict:
    data = _load_case(case_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    classification = data.get("decision", {}).get("classification", "")
    if classification != "Requires Manual Review":
        raise HTTPException(
            status_code=400,
            detail=f"Case '{case_id}' has classification '{classification}' — only 'Requires Manual Review' cases can be resolved here",
        )

    resolved_at = datetime.now(timezone.utc).isoformat()
    with _get_db() as conn:
        conn.execute(
            "UPDATE loan_cases SET resolved_by=?, resolved_at=?, resolution=? WHERE case_id=?",
            (body.resolved_by, resolved_at, body.resolution, case_id),
        )
        conn.commit()

    logger.info(
        "Manual review resolved: case_id=%s resolved_by=%s resolution=%s",
        case_id, body.resolved_by, body.resolution,
    )
    return {
        "case_id": case_id,
        "resolved_by": body.resolved_by,
        "resolved_at": resolved_at,
        "resolution": body.resolution,
        "status": "resolved",
    }
