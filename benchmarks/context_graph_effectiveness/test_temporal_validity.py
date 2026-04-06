"""
Track 2 — Temporal Validity
Real dataset: TimeQA (150 records, temporal_intent in {before, after, at})

Quality metrics are computed from real TimeQA fixture data.
Synthetic graph tests retained only for API-shape edge cases.

Thresholds:
    temporal_precision          >= 0.90
    temporal_recall             >= 0.80
    stale_context_injection_rate < 0.05
    future_context_injection_rate < 0.05
    temporal_rewriter_accuracy  >= 0.85
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import ContextGraph
from semantica.kg.temporal_query_rewriter import TemporalQueryRewriter


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _build_timeqa_node(graph: ContextGraph, record: dict) -> str:
    node_id = f"tqa_{record['id']}"
    kwargs: dict[str, str] = {}
    if record.get("start_time"):
        kwargs["valid_from"] = record["start_time"]
    if record.get("end_time"):
        kwargs["valid_until"] = record["end_time"]
    graph.add_node(
        node_id, "Entity",
        content=f"{record['entity']}: {record['answer']}",
        **kwargs,
    )
    return node_id


def _active_at(graph: ContextGraph, query_time: datetime) -> set[str]:
    return {nid for nid, n in graph.nodes.items() if n.is_active(query_time)}


# ── TimeQA real-data tests ────────────────────────────────────────────────────

def test_timeqa_stale_context_injection_rate(timeqa_dataset):
    """
    Build graph from all 150 TimeQA records with their temporal windows.
    Stale injection rate (active nodes whose valid_until < now) must be < 0.05.
    """
    records = timeqa_dataset["records"]
    graph = ContextGraph(advanced_analytics=True)
    for r in records:
        _build_timeqa_node(graph, r)

    now = datetime.now(timezone.utc)
    active = _active_at(graph, now)
    stale = {
        nid for nid in active
        if getattr(graph.nodes[nid], "valid_until", None)
        and _parse_iso(graph.nodes[nid].valid_until) < now
    }
    rate = len(stale) / max(len(active), 1)
    assert rate < THRESHOLDS["stale_context_injection_rate"][1], (
        f"TimeQA stale injection rate {rate:.3f} >= threshold"
    )


def test_timeqa_future_context_injection_rate(timeqa_dataset):
    """Future injection rate (active nodes whose valid_from > now) must be < 0.05."""
    records = timeqa_dataset["records"]
    graph = ContextGraph(advanced_analytics=True)
    for r in records:
        _build_timeqa_node(graph, r)

    now = datetime.now(timezone.utc)
    active = _active_at(graph, now)
    future_nodes = {
        nid for nid in active
        if getattr(graph.nodes[nid], "valid_from", None)
        and _parse_iso(graph.nodes[nid].valid_from) > now
    }
    rate = len(future_nodes) / max(len(active), 1)
    assert rate < THRESHOLDS["future_context_injection_rate"][1], (
        f"TimeQA future injection rate {rate:.3f} >= threshold"
    )


def test_timeqa_before_intent_precision_recall(timeqa_dataset):
    """
    For records with temporal_intent='before': node with valid_until window
    should be active at 30 days before that cutoff. Measures real temporal
    filter correctness across all qualifying TimeQA records.
    """
    records = [
        r for r in timeqa_dataset["records"]
        if r.get("temporal_intent") == "before" and r.get("end_time")
    ]
    if not records:
        pytest.skip("No TimeQA before-intent records with end_time")

    tp = retrieved_total = 0
    for r in records:
        graph = ContextGraph(advanced_analytics=True)
        node_id = _build_timeqa_node(graph, r)
        end_dt = _parse_iso(r["end_time"])
        query_time = end_dt - timedelta(days=30)
        active = _active_at(graph, query_time)
        retrieved_total += len(active)
        if node_id in active:
            tp += 1

    assert tp / max(retrieved_total, 1) >= THRESHOLDS["temporal_precision"][1], (
        f"TimeQA before precision {tp}/{retrieved_total} < threshold"
    )
    assert tp / max(len(records), 1) >= THRESHOLDS["temporal_recall"][1], (
        f"TimeQA before recall {tp}/{len(records)} < threshold"
    )


def test_timeqa_after_intent_precision_recall(timeqa_dataset):
    """
    For records with temporal_intent='after': node with valid_from window
    should be active at 30 days after that start.
    """
    records = [
        r for r in timeqa_dataset["records"]
        if r.get("temporal_intent") == "after" and r.get("start_time")
    ]
    if not records:
        pytest.skip("No TimeQA after-intent records with start_time")

    tp = retrieved_total = 0
    for r in records:
        graph = ContextGraph(advanced_analytics=True)
        node_id = _build_timeqa_node(graph, r)
        start_dt = _parse_iso(r["start_time"])
        query_time = start_dt + timedelta(days=30)
        active = _active_at(graph, query_time)
        retrieved_total += len(active)
        if node_id in active:
            tp += 1

    assert tp / max(retrieved_total, 1) >= THRESHOLDS["temporal_precision"][1], (
        f"TimeQA after precision {tp}/{retrieved_total} < threshold"
    )
    assert tp / max(len(records), 1) >= THRESHOLDS["temporal_recall"][1], (
        f"TimeQA after recall {tp}/{len(records)} < threshold"
    )


def test_timeqa_entity_version_disambiguation(timeqa_dataset):
    """
    Place two versions of a real TimeQA entity (one expired, one current)
    in the same graph. Only the current version should be active.
    """
    with_end = [r for r in timeqa_dataset["records"] if r.get("end_time")]
    if len(with_end) < 2:
        pytest.skip("Not enough TimeQA records with end_time")

    now = datetime.now(timezone.utc)
    old_until = (now - timedelta(days=3650)).isoformat()
    new_from = (now - timedelta(days=3650)).isoformat()
    new_until = (now + timedelta(days=3650)).isoformat()

    graph = ContextGraph(advanced_analytics=True)
    graph.add_node("old_ver", "Entity", content=with_end[0]["entity"], valid_until=old_until)
    graph.add_node("new_ver", "Entity", content=with_end[1]["entity"],
                   valid_from=new_from, valid_until=new_until)

    active = _active_at(graph, now)
    assert "new_ver" in active, "Current version should be active"
    assert "old_ver" not in active, "Expired version should not be active"


def test_timeqa_query_rewriter_accuracy(timeqa_dataset):
    """
    Feed all 150 TimeQA questions to TemporalQueryRewriter.
    Verify the temporal_intent label (before/after/at) appears in the output.
    Accuracy >= temporal_rewriter_accuracy threshold.
    """
    rewriter = TemporalQueryRewriter()
    records = timeqa_dataset["records"]
    correct = sum(
        1 for r in records
        if r.get("temporal_intent")
        and r["temporal_intent"] in str(rewriter.rewrite(r["question"])).lower()
    )
    accuracy = correct / max(len(records), 1)
    assert accuracy >= THRESHOLDS["temporal_rewriter_accuracy"][1], (
        f"TimeQA rewriter accuracy {accuracy:.3f} < threshold ({correct}/{len(records)})"
    )


def test_timeqa_windowless_nodes_always_active(timeqa_dataset):
    """Nodes with no temporal bounds should be active at any query time."""
    windowless = [
        r for r in timeqa_dataset["records"]
        if not r.get("start_time") and not r.get("end_time") and not r.get("at_time")
    ]
    if not windowless:
        pytest.skip("No windowless TimeQA records")

    graph = ContextGraph(advanced_analytics=True)
    for r in windowless:
        graph.add_node(f"tqa_{r['id']}", "Entity", content=r["entity"])

    active = _active_at(graph, datetime.now(timezone.utc))
    expected = {f"tqa_{r['id']}" for r in windowless}
    assert expected == active, f"Missing: {expected - active}"


# ── Synthetic edge-case tests (API shape / topology) ──────────────────────────

def test_stale_context_injection_rate(synthetic_graph_factory):
    """API shape: is_active() excludes expired nodes. Synthetic graph."""
    graph = synthetic_graph_factory.create_temporal_graph()
    now = datetime.now(timezone.utc)
    returned = [node for node in graph.nodes.values() if node.is_active(now)]
    stale = [
        node for node in returned
        if getattr(node, "valid_until", None)
        and _parse_iso(node.valid_until.replace("Z", "+00:00")) < now
    ]
    assert len(stale) / max(len(returned), 1) < THRESHOLDS["stale_context_injection_rate"][1]


def test_future_context_injection_rate(synthetic_graph_factory):
    """API shape: is_active() excludes future-only nodes. Synthetic graph."""
    graph = synthetic_graph_factory.create_temporal_graph()
    now = datetime.now(timezone.utc)
    returned = [node for node in graph.nodes.values() if node.is_active(now)]
    future = [
        node for node in returned
        if getattr(node, "valid_from", None)
        and _parse_iso(node.valid_from.replace("Z", "+00:00")) > now
    ]
    assert len(future) / max(len(returned), 1) < THRESHOLDS["future_context_injection_rate"][1]


def test_competing_validity_window_disambiguation():
    """Two nodes, one expired, one current — only current returned."""
    graph = ContextGraph()
    now = datetime.now(timezone.utc)
    graph.add_node("A", "Role", content="old", valid_until=(now - timedelta(days=1)).isoformat())
    graph.add_node("B", "Role", content="new", valid_from=(now - timedelta(days=1)).isoformat())
    active = {nid for nid, n in graph.nodes.items() if n.is_active(now)}
    assert active == {"B"}
