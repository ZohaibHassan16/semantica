from __future__ import annotations

from collections import defaultdict

import pytest

from benchmarks.context_graph_effectiveness.metrics import (
    absolute_lift,
    bucket_hop_depth,
    extract_node_ids,
    hit_at_k,
    map_at_k,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    relative_lift,
    safe_mean,
    slice_records,
)
from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.context import ContextGraph
from semantica.context.context_retriever import ContextRetriever, RetrievedContext


def _materialize_record_graph(record: dict) -> tuple[ContextGraph, str]:
    graph = ContextGraph(advanced_analytics=True)
    query_type = record["query_type"]
    relevant_ids = list(record.get("relevant_node_ids", []))
    irrelevant_ids = list(record.get("irrelevant_node_ids", []))
    anchor_id = f"anchor::{record['id']}"

    if query_type != "no_match":
        graph.add_node(anchor_id, "QueryAnchor", content=record["query"])

    for index, node_id in enumerate(relevant_ids):
        content = f"{record['query']} relevant context {node_id}"
        metadata = {}
        if query_type == "temporal" and record.get("at_time"):
            metadata["valid_from"] = "2020-01-01T00:00:00+00:00"
            metadata["valid_until"] = "2030-01-01T00:00:00+00:00"
        graph.add_node(node_id, "Evidence", content=content, **metadata)
        if query_type in {"direct_lookup", "temporal"}:
            graph.add_edge(anchor_id, node_id, "RELATED_TO", weight=1.0)
        else:
            source = anchor_id if index == 0 else relevant_ids[index - 1]
            edge_type = "CAUSED" if query_type == "causal" else "RELATED_TO"
            graph.add_edge(source, node_id, edge_type, weight=1.0)

    for node_id in irrelevant_ids:
        distractor_metadata = {}
        if query_type == "temporal" and record.get("at_time"):
            distractor_metadata["valid_from"] = "2035-01-01T00:00:00+00:00"
            distractor_metadata["valid_until"] = "2036-01-01T00:00:00+00:00"
        graph.add_node(node_id, "Distractor", content=f"Irrelevant distractor {node_id}", **distractor_metadata)

    return graph, anchor_id


def _ranked_ids(record: dict, mode: str) -> list[str]:
    graph, anchor_id = _materialize_record_graph(record)

    if mode == "traversal":
        frontier = {anchor_id}
        reached = []
        visited = {anchor_id}
        for _ in range(max(record.get("expected_hop_depth", 1), 1)):
            next_frontier = set()
            for current in frontier:
                for neighbor in graph.get_neighbor_ids(current) or []:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        reached.append(str(neighbor))
                        next_frontier.add(neighbor)
            frontier = next_frontier
        return reached

    hybrid_alpha = {"lexical": 0.0, "hybrid": 0.5, "embedding": 1.0}[mode]
    retriever = ContextRetriever(
        knowledge_graph=graph,
        use_graph_expansion=True,
        max_expansion_hops=max(record.get("expected_hop_depth", 1), 1),
        hybrid_alpha=hybrid_alpha,
    )
    results = retriever.retrieve(
        record["query"],
        max_results=max(len(record.get("relevant_node_ids", [])) + len(record.get("irrelevant_node_ids", [])), 5),
    )
    return extract_node_ids(results)


def _record_metrics(record: dict, mode: str) -> dict[str, float]:
    retrieved_ids = _ranked_ids(record, mode)
    relevant_ids = record.get("relevant_node_ids", [])
    graded = {node_id: 1.0 for node_id in relevant_ids}
    return {
        "precision@1": precision_at_k(retrieved_ids, relevant_ids, 1),
        "precision@3": precision_at_k(retrieved_ids, relevant_ids, 3),
        "precision@5": precision_at_k(retrieved_ids, relevant_ids, 5),
        "recall@1": recall_at_k(retrieved_ids, relevant_ids, 1),
        "recall@3": recall_at_k(retrieved_ids, relevant_ids, 3),
        "recall@5": recall_at_k(retrieved_ids, relevant_ids, 5),
        "hit@1": hit_at_k(retrieved_ids, relevant_ids, 1),
        "hit@3": hit_at_k(retrieved_ids, relevant_ids, 3),
        "mrr": mrr(retrieved_ids, relevant_ids),
        "map@5": map_at_k(retrieved_ids, relevant_ids, 5),
        "ndcg@5": ndcg_at_k(retrieved_ids, graded, 5),
    }


def _aggregate_metrics(records: list[dict], mode: str) -> dict[str, float]:
    per_record = [_record_metrics(record, mode) for record in records]
    if not per_record:
        return {}
    return {metric: safe_mean(values[metric] for values in per_record) for metric in per_record[0]}


def _slice_metrics(records: list[dict], mode: str, key_fn) -> dict[str, dict[str, float]]:
    return {slice_name: _aggregate_metrics(slice_records_list, mode) for slice_name, slice_records_list in slice_records(records, key_fn).items()}


def _no_match_false_positive_rate(records: list[dict], mode: str) -> float:
    false_hit_rates = []
    for record in records:
        retrieved_ids = _ranked_ids(record, mode)
        false_hit_rates.append(hit_at_k(retrieved_ids, record.get("irrelevant_node_ids", []), 1))
    return safe_mean(false_hit_rates)


@pytest.fixture(scope="module")
def retrieval_benchmark_report(retrieval_eval_dataset):
    records = retrieval_eval_dataset["records"]
    measurable = [record for record in records if record["query_type"] != "no_match"]
    report = {
        "sample_size": len(records),
        "slices": {
            "query_type": _slice_metrics(measurable, "hybrid", lambda record: record["query_type"]),
            "hop_depth": _slice_metrics(
                [record for record in measurable if record["query_type"] == "multi_hop"],
                "traversal",
                lambda record: bucket_hop_depth(record.get("expected_hop_depth")),
            ),
        },
        "baselines": {
            "lexical": _aggregate_metrics(measurable, "lexical"),
            "embedding": _aggregate_metrics(measurable, "embedding"),
            "traversal": _aggregate_metrics([record for record in measurable if record["query_type"] == "multi_hop"], "traversal"),
            "hybrid": _aggregate_metrics(measurable, "hybrid"),
        },
        "no_match_false_positive_rate": {
            "lexical": _no_match_false_positive_rate([record for record in records if record["query_type"] == "no_match"], "lexical"),
            "embedding": _no_match_false_positive_rate([record for record in records if record["query_type"] == "no_match"], "embedding"),
            "hybrid": _no_match_false_positive_rate([record for record in records if record["query_type"] == "no_match"], "hybrid"),
        },
    }
    report["lift"] = {
        "hybrid_vs_lexical_mrr": absolute_lift(report["baselines"]["hybrid"]["mrr"], report["baselines"]["lexical"]["mrr"]),
        "hybrid_vs_embedding_mrr": absolute_lift(report["baselines"]["hybrid"]["mrr"], report["baselines"]["embedding"]["mrr"]),
        "hybrid_vs_lexical_recall@5": absolute_lift(
            report["baselines"]["hybrid"]["recall@5"],
            report["baselines"]["lexical"]["recall@5"],
        ),
    }
    return report


def test_lookup_hit_rate(retrieval_benchmark_report):
    direct = retrieval_benchmark_report["slices"]["query_type"]["direct_lookup"]
    assert direct["hit@1"] >= THRESHOLDS["direct_lookup_hit_rate"][1]
    assert direct["mrr"] >= 0.70


def test_multi_hop_traversal_recall(retrieval_benchmark_report):
    hop_slices = retrieval_benchmark_report["slices"]["hop_depth"]
    assert hop_slices["2-hop"]["recall@5"] >= THRESHOLDS["multi_hop_recall_2hop"][1]
    assert safe_mean(
        hop_slices[depth]["recall@5"] for depth in hop_slices if depth in {"3-hop", "4+-hop"}
    ) >= THRESHOLDS["multi_hop_recall_3hop"][1]


def test_graph_native_slices_are_measured(retrieval_benchmark_report):
    query_type_slices = retrieval_benchmark_report["slices"]["query_type"]
    assert {"direct_lookup", "multi_hop", "temporal", "causal"} <= set(query_type_slices)
    assert query_type_slices["temporal"]["recall@5"] > 0.0
    assert query_type_slices["causal"]["recall@5"] > 0.0


def test_hybrid_alpha_sensitivity(retrieval_benchmark_report):
    hybrid = retrieval_benchmark_report["baselines"]["hybrid"]
    lexical = retrieval_benchmark_report["baselines"]["lexical"]
    embedding = retrieval_benchmark_report["baselines"]["embedding"]

    assert hybrid["mrr"] >= lexical["mrr"]
    assert hybrid["recall@5"] >= lexical["recall@5"]
    assert hybrid["mrr"] >= embedding["mrr"]


def test_hybrid_beats_baselines_on_ranking_metrics(retrieval_benchmark_report):
    hybrid = retrieval_benchmark_report["baselines"]["hybrid"]
    lexical = retrieval_benchmark_report["baselines"]["lexical"]
    embedding = retrieval_benchmark_report["baselines"]["embedding"]

    assert absolute_lift(hybrid["mrr"], lexical["mrr"]) >= 0.0
    assert absolute_lift(hybrid["recall@5"], lexical["recall@5"]) >= 0.0
    assert relative_lift(hybrid["precision@3"], lexical["precision@3"]) >= 0.0
    assert absolute_lift(hybrid["mrr"], embedding["mrr"]) >= 0.0


def test_multi_source_boost_verification():
    retriever = ContextRetriever(hybrid_alpha=0.5)
    single = RetrievedContext(content="Single", score=0.3, source="vector:1", metadata={"node_id": "1"})
    dual_vector = RetrievedContext(content="Dual", score=0.8, source="vector:2", metadata={"node_id": "2"})
    dual_graph = RetrievedContext(content="Dual", score=0.8, source="graph:2", metadata={"node_id": "2"})

    merged = retriever._rank_and_merge([single, dual_vector, dual_graph], "query")
    merged_scores = {item.metadata.get("node_id"): item.score for item in merged}

    assert merged_scores["2"] > merged_scores["1"], "Shared graph+vector evidence should outrank single-source evidence"


def test_semantic_reranking_quality(retrieval_benchmark_report):
    hybrid = retrieval_benchmark_report["baselines"]["hybrid"]
    assert hybrid["precision@3"] >= 0.85
    assert hybrid["ndcg@5"] >= 0.85
    assert hybrid["map@5"] >= 0.85


def test_no_match_queries_do_not_claim_hits(retrieval_benchmark_report):
    false_positive_rate = retrieval_benchmark_report["no_match_false_positive_rate"]["hybrid"]
    assert false_positive_rate <= 0.20


def test_retrieval_report_contains_baselines_and_sample_size(retrieval_benchmark_report):
    assert retrieval_benchmark_report["sample_size"] >= 70
    assert {"lexical", "embedding", "traversal", "hybrid"} <= set(retrieval_benchmark_report["baselines"])
    assert "hybrid_vs_lexical_mrr" in retrieval_benchmark_report["lift"]
