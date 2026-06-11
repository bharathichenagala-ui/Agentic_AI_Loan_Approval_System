"""
LangChain LCEL chatbot chain for loan advisor follow-up questions.

Demonstrates the pipe operator: ChatPromptTemplate | ChatAnthropic | StrOutputParser
This is architecturally distinct from the tool-use loop in MCPAgent — it shows
two different Claude invocation patterns in the same project.
"""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

_SYSTEM = """You are a helpful loan advisor at an AI-powered bank.
An applicant has received a loan decision and has a follow-up question.

Answer clearly and concisely. When referring to their case, use the specific
numbers and factors from the case context provided. If they ask how to improve
their chances, give concrete, actionable advice based on the actual risk factors.

Case context:
{case_context}"""

_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{question}"),
])


def build_chatbot_chain():
    """Build and return the LCEL chain: template | llm | parser."""
    llm = ChatAnthropic(
        model=os.getenv("CLAUDE_MODEL", "global.anthropic.claude-sonnet-4-6"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=512,
    )
    return _PROMPT_TEMPLATE | llm | StrOutputParser()


def ask_chatbot(question: str, case_context: dict) -> str:
    """Invoke the chatbot chain with the applicant's question and case context."""
    chain = build_chatbot_chain()
    return chain.invoke({
        "question": question,
        "case_context": str(case_context) if case_context else "No case context available yet.",
    })
