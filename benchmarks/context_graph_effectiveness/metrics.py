from __future__ import annotations

from collections import defaultdict
from math import log2
from typing import Callable, Iterable, Mapping, Sequence


def safe_mean(values: Iterable[float]) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    relevant_set = set(relevant)
    if k <= 0:
        return 0.0
    top_k = list(retrieved[:k])
    if not top_k:
        return 0.0
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(top_k)


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    relevant_set = set(relevant)
    if not relevant_set or k <= 0:
        return 0.0
    top_k = list(retrieved[:k])
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(relevant_set)


def hit_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    relevant_set = set(relevant)
    if not relevant_set or k <= 0:
        return 0.0
    return 1.0 if any(item in relevant_set for item in retrieved[:k]) else 0.0


def mrr(retrieved: Sequence[str], relevant: Iterable[str]) -> float:
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0
    for index, item in enumerate(retrieved, start=1):
        if item in relevant_set:
            return 1.0 / index
    return 0.0


def map_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    relevant_set = set(relevant)
    if not relevant_set or k <= 0:
        return 0.0
    top_k = list(retrieved[:k])
    hits = 0
    precision_sum = 0.0
    for index, item in enumerate(top_k, start=1):
        if item in relevant_set:
            hits += 1
            precision_sum += hits / index
    return precision_sum / min(len(relevant_set), k) if hits else 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Iterable[str] | Mapping[str, float], k: int) -> float:
    if k <= 0:
        return 0.0
    if isinstance(relevant, Mapping):
        relevance_map = {str(key): float(value) for key, value in relevant.items()}
    else:
        relevance_map = {str(item): 1.0 for item in relevant}
    if not relevance_map:
        return 0.0

    dcg = 0.0
    for index, item in enumerate(retrieved[:k], start=1):
        gain = relevance_map.get(item, 0.0)
        if gain > 0:
            dcg += (2**gain - 1) / log2(index + 1)

    ideal_gains = sorted(relevance_map.values(), reverse=True)[:k]
    idcg = sum((2**gain - 1) / log2(index + 1) for index, gain in enumerate(ideal_gains, start=1))
    return dcg / idcg if idcg else 0.0


def confusion_counts(expected_positive: Sequence[bool], predicted_positive: Sequence[bool]) -> dict[str, int]:
    tp = sum(1 for exp, pred in zip(expected_positive, predicted_positive) if exp and pred)
    fp = sum(1 for exp, pred in zip(expected_positive, predicted_positive) if not exp and pred)
    fn = sum(1 for exp, pred in zip(expected_positive, predicted_positive) if exp and not pred)
    tn = sum(1 for exp, pred in zip(expected_positive, predicted_positive) if not exp and not pred)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def accuracy_score(expected: Sequence[str], predicted: Sequence[str]) -> float:
    if not expected:
        return 0.0
    correct = sum(1 for exp, pred in zip(expected, predicted) if exp == pred)
    return correct / len(expected)


def accuracy(expected_positive: Sequence[bool], predicted_positive: Sequence[bool]) -> float:
    counts = confusion_counts(expected_positive, predicted_positive)
    total = counts["tp"] + counts["tn"] + counts["fp"] + counts["fn"]
    return (counts["tp"] + counts["tn"]) / total if total else 0.0


def precision_recall_f1(expected_positive: Sequence[bool], predicted_positive: Sequence[bool]) -> tuple[float, float, float]:
    counts = confusion_counts(expected_positive, predicted_positive)
    precision = counts["tp"] / (counts["tp"] + counts["fp"]) if (counts["tp"] + counts["fp"]) else 0.0
    recall = counts["tp"] / (counts["tp"] + counts["fn"]) if (counts["tp"] + counts["fn"]) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def brier_score(expected_positive: Sequence[bool], predicted_probability: Sequence[float]) -> float:
    if not expected_positive:
        return 0.0
    squared_error = []
    for exp, prob in zip(expected_positive, predicted_probability):
        label = 1.0 if exp else 0.0
        squared_error.append((prob - label) ** 2)
    return safe_mean(squared_error)


def expected_calibration_error(
    expected_positive: Sequence[bool],
    predicted_probability: Sequence[float],
    num_bins: int = 10,
) -> float:
    if not expected_positive or num_bins <= 0:
        return 0.0
    bins: dict[int, list[tuple[bool, float]]] = defaultdict(list)
    for exp, prob in zip(expected_positive, predicted_probability):
        clipped = min(max(prob, 0.0), 1.0)
        bin_index = min(int(clipped * num_bins), num_bins - 1)
        bins[bin_index].append((exp, clipped))

    total = len(expected_positive)
    ece = 0.0
    for bucket in bins.values():
        if not bucket:
            continue
        accuracy_bucket = safe_mean(1.0 if exp else 0.0 for exp, _ in bucket)
        confidence_bucket = safe_mean(prob for _, prob in bucket)
        ece += (len(bucket) / total) * abs(accuracy_bucket - confidence_bucket)
    return ece


def risk_coverage_points(expected_positive: Sequence[bool], predicted_probability: Sequence[float]) -> list[dict[str, float]]:
    if not expected_positive:
        return []
    ranked = sorted(zip(expected_positive, predicted_probability), key=lambda item: item[1], reverse=True)
    accepted = 0
    errors = 0
    total = len(ranked)
    points = []
    for exp, _ in ranked:
        accepted += 1
        if not exp:
            errors += 1
        coverage = accepted / total
        risk = errors / accepted if accepted else 0.0
        points.append({"coverage": coverage, "risk": risk})
    return points


def abstain_quality(correct_abstentions: int, total_abstention_cases: int) -> float:
    return correct_abstentions / total_abstention_cases if total_abstention_cases else 0.0


def relative_lift(metric_value: float, baseline_value: float) -> float:
    if baseline_value == 0:
        return 0.0 if metric_value == 0 else float("inf")
    return (metric_value - baseline_value) / abs(baseline_value)


def absolute_lift(metric_value: float, baseline_value: float) -> float:
    return metric_value - baseline_value


def slice_records(records: Sequence[dict], key_fn: Callable[[dict], str]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[key_fn(record)].append(record)
    return dict(grouped)


def bucket_hop_depth(depth: int | None) -> str:
    if depth is None or depth <= 1:
        return "1-hop"
    if depth == 2:
        return "2-hop"
    if depth == 3:
        return "3-hop"
    return "4+-hop"


def normalize_decision_label(label: str | None) -> str:
    if label is None:
        return "unknown"
    lowered = str(label).strip().lower()
    if any(token in lowered for token in ["approve", "approved", "accept"]):
        return "approve"
    if any(token in lowered for token in ["reject", "rejected", "deny", "denied"]):
        return "reject"
    if any(token in lowered for token in ["escalate", "review", "manual"]):
        return "escalate"
    return lowered


def extract_node_ids(results: Sequence[object]) -> list[str]:
    extracted: list[str] = []
    for item in results:
        metadata = getattr(item, "metadata", {}) or {}
        node_id = metadata.get("node_id") or metadata.get("id")
        if node_id is None:
            node_id = getattr(item, "node_id", None)
        if node_id is None:
            node_id = getattr(item, "content", None)
        if node_id is None:
            continue
        node_id = str(node_id)
        if node_id.startswith("anchor::"):
            continue
        extracted.append(node_id)
    return extracted
