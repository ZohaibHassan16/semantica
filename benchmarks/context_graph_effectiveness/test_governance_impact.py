"""
Track 24 - Governance Impact and Change Propagation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks.context_graph_effectiveness.metrics import absolute_lift, safe_mean, slice_records
from semantica.context import ContextGraph

try:
    from semantica.kg.version_manager import VersionManager

    _HAS_VERSION_MANAGER = True
except ImportError:
    _HAS_VERSION_MANAGER = False

FIXTURES = Path(__file__).parent / "fixtures" / "semantic_layer"


def _load(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def change_pairs():
    data = _load("metric_change_pairs.json")
    return data["records"], data["policy_decision_registry"]


def _build_decision_graph(registry: dict, metric_name: str) -> ContextGraph:
    graph = ContextGraph()
    graph.add_node(metric_name, "Metric", metric_name)
    for decision_id, policy in registry.items():
        if policy["metric"] == metric_name:
            graph.add_node(
                decision_id,
                "Decision",
                decision_id,
                condition=policy["condition"],
                value=str(policy["value"]),
            )
            graph.add_edge(metric_name, decision_id, "GOVERNS", 1.0)
    return graph


def _baseline_neighbors(registry: dict, metric_name: str) -> set[str]:
    return {decision_id for decision_id, policy in registry.items() if policy["metric"] == metric_name}


@pytest.fixture(scope="module")
def governance_impact_report(change_pairs):
    records, registry = change_pairs
    per_record = []

    for record in records:
        metric_name = record["metric_name"]
        graph = _build_decision_graph(registry, metric_name)
        graph_neighbors = set(graph.get_neighbor_ids(metric_name) or [])
        baseline = _baseline_neighbors(registry, metric_name)
        affected_gold = set(record["affected_decisions"])
        unaffected_gold = set(record["unaffected_decisions"])

        impact_score = len(graph_neighbors & affected_gold) / len(affected_gold) if affected_gold else 0.0
        impact_precision = len(graph_neighbors & affected_gold) / len(graph_neighbors) if graph_neighbors else 0.0
        decision_drift_rate = len(graph_neighbors & unaffected_gold) / len(unaffected_gold) if unaffected_gold else 0.0
        baseline_impact = len(baseline & affected_gold) / len(affected_gold) if affected_gold else 0.0

        per_record.append(
            {
                "id": record["id"],
                "change_type": record["change_type"],
                "impact_score": impact_score,
                "impact_precision": impact_precision,
                "decision_drift_rate": decision_drift_rate,
                "baseline_impact": baseline_impact,
            }
        )

    change_type_breakdown = {
        change_type: {
            "sample_size": len(rows),
            "impact_score": safe_mean(row["impact_score"] for row in rows),
            "impact_precision": safe_mean(row["impact_precision"] for row in rows),
        }
        for change_type, rows in slice_records(per_record, lambda row: row["change_type"]).items()
    }

    return {
        "sample_size": len(per_record),
        "metric_change_impact_score": safe_mean(row["impact_score"] for row in per_record),
        "decision_drift_rate": safe_mean(row["decision_drift_rate"] for row in per_record),
        "impact_precision": safe_mean(row["impact_precision"] for row in per_record),
        "change_type_coverage": len(change_type_breakdown) / 8.0,
        "baseline_impact_score": safe_mean(row["baseline_impact"] for row in per_record),
        "change_type_breakdown": change_type_breakdown,
        "lift": {
            "impact_score_vs_baseline": absolute_lift(
                safe_mean(row["impact_score"] for row in per_record),
                safe_mean(row["baseline_impact"] for row in per_record),
            )
        },
    }


class TestGovernanceImpact:
    def test_metric_change_impact_score(self, governance_impact_report):
        assert governance_impact_report["metric_change_impact_score"] >= 0.95

    def test_decision_drift_rate(self, governance_impact_report):
        assert governance_impact_report["decision_drift_rate"] <= 0.02

    def test_change_type_coverage(self, governance_impact_report):
        assert governance_impact_report["change_type_coverage"] >= 0.80

    def test_impact_precision(self, governance_impact_report):
        assert governance_impact_report["impact_precision"] >= 0.85

    def test_change_breakdown_is_reported(self, governance_impact_report):
        assert governance_impact_report["sample_size"] >= 8
        assert "expression_and_filter" in governance_impact_report["change_type_breakdown"]

    def test_graph_impact_matches_or_beats_baseline(self, governance_impact_report):
        assert governance_impact_report["metric_change_impact_score"] >= governance_impact_report["baseline_impact_score"]

    @pytest.mark.skipif(not _HAS_VERSION_MANAGER, reason="VersionManager not available")
    def test_version_snapshot_fidelity(self, change_pairs):
        records, registry = change_pairs
        record = records[0]
        metric_name = record["metric_name"]

        version_manager = VersionManager()
        graph = _build_decision_graph(registry, metric_name)
        before = version_manager.create_snapshot(graph, label="before_change", author="test")
        assert before is not None

        graph.add_node(
            metric_name,
            "Metric",
            f"{metric_name} (updated)",
            expression=record["version_after"].get("expression", ""),
        )
        after = version_manager.create_snapshot(graph, label="after_change", author="test")
        assert after is not None
        assert before != after or before.get("checksum") != after.get("checksum")
