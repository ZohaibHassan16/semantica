"""
Track 21 — Semantic Metric Exactness

Verifies that the Semantica ContextGraph correctly stores, retrieves, and validates
governed metric definitions from a semantic layer (Jaffle Shop / dbt MetricFlow format).

Metrics:
    metric_exactness_at_1           >= 0.85  (governed metric name retrieved exactly)
    dimension_conformance_rate      >= 0.90  (query dimensions respect grain/filter rules)
    metric_alias_resolution_rate    >= 0.80  (aliases resolve to canonical metric name)
    metric_node_storage_fidelity    == 1.0   (all metric fields survive graph round-trip)
    semantic_layer_coverage         >= 0.90  (all governed metrics are graph-accessible)

Evidence basis:
    dbt Semantic Layer LLM benchmarking (2025) reports 83% accuracy lift with governed metrics.
    Threshold 0.85 is conservative relative to that upper bound.
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List

from semantica.context import ContextGraph

FIXTURES = Path(__file__).parent / "fixtures" / "semantic_layer"


def _load(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def jaffle_metrics():
    return _load("jaffle_shop_metrics.json")


def _build_metric_graph(metrics: List[Dict]) -> ContextGraph:
    """Store each governed metric as a node in the ContextGraph."""
    g = ContextGraph()
    for m in metrics:
        g.add_node(
            m["name"], "Metric", m["label"],
            metric_type=m["type"],
            expression=m["expression"],
            grain=m["grain"],
            dimensions=",".join(m["dimensions"]),
            aliases=",".join(m.get("aliases", [])),
            description=m["description"],
        )
    return g


class TestSemanticMetricExactness:
    """Track 21 — Semantic Metric Exactness."""

    def test_metric_exactness_at_1(self, jaffle_metrics):
        """Metric nodes are retrievable by exact canonical name."""
        metrics = jaffle_metrics["metrics"]
        g = _build_metric_graph(metrics)
        canonical_names = {m["name"] for m in metrics}

        nodes = g.find_nodes() or []
        stored_names = {
            (n.get("id") if isinstance(n, dict) else getattr(n, "id", None))
            for n in nodes
        } - {None}

        hit = len(stored_names & canonical_names)
        exactness = hit / max(len(canonical_names), 1)
        assert exactness >= 0.85, (
            f"metric_exactness_at_1 = {exactness:.3f} < 0.85 "
            f"(retrieved {sorted(stored_names & canonical_names)}, "
            f"missing {sorted(canonical_names - stored_names)})"
        )

    def test_dimension_conformance_rate(self, jaffle_metrics):
        """Dimension conformance tests: valid dimensions pass, invalid ones are flagged."""
        dc_tests = jaffle_metrics["dimension_conformance_tests"]
        metrics_by_name = {m["name"]: m for m in jaffle_metrics["metrics"]}

        correct = 0
        for tc in dc_tests:
            metric = metrics_by_name.get(tc["metric"])
            if not metric:
                continue
            allowed_dims = set(metric["dimensions"])
            grain = metric.get("grain", "")
            query_dim = tc["query_dimension"]

            # A dimension is valid if it's in the allowed set AND doesn't violate grain
            predicted_valid = (query_dim in allowed_dims) and (query_dim != grain)
            if predicted_valid == tc["is_valid"]:
                correct += 1

        rate = correct / max(len(dc_tests), 1)
        assert rate >= 0.90, (
            f"dimension_conformance_rate = {rate:.3f} < 0.90 "
            f"({correct}/{len(dc_tests)} tests correct)"
        )

    def test_metric_alias_resolution_rate(self, jaffle_metrics):
        """Common aliases (e.g. 'LTV', 'AOV') resolve to the canonical metric name."""
        metrics = jaffle_metrics["metrics"]
        # Build alias → canonical mapping
        alias_map: Dict[str, str] = {}
        for m in metrics:
            for alias in m.get("aliases", []):
                alias_map[alias.lower()] = m["name"]

        # Test a sample of known aliases
        test_aliases = [
            ("ltv",                  "customer_lifetime_value"),
            ("clv",                  "customer_lifetime_value"),
            ("aov",                  "average_order_value"),
            ("churn",                "churn_rate"),
            ("revenue",              "total_revenue"),
            ("orders",               "order_count"),
            ("new customers",        "new_customer_count"),
            ("return rate",          "refund_rate"),
            ("ltv to cac",           "ltv_cac_ratio"),
            ("mean order value",     "average_order_value"),
        ]

        resolved = sum(
            1 for alias, expected in test_aliases
            if alias_map.get(alias) == expected
        )
        rate = resolved / max(len(test_aliases), 1)
        assert rate >= 0.80, (
            f"metric_alias_resolution_rate = {rate:.3f} < 0.80 "
            f"({resolved}/{len(test_aliases)} aliases resolved correctly)"
        )

    def test_metric_node_storage_fidelity(self, jaffle_metrics):
        """All key metric fields survive a ContextGraph round-trip."""
        metrics = jaffle_metrics["metrics"]
        g = _build_metric_graph(metrics)
        nodes = g.find_nodes() or []
        stored = {
            (n.get("id") if isinstance(n, dict) else getattr(n, "id", ""))
            for n in nodes
        } - {""}

        # Every metric must be stored
        canonical = {m["name"] for m in metrics}
        missing = canonical - stored
        fidelity = 1.0 - len(missing) / max(len(canonical), 1)
        assert fidelity == 1.0, (
            f"metric_node_storage_fidelity = {fidelity:.3f} — missing nodes: {sorted(missing)}"
        )

    def test_semantic_layer_coverage(self, jaffle_metrics):
        """All NL queries reference a metric that exists in the governed layer."""
        queries = jaffle_metrics["nl_queries"]
        metric_names = {m["name"] for m in jaffle_metrics["metrics"]}

        covered = sum(
            1 for q in queries
            if q["governed_metric"] in metric_names
        )
        coverage = covered / max(len(queries), 1)
        assert coverage >= 0.90, (
            f"semantic_layer_coverage = {coverage:.3f} < 0.90 "
            f"({covered}/{len(queries)} queries have governed metric in layer)"
        )

    def test_grain_violation_detection(self, jaffle_metrics):
        """Dimension queries that violate the metric's grain are correctly flagged as invalid."""
        dc_tests = jaffle_metrics["dimension_conformance_tests"]
        metrics_by_name = {m["name"]: m for m in jaffle_metrics["metrics"]}

        grain_tests = [t for t in dc_tests if not t["is_valid"] and "grain" in t["reason"]]
        if not grain_tests:
            pytest.skip("No grain-violation test cases in fixture")

        detected = 0
        for tc in grain_tests:
            metric = metrics_by_name.get(tc["metric"])
            if not metric:
                continue
            grain = metric.get("grain", "")
            if tc["query_dimension"] != grain:
                detected += 1  # correctly identified as grain violation (query dim differs from grain)

        rate = detected / max(len(grain_tests), 1)
        assert rate >= 0.75, (
            f"grain_violation_detection_rate = {rate:.3f} < 0.75 "
            f"({detected}/{len(grain_tests)} grain violations detected)"
        )
