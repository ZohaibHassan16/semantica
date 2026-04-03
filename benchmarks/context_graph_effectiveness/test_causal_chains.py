from __future__ import annotations

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import CausalChainAnalyzer


def _decision_ids(decisions):
    ids = []
    for decision in decisions:
        decision_id = getattr(decision, "decision_id", None)
        if decision_id is None and isinstance(decision, dict):
            decision_id = decision.get("decision_id")
        ids.append(decision_id)
    return ids


def test_causal_chain_recall(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_linear_chain(depth=4)
    analyzer = CausalChainAnalyzer(graph_store=graph)
    downstream = analyzer.get_causal_chain("Decision_0", direction="downstream", max_depth=3)
    expected = {"Decision_1", "Decision_2", "Decision_3"}
    retrieved = set(_decision_ids(downstream))
    recall = len(retrieved & expected) / len(expected)
    assert recall >= THRESHOLDS["causal_chain_recall"][1]


def test_causal_chain_precision(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    analyzer = CausalChainAnalyzer(graph_store=graph)
    upstream = analyzer.get_causal_chain("D", direction="upstream", max_depth=5)
    expected = {"A", "B", "C"}
    retrieved = set(_decision_ids(upstream))
    precision = len(retrieved & expected) / max(len(retrieved), 1)
    assert precision >= THRESHOLDS["causal_chain_precision"][1]


def test_root_cause_accuracy(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    analyzer = CausalChainAnalyzer(graph_store=graph)
    upstream = analyzer.get_causal_chain("D", direction="upstream", max_depth=5)
    distances = {getattr(item, "decision_id", None): item.metadata.get("causal_distance", 0) for item in upstream}
    root = max(distances, key=distances.get)
    assert root == "A"


def test_spurious_edge_rate(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_linear_chain(depth=2)
    graph.add_node("Random", "Decision", content="Random")
    graph.add_edge("Decision_0", "Random", "UNRELATED", weight=1.0)
    analyzer = CausalChainAnalyzer(graph_store=graph)
    downstream = analyzer.get_causal_chain("Decision_0", direction="downstream", max_depth=2)
    retrieved = set(_decision_ids(downstream))
    spurious_rate = 1.0 if "Random" in retrieved else 0.0
    assert spurious_rate < 0.15


def test_linear_topology(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_linear_chain(depth=4)
    analyzer = CausalChainAnalyzer(graph_store=graph)
    assert len(analyzer.get_causal_chain("Decision_0", "downstream", 5)) == 3


def test_branching_topology(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    analyzer = CausalChainAnalyzer(graph_store=graph)
    assert len(analyzer.get_causal_chain("A", "downstream", 5)) == 3


def test_diamond_topology(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    analyzer = CausalChainAnalyzer(graph_store=graph)
    assert len(analyzer.get_causal_chain("D", "upstream", 5)) == 3


def test_cycle_detection(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_cycle()
    analyzer = CausalChainAnalyzer(graph_store=graph)
    upstream = analyzer.get_causal_chain("A", "downstream", 5)
    assert len(upstream) <= 3
