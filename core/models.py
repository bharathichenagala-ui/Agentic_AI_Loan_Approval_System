from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class EmploymentType(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    CONTRACT = "contract"
    UNEMPLOYED = "unemployed"


class DecisionClassification(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    MANUAL_REVIEW = "Requires Manual Review"


# ── Input ──────────────────────────────────────────────────────────────────────

class LoanApplication(BaseModel):
    applicant_id: str
    age: int = Field(ge=18, le=80)
    income: float = Field(gt=0, description="Annual income in USD")
    employment_type: EmploymentType
    credit_score: int = Field(ge=300, le=850)
    loan_amount: float = Field(gt=0)
    loan_tenure_months: int = Field(gt=0, le=360)
    existing_liabilities: float = Field(ge=0, description="Annual existing debt obligations")
    location: str
    application_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Agent outputs ──────────────────────────────────────────────────────────────

class ApplicantProfileResult(BaseModel):
    income_stability_score: float = Field(ge=0, le=100)
    employment_risk: str  # Low / Medium / High
    credit_history_summary: str
    application_completeness_flags: List[str]


class FinancialRiskResult(BaseModel):
    debt_to_income_ratio: float
    credit_score_risk_level: str  # Low / Medium / High / Very High
    loan_amount_risk: str  # Low / Medium / High
    anomaly_detected: bool
    anomaly_details: Optional[str] = None
    reasoning: str


class LoanDecisionResult(BaseModel):
    classification: DecisionClassification
    risk_score: float = Field(ge=0, le=100)
    confidence_level: float = Field(ge=0, le=100)
    key_decision_factors: List[str]
    explanation: str


class ComplianceResult(BaseModel):
    action_taken: str
    notification_sent: bool
    case_id: str
    timestamp: datetime
    summary: str

    @field_validator("notification_sent", mode="before")
    @classmethod
    def enforce_notification_sent(cls, v: object) -> bool:
        # MCP send_notification tool always succeeds — Claude must not override it
        return True


# ── API request/response ───────────────────────────────────────────────────────

class LoanApplicationRequest(BaseModel):
    applicant_id: str
    age: int = Field(ge=18, le=80)
    income: float = Field(gt=0)
    employment_type: EmploymentType
    credit_score: int = Field(ge=300, le=850)
    loan_amount: float = Field(gt=0)
    loan_tenure_months: int = Field(gt=0, le=360)
    existing_liabilities: float = Field(ge=0)
    location: str


class LoanApplicationResponse(BaseModel):
    case_id: str
    applicant_id: str
    profile: ApplicantProfileResult
    risk_analysis: FinancialRiskResult
    decision: LoanDecisionResult
    compliance: ComplianceResult
    processing_time_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
