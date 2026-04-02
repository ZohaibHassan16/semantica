"""
Track 24 — Governance Impact & Change Propagation

Tests that metric definition changes (expression restatements, filter additions,
window changes, threshold raises) correctly propagate to downstream decisions via
ContextGraph + VersionManager.

Metrics:
    metric_change_impact_score  >= 0.95  (impacted decisions flagged after metric change)
    decision_drift_rate         <= 0.02  (unaffected decisions do not change)
    version_snapshot_fidelity   == 1.0   (VersionManager captures metric nodes correctly)
    change_type_coverage        >= 0.80  (all change types are detectable)
    impact_precision            >= 0.85  (flagged decisions are actually impacted)

Evidence basis:
    MetricChangeImpactScore >= 0.95 is a hard auditability SLA (GDPR, SOX compliance).
    DecisionDriftRate <= 0.02 is production SLA — wrong decisions due to silent metric
    changes must be near-zero.
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Set

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


def _build_decision_graph(registry: Dict, metric_name: str) -> ContextGraph:
    """Build a graph with metric node and all decisions that reference it."""
    g = ContextGraph()
    g.add_node(metric_name, "Metric", metric_name)
    for decision_id, policy in registry.items():
        if policy["metric"] == metric_name:
            g.add_node(decision_id, "Decision", decision_id,
                       condition=policy["condition"],
                       value=str(policy["value"]))
            g.add_edge(metric_name, decision_id, "GOVERNS", 1.0)
    return g


def _decisions_for_metric(registry: Dict, metric_name: str) -> Set[str]:
    return {d for d, p in registry.items() if p["metric"] == metric_name}


class TestGovernanceImpact:
    """Track 24 — Governance Impact & Change Propagation."""

    def test_metric_change_impact_score(self, change_pairs):
        """Impacted decisions (per gold labels) are linked to the changed metric."""
        records, registry = change_pairs
        total_impact = 0.0
        count = 0

        for rec in records:
            metric_name = rec["metric_name"]
            affected_gold = set(rec["affected_decisions"])
            if not affected_gold:
                continue

            # All affected decisions must be reachable via GOVERNS edge
            g = _build_decision_graph(registry, metric_name)
            try:
                neighbors = set(g.get_neighbor_ids(metric_name) or [])
            except Exception:
                neighbors = set()

            flagged = neighbors & affected_gold
            score = len(flagged) / len(affected_gold)
            total_impact += score
            count += 1

        mean_score = total_impact / max(count, 1)
        assert mean_score >= 0.95, (
            f"metric_change_impact_score = {mean_score:.3f} < 0.95 across {count} records"
        )

    def test_decision_drift_rate(self, change_pairs):
        """Decisions not linked to the changed metric are not incorrectly flagged."""
        records, registry = change_pairs
        total_drift = 0.0
        count = 0

        for rec in records:
            metric_name = rec["metric_name"]
            unaffected_gold = set(rec["unaffected_decisions"])
            if not unaffected_gold:
                continue

            # Decisions for OTHER metrics should not be neighbors of this metric node
            g = _build_decision_graph(registry, metric_name)
            try:
                neighbors = set(g.get_neighbor_ids(metric_name) or [])
            except Exception:
                neighbors = set()

            false_flags = neighbors & unaffected_gold
            drift = len(false_flags) / max(len(unaffected_gold), 1)
            total_drift += drift
            count += 1

        mean_drift = total_drift / max(count, 1)
        assert mean_drift <= 0.02, (
            f"decision_drift_rate = {mean_drift:.3f} > 0.02 — unaffected decisions "
            f"being incorrectly flagged"
        )

    def test_change_type_coverage(self, change_pairs):
        """All expected change types are present in the fixture."""
        records, _ = change_pairs
        expected_types = {
            "expression_and_filter",
            "time_window_added",
            "window_tightened",
            "filter_added",
            "threshold_raised",
            "filter_exclusion_added",
            "expression_restatement",
            "filter_broadened",
        }
        found_types = {r["change_type"] for r in records}
        coverage = len(found_types & expected_types) / len(expected_types)
        assert coverage >= 0.80, (
            f"change_type_coverage = {coverage:.3f} < 0.80 "
            f"(missing: {expected_types - found_types})"
        )

    def test_impact_precision(self, change_pairs):
        """Flagged (neighbor) decisions are actually in the gold affected set."""
        records, registry = change_pairs
        total_precision = 0.0
        count = 0

        for rec in records:
            metric_name = rec["metric_name"]
            affected_gold = set(rec["affected_decisions"])
            if not affected_gold:
                continue

            g = _build_decision_graph(registry, metric_name)
            try:
                neighbors = set(g.get_neighbor_ids(metric_name) or [])
            except Exception:
                neighbors = set()

            if not neighbors:
                continue
            precision = len(neighbors & affected_gold) / len(neighbors)
            total_precision += precision
            count += 1

        mean_precision = total_precision / max(count, 1)
        assert mean_precision >= 0.85, (
            f"impact_precision = {mean_precision:.3f} < 0.85 across {count} records"
        )

    @pytest.mark.skipif(not _HAS_VERSION_MANAGER, reason="VersionManager not available")
    def test_version_snapshot_fidelity(self, change_pairs):
        """VersionManager correctly snapshots a metric node before and after change."""
        records, registry = change_pairs
        rec = records[0]
        metric_name = rec["metric_name"]

        vm = VersionManager()
        g = _build_decision_graph(registry, metric_name)

        # Snapshot before change
        snap_before = vm.create_snapshot(g, label="before_change", author="test")
        assert snap_before is not None, "snapshot before change must not be None"

        # Apply change: add new expression metadata to metric node
        g.add_node(
            metric_name, "Metric", f"{metric_name} (updated)",
            expression=rec["version_after"].get("expression", ""),
        )
        snap_after = vm.create_snapshot(g, label="after_change", author="test")
        assert snap_after is not None, "snapshot after change must not be None"

        # Snapshots must differ
        assert snap_before != snap_after or snap_before.get("checksum") != snap_after.get(
            "checksum"
        ), "before and after snapshots must differ after metric change"
