"""
LangGraph topology tests.

Verifies the graph structure without making any API calls.

Run:  pytest tests/test_graph.py -v
"""

import pytest
from orchestration.loan_graph import build_loan_graph, LoanState


def test_graph_compiles():
    """Graph should compile without errors."""
    graph = build_loan_graph()
    assert graph is not None


def test_graph_has_all_four_nodes():
    """All four agent nodes must be present."""
    graph = build_loan_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "profile_node" in node_names
    assert "risk_node" in node_names
    assert "decision_node" in node_names
    assert "compliance_node" in node_names


def test_graph_fan_out_from_start():
    """Both profile_node and risk_node should be reachable from __start__."""
    graph = build_loan_graph()
    raw = graph.get_graph()
    start_edges = [e for e in raw.edges if e[0] == "__start__"]
    targets = {e[1] for e in start_edges}
    assert "profile_node" in targets, "profile_node must connect from START"
    assert "risk_node" in targets, "risk_node must connect from START (parallel fan-out)"


def test_graph_fan_in_to_decision():
    """decision_node must have edges from both profile_node and risk_node."""
    graph = build_loan_graph()
    raw = graph.get_graph()
    incoming_to_decision = {e[0] for e in raw.edges if e[1] == "decision_node"}
    assert "profile_node" in incoming_to_decision
    assert "risk_node" in incoming_to_decision


def test_graph_linear_tail():
    """decision_node → compliance_node → __end__ must be sequential."""
    graph = build_loan_graph()
    raw = graph.get_graph()
    edges = {(e[0], e[1]) for e in raw.edges}
    assert ("decision_node", "compliance_node") in edges
    assert ("compliance_node", "__end__") in edges


def test_loan_state_schema_has_error_field():
    """LoanState TypedDict must include the error field for pipeline fault handling."""
    annotations = LoanState.__annotations__
    assert "error" in annotations
    assert "profile_result" in annotations
    assert "risk_result" in annotations
    assert "decision_result" in annotations
    assert "compliance_result" in annotations
