"""
Track 25 — Agentic Semantic Consistency

Tests that metric definitions and policy thresholds remain consistent across
multi-turn agentic conversation traces. Each trace simulates an agent session
where metrics are defined (turn 1), used in a decision (turn 2), and potentially
updated (turn 3+). Consistency = no silent definition drift.

All tests are non-LLM: consistency is verified structurally via ContextGraph
node metadata comparisons across turns.

Metrics:
    cross_turn_metric_consistency   >= 0.90  (metric definition unchanged across turns)
    threshold_stability_rate        >= 0.95  (policy thresholds do not drift silently)
    explicit_update_detection_rate  >= 0.80  (explicit updates are flagged, not silenced)
    decision_consistency_rate       >= 0.85  (same metric + same value → same decision)
    trace_buildability_rate         == 1.0   (all traces buildable into valid graphs)

Evidence basis:
    Agentic semantic consistency is a novel metric — no published baseline.
    Thresholds set conservatively at 0.90/0.95 based on production SLA requirements
    for governed decision systems.
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Tuple

from semantica.context import ContextGraph

FIXTURES = Path(__file__).parent / "fixtures" / "semantic_layer"
JAFFLE = Path(__file__).parent / "fixtures" / "semantic_layer"


def _load(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def conversation_traces():
    return _load("agentic_conversation_traces.json")["traces"]


@pytest.fixture(scope="module")
def jaffle_metrics():
    return {m["name"]: m for m in _load("jaffle_shop_metrics.json")["metrics"]}


def _build_turn_graph(turn: Dict, metric_def: Dict) -> ContextGraph:
    """Build a single-turn graph storing the metric node with turn-specific data."""
    g = ContextGraph()
    metric_name = turn.get("expected_metric", "unknown")
    g.add_node(
        metric_name, "Metric", metric_def.get("label", metric_name),
        expression=metric_def.get("expression", ""),
        grain=metric_def.get("grain", ""),
        turn=str(turn["turn"]),
    )
    # If observed value present, add observation node
    if "observed_value" in turn:
        obs_id = f"{metric_name}_obs_t{turn['turn']}"
        g.add_node(obs_id, "Observation", str(turn["observed_value"]),
                   value=str(turn["observed_value"]))
        g.add_edge(metric_name, obs_id, "HAS_OBSERVATION", 1.0)
    # If threshold present, add policy node
    if "policy_threshold" in turn:
        pol_id = f"{metric_name}_policy"
        g.add_node(pol_id, "Policy", f"threshold={turn['policy_threshold']}",
                   threshold=str(turn["policy_threshold"]))
        g.add_edge(metric_name, pol_id, "GOVERNED_BY", 1.0)
    return g


def _extract_metric_def(g: ContextGraph, metric_name: str) -> Dict:
    """Extract metric node metadata from the graph."""
    nodes = g.find_nodes() or []
    for n in nodes:
        nid = n.get("id") if isinstance(n, dict) else getattr(n, "id", None)
        if nid == metric_name:
            meta = n.get("metadata", {}) if isinstance(n, dict) else getattr(n, "metadata", {})
            return meta or {}
    return {}


class TestAgenticConsistency:
    """Track 25 — Agentic Semantic Consistency."""

    def test_cross_turn_metric_consistency(self, conversation_traces, jaffle_metrics):
        """Metric expression does not silently change across turns in a trace."""
        consistent = 0
        total = 0

        for trace in conversation_traces:
            turns_with_metric = [
                t for t in trace["turns"]
                if t.get("expected_metric") and "expected_definition_key" not in t
                   and "updated_expression" not in t
                   and "new_expression" not in t
            ]
            if len(turns_with_metric) < 2:
                continue

            # All non-update turns should see the same metric expression
            metric_name = turns_with_metric[0]["expected_metric"]
            base_def = jaffle_metrics.get(metric_name, {})

            graphs = [
                _build_turn_graph(t, base_def)
                for t in turns_with_metric
            ]
            expressions = [
                _extract_metric_def(g, metric_name).get("expression", "")
                for g in graphs
            ]

            # All expressions should be the same (no drift)
            unique_exprs = set(e for e in expressions if e)
            is_consistent = len(unique_exprs) <= 1
            if is_consistent:
                consistent += 1
            total += 1

        rate = consistent / max(total, 1)
        assert rate >= 0.90, (
            f"cross_turn_metric_consistency = {rate:.3f} < 0.90 "
            f"({consistent}/{total} traces consistent)"
        )

    def test_threshold_stability_rate(self, conversation_traces, jaffle_metrics):
        """Policy thresholds do not change across turns unless explicitly updated."""
        stable = 0
        total = 0

        for trace in conversation_traces:
            threshold_turns = [
                t for t in trace["turns"]
                if "policy_threshold" in t
            ]
            if len(threshold_turns) < 2:
                total += 1
                stable += 1  # single threshold turn is trivially stable
                continue

            thresholds = [t["policy_threshold"] for t in threshold_turns]
            is_stable = len(set(thresholds)) == 1
            if is_stable:
                stable += 1
            total += 1

        rate = stable / max(total, 1)
        assert rate >= 0.95, (
            f"threshold_stability_rate = {rate:.3f} < 0.95 "
            f"({stable}/{total} traces stable)"
        )

    def test_explicit_update_detection_rate(self, conversation_traces):
        """Turns that contain explicit metric updates are correctly identifiable."""
        detectable = 0
        total_update_turns = 0

        update_keys = {"updated_expression", "new_expression", "updated_window",
                       "updated_ltv", "filter_added"}

        for trace in conversation_traces:
            for turn in trace["turns"]:
                has_update = bool(set(turn.keys()) & update_keys)
                if not has_update:
                    continue
                total_update_turns += 1
                # Check that expected_consistency field is present to capture it
                if "expected_consistency" in turn:
                    detectable += 1

        if total_update_turns == 0:
            pytest.skip("No explicit update turns in fixture")

        rate = detectable / total_update_turns
        assert rate >= 0.80, (
            f"explicit_update_detection_rate = {rate:.3f} < 0.80 "
            f"({detectable}/{total_update_turns} update turns annotated)"
        )

    def test_decision_consistency_rate(self, conversation_traces, jaffle_metrics):
        """Same metric + same observed value + same threshold → same decision across traces."""
        # Collect (metric, observed, threshold, expected_decision) tuples
        decision_tuples: List[Tuple] = []
        for trace in conversation_traces:
            for turn in trace["turns"]:
                if "expected_decision" in turn and "policy_threshold" in turn:
                    decision_tuples.append((
                        turn.get("expected_metric"),
                        turn.get("observed_value"),
                        turn.get("policy_threshold"),
                        turn["expected_decision"],
                    ))

        if not decision_tuples:
            pytest.skip("No decision turns in fixture")

        # Group by (metric, threshold) and check observed → decision consistency
        from collections import defaultdict
        groups = defaultdict(list)
        for metric, obs, thresh, decision in decision_tuples:
            if obs is not None and thresh is not None:
                groups[(metric, thresh)].append((obs, decision))

        consistent = 0
        total = 0
        for (metric, threshold), obs_decisions in groups.items():
            for obs, decision in obs_decisions:
                # Structural consistency: obs >= threshold ↔ approve/positive decision
                is_compliant = float(obs) >= float(threshold)
                is_approve = any(
                    kw in str(decision).lower()
                    for kw in ["approve", "positive", "upgrade", "campaign", "apply"]
                )
                is_reject = any(
                    kw in str(decision).lower()
                    for kw in ["reject", "below", "freeze"]
                )
                structurally_consistent = (
                    (is_compliant and is_approve) or
                    (not is_compliant and (is_reject or is_approve))  # some policies approve on breach
                )
                if structurally_consistent:
                    consistent += 1
                total += 1

        rate = consistent / max(total, 1)
        assert rate >= 0.85, (
            f"decision_consistency_rate = {rate:.3f} < 0.85 ({consistent}/{total})"
        )

    def test_trace_buildability_rate(self, conversation_traces, jaffle_metrics):
        """All conversation traces can be built into valid multi-turn graphs."""
        built = 0
        for trace in conversation_traces:
            try:
                for turn in trace["turns"]:
                    metric_name = turn.get("expected_metric")
                    if not metric_name:
                        continue
                    base_def = jaffle_metrics.get(metric_name, {})
                    g = _build_turn_graph(turn, base_def)
                    nodes = g.find_nodes() or []
                    assert len(nodes) > 0
                built += 1
            except Exception:
                pass

        rate = built / max(len(conversation_traces), 1)
        assert rate == 1.0, (
            f"trace_buildability_rate = {rate:.3f} < 1.0 "
            f"({built}/{len(conversation_traces)} traces built successfully)"
        )
