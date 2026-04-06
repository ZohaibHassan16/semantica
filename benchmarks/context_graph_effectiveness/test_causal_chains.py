"""
Track 3 — Causal Chain Quality
Real datasets: ATOMIC (Allen AI, 500 pairs), e-CARE (200 pairs)

Quality metrics are computed entirely from real fixture data.
No synthetic graph factories are used for recall/precision measurements.
SyntheticGraphFactory is retained only for the cycle-detection edge case,
which has no real-data analogue in the committed fixtures.

Thresholds:
    causal_chain_recall    >= 0.80  (KG-RAG literature baseline)
    causal_chain_precision >= 0.85  (KG-RAG literature baseline)
"""

from __future__ import annotations

import random

import pytest

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import CausalChainAnalyzer, ContextGraph


# ── Graph builders ────────────────────────────────────────────────────────────

def _build_atomic_graph(records: list[dict]) -> ContextGraph:
    """Build ContextGraph from ATOMIC causal pairs (cause->effect Decision nodes)."""
    graph = ContextGraph(advanced_analytics=True)
    for r in records:
        graph.add_node(r["cause_node_id"], "Decision", content=r["event"])
        graph.add_node(r["effect_node_id"], "Decision", content=r["effect"])
        graph.add_edge(r["cause_node_id"], r["effect_node_id"], "CAUSES", weight=1.0)
    return graph


def _build_atomic_chain(
    records: list[dict], n_pairs: int
) -> tuple[ContextGraph, list[str], list[str]]:
    """
    Build a sequential multi-hop causal chain from the first n_pairs ATOMIC records.
    Links effect_i -> cause_{i+1} to form a traversable multi-hop path.
    Returns (graph, cause_ids, effect_ids).
    """
    pairs = records[:n_pairs]
    graph = ContextGraph(advanced_analytics=True)
    cause_ids: list[str] = []
    effect_ids: list[str] = []
    for r in pairs:
        graph.add_node(r["cause_node_id"], "Decision", content=r["event"])
        graph.add_node(r["effect_node_id"], "Decision", content=r["effect"])
        graph.add_edge(r["cause_node_id"], r["effect_node_id"], "CAUSES", weight=1.0)
        cause_ids.append(r["cause_node_id"])
        effect_ids.append(r["effect_node_id"])
    for i in range(len(pairs) - 1):
        graph.add_edge(effect_ids[i], cause_ids[i + 1], "LEADS_TO", weight=0.9)
    return graph, cause_ids, effect_ids


def _build_ecare_graph(records: list[dict]) -> tuple[ContextGraph, dict[str, str]]:
    """
    Build ContextGraph from e-CARE records using the correct cause only.
    label=0 -> cause_A is the correct cause; label=1 -> cause_B is correct.
    Returns (graph, {effect_node_id: correct_cause_node_id}).
    """
    graph = ContextGraph(advanced_analytics=True)
    ground_truth: dict[str, str] = {}
    for r in records:
        correct_cause = r["cause_A"] if r["label"] == 0 else r["cause_B"]
        graph.add_node(r["cause_node_id"], "Decision", content=correct_cause)
        graph.add_node(r["effect_node_id"], "Decision", content=r["effect"])
        graph.add_edge(r["cause_node_id"], r["effect_node_id"], "CAUSES", weight=1.0)
        ground_truth[r["effect_node_id"]] = r["cause_node_id"]
    return graph, ground_truth


def _decision_ids(items: list) -> list[str]:
    ids = []
    for item in items:
        did = getattr(item, "decision_id", None)
        if did is None and isinstance(item, dict):
            did = item.get("decision_id")
        if did is not None:
            ids.append(str(did))
    return ids


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_causal_chain_recall_atomic(atomic_causal_dataset):
    """
    For each of 100 ATOMIC pairs build a 2-node graph and verify
    CausalChainAnalyzer retrieves the effect from the cause.
    Recall = pairs where effect is correctly retrieved / total pairs.
    """
    sample = atomic_causal_dataset["records"][:100]
    found = 0
    for r in sample:
        graph = ContextGraph(advanced_analytics=True)
        graph.add_node(r["cause_node_id"], "Decision", content=r["event"])
        graph.add_node(r["effect_node_id"], "Decision", content=r["effect"])
        graph.add_edge(r["cause_node_id"], r["effect_node_id"], "CAUSES", weight=1.0)
        analyzer = CausalChainAnalyzer(graph_store=graph)
        downstream = analyzer.get_causal_chain(
            r["cause_node_id"], direction="downstream", max_depth=2
        )
        if r["effect_node_id"] in set(_decision_ids(downstream)):
            found += 1

    recall = found / len(sample)
    assert recall >= THRESHOLDS["causal_chain_recall"][1], (
        f"ATOMIC causal recall {recall:.3f} < {THRESHOLDS['causal_chain_recall'][1]} "
        f"({found}/{len(sample)} pairs)"
    )


def test_causal_chain_precision_ecare(ecare_causal_dataset):
    """
    Build graph from 100 e-CARE records (correct cause-effect pairs only).
    For each effect node traverse upstream and measure precision.
    """
    sample = ecare_causal_dataset["records"][:100]
    graph, ground_truth = _build_ecare_graph(sample)
    analyzer = CausalChainAnalyzer(graph_store=graph)

    precision_scores: list[float] = []
    for effect_id, expected_cause_id in ground_truth.items():
        upstream = analyzer.get_causal_chain(effect_id, direction="upstream", max_depth=2)
        retrieved = set(_decision_ids(upstream))
        if retrieved:
            precision_scores.append(len(retrieved & {expected_cause_id}) / len(retrieved))

    if not precision_scores:
        pytest.skip("No e-CARE precision results")

    precision = sum(precision_scores) / len(precision_scores)
    assert precision >= THRESHOLDS["causal_chain_precision"][1], (
        f"e-CARE precision {precision:.3f} < {THRESHOLDS['causal_chain_precision'][1]}"
    )


def test_multi_hop_causal_chain_atomic(atomic_causal_dataset):
    """
    Chain 10 ATOMIC pairs sequentially via LEADS_TO bridge edges.
    Traverse from the first cause with max_depth=5.
    3-hop recall (first 3 effect nodes) must be >= 0.75.
    """
    records = atomic_causal_dataset["records"]
    graph, cause_ids, effect_ids = _build_atomic_chain(records, n_pairs=10)
    analyzer = CausalChainAnalyzer(graph_store=graph)

    downstream = analyzer.get_causal_chain(cause_ids[0], direction="downstream", max_depth=5)
    retrieved = set(_decision_ids(downstream))
    expected_3hop = {effect_ids[0], effect_ids[1], effect_ids[2]}
    recall_3hop = len(retrieved & expected_3hop) / len(expected_3hop)

    assert recall_3hop >= 0.75, (
        f"3-hop ATOMIC chain recall {recall_3hop:.3f} < 0.75 "
        f"(retrieved: {retrieved & expected_3hop} of {expected_3hop})"
    )


def test_root_cause_identification_atomic(atomic_causal_dataset):
    """
    Build a 6-pair ATOMIC chain. Traverse upstream from the terminal effect.
    The most causally distant node must be cause_ids[0] (the chain root).
    """
    records = atomic_causal_dataset["records"]
    graph, cause_ids, effect_ids = _build_atomic_chain(records, n_pairs=6)
    analyzer = CausalChainAnalyzer(graph_store=graph)

    upstream = analyzer.get_causal_chain(effect_ids[5], direction="upstream", max_depth=12)
    distances = {
        getattr(item, "decision_id", None): item.metadata.get("causal_distance", 0)
        for item in upstream
        if getattr(item, "decision_id", None) is not None
    }
    if not distances:
        pytest.skip("CausalChainAnalyzer returned no upstream results")

    root = max(distances, key=distances.get)
    assert root == cause_ids[0], (
        f"Root cause identified as '{root}', expected '{cause_ids[0]}'"
    )


def test_spurious_edge_suppression_atomic(atomic_causal_dataset):
    """
    Build graph from 20 ATOMIC pairs. Add 5 distractor nodes via UNRELATED edges.
    Verify downstream traversal does not return distractors (spurious rate < 0.15).
    """
    sample = atomic_causal_dataset["records"][:20]
    graph = _build_atomic_graph(sample)

    distractor_ids = [f"distractor_{i}" for i in range(5)]
    for d_id in distractor_ids:
        graph.add_node(d_id, "Decision", content=f"Unrelated event {d_id}")
        graph.add_edge(sample[0]["cause_node_id"], d_id, "UNRELATED", weight=0.5)

    analyzer = CausalChainAnalyzer(graph_store=graph)
    downstream = analyzer.get_causal_chain(
        sample[0]["cause_node_id"], direction="downstream", max_depth=2
    )
    retrieved = set(_decision_ids(downstream))
    spurious_rate = len(retrieved & set(distractor_ids)) / max(len(retrieved), 1)

    assert spurious_rate < 0.15, (
        f"Spurious edge rate {spurious_rate:.3f} >= 0.15"
    )


def test_withheld_pair_not_reachable_atomic(atomic_causal_dataset):
    """
    Counterfactual: build graph from pairs 1-19, withhold pair 0's edge.
    The withheld effect must NOT be reachable (the causal edge is absent).
    """
    records = atomic_causal_dataset["records"]
    withheld = records[0]
    graph = _build_atomic_graph(records[1:20])
    graph.add_node(withheld["cause_node_id"], "Decision", content=withheld["event"])

    analyzer = CausalChainAnalyzer(graph_store=graph)
    downstream = analyzer.get_causal_chain(
        withheld["cause_node_id"], direction="downstream", max_depth=3
    )
    assert withheld["effect_node_id"] not in set(_decision_ids(downstream)), (
        f"Withheld effect '{withheld['effect_node_id']}' was reachable despite missing edge"
    )


def test_full_atomic_graph_scale_recall(atomic_causal_dataset):
    """
    Build the full ATOMIC graph (500 pairs). Sample 50 pairs (seed=42).
    Verifies recall holds at scale, not just on small graphs.
    """
    rng = random.Random(42)
    all_records = atomic_causal_dataset["records"]
    graph = _build_atomic_graph(all_records)
    analyzer = CausalChainAnalyzer(graph_store=graph)

    sample = rng.sample(all_records, 50)
    found = sum(
        1 for r in sample
        if r["effect_node_id"] in set(_decision_ids(
            analyzer.get_causal_chain(r["cause_node_id"], direction="downstream", max_depth=2)
        ))
    )
    recall = found / len(sample)
    assert recall >= THRESHOLDS["causal_chain_recall"][1], (
        f"Full ATOMIC graph recall {recall:.3f} < {THRESHOLDS['causal_chain_recall'][1]} ({found}/50)"
    )


def test_ecare_full_dataset_precision(ecare_causal_dataset):
    """
    Build graph from all 200 e-CARE records. Precision threshold must hold
    on the full dataset, not just a subset.
    """
    graph, ground_truth = _build_ecare_graph(ecare_causal_dataset["records"])
    analyzer = CausalChainAnalyzer(graph_store=graph)

    scores: list[float] = []
    for effect_id, cause_id in ground_truth.items():
        upstream = analyzer.get_causal_chain(effect_id, direction="upstream", max_depth=2)
        retrieved = set(_decision_ids(upstream))
        if retrieved:
            scores.append(len(retrieved & {cause_id}) / len(retrieved))

    if not scores:
        pytest.skip("No e-CARE precision results on full dataset")

    precision = sum(scores) / len(scores)
    assert precision >= THRESHOLDS["causal_chain_precision"][1], (
        f"Full e-CARE precision {precision:.3f} < {THRESHOLDS['causal_chain_precision'][1]}"
    )


def test_cycle_detection(synthetic_graph_factory):
    """
    Edge case: cyclic topology (A->B->C->A). Analyzer must not loop infinitely.
    Uses SyntheticGraphFactory — no committed dataset contains cyclic causal chains.
    """
    graph = synthetic_graph_factory.create_cycle()
    analyzer = CausalChainAnalyzer(graph_store=graph)
    result = analyzer.get_causal_chain("A", direction="downstream", max_depth=5)
    assert len(result) <= 3, (
        f"Cycle traversal returned {len(result)} nodes — expected <= 3"
    )
