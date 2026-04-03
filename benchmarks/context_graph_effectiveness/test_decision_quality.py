from __future__ import annotations

import pytest

from benchmarks.context_graph_effectiveness.metrics import normalize_decision_label
from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import ContextGraph

pytestmark = pytest.mark.real_llm


def _build_context_graph(record: dict) -> ContextGraph:
    graph = ContextGraph(advanced_analytics=True)
    graph.add_node(record["id"], "Scenario", content=record["scenario"], domain=record["domain"])

    for node in record.get("context_graph", {}).get("nodes", []):
        node_id = node["id"]
        label = node.get("label") or node_id
        metadata = {k: v for k, v in node.items() if k not in {"id", "type", "label"}}
        graph.add_node(node_id, node["type"], content=label, **metadata)
        graph.add_edge(record["id"], node_id, "CONTEXT_FOR", weight=1.0)

    for edge in record.get("context_graph", {}).get("edges", []):
        graph.add_edge(edge["source"], edge["target"], edge["type"], weight=edge.get("weight", 1.0))

    return graph


def _render_context(record: dict) -> str:
    lines = [f"Scenario: {record['scenario']}"]
    for node in record.get("context_graph", {}).get("nodes", []):
        details = []
        if "rules" in node:
            details.append(f"rules={node['rules']}")
        if "outcome" in node:
            details.append(f"outcome={node['outcome']}")
        lines.append(f"- {node['type']} {node['id']}: {node.get('label', node['id'])} {' '.join(details)}".strip())
    lines.append(f"Applicable policies: {', '.join(record.get('applicable_policy_ids', [])) or 'none'}")
    return "\n".join(lines)


def _baseline_prompt(record: dict) -> str:
    return (
        "Decide APPROVE, REJECT, or ESCALATE. Respond with one label and a short reason.\n"
        f"Scenario: {record['scenario']}"
    )


def _context_prompt(record: dict) -> str:
    return (
        "Decide APPROVE, REJECT, or ESCALATE. Use the context graph evidence. "
        "Respond with one label and a short reason.\n"
        f"{_render_context(record)}"
    )


def _hallucination_rate(response: str, allowed_terms: set[str]) -> float:
    tokens = {token.strip(".,:;()[]{}\"'").lower() for token in response.split() if len(token) > 3}
    if not tokens:
        return 0.0
    unsupported = [token for token in tokens if token not in allowed_terms]
    return len(unsupported) / len(tokens)


def _allowed_terms(record: dict) -> set[str]:
    allowed = set(record["scenario"].lower().replace("%", " ").replace("$", " ").replace(",", " ").split())
    allowed.update(record.get("ground_truth_reasoning", "").lower().split())
    for policy_id in record.get("applicable_policy_ids", []):
        allowed.update(policy_id.lower().split("_"))
    for node in record.get("context_graph", {}).get("nodes", []):
        allowed.update(str(node.get("label", "")).lower().split())
        allowed.update(str(node.get("outcome", "")).lower().split())
    allowed.update({"approve", "reject", "escalate", "policy", "context", "review", "manual"})
    return {token for token in allowed if token}


def _evaluate_record(real_llm, record: dict) -> dict[str, object]:
    _build_context_graph(record)
    baseline_response = real_llm.generate(_baseline_prompt(record))
    context_response = real_llm.generate(_context_prompt(record))

    gold = normalize_decision_label(record["ground_truth_decision"])
    baseline_label = normalize_decision_label(baseline_response)
    context_label = normalize_decision_label(context_response)

    allowed_terms = _allowed_terms(record)
    return {
        "gold": gold,
        "baseline_correct": baseline_label == gold,
        "context_correct": context_label == gold,
        "baseline_hallucination": _hallucination_rate(baseline_response, allowed_terms),
        "context_hallucination": _hallucination_rate(context_response, allowed_terms),
        "context_response": context_response,
        "baseline_response": baseline_response,
    }


def test_decision_accuracy_delta(real_llm, decision_dataset):
    sample = decision_dataset["records"][:12]
    outcomes = [_evaluate_record(real_llm, record) for record in sample]
    baseline_accuracy = sum(1 for item in outcomes if item["baseline_correct"]) / len(outcomes)
    context_accuracy = sum(1 for item in outcomes if item["context_correct"]) / len(outcomes)
    assert context_accuracy - baseline_accuracy > THRESHOLDS["decision_accuracy_delta"][1]


def test_hallucination_rate_delta(real_llm, decision_dataset):
    sample = decision_dataset["records"][:12]
    outcomes = [_evaluate_record(real_llm, record) for record in sample]
    baseline_rate = sum(item["baseline_hallucination"] for item in outcomes) / len(outcomes)
    context_rate = sum(item["context_hallucination"] for item in outcomes) / len(outcomes)
    assert baseline_rate - context_rate > THRESHOLDS["hallucination_rate_delta"][1]


def test_citation_groundedness(real_llm, decision_dataset):
    sample = decision_dataset["records"][:8]
    grounded = []
    for record in sample:
        outcome = _evaluate_record(real_llm, record)
        response = outcome["context_response"].lower()
        context_terms = _allowed_terms(record)
        tokens = [token.strip(".,:;()[]{}\"'") for token in response.split() if len(token) > 3]
        if not tokens:
            grounded.append(0.0)
            continue
        supported = sum(1 for token in tokens if token in context_terms)
        grounded.append(supported / len(tokens))
    citation_groundedness = sum(grounded) / len(grounded)
    assert citation_groundedness >= THRESHOLDS["citation_groundedness"][1]


def test_policy_compliance_rate(real_llm, decision_dataset):
    sample = decision_dataset["records"][:12]
    outcomes = [_evaluate_record(real_llm, record) for record in sample]
    compliance_rate = sum(1 for item in outcomes if item["context_correct"]) / len(outcomes)
    assert compliance_rate >= THRESHOLDS["policy_compliance_rate"][1]
