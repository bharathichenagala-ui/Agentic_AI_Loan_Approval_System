"""
FastAPI request/response schemas.

These re-export the canonical Pydantic models from core.models and add
any API-specific envelope types.
"""

from core.models import (
    DecisionClassification,
    EmploymentType,
    LoanApplicationRequest,
    LoanApplicationResponse,
    HealthResponse,
)

__all__ = [
    "EmploymentType",
    "DecisionClassification",
    "LoanApplicationRequest",
    "LoanApplicationResponse",
    "HealthResponse",
]
