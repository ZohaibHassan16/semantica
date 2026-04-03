import json
import os
from pathlib import Path
import pytest
from datetime import datetime, timedelta, timezone

from semantica.context import ContextGraph


class MockLLM:
    """Deterministic mock LLM for shape-only tests, never benchmark evidence."""

    def __init__(self, deterministic_response="Mock deterministic response based on context"):
        self.deterministic_response = deterministic_response
        self.call_history = []

    def predict(self, prompt: str) -> str:
        self.call_history.append(prompt)
        return self.deterministic_response


class _SkippedRealLLM:
    def generate(self, prompt: str) -> str:
        pytest.skip("Real LLM fixture is unavailable in this environment")


class SyntheticGraphFactory:
    """Factory to generate deterministic synthetic graphs of various topologies."""

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


_FIXTURES = Path(__file__).parent / "fixtures"
_SL_FIXTURES = _FIXTURES / "semantic_layer"


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def synthetic_graph_factory():
    return SyntheticGraphFactory(seed=42)


@pytest.fixture
def qa_dataset():
    fixture_path = _FIXTURES / "qa_pairs.json"
    if not fixture_path.exists():
        return []
    return _load_json(fixture_path)


@pytest.fixture(scope="session")
def retrieval_eval_dataset():
    return _load_json(_FIXTURES / "retrieval_eval_dataset.json")


@pytest.fixture(scope="session")
def decision_dataset():
    return _load_json(_FIXTURES / "decision_intelligence_dataset.json")


@pytest.fixture(scope="session")
def dedup_dblp_acm_dataset():
    return _load_json(_FIXTURES / "dedup" / "dblp_acm_pairs.json")


@pytest.fixture(scope="session")
def dedup_amazon_google_dataset():
    return _load_json(_FIXTURES / "dedup" / "amazon_google_pairs.json")


@pytest.fixture(scope="session")
def dedup_abt_buy_dataset():
    return _load_json(_FIXTURES / "dedup" / "abt_buy_pairs.json")


@pytest.fixture(scope="session")
def timeqa_dataset():
    return _load_json(_FIXTURES / "temporal" / "timeqa_subset.json")


@pytest.fixture(scope="session")
def copa_dataset():
    return _load_json(_FIXTURES / "reasoning" / "copa_subset.json")["records"]


@pytest.fixture(scope="session")
def wiqa_dataset():
    return _load_json(_FIXTURES / "reasoning" / "wiqa_subset.json")["records"]


@pytest.fixture(scope="session")
def multihop_dataset():
    return {
        "hotpotqa": _load_json(_FIXTURES / "multihop" / "hotpotqa_subset.json"),
        "wikimultihop": _load_json(_FIXTURES / "multihop" / "wikimultihop_subset.json"),
    }


@pytest.fixture(scope="session")
def semantic_extract_dataset():
    return {
        "ner": _load_json(_FIXTURES / "semantic_extract" / "conll2003_ner_subset.json"),
        "re": _load_json(_FIXTURES / "semantic_extract" / "ace2005_re_subset.json"),
        "event": _load_json(_FIXTURES / "semantic_extract" / "event_detection_subset.json"),
    }


@pytest.fixture(scope="session")
def graph_integrity_dataset():
    return {
        "wn18rr": _load_json(_FIXTURES / "graph_integrity" / "wn18rr_triples_subset.json"),
        "fb15k237": _load_json(_FIXTURES / "graph_integrity" / "fb15k237_triples_subset.json"),
    }


@pytest.fixture(scope="session")
def retrieval_dataset(retrieval_eval_dataset):
    return retrieval_eval_dataset


@pytest.fixture(scope="session")
def dedup_dataset(dedup_dblp_acm_dataset):
    return dedup_dblp_acm_dataset["pairs"]


@pytest.fixture
def linear_graph():
    graph = ContextGraph(advanced_analytics=True)
    node_ids = [f"n{i:03d}" for i in range(5)]
    for index, node_id in enumerate(node_ids):
        graph.add_node(node_id, "Decision", content=f"Decision-{node_id}", topic="credit_scoring")
        if index:
            graph.add_edge(node_ids[index - 1], node_id, "CAUSED", weight=1.0)
    return graph


@pytest.fixture
def cycle_graph():
    graph = ContextGraph(advanced_analytics=True)
    for node_id in ["c0", "c1", "c2", "c3"]:
        graph.add_node(node_id, "Decision", content=node_id)
    graph.add_edge("c0", "c1", "CAUSED", weight=1.0)
    graph.add_edge("c1", "c2", "CAUSED", weight=1.0)
    graph.add_edge("c2", "c3", "CAUSED", weight=1.0)
    graph.add_edge("c3", "c0", "CAUSED", weight=1.0)
    return graph


@pytest.fixture
def temporal_graph():
    graph = ContextGraph(advanced_analytics=True)
    graph.add_node("t001", "Decision", content="stale", valid_from="2020-01-01T00:00:00+00:00", valid_until="2021-01-01T00:00:00+00:00")
    graph.add_node("t002", "Decision", content="active", valid_from="2022-01-01T00:00:00+00:00", valid_until="2023-01-01T00:00:00+00:00")
    graph.add_node("t003", "Decision", content="future", valid_from="2024-01-01T00:00:00+00:00", valid_until="2025-01-01T00:00:00+00:00")
    return graph


@pytest.fixture(scope="session")
def real_llm():
    if os.getenv("SEMANTICA_REAL_LLM") != "1":
        pytest.skip("Set SEMANTICA_REAL_LLM=1 to run real-LLM benchmark tracks")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if anthropic_key:
        try:
            import anthropic
        except ImportError:
            pytest.skip("anthropic package not installed for real LLM benchmark")

        client = anthropic.Anthropic(api_key=anthropic_key)

        class AnthropicLLM:
            def generate(self, prompt: str) -> str:
                response = client.messages.create(
                    model="claude-3-5-haiku-latest",
                    max_tokens=300,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
                if not response.content:
                    return ""
                return "".join(getattr(block, "text", "") for block in response.content)

        return AnthropicLLM()

    if openai_key:
        try:
            from openai import OpenAI
        except ImportError:
            pytest.skip("openai package not installed for real LLM benchmark")

        client = OpenAI(api_key=openai_key)

        class OpenAILLM:
            def generate(self, prompt: str) -> str:
                response = client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                    temperature=0,
                    max_output_tokens=300,
                )
                return getattr(response, "output_text", "") or ""

        return OpenAILLM()

    return _SkippedRealLLM()


# Semantic Layer fixtures (Tracks 21-25)

def _load_sl(name: str):
    return _load_json(_SL_FIXTURES / name)


@pytest.fixture(scope="session")
def jaffle_shop_dataset():
    return _load_sl("jaffle_shop_metrics.json")


@pytest.fixture(scope="session")
def metric_change_dataset():
    return _load_sl("metric_change_pairs.json")


@pytest.fixture(scope="session")
def hybrid_metric_graph_dataset():
    return _load_sl("hybrid_metric_graph.json")


@pytest.fixture(scope="session")
def agentic_traces_dataset():
    return _load_sl("agentic_conversation_traces.json")
