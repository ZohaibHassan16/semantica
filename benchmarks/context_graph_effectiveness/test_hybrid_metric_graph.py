"""
Track 23 - Metric-Graph Hybrid Reasoning
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks.context_graph_effectiveness.metrics import absolute_lift, safe_mean, slice_records
from semantica.context import ContextGraph

FIXTURES = Path(__file__).parent / "fixtures" / "semantic_layer"


def _load(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def hybrid_dataset():
    return _load("hybrid_metric_graph.json")["records"]


def _build_hybrid_graph(record: dict) -> ContextGraph:
    graph = ContextGraph()
    metric = record["metric"]
    graph.add_node(
        metric["name"],
        "Metric",
        metric["name"],
        observed_value=str(metric.get("observed_value", "")),
        policy_threshold=str(metric.get("policy_threshold", "")),
        compliant=str(metric.get("compliant", "")),
    )

    for node_id in record.get("causal_nodes", []):
        graph.add_node(node_id, "Decision", node_id)
        graph.add_edge(metric["name"], node_id, "AFFECTED_BY", 1.0)
    for edge in record.get("causal_edges", []):
        graph.add_edge(edge["from"], edge["to"], "CAUSED", 1.0)
    for policy_id in record.get("policy_nodes", []):
        graph.add_node(policy_id, "Policy", policy_id)
        graph.add_edge(metric["name"], policy_id, "GOVERNED_BY", 1.0)

    temporal_window = record.get("temporal_window", {})
    if temporal_window:
        window_id = f"{metric['name']}_window"
        graph.add_node(
            window_id,
            "TemporalWindow",
            "valid period",
            valid_from=temporal_window.get("valid_from", ""),
            valid_until=temporal_window.get("valid_until", ""),
        )
        graph.add_edge(metric["name"], window_id, "VALID_DURING", 1.0)
    return graph


def _bfs_reachable(graph: ContextGraph, start: str, max_hops: int = 5) -> set[str]:
    visited = {start}
    frontier = {start}
    for _ in range(max_hops):
        if not frontier:
            break
        next_frontier: set[str] = set()
        for node_id in frontier:
            neighbors = set(graph.get_neighbor_ids(node_id) or [])
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(str(neighbor))
        frontier = next_frontier
    return visited


def _flat_metric_text_baseline(record: dict) -> set[str]:
    metric = record["metric"]["name"]
    reachable = set(record.get("policy_nodes", []))
    if "ratio" in metric or "revenue" in metric or "rate" in metric:
        reachable |= set(record.get("causal_nodes", [])[:1])
    return reachable


@pytest.fixture(scope="module")
def hybrid_metric_report(hybrid_dataset):
    per_record = []
    for record in hybrid_dataset:
        graph = _build_hybrid_graph(record)
        metric_name = record["metric"]["name"]
        reachable = _bfs_reachable(graph, metric_name)
        target_ids = set(record.get("causal_nodes", [])) | set(record.get("policy_nodes", []))
        baseline_reachable = _flat_metric_text_baseline(record)

        hybrid_recall = len(reachable & target_ids) / len(target_ids) if target_ids else 0.0
        baseline_recall = len(baseline_reachable & target_ids) / len(target_ids) if target_ids else 0.0
        causal_root_accuracy = 1.0 if record.get("gold_causal_root") in reachable else 0.0
        policy_linkage = 1.0 if set(record.get("policy_nodes", [])) & reachable else 0.0
        gold_policy_reachable = 1.0 if record.get("gold_policy_applicable") in reachable else 0.0

        metric_payload = record["metric"]
        policy_metric_compliance = 1.0
        if "policy_threshold" in metric_payload and "compliant" in metric_payload:
            observed = float(metric_payload.get("observed_value", 0))
            threshold = float(metric_payload["policy_threshold"])
            predicted = observed >= threshold
            policy_metric_compliance = 1.0 if predicted == metric_payload["compliant"] else 0.0

        per_record.append(
            {
                "id": record["id"],
                "metric_name": metric_name,
                "hybrid_recall": hybrid_recall,
                "baseline_recall": baseline_recall,
                "causal_root_accuracy": causal_root_accuracy,
                "policy_metric_compliance": policy_metric_compliance,
                "metric_policy_linkage_rate": policy_linkage,
                "gold_policy_reachable": gold_policy_reachable,
                "buildable": 1.0 if (graph.find_nodes() or []) else 0.0,
            }
        )

    metric_slices = {
        metric_name: {
            "sample_size": len(rows),
            "hybrid_recall": safe_mean(row["hybrid_recall"] for row in rows),
            "causal_root_accuracy": safe_mean(row["causal_root_accuracy"] for row in rows),
        }
        for metric_name, rows in slice_records(per_record, lambda row: row["metric_name"]).items()
    }

    return {
        "sample_size": len(per_record),
        "hybrid_recall": safe_mean(row["hybrid_recall"] for row in per_record),
        "baseline_recall": safe_mean(row["baseline_recall"] for row in per_record),
        "policy_metric_compliance": safe_mean(row["policy_metric_compliance"] for row in per_record),
        "causal_root_accuracy": safe_mean(row["causal_root_accuracy"] for row in per_record),
        "metric_policy_linkage_rate": safe_mean(row["metric_policy_linkage_rate"] for row in per_record),
        "hybrid_graph_coverage": safe_mean(row["buildable"] for row in per_record),
        "gold_policy_reachable": safe_mean(row["gold_policy_reachable"] for row in per_record),
        "metric_slices": metric_slices,
        "lift": {
            "hybrid_recall_vs_flat_text": absolute_lift(
                safe_mean(row["hybrid_recall"] for row in per_record),
                safe_mean(row["baseline_recall"] for row in per_record),
            )
        },
    }


class TestHybridMetricGraph:
    def test_hybrid_recall(self, hybrid_metric_report):
        assert hybrid_metric_report["hybrid_recall"] >= 0.75

    def test_policy_metric_compliance(self, hybrid_metric_report):
        assert hybrid_metric_report["policy_metric_compliance"] >= 0.85

    def test_causal_root_accuracy(self, hybrid_metric_report):
        assert hybrid_metric_report["causal_root_accuracy"] >= 0.70

    def test_metric_policy_linkage_rate(self, hybrid_metric_report):
        assert hybrid_metric_report["metric_policy_linkage_rate"] >= 0.90

    def test_hybrid_graph_coverage(self, hybrid_metric_report):
        assert hybrid_metric_report["hybrid_graph_coverage"] >= 0.80

    def test_gold_policy_reachable(self, hybrid_metric_report):
        assert hybrid_metric_report["gold_policy_reachable"] >= 0.80

    def test_hybrid_graph_beats_flat_metric_baseline(self, hybrid_metric_report):
        assert hybrid_metric_report["hybrid_recall"] >= hybrid_metric_report["baseline_recall"]
        assert hybrid_metric_report["lift"]["hybrid_recall_vs_flat_text"] >= 0.0

    def test_metric_slices_are_reported(self, hybrid_metric_report):
        assert hybrid_metric_report["sample_size"] > 0
        assert "total_revenue" in hybrid_metric_report["metric_slices"]
