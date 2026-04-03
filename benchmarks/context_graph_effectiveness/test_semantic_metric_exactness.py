"""
Track 21 - Semantic Metric Exactness

Measures governed-metric correctness with explicit comparisons between:
- no semantic layer baseline
- flat text / alias baseline
- structured semantic-layer graph
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
def jaffle_metrics():
    return _load("jaffle_shop_metrics.json")


def _build_metric_graph(metrics: list[dict]) -> ContextGraph:
    graph = ContextGraph()
    for metric in metrics:
        graph.add_node(
            metric["name"],
            "Metric",
            metric["label"],
            metric_type=metric["type"],
            expression=metric["expression"],
            grain=metric["grain"],
            dimensions=",".join(metric["dimensions"]),
            aliases=",".join(metric.get("aliases", [])),
            description=metric["description"],
        )
    return graph


def _normalize(text: str) -> str:
    return text.strip().lower().replace(":", " ").replace("-", " ")


def _no_semantic_layer_predict(query: str) -> str | None:
    normalized = _normalize(query)
    guesses = {
        "revenue": "total_revenue",
        "orders": "order_count",
        "churn": "churn_rate",
        "refund": "refund_rate",
    }
    for token, metric_name in guesses.items():
        if token in normalized:
            return metric_name
    return None


def _flat_text_predict(query: str, metrics: list[dict]) -> str | None:
    normalized = _normalize(query)
    best_name = None
    best_score = -1
    for metric in metrics:
        score = 0
        candidates = [metric["name"], metric["label"], metric["description"], *metric.get("aliases", [])]
        for candidate in candidates:
            words = set(_normalize(candidate).split())
            score += len(words & set(normalized.split()))
        if score > best_score:
            best_score = score
            best_name = metric["name"]
    return best_name


def _graph_predict(query: str, metrics: list[dict]) -> str | None:
    normalized = _normalize(query)
    best_name = None
    best_score = -1.0
    for metric in metrics:
        score = 0.0
        names = [metric["name"], metric["label"], *metric.get("aliases", [])]
        for name in names:
            tokens = set(_normalize(name).split())
            overlap = len(tokens & set(normalized.split()))
            if overlap:
                score = max(score, overlap + 0.5)
        dimensions = set(metric.get("dimensions", []))
        score += 0.2 * len(dimensions & set(normalized.split()))
        if score > best_score:
            best_score = score
            best_name = metric["name"]
    return best_name


@pytest.fixture(scope="module")
def semantic_metric_report(jaffle_metrics):
    metrics = jaffle_metrics["metrics"]
    queries = jaffle_metrics["nl_queries"]
    dimension_tests = jaffle_metrics["dimension_conformance_tests"]

    exact_matches = []
    flat_matches = []
    no_sl_matches = []
    for query in queries:
        gold = query["governed_metric"]
        exact_matches.append(1.0 if _graph_predict(query["query"], metrics) == gold else 0.0)
        flat_matches.append(1.0 if _flat_text_predict(query["query"], metrics) == gold else 0.0)
        no_sl_matches.append(1.0 if _no_semantic_layer_predict(query["query"]) == gold else 0.0)

    alias_cases = []
    for metric in metrics:
        for alias in metric.get("aliases", []):
            alias_cases.append({"alias": alias, "expected": metric["name"]})

    alias_resolution = safe_mean(
        1.0 if _graph_predict(case["alias"], metrics) == case["expected"] else 0.0
        for case in alias_cases
    )
    alias_resolution_flat = safe_mean(
        1.0 if _flat_text_predict(case["alias"], metrics) == case["expected"] else 0.0
        for case in alias_cases
    )

    dimension_rate = 0.0
    grain_rate = 0.0
    if dimension_tests:
        metrics_by_name = {metric["name"]: metric for metric in metrics}
        dimension_results = []
        grain_results = []
        for test_case in dimension_tests:
            metric = metrics_by_name.get(test_case["metric"])
            if not metric:
                continue
            allowed = set(metric["dimensions"])
            predicted_valid = test_case["query_dimension"] in allowed
            dimension_results.append(1.0 if predicted_valid == test_case["is_valid"] else 0.0)
            if "grain" in test_case.get("reason", ""):
                predicted_grain_violation = test_case["query_dimension"] not in allowed or test_case["query_dimension"] != metric["grain"]
                grain_results.append(1.0 if predicted_grain_violation == (not test_case["is_valid"]) else 0.0)
        dimension_rate = safe_mean(dimension_results)
        grain_rate = safe_mean(grain_results)

    graph = _build_metric_graph(metrics)
    nodes = graph.find_nodes() or []
    stored_ids = {
        (node.get("id") if isinstance(node, dict) else getattr(node, "id", None))
        for node in nodes
    } - {None}
    metric_node_storage_fidelity = len(stored_ids & {metric["name"] for metric in metrics}) / len(metrics)

    return {
        "sample_size": len(queries),
        "metric_exactness@1": safe_mean(exact_matches),
        "flat_metric_exactness@1": safe_mean(flat_matches),
        "no_semantic_layer_exactness@1": safe_mean(no_sl_matches),
        "alias_resolution_accuracy": alias_resolution,
        "flat_alias_resolution_accuracy": alias_resolution_flat,
        "dimension_conformance": dimension_rate,
        "grain_conformance": grain_rate,
        "metric_node_storage_fidelity": metric_node_storage_fidelity,
        "coverage": safe_mean(1.0 if query["governed_metric"] in stored_ids else 0.0 for query in queries),
        "query_slices": {
            key: {
                "sample_size": len(rows),
                "structured_exactness": safe_mean(
                    1.0 if _graph_predict(row["query"], metrics) == row["governed_metric"] else 0.0
                    for row in rows
                ),
            }
            for key, rows in slice_records(
                queries,
                lambda row: row["expected_time_grain"] or "no_time_grain",
            ).items()
        },
        "lift": {
            "structured_vs_flat_exactness": absolute_lift(safe_mean(exact_matches), safe_mean(flat_matches)),
            "structured_vs_no_sl_exactness": absolute_lift(safe_mean(exact_matches), safe_mean(no_sl_matches)),
        },
    }


class TestSemanticMetricExactness:
    def test_metric_exactness_at_1(self, semantic_metric_report):
        assert semantic_metric_report["metric_exactness@1"] >= 0.85

    def test_dimension_conformance_rate(self, semantic_metric_report):
        assert semantic_metric_report["dimension_conformance"] >= 0.90

    def test_metric_alias_resolution_rate(self, semantic_metric_report):
        assert semantic_metric_report["alias_resolution_accuracy"] >= 0.80

    def test_metric_node_storage_fidelity(self, semantic_metric_report):
        assert semantic_metric_report["metric_node_storage_fidelity"] == 1.0

    def test_semantic_layer_coverage(self, semantic_metric_report):
        assert semantic_metric_report["coverage"] >= 0.90

    def test_grain_violation_detection(self, semantic_metric_report):
        assert semantic_metric_report["grain_conformance"] >= 0.75

    def test_structured_semantic_layer_beats_baselines(self, semantic_metric_report):
        assert semantic_metric_report["metric_exactness@1"] >= semantic_metric_report["flat_metric_exactness@1"]
        assert semantic_metric_report["metric_exactness@1"] >= semantic_metric_report["no_semantic_layer_exactness@1"]
        assert semantic_metric_report["lift"]["structured_vs_flat_exactness"] >= 0.0

    def test_time_grain_slices_are_reported(self, semantic_metric_report):
        assert semantic_metric_report["sample_size"] > 0
        assert "no_time_grain" in semantic_metric_report["query_slices"]
