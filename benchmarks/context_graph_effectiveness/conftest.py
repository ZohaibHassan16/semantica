import json
import os
from pathlib import Path
import pytest
from datetime import datetime, timedelta, timezone

from semantica.context import ContextGraph

class MockLLM:
    """
    Deterministic mock LLM for evaluating context effectiveness without API cost.
    """
    
    def __init__(self, deterministic_response="Mock deterministic response based on context"):
        self.deterministic_response = deterministic_response
        self.call_history = []
        
    def predict(self, prompt: str) -> str:
        self.call_history.append(prompt)
        return self.deterministic_response

class SyntheticGraphFactory:
    """
    Factory to generate deterministic synthetic graphs of various topologies 
    (linear, branching, diamond, cyclic) for effectiveness evaluation.
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        
    def create_linear_chain(self, depth: int) -> ContextGraph:
        graph = ContextGraph(advanced_analytics=True)
        prev_id = None
        for i in range(depth):
            node_id = f"Decision_{i}"
            graph.add_node(node_id, "Decision", content=f"Decision {i} content", confidence=0.9, timestamp=datetime.now())
            if prev_id:
                graph.add_edge(prev_id, node_id, "CAUSED", weight=1.0)
            prev_id = node_id
        return graph
        
    def create_diamond_chain(self) -> ContextGraph:
        graph = ContextGraph(advanced_analytics=True)
        graph.add_node("A", "Decision", content="A")
        graph.add_node("B", "Decision", content="B")
        graph.add_node("C", "Decision", content="C")
        graph.add_node("D", "Decision", content="D")
        
        graph.add_edge("A", "B", "CAUSED")
        graph.add_edge("A", "C", "CAUSED")
        graph.add_edge("B", "D", "CAUSED")
        graph.add_edge("C", "D", "CAUSED")
        return graph
        
    def create_cycle(self) -> ContextGraph:
        graph = ContextGraph(advanced_analytics=True)
        graph.add_node("A", "Decision", content="A")
        graph.add_node("B", "Decision", content="B")
        graph.add_node("C", "Decision", content="C")
        
        graph.add_edge("A", "B", "CAUSED")
        graph.add_edge("B", "C", "CAUSED")
        graph.add_edge("C", "A", "CAUSED")
        return graph

    def create_temporal_graph(self) -> ContextGraph:
        graph = ContextGraph(advanced_analytics=True)
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=5)).isoformat()
        future = (now + timedelta(days=5)).isoformat()
        far_future = (now + timedelta(days=15)).isoformat()
        
        graph.add_node("StaleNode", "Entity", content="Stale", valid_until=past)
        graph.add_node("ActiveNode", "Entity", content="Active", valid_from=past, valid_until=future)
        graph.add_node("FutureNode", "Entity", content="Future", valid_from=future, valid_until=far_future)
        return graph


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def synthetic_graph_factory():
    return SyntheticGraphFactory(seed=42)


@pytest.fixture
def qa_dataset():
    """
    Loads the ground-truth Q&A dataset mapping from fixtures.
    """
    fixture_path = Path(__file__).parent / "fixtures" / "qa_pairs.json"
    if not fixture_path.exists():
        return []
        
    with open(fixture_path, "r") as f:
        return json.load(f)
