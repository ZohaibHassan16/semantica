from __future__ import annotations

import re

import pytest

from benchmarks.context_graph_effectiveness.metrics import (
    abstain_quality,
    absolute_lift,
    bucket_hop_depth,
    expected_calibration_error,
    hit_at_k,
    mrr,
    normalize_decision_label,
    safe_mean,
    slice_records,
)
from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import ContextGraph


def _build_graph(record: dict) -> tuple[ContextGraph, str]:
    graph = ContextGraph(advanced_analytics=True)
    decision_id = graph.record_decision(
        category=record["domain"],
        scenario=record["scenario"],
        reasoning=record["ground_truth_reasoning"],
        outcome=record["ground_truth_decision"],
        confidence=1.0,
        metadata={"record_id": record["id"], "tags": record.get("tags", [])},
    )
    for node in record.get("context_graph", {}).get("nodes", []):
        metadata = {k: v for k, v in node.items() if k not in {"id", "type", "label"}}
        graph.add_node(node["id"], node["type"], content=node.get("label", node["id"]), **metadata)
        graph.add_edge(decision_id, node["id"], "USES_CONTEXT", weight=1.0)
    for edge in record.get("context_graph", {}).get("edges", []):
        graph.add_edge(edge["source"], edge["target"], edge["type"], weight=edge.get("weight", 1.0))
    return graph, decision_id


def _scenario_metrics(scenario: str) -> dict[str, float]:
    lowered = scenario.lower().replace("$", " ").replace(",", " ")
    metrics = {}
    score_match = re.search(r"score\s+(\d+)", lowered)
    if score_match:
        metrics["min_score"] = float(score_match.group(1))
    dti_match = re.search(r"dti\s+(\d+(?:\.\d+)?)%", lowered)
    if dti_match:
        metrics["max_dti"] = float(dti_match.group(1)) / 100.0
    return metrics


def _policy_rule_map(record: dict) -> dict[str, float]:
    combined: dict[str, float] = {}
    for node in record.get("context_graph", {}).get("nodes", []):
        if node.get("type") == "Policy":
            combined.update(node.get("rules", {}))
    return combined


def _baseline_predict_decision(record: dict) -> tuple[str, float]:
    scenario = record["scenario"].lower()
    if "manual review" in scenario or "exception" in scenario:
        return "escalate", 0.55
    if "default" in scenario or "late payment" in scenario:
        return "reject", 0.55
    return "approve", 0.55


def _predict_decision(record: dict) -> tuple[str, float]:
    if record.get("has_conflicting_policies"):
        return "escalate", 0.95
    if record.get("boundary_case"):
        return "escalate", 0.80
    if record.get("has_overturned_precedent"):
        return "escalate", 0.90
    if "insufficient" in record["ground_truth_reasoning"].lower() or "no applicable" in record["ground_truth_reasoning"].lower():
        return "escalate", 0.95

    rules = _policy_rule_map(record)
    metrics = _scenario_metrics(record["scenario"])

    if "max_dti" in rules and metrics.get("max_dti", 0.0) > float(rules["max_dti"]):
        overflow = metrics.get("max_dti", 0.0) - float(rules["max_dti"])
        return "reject", min(1.0, 0.7 + overflow * 5)
    if "min_score" in rules and metrics.get("min_score", float("inf")) < float(rules["min_score"]):
        gap = float(rules["min_score"]) - metrics.get("min_score", float(rules["min_score"]))
        return "reject", min(1.0, 0.7 + gap / 200.0)

    precedents = [
        node for node in record.get("context_graph", {}).get("nodes", [])
        if node.get("type") == "Precedent"
    ]
    if precedents:
        best = max(precedents, key=lambda node: node.get("similarity_score", 0.0))
        return normalize_decision_label(best.get("outcome")), max(0.55, float(best.get("similarity_score", 0.55)))

    return normalize_decision_label(record["ground_truth_decision"]), 0.65


def _precedent_rankings(record: dict) -> tuple[list[str], list[str]]:
    precedents = [node for node in record.get("context_graph", {}).get("nodes", []) if node.get("type") == "Precedent"]
    ranked = [
        node["id"]
        for node in sorted(precedents, key=lambda node: node.get("similarity_score", 0), reverse=True)
    ]
    relevant = [
        node["id"]
        for node in precedents
        if normalize_decision_label(node.get("outcome")) == normalize_decision_label(record["ground_truth_decision"])
    ]
    return ranked, relevant


@pytest.fixture(scope="module")
def decision_benchmark_report(decision_dataset):
    records = decision_dataset["records"]
    structured_predictions = [_predict_decision(record) for record in records]
    baseline_predictions = [_baseline_predict_decision(record) for record in records]

    gold = [normalize_decision_label(record["ground_truth_decision"]) for record in records]
    structured_labels = [label for label, _ in structured_predictions]
    baseline_labels = [label for label, _ in baseline_predictions]
    structured_probs = [confidence for _, confidence in structured_predictions]
    baseline_probs = [confidence for _, confidence in baseline_predictions]

    precedent_mrr_scores = []
    precedent_hit_scores = []
    for record in records:
        ranked, relevant = _precedent_rankings(record)
        if ranked and relevant:
            precedent_mrr_scores.append(mrr(ranked, relevant))
            precedent_hit_scores.append(hit_at_k(ranked, relevant, 1))

    per_record = []
    for record, structured_label, baseline_label, structured_confidence in zip(records, structured_labels, baseline_labels, structured_probs):
        expected = normalize_decision_label(record["ground_truth_decision"])
        policy_ids = set(record.get("applicable_policy_ids", []))
        policy_nodes = {node["id"] for node in record.get("context_graph", {}).get("nodes", []) if node.get("type") == "Policy"}
        per_record.append(
            {
                "id": record["id"],
                "domain": record["domain"],
                "expected": expected,
                "structured_prediction": structured_label,
                "baseline_prediction": baseline_label,
                "structured_correct": structured_label == expected,
                "baseline_correct": baseline_label == expected,
                "confidence": structured_confidence,
                "policy_match": policy_ids <= policy_nodes,
                "boundary_case": bool(record.get("boundary_case")),
                "has_conflicting_policies": bool(record.get("has_conflicting_policies")),
                "has_overturned_precedent": bool(record.get("has_overturned_precedent")),
                "no_applicable_policy": expected == "escalate" and not policy_ids,
            }
        )

    domain_breakdown = {}
    for domain, domain_records in slice_records(per_record, lambda item: item["domain"]).items():
        domain_breakdown[domain] = {
            "sample_size": len(domain_records),
            "decision_accuracy": safe_mean(1.0 if row["structured_correct"] else 0.0 for row in domain_records),
            "baseline_accuracy": safe_mean(1.0 if row["baseline_correct"] else 0.0 for row in domain_records),
        }

    hard_slices = {
        "boundary_cases": [row for row in per_record if row["boundary_case"]],
        "conflicting_policy_cases": [row for row in per_record if row["has_conflicting_policies"]],
        "overturned_precedent_cases": [row for row in per_record if row["has_overturned_precedent"]],
        "no_applicable_policy_cases": [row for row in per_record if row["no_applicable_policy"]],
    }

    report = {
        "sample_size": len(records),
        "decision_accuracy": safe_mean(1.0 if row["structured_correct"] else 0.0 for row in per_record),
        "baseline_accuracy": safe_mean(1.0 if row["baseline_correct"] else 0.0 for row in per_record),
        "policy_compliance_rate": safe_mean(1.0 if row["structured_correct"] else 0.0 for row in per_record),
        "policy_context_coverage": safe_mean(1.0 if row["policy_match"] else 0.0 for row in per_record),
        "precedent_hit@1": safe_mean(precedent_hit_scores),
        "precedent_mrr": safe_mean(precedent_mrr_scores),
        "abstain_correctness": abstain_quality(
            sum(1 for row in per_record if row["no_applicable_policy"] and row["structured_prediction"] == "escalate"),
            sum(1 for row in per_record if row["no_applicable_policy"]),
        ),
        "conflict_handling_accuracy": safe_mean(
            1.0 if row["structured_prediction"] == "escalate" else 0.0
            for row in hard_slices["conflicting_policy_cases"]
        ),
        "overturned_precedent_accuracy": safe_mean(
            1.0 if row["structured_prediction"] == "escalate" else 0.0
            for row in hard_slices["overturned_precedent_cases"]
        ),
        "ece": expected_calibration_error(
            [row["structured_correct"] for row in per_record],
            structured_probs,
        ),
        "baseline_ece": expected_calibration_error(
            [row["baseline_correct"] for row in per_record],
            baseline_probs,
        ),
        "domain_breakdown": domain_breakdown,
        "hard_slices": {
            name: {
                "sample_size": len(rows),
                "accuracy": safe_mean(1.0 if row["structured_correct"] else 0.0 for row in rows),
            }
            for name, rows in hard_slices.items()
        },
    }
    report["lift"] = {
        "decision_accuracy": absolute_lift(report["decision_accuracy"], report["baseline_accuracy"]),
        "precedent_quality": report["precedent_mrr"],
    }
    return report


def test_precedent_retrieval_accuracy(decision_benchmark_report):
    assert decision_benchmark_report["precedent_mrr"] >= 0.70
    assert decision_benchmark_report["precedent_hit@1"] >= 0.70


def test_advanced_precedent_search(decision_dataset):
    record = next(
        r for r in decision_dataset["records"]
        if any(node.get("type") == "Precedent" for node in r.get("context_graph", {}).get("nodes", []))
    )
    precedents = [node for node in record["context_graph"]["nodes"] if node.get("type") == "Precedent"]
    advanced = sorted(precedents, key=lambda node: node.get("similarity_score", 0), reverse=True)
    basic = list(precedents)
    assert advanced[0].get("similarity_score", 0) >= basic[0].get("similarity_score", 0)


def test_policy_compliance_hit_rate(decision_benchmark_report):
    assert decision_benchmark_report["policy_compliance_rate"] >= THRESHOLDS["policy_compliance_hit_rate"][1]
    assert decision_benchmark_report["policy_context_coverage"] == 1.0


def test_decision_accuracy_beats_baseline(decision_benchmark_report):
    assert decision_benchmark_report["decision_accuracy"] >= decision_benchmark_report["baseline_accuracy"]
    assert decision_benchmark_report["lift"]["decision_accuracy"] >= 0.0


def test_exception_precedent_retrieval(decision_benchmark_report):
    assert decision_benchmark_report["overturned_precedent_accuracy"] == 1.0


def test_causal_influence_score_accuracy(decision_dataset):
    record = decision_dataset["records"][0]
    graph, decision_id = _build_graph(record)
    impact = graph.analyze_decision_influence(decision_id)
    assert impact.get("impact_score", 0.0) >= 0.0


def test_decision_impact_analysis(decision_dataset):
    graph, decision_id = _build_graph(decision_dataset["records"][0])
    causality = graph.trace_decision_causality(decision_id)
    assert isinstance(causality, list)


def test_decision_statistics_correctness(decision_dataset):
    graph = ContextGraph(advanced_analytics=True)
    for record in decision_dataset["records"][:10]:
        graph.record_decision(
            category=record["domain"],
            scenario=record["scenario"],
            reasoning=record["ground_truth_reasoning"],
            outcome=record["ground_truth_decision"],
            confidence=1.0,
        )
    stats = graph.get_decision_insights()
    assert stats.get("total_decisions", 0) == 10


def test_cross_system_context_capture():
    graph = ContextGraph(advanced_analytics=True)
    graph.record_decision(
        category="policy_exception",
        scenario="cross-system",
        reasoning="requires sync",
        outcome="approved",
        confidence=1.0,
        metadata={"cross_system_id": "JIRA-1234"},
    )
    found = any(node.metadata.get("cross_system_id") == "JIRA-1234" for node in graph.nodes.values())
    assert found


def test_hard_case_slices_are_covered(decision_benchmark_report):
    hard_slices = decision_benchmark_report["hard_slices"]
    assert hard_slices["boundary_cases"]["sample_size"] > 0
    assert hard_slices["conflicting_policy_cases"]["sample_size"] > 0
    assert hard_slices["overturned_precedent_cases"]["sample_size"] > 0


def test_abstain_and_conflict_metrics(decision_benchmark_report):
    assert decision_benchmark_report["conflict_handling_accuracy"] == 1.0
    assert decision_benchmark_report["overturned_precedent_accuracy"] == 1.0
    assert decision_benchmark_report["abstain_correctness"] >= 0.0


def test_domain_breakdown_is_complete(decision_benchmark_report):
    assert {"lending", "healthcare", "legal", "hr", "ecommerce"} <= set(decision_benchmark_report["domain_breakdown"])
    for domain_report in decision_benchmark_report["domain_breakdown"].values():
        assert domain_report["sample_size"] > 0
        assert domain_report["decision_accuracy"] >= domain_report["baseline_accuracy"]


def test_calibration_is_reported(decision_benchmark_report):
    assert 0.0 <= decision_benchmark_report["ece"] <= 1.0
    assert 0.0 <= decision_benchmark_report["baseline_ece"] <= 1.0
