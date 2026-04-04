from __future__ import annotations

import pytest

from benchmarks.context_graph_effectiveness.metrics import normalize_decision_label
from benchmarks.context_graph_effectiveness.reporting import (
    binary_rate,
    coverage_summary,
    make_track_report,
    paired_lift_report,
    require_reportable,
)
from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS

pytestmark = pytest.mark.real_llm


def _policy_case(decision_dataset: dict) -> dict:
    return next(
        record
        for record in decision_dataset["records"]
        if record.get("applicable_policy_ids")
        and normalize_decision_label(record["ground_truth_decision"]) in {"approve", "reject"}
    )


def _abstain_case(decision_dataset: dict) -> dict:
    return next(
        record
        for record in decision_dataset["records"]
        if not record.get("applicable_policy_ids")
        and normalize_decision_label(record["ground_truth_decision"]) == "escalate"
    )


def _precedent_case(decision_dataset: dict) -> dict:
    return next(
        record
        for record in decision_dataset["records"]
        if any(node.get("type") == "Precedent" for node in record.get("context_graph", {}).get("nodes", []))
    )


def _temporal_case(retrieval_eval_dataset: dict) -> dict:
    return next(
        record for record in retrieval_eval_dataset["records"] if record["query_type"] == "temporal"
    )


def _policy_prompt(record: dict, with_context: bool) -> str:
    if not with_context:
        return (
            "Decide APPROVE, REJECT, or ESCALATE. Respond with one label and a short reason.\n"
            f"Scenario: {record['scenario']}"
        )
    lines = [f"Scenario: {record['scenario']}"]
    for node in record.get("context_graph", {}).get("nodes", []):
        if node.get("type") == "Policy":
            lines.append(f"Policy {node['id']}: {node.get('rules', {})}")
    lines.append(f"Applicable policies: {', '.join(record.get('applicable_policy_ids', [])) or 'none'}")
    return (
        "Decide APPROVE, REJECT, or ESCALATE using the policy context. "
        "Reference the applicable policy when you answer.\n" + "\n".join(lines)
    )


def _precedent_prompt(record: dict, with_context: bool) -> str:
    if not with_context:
        return (
            "Decide APPROVE, REJECT, or ESCALATE. Respond with one label and a short reason.\n"
            f"Scenario: {record['scenario']}"
        )
    precedents = [
        node for node in record.get("context_graph", {}).get("nodes", []) if node.get("type") == "Precedent"
    ]
    details = "\n".join(
        f"{node['id']}: outcome={node.get('outcome')} similarity={node.get('similarity_score', 0.0):.2f}"
        for node in precedents
    )
    return (
        "Decide APPROVE, REJECT, or ESCALATE using the precedent context. "
        "Name the strongest precedent in your answer.\n"
        f"Scenario: {record['scenario']}\n{details}"
    )


def _abstain_prompt(record: dict, with_context: bool) -> str:
    if not with_context:
        return f"Answer decisively if possible.\nScenario: {record['scenario']}"
    return (
        "No applicable policy nodes were retrieved for this scenario. "
        "Do not invent evidence. Decide APPROVE, REJECT, or ESCALATE.\n"
        f"Scenario: {record['scenario']}\nApplicable policies: none"
    )


def _temporal_prompt(record: dict, with_context: bool) -> str:
    if not with_context:
        return (
            "Select the best matching node id for the query.\n"
            f"Query: {record['query']}\nAs-of: {record['at_time']}"
        )
    relevant = ", ".join(record.get("relevant_node_ids", []))
    irrelevant = ", ".join(record.get("irrelevant_node_ids", []))
    return (
        "Select the valid node id for the query and explain briefly.\n"
        f"Query: {record['query']}\n"
        f"As-of: {record['at_time']}\n"
        f"Valid candidates: {relevant}\n"
        f"Invalid candidates: {irrelevant}"
    )


def _contains_any(text: str, terms: list[str]) -> bool:
    normalized = text.lower()
    return any(term.lower() in normalized for term in terms)


@pytest.fixture(scope="module")
def skill_injection_report(real_llm, decision_dataset, retrieval_eval_dataset):
    policy_record = _policy_case(decision_dataset)
    abstain_record = _abstain_case(decision_dataset)
    precedent_record = _precedent_case(decision_dataset)
    temporal_record = _temporal_case(retrieval_eval_dataset)

    cases = []

    baseline = real_llm.generate(_policy_prompt(policy_record, with_context=False))
    contextual = real_llm.generate(_policy_prompt(policy_record, with_context=True))
    expected = normalize_decision_label(policy_record["ground_truth_decision"])
    cases.append(
        {
            "name": "policy_compliance",
            "expected": expected,
            "baseline_label": normalize_decision_label(baseline),
            "context_label": normalize_decision_label(contextual),
            "policy_reference": _contains_any(contextual, list(policy_record.get("applicable_policy_ids", []))),
            "context_success": normalize_decision_label(contextual) == expected
            and _contains_any(contextual, list(policy_record.get("applicable_policy_ids", []))),
        }
    )

    baseline = real_llm.generate(_precedent_prompt(precedent_record, with_context=False))
    contextual = real_llm.generate(_precedent_prompt(precedent_record, with_context=True))
    precedents = [
        node for node in precedent_record.get("context_graph", {}).get("nodes", []) if node.get("type") == "Precedent"
    ]
    strongest = max(precedents, key=lambda node: node.get("similarity_score", 0.0))
    expected = normalize_decision_label(precedent_record["ground_truth_decision"])
    cases.append(
        {
            "name": "precedent_selection",
            "expected": expected,
            "baseline_label": normalize_decision_label(baseline),
            "context_label": normalize_decision_label(contextual),
            "precedent_selected": strongest["id"].lower() in contextual.lower(),
            "context_success": normalize_decision_label(contextual) == expected
            and strongest["id"].lower() in contextual.lower(),
        }
    )

    baseline = real_llm.generate(_abstain_prompt(abstain_record, with_context=False))
    contextual = real_llm.generate(_abstain_prompt(abstain_record, with_context=True))
    cases.append(
        {
            "name": "uncertainty_flagging",
            "expected": "escalate",
            "baseline_label": normalize_decision_label(baseline),
            "context_label": normalize_decision_label(contextual),
            "abstain_reasoning": _contains_any(contextual, ["insufficient", "context", "review", "cannot"]),
            "context_success": normalize_decision_label(contextual) == "escalate"
            and _contains_any(contextual, ["insufficient", "context", "review", "cannot"]),
        }
    )

    baseline = real_llm.generate(_temporal_prompt(temporal_record, with_context=False))
    contextual = real_llm.generate(_temporal_prompt(temporal_record, with_context=True))
    valid_ids = temporal_record.get("relevant_node_ids", [])
    invalid_ids = temporal_record.get("irrelevant_node_ids", [])
    cases.append(
        {
            "name": "temporal_selection",
            "expected": valid_ids[0],
            "baseline_label": baseline.strip().lower(),
            "context_label": contextual.strip().lower(),
            "temporal_selection": _contains_any(contextual, valid_ids) and not _contains_any(contextual, invalid_ids),
            "context_success": _contains_any(contextual, valid_ids) and not _contains_any(contextual, invalid_ids),
        }
    )

    decision_cases = [case for case in cases if case["name"] != "temporal_selection"]
    lift = paired_lift_report(
        [case["expected"] for case in decision_cases],
        [case["baseline_label"] for case in decision_cases],
        [case["context_label"] for case in decision_cases],
    )
    report = make_track_report(
        name="skill_injection",
        sample_size=len(cases),
        metrics={
            "baseline_accuracy": lift["baseline_accuracy"],
            "contextual_accuracy": lift["contextual_accuracy"],
            "decision_accuracy_delta": lift["absolute_lift"],
            "policy_reference_fidelity": binary_rate(case.get("policy_reference", False) for case in cases),
            "precedent_selection_accuracy": binary_rate(case.get("precedent_selected", False) for case in cases),
            "abstain_correctness": binary_rate(case.get("abstain_reasoning", False) for case in cases),
            "temporal_selection_accuracy": binary_rate(case.get("temporal_selection", False) for case in cases),
            "skill_activation_rate": binary_rate(case["context_success"] for case in cases),
        },
        baselines={"no_context": {"accuracy": lift["baseline_accuracy"]}},
        slices={case["name"]: {"sample_size": 1, "success_rate": 1.0 if case["context_success"] else 0.0} for case in cases},
        coverage=coverage_summary(executed=len(cases), eligible=len(cases), required=len(cases)),
    )
    require_reportable(
        report,
        min_sample_size=4,
        min_executed_ratio=1.0,
        required_metrics=("skill_activation_rate", "decision_accuracy_delta"),
    )
    return report


def test_skill_activation_rate(skill_injection_report):
    assert skill_injection_report["skill_activation_rate"] >= THRESHOLDS["skill_activation_rate"][1]


def test_contextual_skill_accuracy_beats_no_context(skill_injection_report):
    assert skill_injection_report["contextual_accuracy"] >= skill_injection_report["baseline_accuracy"]
    assert skill_injection_report["decision_accuracy_delta"] >= 0.0


def test_policy_reference_fidelity(skill_injection_report):
    assert skill_injection_report["policy_reference_fidelity"] >= 0.25


def test_precedent_selection_accuracy(skill_injection_report):
    assert skill_injection_report["precedent_selection_accuracy"] >= 0.5


def test_uncertainty_flagging(skill_injection_report):
    assert skill_injection_report["abstain_correctness"] >= 0.5


def test_temporal_selection(skill_injection_report):
    assert skill_injection_report["temporal_selection_accuracy"] >= 0.5
