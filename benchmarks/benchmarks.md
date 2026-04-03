# Semantica Benchmark Suite

## Purpose

This document defines how Semantica benchmarks the effectiveness of context graphs, decision intelligence, and semantic layers without relying on hardcoded benchmark values.

The suite is intentionally hybrid:
- **Offline deterministic core** for reproducible, dataset-driven measurement
- **Manual real-LLM auxiliary layer** for prompt-time lift, policy-grounding, and semantic-layer behavior

Benchmarks are manual and offline by design. They are not part of CI and should not block merges.

## Current Validation Status

Latest offline deterministic validation run:

```bash
pytest benchmarks/context_graph_effectiveness/ -m "not real_llm" -q
```

Observed result on April 3, 2026:
- `139 passed`
- `12 skipped`
- `12 deselected`

Interpretation:
- `passed`: benchmark track or scenario completed and met its assertions
- `skipped`: the benchmark intentionally did not run because the required optional component or API shape was not available in the current environment
- `deselected`: `real_llm` tracks excluded from the offline deterministic run

This result is the current reference point for the offline benchmark core. Real-LLM auxiliary tracks remain separate.

## Principles

- Every passing benchmark should derive its assertion from actual Semantica outputs.
- Labeled fixtures are the source of truth for scoring.
- Thresholds are regression floors, not the only benchmark signal.
- Major tracks should report baselines, slice breakdowns, and sample sizes.
- Mock LLMs are acceptable for shape tests, not for headline effectiveness claims.
- Any benchmark that cannot yet be measured honestly should be marked `partial` or `skipped`.

## Benchmark Families

### 1. Context Graph Retrieval

Why it exists:
Semantica's core claim is not just generic retrieval quality, but retrieval quality on graph-native queries: direct lookup, multi-hop traversal, temporal filtering, causal traversal, and no-match handling.

What it measures:
- node retrieval quality
- traversal completeness
- stale or noisy context contamination
- baseline lift from hybrid graph-aware retrieval

### 2. Decision Intelligence

Why it exists:
Decision systems need more than answer accuracy. They must apply policies, retrieve precedents, handle conflict, and abstain or escalate when the graph does not justify an answer.

What it measures:
- decision correctness
- policy compliance
- precedent quality
- hard-case handling
- confidence quality and abstention quality

### 3. Semantic Layer Effectiveness

Why it exists:
A semantic layer is valuable only if it keeps governed metrics correct and consistent across queries, follow-up turns, and downstream decisions.

What it measures:
- metric exactness
- alias resolution
- dimension and grain conformance
- change propagation
- cross-turn consistency

### 4. Trustworthy Context

Why it exists:
Context graphs only help if the context is trustworthy. That means provenance, change tracking, context relevance, and low noise.

What it measures:
- provenance completeness
- checksum integrity
- context relevance / noise
- snapshot fidelity
- governance impact precision

## Core Metrics And Formulas

This suite uses a small set of reusable metric families. The same formulas should be reused across tracks where possible.

### 1. Classification Metrics

Used in:
- deduplication quality
- conflict detection
- policy compliance
- semantic-layer exactness checks
- rubric scoring for real-LLM tracks

Definitions:
- `TP`: true positives
- `FP`: false positives
- `FN`: false negatives
- `TN`: true negatives

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
Accuracy  = (TP + TN) / (TP + TN + FP + FN)
```

### 2. Ranking Metrics

Used in:
- retrieval benchmarks
- precedent retrieval
- graph-native ranking comparisons

Definitions:
- `R_k`: top-`k` returned items
- `Rel`: relevant items for a query
- `rank_i`: rank of the first correct item for query `i`
- `Q`: set of evaluated queries

```text
Precision@k = |R_k n Rel| / |R_k|
Recall@k    = |R_k n Rel| / |Rel|
Hit@k       = 1 if R_k n Rel is non-empty, else 0
MRR         = (1 / |Q|) * S_i (1 / rank_i)
MAP@k       = mean of per-query average precision at k
```

Optional graded ranking metric:

```text
DCG@k  = S_i ((2^rel_i - 1) / log2(i + 1))
nDCG@k = DCG@k / IDCG@k
```

### 3. Decision Metrics

Used in:
- decision intelligence
- decision quality
- governed decision tracks

```text
Decision Accuracy      = correct_decisions / total_decisions
Policy Compliance Rate = compliant_decisions / applicable_policy_cases
Abstain Correctness    = correct_abstentions / no-policy_cases
Conflict Handling Rate = correct_conflict_resolutions / conflict_cases
```

Precedent retrieval reuses ranking metrics:

```text
Precedent Hit@k = relevant_precedent_found / total_queries
Precedent MRR   = (1 / |Q|) * S_i (1 / rank_i)
```

### 4. Temporal Metrics

Used in:
- temporal validity
- time-aware retrieval
- stale/future contamination checks

A node is valid at time `t` when:

```text
valid(node, t) =
  node.valid_from <= t
  and
  (node.valid_until is None or t < node.valid_until)
```

```text
Temporal Precision    = valid_retrieved_items / total_retrieved_items
Temporal Recall       = valid_retrieved_items / total_valid_relevant_items
Stale Injection Rate  = stale_retrieved_items / total_retrieved_items
Future Injection Rate = future_retrieved_items / total_retrieved_items
```

### 5. Causal Metrics

Used in:
- causal chain quality
- hybrid metric-graph reasoning

```text
Causal Precision = correctly_retrieved_causal_nodes / retrieved_causal_nodes
Causal Recall    = correctly_retrieved_causal_nodes / expected_causal_nodes
Root Accuracy    = correct_root_predictions / total_cases
Depth Accuracy   = correct_depth_predictions / total_cases
```

### 6. Confidence And Calibration Metrics

Used in:
- decision intelligence
- manual real-LLM decision tracks

```text
Brier Score = mean((predicted_probability - observed_label)^2)
ECE         = S_bins (bin_weight * |bin_accuracy - bin_confidence|)
```

Risk / coverage reporting:
- sort predictions by confidence
- compute coverage as accepted predictions / total predictions
- compute risk as errors / accepted predictions

### 7. Provenance And Change Metrics

Used in:
- provenance integrity
- change management
- governance impact

```text
Lineage Completeness   = recovered_lineage_hops / expected_lineage_hops
Checksum Integrity     = checksum_verified_entities / total_verified_entities
Snapshot Fidelity      = correctly_restored_items / expected_items
Change Impact Accuracy = correctly_identified_impacts / expected_impacts
Decision Drift Rate    = changed_decisions_after_update / affected_decisions
```

### 8. Embedding Metrics

Used in:
- embedding quality
- graph similarity checks

```text
Semantic Coherence Delta = mean(similar_pairs) - mean(random_pairs)
Batch Consistency        = mean(|batch_embedding - single_embedding|)
Reproducibility Rate     = identical_recomputations / total_recomputations
```

### 9. Semantic Layer Metrics

Used in:
- semantic metric exactness
- governance impact
- agentic consistency

```text
Metric Exactness@1        = correct_top_metric_predictions / total_queries
Alias Resolution Accuracy = correct_alias_resolutions / alias_queries
Dimension Conformance     = correct_dimension_choices / checked_queries
Grain Conformance         = correct_grain_choices / checked_queries
Cross-turn Consistency    = consistent_followup_answers / multi_turn_traces
```

### 10. Real-LLM Auxiliary Metrics

Used in:
- decision quality delta
- skill injection
- NL-to-governed-decision

```text
Decision Accuracy Delta    = accuracy_with_context - accuracy_without_context
Hallucination Rate         = unsupported_claims / total_claims
Hallucination Rate Delta   = hallucination_without_context - hallucination_with_context
Skill Activation Rate      = correctly_activated_skill_cases / total_skill_cases
Citation Groundedness Rate = grounded_citations / cited_claims
```

## Slice Definitions

Major tracks should report slice-level performance instead of only one aggregate number.

Retrieval slices:
- direct lookup
- 2-hop
- 3-hop
- 4+-hop
- temporal queries
- causal queries
- no-match queries
- multi-source merge queries

Decision slices:
- lending
- healthcare
- legal
- HR
- e-commerce
- boundary cases
- conflicting-policy cases
- overturned-precedent cases
- no-applicable-policy cases

Semantic-layer slices:
- time-grain queries
- no-time-grain queries
- alias-heavy queries
- change-type slices
- metric family slices

## Baseline Definitions

Thresholds remain useful as floors, but benchmark reporting should also compare Semantica against clear baselines.

Offline baselines:
- **lexical baseline**: keyword-only or name-overlap style retrieval
- **embedding baseline**: embedding-only retrieval with no graph structure
- **traversal baseline**: raw graph reachability without ranking fusion
- **flat metric text baseline**: match against metric names, labels, aliases, descriptions as plain text
- **no semantic layer baseline**: weak heuristic metric guessing without governed structure

Manual real-LLM baselines:
- **no-context baseline**: user prompt only
- **flat-context baseline**: plain text context block
- **structured graph / semantic-layer baseline**: graph-derived or governed structured context

For major tracks, report:
- metric value
- threshold floor
- baseline value
- absolute lift
- relative lift when meaningful
- sample size
- slice breakdown

## Datasets And Record Types

Datasets live under `benchmarks/context_graph_effectiveness/fixtures/`.

Current dataset families include:
- retrieval fixtures
- decision intelligence fixtures
- temporal fixtures
- causal fixtures
- deduplication gold pairs
- provenance fixtures
- semantic extraction fixtures
- semantic-layer fixtures
- multihop fixtures
- graph integrity fixtures

Important record types already present in fixtures:
- direct lookup, multi-hop, temporal, causal, no-match retrieval queries
- cross-domain decision records
- boundary cases
- conflicting-policy cases
- overturned-precedent cases
- governed metric NL queries
- metric change before/after pairs
- hybrid metric + policy + causal graph records
- agentic conversation traces

Dataset documentation for each benchmark family should capture:
- source or provenance
- label semantics
- whether the record is real, transformed, or synthetic
- expected benchmark consumer

## Deterministic Vs Real-LLM Separation

### Offline deterministic core

Use for:
- retrieval
- temporal validity
- causal chains
- decision intelligence
- deduplication
- provenance
- semantic metric exactness
- governance impact
- hybrid metric graph
- agentic consistency where no model call is required

Requirements:
- all assertions derived from real outputs and labeled fixtures
- no hardcoded benchmark numbers used as result values
- results should be reproducible locally

Current offline suite status:
- validated with `139 passed, 12 skipped, 12 deselected`
- skips currently represent optional or environment-dependent benchmark paths, not CI failures

### Manual real-LLM auxiliary layer

Use for:
- decision quality delta
- skill injection
- NL governed decision
- semantic-layer prompt lift

Requirements:
- gated behind `SEMANTICA_REAL_LLM=1`
- fixed prompts and fixed model configuration
- compare at least two prompt conditions
- no mock output used as evidence of lift

## Manual Run Modes

Offline deterministic benchmarks:

```bash
pytest benchmarks/context_graph_effectiveness/ -m "not real_llm"
```

Manual real-LLM benchmarks:

```bash
pytest benchmarks/context_graph_effectiveness/ -m "real_llm"
```

Focused rerun for the expanded deeper-metrics core:

```bash
pytest benchmarks/context_graph_effectiveness/test_retrieval.py \
  benchmarks/context_graph_effectiveness/test_decision_intelligence.py \
  benchmarks/context_graph_effectiveness/test_semantic_metric_exactness.py \
  benchmarks/context_graph_effectiveness/test_hybrid_metric_graph.py \
  benchmarks/context_graph_effectiveness/test_governance_impact.py \
  benchmarks/context_graph_effectiveness/test_temporal_validity.py \
  benchmarks/context_graph_effectiveness/test_causal_chains.py \
  benchmarks/context_graph_effectiveness/test_conflict_resolution.py \
  benchmarks/context_graph_effectiveness/test_provenance_integrity.py -q
```

Observed result for that focused set:
- `71 passed`
- `1 skipped`

## Track Status Guidance

Use these labels in benchmark reports:
- `measured`: metric derived from actual outputs and labeled fixtures
- `partial`: some real computation exists, but the track still needs audit or expansion
- `skipped`: intentionally not evaluated in the current environment
- `real_llm`: manual auxiliary benchmark, not part of offline totals

## Reporting Template

When publishing benchmark results, include:
- track name
- dataset and sample size
- deterministic or `real_llm` run mode
- formulas used
- threshold floor
- baseline value
- measured value
- absolute lift
- relative lift if meaningful
- slice breakdown
- open limitations or skips

Recommended conference-facing framing:
- lead with graph-native retrieval and decision metrics
- support with provenance / governance / semantic consistency metrics
- separate deterministic evidence from auxiliary model-dependent lift

## Current Direction

The benchmark suite is being strengthened track-by-track to deepen metrics rather than simply adding more categories. The goal is a research-grade benchmark reference that combines reproducible offline measurement with carefully scoped manual real-LLM evaluations.
