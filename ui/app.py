"""
Streamlit Chatbot UI — Agentic AI Loan Approval System

Run:  streamlit run ui/app.py
Requires the FastAPI server running on port 8000 (or API_BASE env var).
"""

from __future__ import annotations

import os
import json

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Loan Approval System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .agent-card {
        background: #f8f9fa;
        border-left: 4px solid #0066cc;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 12px;
    }
    .approved   { border-left-color: #28a745; background: #f0fff4; }
    .rejected   { border-left-color: #dc3545; background: #fff5f5; }
    .review     { border-left-color: #ffc107; background: #fffdf0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to the **AI Loan Approval System**.\n\n"
                "Fill in the application form in the sidebar and click **Evaluate Loan** "
                "to get an instant AI-driven decision with full explainability.\n\n"
                "After evaluation, you can ask me follow-up questions about the decision."
            ),
        }
    ]

if "last_result" not in st.session_state:
    st.session_state.last_result = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def decision_css_class(classification: str) -> str:
    return {"Approved": "approved", "Rejected": "rejected", "Requires Manual Review": "review"}.get(classification, "")


def render_chat_history():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def call_api(payload: dict) -> dict | None:
    try:
        resp = requests.post(f"{API_BASE}/loan/apply", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at {API_BASE}. Make sure the server is running.")
        return None
    except requests.exceptions.HTTPError as exc:
        st.error(f"API error {exc.response.status_code}: {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


def format_result_as_markdown(result: dict) -> str:
    classification = result["decision"]["classification"]

    decision_icon = {"Approved": "✅", "Rejected": "❌", "Requires Manual Review": "⏳"}.get(classification, "ℹ️")

    lines = [
        f"## {decision_icon} Loan Decision: **{classification}**",
        f"**Case ID:** `{result['case_id']}`  |  **Processing Time:** {result['processing_time_ms']:.0f} ms",
        "",
        "---",
        "### Agent A — Applicant Profile",
        f"- Income Stability Score: **{result['profile']['income_stability_score']}/100**",
        f"- Employment Risk: **{result['profile']['employment_risk']}**",
        f"- Credit History: {result['profile']['credit_history_summary']}",
    ]
    flags = result["profile"]["application_completeness_flags"]
    if flags:
        lines.append("- Completeness Flags:")
        for f in flags:
            lines.append(f"  - ⚠️ {f}")
    else:
        lines.append("- Completeness: ✅ All fields complete")

    lines += [
        "",
        "### Agent B — Financial Risk Analysis",
        f"- Debt-to-Income Ratio: **{result['risk_analysis']['debt_to_income_ratio']:.2%}**",
        f"- Credit Score Risk: **{result['risk_analysis']['credit_score_risk_level']}**",
        f"- Loan Amount Risk: **{result['risk_analysis']['loan_amount_risk']}**",
        f"- Anomaly Detected: {'⚠️ Yes' if result['risk_analysis']['anomaly_detected'] else '✅ No'}",
    ]
    if result["risk_analysis"].get("anomaly_details"):
        lines.append(f"  - _{result['risk_analysis']['anomaly_details']}_")
    lines.append(f"- Reasoning: _{result['risk_analysis']['reasoning']}_")

    lines += [
        "",
        "### Agent C — Loan Decision",
        f"- Risk Score: **{result['decision']['risk_score']}/100**",
        f"- Confidence: **{result['decision']['confidence_level']}%**",
        "- Key Factors:",
    ]
    for factor in result["decision"]["key_decision_factors"]:
        lines.append(f"  - {factor}")
    lines.append(f"- Explanation: _{result['decision']['explanation']}_")

    lines += [
        "",
        "### Agent D — Compliance & Action",
        f"- Action: {result['compliance']['action_taken']}",
        f"- Notification Sent: {'✅ Yes' if result['compliance']['notification_sent'] else '❌ No'}",
        f"- Timestamp: {result['compliance']['timestamp']}",
        f"- Summary: _{result['compliance']['summary']}_",
    ]

    return "\n".join(lines)


# ── Sidebar — Application Form ─────────────────────────────────────────────────
with st.sidebar:
    st.title("🏦 Loan Application")
    st.caption("Claude Sonnet · LangGraph · FastMCP · LangChain")
    st.divider()

    applicant_id = st.text_input("Applicant ID", value="APP-001", max_chars=20)
    age = st.number_input("Age", min_value=18, max_value=80, value=35)
    income = st.number_input("Annual Income ($)", min_value=15_000, max_value=5_000_000, value=75_000, step=1_000)
    employment_type = st.selectbox(
        "Employment Type",
        ["salaried", "self_employed", "contract", "unemployed"],
        index=0,
    )
    credit_score = st.slider("Credit Score", min_value=300, max_value=850, value=700)
    loan_amount = st.number_input("Loan Amount ($)", min_value=1_000, max_value=10_000_000, value=150_000, step=1_000)
    loan_tenure = st.selectbox(
        "Loan Tenure",
        [12, 24, 36, 48, 60, 84, 120, 180, 240, 360],
        index=4,
        format_func=lambda x: f"{x} months ({x // 12} yr)" if x >= 12 else f"{x} months",
    )
    existing_liabilities = st.number_input(
        "Existing Annual Liabilities ($)",
        min_value=0,
        max_value=2_000_000,
        value=10_000,
        step=500,
    )
    location = st.text_input("Location", value="New York, NY")

    st.divider()
    submit = st.button("Evaluate Loan", type="primary", use_container_width=True)

# ── Main content ───────────────────────────────────────────────────────────────
st.title("Agentic AI Intelligent Loan Approval System")
st.caption("Multi-agent · LangGraph · FastMCP · LangChain LCEL · Claude Sonnet 4.6")

render_chat_history()

# ── Handle submission ──────────────────────────────────────────────────────────
if submit:
    payload = {
        "applicant_id": applicant_id,
        "age": int(age),
        "income": float(income),
        "employment_type": employment_type,
        "credit_score": int(credit_score),
        "loan_amount": float(loan_amount),
        "loan_tenure_months": int(loan_tenure),
        "existing_liabilities": float(existing_liabilities),
        "location": location,
    }

    user_summary = (
        f"**New Loan Application**\n"
        f"- Applicant: `{applicant_id}` | Age: {age} | Location: {location}\n"
        f"- Income: ${income:,.0f} | Employment: {employment_type}\n"
        f"- Credit Score: {credit_score} | Loan: ${loan_amount:,.0f} over {loan_tenure} months\n"
        f"- Existing Liabilities: ${existing_liabilities:,.0f}"
    )
    add_message("user", user_summary)

    with st.chat_message("user"):
        st.markdown(user_summary)

    with st.chat_message("assistant"):
        with st.spinner("Running multi-agent pipeline... (Profile ∥ Risk → Decision → Compliance)"):
            result = call_api(payload)

        if result:
            # Store for chatbot context
            st.session_state.last_result = result

            response_md = format_result_as_markdown(result)
            st.markdown(response_md)
            add_message("assistant", response_md)

            with st.expander("Raw JSON response (developer view)"):
                st.json(result)
        else:
            err_msg = "Failed to process the application. Check that the API server is running."
            st.error(err_msg)
            add_message("assistant", f"Error: {err_msg}")

# ── Follow-up chatbot (LangChain LCEL chain) ──────────────────────────────────
if prompt := st.chat_input("Ask a follow-up question about the decision..."):
    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                from ui.chatbot_chain import ask_chatbot
                response = ask_chatbot(prompt, st.session_state.last_result)
            except Exception as exc:
                response = (
                    "I couldn't connect to the AI advisor right now. "
                    "Please ensure your ANTHROPIC_API_KEY is set and try again."
                )
        st.markdown(response)
    add_message("assistant", response)
