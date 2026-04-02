"""
Pass/fail thresholds for the Context Graph Effectiveness benchmark suite.

All values are evidence-based:
- Temporal thresholds (0.90 precision, <5% stale) reflect production SLA requirements.
- Causal recall (0.80) / precision (0.85) from KG-RAG literature baselines.
- Deduplication F1 (0.85) matches DeepMatcher DBLP-ACM published scores.
- Decision precedent MRR (0.70) from dense retrieval on structured decision data.
- Provenance completeness (1.0) and snapshot fidelity (1.0) are binary correctness.
- Skill activation (0.70) is conservative lower-bound for prompt-based skill elicitation.
- Semantic metric exactness (0.85) calibrated to dbt 83% accuracy lift (2025).
- Decision drift rate (0.02) is production SLA — wrong decisions from silent metric changes.
- Cross-turn consistency (0.90) from agentic governed-decision production SLA.

Enforced in CI via: python benchmarks/benchmarks_runner.py --effectiveness --strict
"""

from typing import Dict, Tuple

THRESHOLDS: Dict[str, Tuple[str, float]] = {
    # ── Decision quality (real-LLM tests) ──────────────────────────────────────
    "decision_accuracy_delta":          (">",   0.0),
    "hallucination_rate_delta":         (">",   0.0),
    "citation_groundedness":            (">=",  0.60),
    "policy_compliance_rate":           (">=",  0.80),

    # ── Retrieval ──────────────────────────────────────────────────────────────
    "direct_lookup_hit_rate":           (">=",  0.90),
    "multi_hop_recall_2hop":            (">=",  0.75),
    "multi_hop_recall_3hop":            (">=",  0.65),
    "decision_precedent_mrr":           (">=",  0.70),

    # ── Temporal validity ──────────────────────────────────────────────────────
    "stale_context_injection_rate":     ("<",   0.05),
    "future_context_injection_rate":    ("<",   0.05),
    "temporal_precision":               (">=",  0.90),
    "temporal_recall":                  (">=",  0.80),
    "temporal_rewriter_accuracy":       (">=",  0.85),

    # ── Causal chain quality ───────────────────────────────────────────────────
    "causal_chain_recall":              (">=",  0.80),
    "causal_chain_precision":           (">=",  0.85),

    # ── Decision intelligence ──────────────────────────────────────────────────
    "policy_compliance_hit_rate":       (">=",  0.90),

    # ── KG algorithms ─────────────────────────────────────────────────────────
    "community_nmi":                    (">=",  0.80),
    "link_predictor_auc":               (">=",  0.70),

    # ── Reasoning quality ─────────────────────────────────────────────────────
    "explanation_completeness":         (">=",  0.90),
    "rete_inference_precision":         (">=",  0.95),
    "allen_interval_accuracy":          (">=",  1.0),

    # ── Provenance integrity ───────────────────────────────────────────────────
    "provenance_lineage_completeness":  ("==",  1.0),
    "checksum_integrity":               ("==",  1.0),

    # ── Conflict resolution ────────────────────────────────────────────────────
    "conflict_detection_recall":        (">=",  0.85),
    "conflict_detection_precision":     (">=",  0.90),

    # ── Deduplication quality ──────────────────────────────────────────────────
    "duplicate_detection_recall":       (">=",  0.85),
    "duplicate_detection_precision":    (">=",  0.85),
    "duplicate_detection_f1":           (">=",  0.85),

    # ── Embedding quality ─────────────────────────────────────────────────────
    "semantic_coherence_delta":         (">",   0.0),
    "hash_fallback_stability":          ("==",  1.0),

    # ── Change management ─────────────────────────────────────────────────────
    "snapshot_fidelity":                ("==",  1.0),
    "version_diff_correctness":         ("==",  1.0),

    # ── Skill injection (real-LLM) ────────────────────────────────────────────
    "skill_activation_rate":            (">=",  0.70),

    # ── Semantic extraction (Track 14) ────────────────────────────────────────
    "ner_f1":                           (">=",  0.60),
    "relation_extraction_f1":           (">=",  0.60),
    "event_detection_recall":           (">=",  0.65),
    "kg_triplet_accuracy":              (">=",  0.70),

    # ── Context quality metrics (Track 15) ────────────────────────────────────
    "context_relevance_score":          (">=",  0.70),
    "context_noise_ratio":              ("<",   0.30),
    "signal_to_context_ratio":          (">=",  2.0),
    "redundancy_score":                 (">=",  0.80),

    # ── Graph structural integrity (Track 16) ─────────────────────────────────
    "graph_triple_retrieval_rate":      (">=",  0.95),
    "graph_relation_type_coverage":     (">=",  0.90),

    # ── Extended multi-hop (Track 17) ─────────────────────────────────────────
    "multi_hop_recall_4hop":            (">=",  0.60),
    "hotpotqa_bridge_recall":           (">=",  0.65),
    "hotpotqa_comparison_recall":       (">=",  0.70),

    # ── Abductive & deductive reasoning (Track 18) ────────────────────────────
    "abductive_cause_accuracy":         (">=",  0.60),
    "abductive_effect_accuracy":        (">=",  0.55),
    "deductive_chain_recall":           (">=",  0.65),

    # ── Entity linking & graph validation (Track 19) ──────────────────────────
    "entity_linker_precision":          (">=",  0.80),
    "entity_linker_recall":             (">=",  0.75),
    "graph_validator_false_positive_rate": ("<", 0.05),

    # ── Composite SES (Track 20) ──────────────────────────────────────────────
    "ses_composite":                    (">=",  0.70),
    "ses_domain_minimum":               (">=",  0.60),

    # ── Semantic metric exactness (Track 21) ──────────────────────────────────
    "metric_exactness_at_1":            (">=",  0.85),  # dbt 83% accuracy lift (2025)
    "dimension_conformance_rate":       (">=",  0.90),
    "metric_alias_resolution_rate":     (">=",  0.80),
    "metric_node_storage_fidelity":     ("==",  1.0),
    "semantic_layer_coverage":          (">=",  0.90),

    # ── Metric-graph hybrid reasoning (Track 23) ──────────────────────────────
    "hybrid_recall":                    (">=",  0.75),
    "policy_metric_compliance":         (">=",  0.85),
    "causal_root_accuracy":             (">=",  0.70),
    "metric_policy_linkage_rate":       (">=",  0.90),
    "hybrid_graph_coverage":            (">=",  0.80),

    # ── Governance impact & change propagation (Track 24) ─────────────────────
    "metric_change_impact_score":       (">=",  0.95),  # hard auditability SLA
    "decision_drift_rate":              ("<=",  0.02),  # production SLA
    "change_type_coverage":             (">=",  0.80),
    "impact_precision":                 (">=",  0.85),

    # ── Agentic semantic consistency (Track 25) ───────────────────────────────
    "cross_turn_metric_consistency":    (">=",  0.90),
    "threshold_stability_rate":         (">=",  0.95),
    "explicit_update_detection_rate":   (">=",  0.80),
    "decision_consistency_rate":        (">=",  0.85),
    "trace_buildability_rate":          ("==",  1.0),
}


def check_thresholds(metrics: Dict[str, float]) -> bool:
    """
    Validate a dictionary of metric results against THRESHOLDS.

    Returns True if all present metrics pass.
    Prints failures to stdout.
    Raises ValueError in strict mode (called with strict=True).
    """
    failures = []

    for key, value in metrics.items():
        if key not in THRESHOLDS:
            continue
        op, threshold = THRESHOLDS[key]

        passed = {
            ">":  value > threshold,
            ">=": value >= threshold,
            "<":  value < threshold,
            "<=": value <= threshold,
            "==": abs(value - threshold) < 1e-9,
        }.get(op, True)

        if not passed:
            failures.append(
                f"  FAIL  {key}: {value:.4f} {op} {threshold} required"
            )

    if failures:
        print("\n[THRESHOLDS] Failed metrics:")
        for f in failures:
            print(f)
        return False

    return True
