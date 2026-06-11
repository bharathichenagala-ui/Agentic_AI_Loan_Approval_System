"""
LangChain integration tests.

Verifies JsonOutputParser, ChatPromptTemplate usage, and chatbot chain
construction — no API calls required.

Run:  pytest tests/test_langchain.py -v
"""

import os
import pytest

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate


# ── JsonOutputParser ───────────────────────────────────────────────────────────

def test_json_output_parser_plain_json():
    """Parser must handle a plain JSON string."""
    parser = JsonOutputParser()
    result = parser.parse('{"income_stability_score": 75.5, "employment_risk": "Low"}')
    assert result["income_stability_score"] == 75.5
    assert result["employment_risk"] == "Low"


def test_json_output_parser_fenced_json():
    """Parser must handle Claude's markdown code-fenced JSON response."""
    parser = JsonOutputParser()
    raw = '```json\n{"classification": "Approved", "risk_score": 28.0}\n```'
    result = parser.parse(raw)
    assert result["classification"] == "Approved"
    assert result["risk_score"] == 28.0


def test_json_output_parser_nested_fields():
    """Parser must handle nested structures and lists."""
    parser = JsonOutputParser()
    raw = '{"key_decision_factors": ["Low DTI", "Good credit"], "confidence_level": 92.0}'
    result = parser.parse(raw)
    assert isinstance(result["key_decision_factors"], list)
    assert len(result["key_decision_factors"]) == 2


# ── ChatPromptTemplate ─────────────────────────────────────────────────────────

def test_chat_prompt_template_formats_correctly():
    """ChatPromptTemplate must inject variables and produce correct message types."""
    template = ChatPromptTemplate.from_messages([
        ("system", "You are a {role}."),
        ("human", "{question}"),
    ])
    messages = template.format_messages(role="loan advisor", question="What is DTI?")
    assert len(messages) == 2
    assert "loan advisor" in messages[0].content
    assert "What is DTI?" in messages[1].content


def test_chat_prompt_template_with_double_braces():
    """Template with {{ }} literal braces must not expand them as variables."""
    template = ChatPromptTemplate.from_messages([
        ("system", 'Return JSON: {{"key": "value"}}'),
        ("human", "{input}"),
    ])
    messages = template.format_messages(input="test")
    # {{ }} should become literal { } in the output
    assert '{"key": "value"}' in messages[0].content


# ── Chatbot chain ──────────────────────────────────────────────────────────────

def test_chatbot_chain_builds_without_error():
    """build_chatbot_chain() must return a runnable chain (no API call made)."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-placeholder")
    from ui.chatbot_chain import build_chatbot_chain
    chain = build_chatbot_chain()
    assert chain is not None


def test_chatbot_chain_is_lcel_pipeline():
    """The chain should be an LCEL RunnableSequence (pipe operator used)."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-placeholder")
    from langchain_core.runnables import RunnableSequence
    from ui.chatbot_chain import build_chatbot_chain
    chain = build_chatbot_chain()
    assert isinstance(chain, RunnableSequence)
