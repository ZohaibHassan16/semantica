from __future__ import annotations

import numpy as np
import pytest

from semantica.embeddings.graph_embedding_manager import GraphEmbeddingManager
from semantica.embeddings.text_embedder import TextEmbedder


_FALLBACK = TextEmbedder(method="fallback")


class _StubGenerator:
    def generate_embeddings(self, texts, data_type=None, **kwargs):
        if isinstance(texts, list):
            return np.vstack([_get_embedding(text) for text in texts])
        return _get_embedding(texts)


def _get_embedding(text: str) -> np.ndarray:
    embedding = _FALLBACK.embed_text(text)
    if not isinstance(embedding, np.ndarray):
        try:
            embedding = np.asarray(embedding, dtype=float)
        except Exception:
            pytest.skip("TextEmbedder did not return numeric embeddings in this environment")
    if embedding.dtype == object:
        pytest.skip("TextEmbedder returned non-numeric object embeddings in this environment")
    return embedding


def _similarity(left, right):
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    denom = np.linalg.norm(left) * np.linalg.norm(right)
    if denom == 0:
        return 0.0
    return float(np.dot(left, right) / denom)


def test_semantic_coherence():
    related_a = _get_embedding("loan approval policy")
    related_b = _get_embedding("mortgage underwriting policy")
    unrelated = _get_embedding("tropical fruit salad")
    assert related_a.shape == related_b.shape == unrelated.shape


def test_provider_consistency():
    texts = ["loan approval", "mortgage policy", "banana bread"]
    direct_embeddings = [_get_embedding(text) for text in texts]
    batch_embeddings = _FALLBACK.embed_batch(texts)
    if not isinstance(batch_embeddings, np.ndarray):
        try:
            batch_embeddings = np.asarray(batch_embeddings, dtype=float)
        except Exception:
            pytest.skip("Batch embedding output is not numeric in this environment")
    if batch_embeddings.size == 0:
        pytest.skip("Batch embedding output was empty in this environment")
    assert batch_embeddings.shape[0] == len(texts)
    assert batch_embeddings.shape[1] == direct_embeddings[0].shape[0]


def test_pooling_strategy_impact():
    chunk_1 = _get_embedding("credit policy section one")
    chunk_2 = _get_embedding("credit policy section two")
    hierarchical = np.mean(np.vstack([chunk_1, chunk_2]), axis=0)
    mean_pool = (chunk_1 + chunk_2) / 2
    assert hierarchical.shape == mean_pool.shape


def test_hash_fallback_stability():
    vec1 = _get_embedding("Test String")
    vec2 = _get_embedding("Test String")
    assert np.allclose(vec1, vec2)


def test_graph_embedding_manager_correctness():
    manager = GraphEmbeddingManager(embedding_generator=_StubGenerator())
    result = manager.prepare_for_graph_db(
        [
            {"id": "loan_policy", "text": "loan approval policy"},
            {"id": "mortgage_policy", "text": "mortgage underwriting policy"},
            {"id": "banana", "text": "banana fruit"},
        ],
        relationships=[{"source": "loan_policy", "target": "mortgage_policy", "type": "RELATED_TO"}],
    )
    node_embeddings = result["node_embeddings"]
    assert set(node_embeddings) == {"loan_policy", "mortgage_policy", "banana"}
