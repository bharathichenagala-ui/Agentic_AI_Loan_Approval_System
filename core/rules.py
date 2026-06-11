"""
Deterministic rule engine for credit and risk scoring.

All business-critical arithmetic lives here — Claude is used only for
natural-language reasoning on top of these computed values.
"""

from __future__ import annotations

from typing import Optional, Tuple


# ── Income & Employment ────────────────────────────────────────────────────────

def compute_income_stability_score(
    income: float,
    employment_type: str,
    age: int,
) -> float:
    """Returns 0-100 score; higher = more stable."""
    # Income component: up to 40 points (saturates at $200k)
    income_pts = min(income / 200_000 * 40, 40)

    emp_pts = {
        "salaried": 40,
        "self_employed": 25,
        "contract": 20,
        "unemployed": 0,
    }.get(employment_type, 10)

    # Age sweet spot 25-55
    if 25 <= age <= 55:
        age_pts = 20
    elif (18 <= age < 25) or (55 < age <= 65):
        age_pts = 12
    else:
        age_pts = 5

    return round(min(income_pts + emp_pts + age_pts, 100), 2)


def compute_employment_risk(employment_type: str) -> str:
    return {
        "salaried": "Low",
        "self_employed": "Medium",
        "contract": "Medium",
        "unemployed": "High",
    }.get(employment_type, "High")


def summarize_credit_history(credit_score: int) -> str:
    if credit_score >= 750:
        return f"Excellent credit history (score {credit_score}). Consistent repayment record likely."
    elif credit_score >= 700:
        return f"Good credit history (score {credit_score}). Minor blemishes possible."
    elif credit_score >= 650:
        return f"Fair credit history (score {credit_score}). Some delinquencies may exist."
    elif credit_score >= 550:
        return f"Poor credit history (score {credit_score}). Likely late payments or defaults."
    else:
        return f"Very poor credit history (score {credit_score}). High probability of prior defaults."


def check_completeness(application: dict) -> list[str]:
    flags = []
    required = [
        "applicant_id", "age", "income", "employment_type",
        "credit_score", "loan_amount", "loan_tenure_months",
        "existing_liabilities", "location",
    ]
    for field in required:
        if not application.get(field) and application.get(field) != 0:
            flags.append(f"Missing field: {field}")

    if application.get("age") and application["age"] < 21:
        flags.append("Applicant under 21 — may require co-signer per policy")
    if application.get("income") and application["income"] < 15_000:
        flags.append("Income below minimum threshold of $15,000")

    return flags


# ── Financial Risk ─────────────────────────────────────────────────────────────

def compute_dti(
    income: float,
    existing_liabilities: float,
    loan_amount: float,
    loan_tenure_months: int,
) -> float:
    """Debt-to-Income ratio: total monthly debt / monthly income."""
    monthly_income = income / 12
    if monthly_income <= 0:
        return 999.0
    monthly_existing = existing_liabilities / 12
    monthly_new_loan = loan_amount / loan_tenure_months
    return round((monthly_existing + monthly_new_loan) / monthly_income, 4)


def compute_credit_score_risk(credit_score: int) -> str:
    if credit_score >= 750:
        return "Low"
    elif credit_score >= 670:
        return "Medium"
    elif credit_score >= 580:
        return "High"
    else:
        return "Very High"


def compute_loan_amount_risk(income: float, loan_amount: float) -> str:
    ratio = loan_amount / income if income > 0 else 999.0
    if ratio <= 3:
        return "Low"
    elif ratio <= 6:
        return "Medium"
    else:
        return "High"


def detect_anomalies(
    income: float,
    age: int,
    credit_score: int,
    loan_amount: float,
    existing_liabilities: float,
) -> Tuple[bool, Optional[str]]:
    flags = []

    if income > 0 and existing_liabilities / income > 0.7:
        flags.append("Existing liabilities exceed 70% of annual income")
    if age < 23 and credit_score > 800:
        flags.append("Unusually high credit score for applicant age")
    if income > 0 and loan_amount > income * 10:
        flags.append("Loan amount exceeds 10× annual income")
    if credit_score < 400 and income > 200_000:
        flags.append("Very low credit score despite high income — possible data error")
    if loan_amount <= 0:
        flags.append("Loan amount is zero or negative")

    return bool(flags), "; ".join(flags) if flags else None


# ── Decision ───────────────────────────────────────────────────────────────────

def compute_risk_score(
    income_stability: float,
    dti: float,
    credit_score: int,
    anomaly_detected: bool,
) -> float:
    """Composite risk score 0-100; higher = riskier."""
    # Credit risk: 0 (best=850) to 100 (worst=300)
    credit_component = max(0.0, (750 - credit_score) / 4.5)

    # DTI risk: DTI of 0.5 → 25 pts; DTI of 2.0 → 100 pts
    dti_component = min(dti * 50, 100)

    # Stability inverse
    stability_component = 100 - income_stability

    anomaly_penalty = 15.0 if anomaly_detected else 0.0

    raw = (
        credit_component * 0.35
        + dti_component * 0.30
        + stability_component * 0.25
        + anomaly_penalty * 0.10
    )
    return round(min(raw, 100), 2)


def classify_loan(
    risk_score: float,
    anomaly_detected: bool,
    dti: float,
    credit_score_risk: str,
) -> str:
    if anomaly_detected:
        return "Requires Manual Review"
    if credit_score_risk == "Very High":
        return "Rejected"
    if dti > 0.65:
        return "Rejected"
    if risk_score >= 65:
        return "Rejected"
    if risk_score <= 35 and dti <= 0.40:
        return "Approved"
    return "Requires Manual Review"


def compute_confidence(
    risk_score: float,
    anomaly_detected: bool,
    completeness_flags: list,
) -> float:
    """Confidence in the decision, 0-100."""
    base = 95.0
    # Confidence decreases near decision boundaries (35 and 65)
    dist_from_boundary = min(abs(risk_score - 35), abs(risk_score - 65))
    boundary_penalty = max(0, (15 - dist_from_boundary))
    anomaly_penalty = 20.0 if anomaly_detected else 0.0
    completeness_penalty = len(completeness_flags) * 5.0
    return round(max(0, base - boundary_penalty - anomaly_penalty - completeness_penalty), 2)
