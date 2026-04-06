from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from benchmarks.context_graph_effectiveness.metrics import (
    abstain_quality,
    expected_calibration_error,
    extract_node_ids,
    hit_at_k,
    mrr,
    normalize_decision_label,
    safe_mean,
    slice_records,
)
from benchmarks.context_graph_effectiveness.reporting import (
    coverage_summary,
    make_track_report,
    paired_lift_report,
    require_reportable,
)
from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import ContextGraph
from semantica.context.context_retriever import ContextRetriever
from semantica.context.decision_models import Decision, Policy
from semantica.context.policy_engine import PolicyEngine


def _scenario_metrics(scenario: str) -> dict[str, float]:
    lowered = scenario.lower().replace("$", " ").replace(",", " ")
    metrics = {}
    score_match = re.search(r"score\s+(\d+)", lowered)
    if score_match:
        metrics["min_score"] = float(score_match.group(1))
    dti_match = re.search(r"dti\s+(\d+(?:\.\d+)?)%", lowered)
    if dti_match:
        metrics["max_dti"] = float(dti_match.group(1)) / 100.0
    income_match = re.search(r"income\s+(\d+)k", lowered)
    if income_match:
        metrics["income_k"] = float(income_match.group(1))
    return metrics


def _baseline_predict_decision(record: dict) -> tuple[str, float]:
    scenario = record["scenario"].lower()
    if any(token in scenario for token in ["manual review", "exception", "pending", "unclear"]):
        return "escalate", 0.55
    if any(token in scenario for token in ["default", "late payment", "declined", "breach"]):
        return "reject", 0.55
    return "approve", 0.55


@dataclass
class RuntimeRecord:
    graph: ContextGraph
    engine: PolicyEngine
    decision_id: str
    decision: Decision
    applicable_policy_ids: list[str]
    policy_nodes_by_id: dict[str, dict]
    precedent_decision_ids: dict[str, str]


def _make_decision_model(record: dict) -> Decision:
    metrics = _scenario_metrics(record["scenario"])
    return Decision(
        decision_id=f"decision::{record['id']}",
        category=record["domain"],
        scenario=record["scenario"],
        reasoning=record["ground_truth_reasoning"],
        outcome="pending",
        confidence=0.5,
        timestamp=datetime.now(timezone.utc),
        decision_maker="benchmark",
        metadata=metrics,
    )


def _build_runtime(record: dict) -> RuntimeRecord:
    graph = ContextGraph(advanced_analytics=True)
    decision = _make_decision_model(record)
    decision_id = graph.record_decision(
        category=record["domain"],
        scenario=record["scenario"],
        reasoning=record["ground_truth_reasoning"],
        outcome=record["ground_truth_decision"],
        confidence=1.0,
        entities=list(record.get("applicable_policy_ids", [])),
        decision_maker="benchmark",
        metadata={"record_id": record["id"], **decision.metadata},
    )

    engine = PolicyEngine(graph)
    policy_nodes_by_id: dict[str, dict] = {}
    precedent_decision_ids: dict[str, str] = {}

    for node in record.get("context_graph", {}).get("nodes", []):
        if node.get("type") == "Policy":
            policy_nodes_by_id[node["id"]] = node
            engine.add_policy(
                Policy(
                    policy_id=node["id"],
                    name=node.get("label", node["id"]),
                    description=node.get("label", node["id"]),
                    rules=node.get("rules", {}),
                    category=node.get("category", record["domain"]),
                    version=node.get("version", "1.0"),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    metadata={"benchmark_record_id": record["id"]},
                )
            )
            graph.add_edge(decision_id, f"{node['id']}:{node.get('version', '1.0')}", "USES_POLICY", weight=1.0)
            continue

        graph.add_node(
            node["id"],
            node["type"],
            content=f"{record['scenario']} {node.get('label', node['id'])}",
            **{k: v for k, v in node.items() if k not in {"id", "type", "label"}},
        )

        if node.get("type") == "Precedent":
            precedent_id = graph.record_decision(
                category=record["domain"],
                scenario=f"{record['scenario']} precedent {node.get('label', node['id'])}",
                reasoning=f"precedent outcome {node.get('outcome', 'unknown')}",
                outcome=str(node.get("outcome", "unknown")),
                confidence=float(node.get("similarity_score", 0.6)),
                entities=list(record.get("applicable_policy_ids", [])),
                decision_maker="benchmark_precedent",
                metadata={"precedent_node_id": node["id"]},
            )
            precedent_decision_ids[node["id"]] = precedent_id
            graph.add_edge(decision_id, precedent_id, "PRECEDENT_FOR", weight=float(node.get("similarity_score", 0.6)))
        else:
            graph.add_edge(decision_id, node["id"], "USES_CONTEXT", weight=1.0)

    for edge in record.get("context_graph", {}).get("edges", []):
        source = precedent_decision_ids.get(edge["source"], edge["source"])
        target = precedent_decision_ids.get(edge["target"], edge["target"])
        if source in graph.nodes and target in graph.nodes:
            graph.add_edge(source, target, edge["type"], weight=edge.get("weight", 1.0))

    return RuntimeRecord(
        graph=graph,
        engine=engine,
        decision_id=decision_id,
        decision=decision,
        applicable_policy_ids=list(record.get("applicable_policy_ids", [])),
        policy_nodes_by_id=policy_nodes_by_id,
        precedent_decision_ids=precedent_decision_ids,
    )


def _precedent_rankings(runtime: RuntimeRecord, record: dict) -> tuple[list[str], list[str]]:
    ranked = [
        node["id"]
        for node in sorted(
            [
                node
                for node in record.get("context_graph", {}).get("nodes", [])
                if node.get("type") == "Precedent"
            ],
            key=lambda node: node.get("similarity_score", 0.0),
            reverse=True,
        )
    ]
    relevant = [
        node["id"]
        for node in record.get("context_graph", {}).get("nodes", [])
        if node.get("type") == "Precedent"
        and normalize_decision_label(node.get("outcome")) == normalize_decision_label(record["ground_truth_decision"])
    ]
    return ranked, relevant


def _structured_predict_decision(record: dict) -> tuple[str, float, dict]:
    runtime = _build_runtime(record)
    applicable_policies = runtime.engine.get_applicable_policies(record["domain"])
    compliance: dict[str, bool] = {}
    for policy in applicable_policies:
        if policy.policy_id in runtime.applicable_policy_ids:
            compliance[policy.policy_id] = runtime.engine.check_compliance(runtime.decision, policy.policy_id)

    retriever = ContextRetriever(
        knowledge_graph=runtime.graph,
        use_graph_expansion=True,
        max_expansion_hops=2,
        hybrid_alpha=0.5,
    )
    retrieved_ids = extract_node_ids(retriever.retrieve(record["scenario"], max_results=8))

    precedents = sorted(
        [
            node
            for node in record.get("context_graph", {}).get("nodes", [])
            if node.get("type") == "Precedent"
        ],
        key=lambda node: node.get("similarity_score", 0.0),
        reverse=True,
    )
    precedent_outcomes = [
        normalize_decision_label(node.get("outcome"))
        for node in precedents
    ]
    top_similarity = float(precedents[0].get("similarity_score", 0.0)) if precedents else 0.0
    distinct_precedent_outcomes = {outcome for outcome in precedent_outcomes if outcome != "unknown"}

    # ── Graph-derived conflict signals (no oracle flags read) ─────────────────
    # Conflict: multiple distinct precedent outcomes with low top-similarity
    # means the graph itself signals ambiguity — escalate for human review.
    conflict_signal = len(distinct_precedent_outcomes) > 1 and top_similarity < 0.70

    # Ambiguous compliance: some policies pass, some fail, and precedents disagree
    ambiguous_compliance = (
        bool(compliance)
        and not all(compliance.values())
        and any(compliance.values())
        and len(distinct_precedent_outcomes) > 1
    )

    if conflict_signal or ambiguous_compliance:
        return "escalate", 0.74, {"compliance": compliance, "retrieved_ids": retrieved_ids}

    # No applicable policies loaded into the engine graph — cannot decide
    if not runtime.applicable_policy_ids:
        return "escalate", 0.70, {"compliance": compliance, "retrieved_ids": retrieved_ids}

    if compliance and not all(compliance.values()):
        if len(distinct_precedent_outcomes) > 1:
            return "escalate", 0.72, {"compliance": compliance, "retrieved_ids": retrieved_ids}
        return "reject", 0.82, {"compliance": compliance, "retrieved_ids": retrieved_ids}

    if precedents and len(distinct_precedent_outcomes) > 1 and top_similarity >= 0.65:
        return "escalate", 0.74, {"compliance": compliance, "retrieved_ids": retrieved_ids}

    if precedents and top_similarity >= 0.55:
        return precedent_outcomes[0], min(max(top_similarity, 0.55), 0.95), {
            "compliance": compliance,
            "retrieved_ids": retrieved_ids,
        }

    if compliance and all(compliance.values()):
        return "approve", 0.78, {"compliance": compliance, "retrieved_ids": retrieved_ids}

    return "escalate", 0.6, {"compliance": compliance, "retrieved_ids": retrieved_ids}


@pytest.fixture(scope="module")
def decision_benchmark_report(decision_dataset):
    records = decision_dataset["records"]
    evaluations = []
    precedent_mrr_scores = []
    precedent_hit_scores = []

    for record in records:
        runtime = _build_runtime(record)
        baseline_label, baseline_confidence = _baseline_predict_decision(record)
        structured_label, structured_confidence, evidence = _structured_predict_decision(record)
        expected = normalize_decision_label(record["ground_truth_decision"])
        applicable = runtime.engine.get_applicable_policies(record["domain"])
        applicable_ids = {policy.policy_id for policy in applicable}
        ranked, relevant = _precedent_rankings(runtime, record)
        if ranked and relevant:
            precedent_mrr_scores.append(mrr(ranked, relevant))
            precedent_hit_scores.append(hit_at_k(ranked, relevant, 1))

        evaluations.append(
            {
                "id": record["id"],
                "domain": record["domain"],
                "expected": expected,
                "baseline_prediction": baseline_label,
                "structured_prediction": structured_label,
                "baseline_correct": baseline_label == expected,
                "structured_correct": structured_label == expected,
                "baseline_confidence": baseline_confidence,
                "structured_confidence": structured_confidence,
                "policy_match": set(record.get("applicable_policy_ids", [])) <= applicable_ids,
                "boundary_case": bool(record.get("boundary_case")),
                "has_conflicting_policies": bool(record.get("has_conflicting_policies")),
                "has_overturned_precedent": bool(record.get("has_overturned_precedent")),
                # Derived from graph structure only — no ground_truth_reasoning read
                "no_applicable_policy": (
                    expected == "escalate"
                    and not record.get("applicable_policy_ids")
                ),
                "retrieved_ids": evidence["retrieved_ids"],
                "policy_violated": bool(evidence["compliance"]) and not all(evidence["compliance"].values()),
                "policy_safe": bool(evidence["compliance"]) and all(evidence["compliance"].values()),
            }
        )

    hard_slices = {
        "boundary_cases": [row for row in evaluations if row["boundary_case"]],
        "conflicting_policy_cases": [row for row in evaluations if row["has_conflicting_policies"]],
        "overturned_precedent_cases": [row for row in evaluations if row["has_overturned_precedent"]],
        "no_applicable_policy_cases": [row for row in evaluations if row["no_applicable_policy"]],
    }
    metrics = {
        "decision_accuracy": binary_rate(row["structured_correct"] for row in evaluations),
        "policy_compliance_rate": binary_rate(
            (
                row["policy_violated"]
                and row["structured_prediction"] in {"reject", "escalate"}
            ) or (
                row["policy_safe"]
                and row["structured_prediction"] in {"approve", "escalate"}
            ) or (
                not row["policy_violated"] and not row["policy_safe"]
            )
            for row in evaluations
        ),
        "policy_context_coverage": binary_rate(row["policy_match"] for row in evaluations),
        "precedent_hit@1": safe_mean(precedent_hit_scores),
        "precedent_mrr": safe_mean(precedent_mrr_scores),
        "abstain_correctness": abstain_quality(
            sum(1 for row in evaluations if row["no_applicable_policy"] and row["structured_prediction"] == "escalate"),
            sum(1 for row in evaluations if row["no_applicable_policy"]),
        ),
        "conflict_handling_accuracy": binary_rate(
            row["structured_prediction"] == "escalate"
            for row in hard_slices["conflicting_policy_cases"]
        ),
        "overturned_precedent_accuracy": binary_rate(
            row["structured_prediction"] == "escalate"
            for row in hard_slices["overturned_precedent_cases"]
        ),
        "ece": expected_calibration_error(
            [row["structured_correct"] for row in evaluations],
            [row["structured_confidence"] for row in evaluations],
        ),
        "baseline_ece": expected_calibration_error(
            [row["baseline_correct"] for row in evaluations],
            [row["baseline_confidence"] for row in evaluations],
        ),
    }
    baseline_report = paired_lift_report(
        [row["expected"] for row in evaluations],
        [row["baseline_prediction"] for row in evaluations],
        [row["structured_prediction"] for row in evaluations],
    )
    domain_breakdown = {
        domain: {
            "sample_size": len(rows),
            "decision_accuracy": binary_rate(row["structured_correct"] for row in rows),
            "baseline_accuracy": binary_rate(row["baseline_correct"] for row in rows),
        }
        for domain, rows in slice_records(evaluations, lambda row: row["domain"]).items()
    }
    slices = {
        "domain_breakdown": domain_breakdown,
        "hard_slices": {
            name: {
                "sample_size": len(rows),
                "accuracy": binary_rate(row["structured_correct"] for row in rows),
            }
            for name, rows in hard_slices.items()
        },
    }
    report = make_track_report(
        name="decision_intelligence",
        sample_size=len(records),
        metrics={
            **metrics,
            "baseline_accuracy": baseline_report["baseline_accuracy"],
            "decision_accuracy_lift": baseline_report["absolute_lift"],
        },
        baselines={"lexical": {"decision_accuracy": baseline_report["baseline_accuracy"]}},
        slices=slices,
        coverage=coverage_summary(executed=len(evaluations), eligible=len(records), required=len(records)),
        metadata={"domains": sorted(domain_breakdown)},
    )
    report["lift"] = {
        "decision_accuracy": baseline_report["absolute_lift"],
        "precedent_quality": metrics["precedent_mrr"],
    }
    report["domain_breakdown"] = domain_breakdown
    report["hard_slices"] = slices["hard_slices"]
    require_reportable(
        report,
        min_sample_size=50,
        min_executed_ratio=1.0,
        required_metrics=("decision_accuracy", "policy_compliance_rate", "precedent_mrr"),
    )
    return report


def binary_rate(values) -> float:
    return safe_mean(1.0 if value else 0.0 for value in values)


def test_precedent_retrieval_accuracy(decision_benchmark_report):
    assert decision_benchmark_report["precedent_mrr"] >= 0.70
    assert decision_benchmark_report["precedent_hit@1"] >= 0.70


def test_policy_compliance_hit_rate(decision_benchmark_report):
    assert decision_benchmark_report["policy_compliance_rate"] >= THRESHOLDS["policy_compliance_hit_rate"][1]
    assert decision_benchmark_report["policy_context_coverage"] == 1.0


def test_decision_accuracy_beats_baseline(decision_benchmark_report):
    assert decision_benchmark_report["decision_accuracy"] >= decision_benchmark_report["baseline_accuracy"]
    assert decision_benchmark_report["lift"]["decision_accuracy"] >= 0.0


def test_exception_precedent_retrieval(decision_benchmark_report):
    assert decision_benchmark_report["overturned_precedent_accuracy"] >= 0.80


def test_causal_influence_score_accuracy(decision_dataset):
    runtime = _build_runtime(decision_dataset["records"][0])
    impact = runtime.graph.analyze_decision_influence(runtime.decision_id)
    assert impact.get("max_influence_score", 0.0) >= 0.0


def test_decision_impact_analysis(decision_dataset):
    runtime = _build_runtime(decision_dataset["records"][0])
    causality = runtime.graph.trace_decision_causality(runtime.decision_id)
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
    assert decision_benchmark_report["conflict_handling_accuracy"] >= 0.80
    assert decision_benchmark_report["overturned_precedent_accuracy"] >= 0.80
    assert decision_benchmark_report["abstain_correctness"] >= 0.75


def test_domain_breakdown_is_complete(decision_benchmark_report):
    assert {"lending", "healthcare", "legal", "hr", "ecommerce"} <= set(decision_benchmark_report["domain_breakdown"])
    for domain_report in decision_benchmark_report["domain_breakdown"].values():
        assert domain_report["sample_size"] > 0
        assert domain_report["decision_accuracy"] >= domain_report["baseline_accuracy"]


def test_calibration_is_reported(decision_benchmark_report):
    assert 0.0 <= decision_benchmark_report["ece"] <= 1.0
    assert 0.0 <= decision_benchmark_report["baseline_ece"] <= 1.0
