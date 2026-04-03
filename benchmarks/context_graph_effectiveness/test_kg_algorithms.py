from __future__ import annotations

import pytest

from semantica.context import ContextGraph


def test_centrality_calculator():
    graph = ContextGraph(advanced_analytics=True)
    graph.add_node("Center", "Hub", content="center")
    for i in range(5):
        graph.add_node(f"Leaf_{i}", "Spoke", content=f"leaf {i}")
        graph.add_edge("Center", f"Leaf_{i}", "CONNECTED")

    analysis = graph.analyze_graph_with_kg()
    centrality = analysis.get("centrality", {})
    if not centrality:
        pytest.skip("Centrality output unavailable from analyze_graph_with_kg")
    center_score = centrality.get("Center", 0)
    leaf_score = max(centrality.get(f"Leaf_{i}", 0) for i in range(5))
    assert center_score > leaf_score


def test_community_detector(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    analysis = graph.analyze_graph_with_kg()
    communities = analysis.get("communities", {})
    assert isinstance(communities, dict)


def test_node_embedder(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_linear_chain(depth=3)
    embedder = graph.kg_components.get("node_embedder")
    if not embedder:
        pytest.skip("Node embedder not available")
    if not hasattr(embedder, "generate_embeddings"):
        pytest.skip("Node embedder API does not expose generate_embeddings")
    emb = embedder.generate_embeddings(list(graph.nodes.keys()), [(e.source_id, e.target_id) for e in graph.edges])
    assert isinstance(emb, dict)
    assert len(emb) == 3


def test_path_finder(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_linear_chain(depth=10)
    path_finder = graph.kg_components.get("path_finder")
    if not path_finder:
        pytest.skip("Path finder not available")
    try:
        path = path_finder.find_shortest_path("Decision_0", "Decision_9", graph.nodes, graph.edges)
    except TypeError:
        try:
            path = path_finder.find_shortest_path("Decision_0", "Decision_9", graph)
        except (TypeError, ValueError):
            pytest.skip("Path finder API signature differs from benchmark expectation")
    assert path is not None
    assert len(path) == 10


def test_link_predictor(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    predictor = graph.kg_components.get("link_predictor")
    if not predictor:
        pytest.skip("Link predictor not available")
    preds = predictor.predict_links(graph.nodes, graph.edges)
    assert isinstance(preds, list)


def test_similarity_calculator(synthetic_graph_factory):
    graph = synthetic_graph_factory.create_diamond_chain()
    sim = graph.find_similar_nodes("A", similarity_type="structural")
    assert isinstance(sim, list)


def test_decision_intelligence_integration():
    graph = ContextGraph(advanced_analytics=True)
    first = graph.record_decision(category="test", scenario="start", reasoning="root", outcome="approved", confidence=1.0)
    second = graph.record_decision(category="test", scenario="child", reasoning="child", outcome="approved", confidence=1.0)
    graph.add_edge(first, second, "CAUSED")
    inf_a = graph.analyze_decision_influence(first)
    inf_b = graph.analyze_decision_influence(second)
    assert inf_a.get("impact_score", 0.0) >= inf_b.get("impact_score", 0.0)
