THRESHOLDS = {
    "decision_accuracy_delta": 0.0,
    "hallucination_rate_delta": 0.0,
    "stale_context_injection_rate": 0.05,
    "causal_chain_recall": 0.80,
    "causal_chain_precision": 0.85,
    "policy_compliance_hit_rate": 0.90,
    "temporal_precision": 0.90,
    "provenance_lineage_completeness": 1.0,
    "duplicate_detection_f1": 0.85,
    "skill_activation_rate": 0.70,
    "explanation_completeness": 0.90
}

def check_thresholds(metrics: dict) -> list[str]:
    """
    Validates a dictionary of metric results against the defined THRESHOLDS.
    Returns a list of error messages for any failed thresholds.
    """
    errors = []
    
    # Positive deltas
    for key in ["decision_accuracy_delta", "hallucination_rate_delta"]:
        if key in metrics and metrics[key] <= THRESHOLDS[key]:
            errors.append(f"{key} must be > {THRESHOLDS[key]}, got {metrics[key]}")
            
   
    if "stale_context_injection_rate" in metrics and metrics["stale_context_injection_rate"] >= THRESHOLDS["stale_context_injection_rate"]:
        errors.append(f"stale_context_injection_rate must be < {THRESHOLDS['stale_context_injection_rate']}, got {metrics['stale_context_injection_rate']}")
        

    lower_bound_keys = [
        "causal_chain_recall", "causal_chain_precision", "policy_compliance_hit_rate",
        "temporal_precision", "duplicate_detection_f1", "skill_activation_rate", "explanation_completeness"
    ]
    for key in lower_bound_keys:
        if key in metrics and metrics[key] < THRESHOLDS[key]:
            errors.append(f"{key} must be >= {THRESHOLDS[key]}, got {metrics[key]}")
            

    if "provenance_lineage_completeness" in metrics and metrics["provenance_lineage_completeness"] != THRESHOLDS["provenance_lineage_completeness"]:
        errors.append(f"provenance_lineage_completeness must be == {THRESHOLDS['provenance_lineage_completeness']}, got {metrics['provenance_lineage_completeness']}")
        
    return errors
