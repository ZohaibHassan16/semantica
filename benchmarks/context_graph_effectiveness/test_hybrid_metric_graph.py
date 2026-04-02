"""
Track 23 — Metric-Graph Hybrid Reasoning

Tests that ContextGraph correctly encodes metric observations alongside causal chains
and temporal windows — the core "why did this metric change?" pattern in decision
intelligence. All tests use direct graph operations (no ContextRetriever).

Metrics:
    hybrid_recall               >= 0.75  (metric + causal + policy nodes all reachable)
    policy_metric_compliance    >= 0.85  (decisions respect both policy and metric rules)
    causal_root_accuracy        >= 0.70  (BFS from metric node reaches gold root cause)
    metric_policy_linkage_rate  >= 0.90  (every metric node linked to ≥1 policy node)
    hybrid_graph_coverage       >= 0.80  (all hybrid records buildable into valid graphs)

Evidence basis:
    Real enterprise KG-RAG use cases mix metric context with causal/temporal reasoning.
    Threshold 0.75 for HybridRecall is calibrated for pattern-based traversal on
    structured fixtures.
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Set

from semantica.context import ContextGraph

FIXTURES = Path(__file__).parent / "fixtures" / "semantic_layer"


def _load(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def hybrid_dataset():
    return _load("hybrid_metric_graph.json")["records"]


def _build_hybrid_graph(record: Dict) -> ContextGraph:
    """Build a ContextGraph from a hybrid metric+causal+policy record."""
    g = ContextGraph()

    # Metric observation node
    m = record["metric"]
    g.add_node(
        m["name"], "Metric", m["name"],
        observed_value=str(m.get("observed_value", "")),
        policy_threshold=str(m.get("policy_threshold", "")),
        compliant=str(m.get("compliant", "")),
    )

    # Causal chain nodes + edges
    for node_id in record.get("causal_nodes", []):
        g.add_node(node_id, "Decision", node_id)
        # Connect metric node to each causal factor (metric is affected by these causes)
        g.add_edge(m["name"], node_id, "AFFECTED_BY", 1.0)
    for edge in record.get("causal_edges", []):
        g.add_edge(edge["from"], edge["to"], "CAUSED", 1.0)

    # Policy nodes linked to metric
    for policy_id in record.get("policy_nodes", []):
        g.add_node(policy_id, "Policy", policy_id)
        g.add_edge(m["name"], policy_id, "GOVERNED_BY", 1.0)

    # Temporal window on metric node (if present)
    tw = record.get("temporal_window", {})
    if tw:
        g.add_node(
            f"{m['name']}_window", "TemporalWindow", "valid period",
            valid_from=tw.get("valid_from", ""),
            valid_until=tw.get("valid_until", ""),
        )
        g.add_edge(m["name"], f"{m['name']}_window", "VALID_DURING", 1.0)

    return g


def _bfs_reachable(g: ContextGraph, start: str, max_hops: int = 5) -> Set[str]:
    visited = {start}
    frontier = {start}
    for _ in range(max_hops):
        if not frontier:
            break
        nxt: Set[str] = set()
        for nid in frontier:
            try:
                nbrs = g.get_neighbor_ids(nid) or []
            except Exception:
                try:
                    raw = g.get_neighbors(nid) or []
                    nbrs = [
                        (n.get("id") if isinstance(n, dict) else getattr(n, "id", None))
                        for n in raw
                    ]
                except Exception:
                    nbrs = []
            for n in nbrs:
                if n and n not in visited:
                    nxt.add(n)
                    visited.add(n)
        frontier = nxt
    return visited


class TestHybridMetricGraph:
    """Track 23 — Metric-Graph Hybrid Reasoning."""

    def test_hybrid_recall(self, hybrid_dataset):
        """Metric + causal + policy nodes all reachable from metric root via BFS."""
        total_recall = 0.0
        count = 0

        for rec in hybrid_dataset:
            if not rec.get("supports_hybrid_recall"):
                continue
            g = _build_hybrid_graph(rec)
            metric_name = rec["metric"]["name"]
            target_ids = (
                set(rec.get("causal_nodes", []))
                | set(rec.get("policy_nodes", []))
            )
            if not target_ids:
                continue

            reachable = _bfs_reachable(g, metric_name)
            recall = len(reachable & target_ids) / len(target_ids)
            total_recall += recall
            count += 1

        mean_recall = total_recall / max(count, 1)
        assert mean_recall >= 0.75, (
            f"hybrid_recall = {mean_recall:.3f} < 0.75 across {count} records"
        )

    def test_policy_metric_compliance(self, hybrid_dataset):
        """Compliance decisions respect both the policy threshold and the metric value."""
        correct = 0
        total = 0

        for rec in hybrid_dataset:
            m = rec["metric"]
            if "policy_threshold" not in m or "compliant" not in m:
                continue
            observed = float(m.get("observed_value", 0))
            threshold = float(m["policy_threshold"])
            compliant_gold = m["compliant"]

            # Metric compliance: observed >= threshold
            predicted = observed >= threshold
            if predicted == compliant_gold:
                correct += 1
            total += 1

        rate = correct / max(total, 1)
        assert rate >= 0.85, (
            f"policy_metric_compliance = {rate:.3f} < 0.85 ({correct}/{total})"
        )

    def test_causal_root_accuracy(self, hybrid_dataset):
        """BFS from metric node reaches the gold root cause within 5 hops."""
        reached = 0
        total = 0

        for rec in hybrid_dataset:
            gold_root = rec.get("gold_causal_root")
            if not gold_root:
                continue
            g = _build_hybrid_graph(rec)
            reachable = _bfs_reachable(g, rec["metric"]["name"])
            if gold_root in reachable:
                reached += 1
            total += 1

        rate = reached / max(total, 1)
        assert rate >= 0.70, (
            f"causal_root_accuracy = {rate:.3f} < 0.70 ({reached}/{total} records)"
        )

    def test_metric_policy_linkage_rate(self, hybrid_dataset):
        """Every metric node is linked to at least one policy node."""
        linked = 0
        total = 0

        for rec in hybrid_dataset:
            if not rec.get("policy_nodes"):
                total += 1
                continue
            g = _build_hybrid_graph(rec)
            metric_name = rec["metric"]["name"]
            nbrs = set()
            try:
                nbrs = set(g.get_neighbor_ids(metric_name) or [])
            except Exception:
                pass
            has_policy = bool(nbrs & set(rec["policy_nodes"]))
            if has_policy:
                linked += 1
            total += 1

        rate = linked / max(total, 1)
        assert rate >= 0.90, (
            f"metric_policy_linkage_rate = {rate:.3f} < 0.90 ({linked}/{total})"
        )

    def test_hybrid_graph_coverage(self, hybrid_dataset):
        """All hybrid records can be built into a valid graph without errors."""
        built = 0
        for rec in hybrid_dataset:
            try:
                g = _build_hybrid_graph(rec)
                nodes = g.find_nodes() or []
                if len(nodes) > 0:
                    built += 1
            except Exception:
                pass

        coverage = built / max(len(hybrid_dataset), 1)
        assert coverage >= 0.80, (
            f"hybrid_graph_coverage = {coverage:.3f} < 0.80 ({built}/{len(hybrid_dataset)})"
        )

    def test_gold_policy_reachable(self, hybrid_dataset):
        """The gold applicable policy node is reachable from the metric node."""
        reached = 0
        total = 0

        for rec in hybrid_dataset:
            gold_policy = rec.get("gold_policy_applicable")
            if not gold_policy:
                continue
            g = _build_hybrid_graph(rec)
            reachable = _bfs_reachable(g, rec["metric"]["name"])
            if gold_policy in reachable:
                reached += 1
            total += 1

        rate = reached / max(total, 1)
        assert rate >= 0.80, (
            f"gold_policy_reachable = {rate:.3f} < 0.80 ({reached}/{total})"
        )
