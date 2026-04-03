from __future__ import annotations

from datetime import datetime, timedelta, timezone

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import ContextGraph
from semantica.kg.temporal_query_rewriter import TemporalQueryRewriter


def test_stale_context_injection_rate(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_temporal_graph()
    now = datetime.now(timezone.utc)
    returned = [node for node in graph.nodes.values() if node.is_active(now)]
    stale = [node for node in returned if getattr(node, "valid_until", None) and datetime.fromisoformat(node.valid_until.replace("Z", "+00:00")) < now]
    stale_injection_rate = len(stale) / max(len(returned), 1)
    assert stale_injection_rate < THRESHOLDS["stale_context_injection_rate"][1]


def test_future_context_injection_rate(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_temporal_graph()
    now = datetime.now(timezone.utc)
    returned = [node for node in graph.nodes.values() if node.is_active(now)]
    future = [node for node in returned if getattr(node, "valid_from", None) and datetime.fromisoformat(node.valid_from.replace("Z", "+00:00")) > now]
    future_injection_rate = len(future) / max(len(returned), 1)
    assert future_injection_rate < THRESHOLDS["future_context_injection_rate"][1]


def test_temporal_precision_and_recall(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_temporal_graph()
    now = datetime.now(timezone.utc)
    returned = [node.node_id for node in graph.nodes.values() if node.is_active(now)]
    expected = {"ActiveNode"}
    precision = len(expected & set(returned)) / max(len(returned), 1)
    recall = len(expected & set(returned)) / len(expected)
    assert precision >= THRESHOLDS["temporal_precision"][1]
    assert recall >= THRESHOLDS["temporal_recall"][1]


def test_query_rewriter_accuracy():
    rewriter = TemporalQueryRewriter()
    queries = {
        "What policies were active before 2021?": "before",
        "Which decisions happened after January 2023?": "after",
        "What was valid on 2022-06-01?": "at",
    }
    correct = 0
    for query, expected in queries.items():
        rewritten = rewriter.rewrite(query)
        normalized = str(rewritten).lower()
        if expected in normalized:
            correct += 1
    accuracy = correct / len(queries)
    assert accuracy >= THRESHOLDS["temporal_rewriter_accuracy"][1]


def test_historical_query_correctness(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_temporal_graph()
    stale_node = graph.nodes["StaleNode"]
    limit = datetime.fromisoformat(stale_node.valid_until.replace("Z", "+00:00"))
    past = limit - timedelta(minutes=5)
    assert stale_node.is_active(past)


def test_competing_validity_window_disambiguation():
    graph = ContextGraph()
    now = datetime.now(timezone.utc)
    graph.add_node("A", "Role", content="old", valid_until=(now - timedelta(days=1)).isoformat())
    graph.add_node("B", "Role", content="new", valid_from=(now - timedelta(days=1)).isoformat())
    active = {node_id for node_id, node in graph.nodes.items() if node.is_active(now)}
    assert active == {"B"}
