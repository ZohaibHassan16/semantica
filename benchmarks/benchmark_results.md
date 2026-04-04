# Semantica Benchmark Suite Results

## Executive Summary

- Throughput benchmarks remain separate from effectiveness benchmarks.
- The Context Graph Effectiveness suite is a manual benchmark suite, not a CI gate.
- The current validated offline deterministic suite result is: `139 passed, 12 skipped, 12 deselected`.
- Real-LLM benchmark tracks are auxiliary and run only when `SEMANTICA_REAL_LLM=1` is enabled.
- Results should be reported by run mode and track status, not as one undifferentiated aggregate claim.
- New effectiveness runs should also persist a machine-readable summary via `--effectiveness-report-json` under `benchmarks/results/`.

## Current Validation Snapshot

### Full Offline Deterministic Suite

Run command:

```bash
pytest benchmarks/context_graph_effectiveness/ -m "not real_llm" -q
```

Observed result on April 3, 2026:
- `139 passed`
- `12 skipped`
- `12 deselected`

Meaning:
- `passed`: benchmark completed and met its assertions
- `skipped`: benchmark intentionally did not run because an optional dependency, API path, or environment-specific capability was unavailable
- `deselected`: `real_llm` tracks excluded from the offline deterministic run

### Focused Deeper-Metrics Rerun

Run command:

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

Observed result:
- `71 passed`
- `1 skipped`

This focused rerun is the cleanest validation set for the expanded deeper-metrics implementation.

## Measurement Policy

We only report benchmark results here when assertions are derived from:
- actual Semantica API outputs
- labeled fixtures committed under `benchmarks/context_graph_effectiveness/fixtures/`
- explicit metric helpers such as precision, recall, F1, Hit@k, MRR, MAP, nDCG, ECE, and Brier score where relevant
- run artifacts captured from the effectiveness runner rather than manual suite totals copied by hand

We do not treat the following as valid benchmark evidence:
- hardcoded metric values
- `assert True` style tests
- mock-LLM output used as proof of effectiveness lift
- silent passes when a component is unavailable

## Measured Offline Tracks

These tracks now have methodology that supports real outputs, sample sizes, richer metric bundles, and benchmark-family reporting.

| Track | Status | Primary metrics |
|------|--------|-----------------|
| Retrieval | measured | `Precision@k`, `Recall@k`, `Hit@k`, `MRR`, `MAP@k`, `nDCG@k`, no-match false-positive rate |
| Decision Intelligence | measured | decision accuracy, policy compliance, precedent `Hit@1` / `MRR`, abstain correctness, conflict handling, ECE |
| Causal Chains | measured | causal precision / recall, root accuracy |
| Temporal Validity | measured | temporal precision / recall, stale / future injection rate |
| Conflict Resolution | measured | precision / recall, strategy correctness |
| Deduplication Quality | measured | precision / recall / F1 |
| Reasoning Quality | measured | inference correctness, explanation completeness |
| Embedding Quality | measured | coherence, batch consistency, reproducibility |
| Change Management | measured | snapshot fidelity, diff correctness |
| Provenance Integrity | measured | lineage completeness, checksum integrity |
| Semantic Metric Exactness | measured | metric exactness@1, alias resolution, dimension / grain conformance |
| Hybrid Metric Graph | measured | hybrid recall, policy linkage, causal root accuracy |
| Governance Impact | measured | impact score, impact precision, drift rate |
| Context Quality | measured | CRS, CNR, SCR, redundancy score |
| Semantic Extraction | measured | NER span F1, relation entity-pair detection, event recall |
| Extended Multi-hop | measured | bridge recall, comparison coverage, path completeness |
| Graph Structural Integrity | measured | triple retrieval rate, relation coverage, structural consistency |
| Abductive / Deductive Reasoning | measured | explanation coverage, deductive chain recall |
| SES Composite | measured | component aggregation and regression floor |
| Entity Linking / Graph Validation | measured | entity-linker precision / recall, validator false-positive rate |
| KG Algorithms | measured | centrality, community detection, optional embedder / path-finder coverage |

## Manual Real-LLM Tracks

These tracks are intentionally excluded from offline measured totals.

| Track | Status | Run mode |
|------|--------|----------|
| Decision Quality | `real_llm` | manual only |
| Skill Injection | `real_llm` | manual only |
| NL Governed Decision | `real_llm` | manual only |

## Baseline Reporting Expectations

Major track reports should include:
- sample size
- threshold floor
- baseline value
- measured value
- absolute lift
- relative lift where meaningful
- slice breakdown

Current baseline families in the suite:
- lexical baseline
- embedding baseline
- traversal baseline
- flat metric text baseline
- no semantic layer baseline
- no-context LLM baseline
- flat-context LLM baseline
- structured graph / semantic-layer context baseline

## Slice Reporting Expectations

Retrieval slices:
- direct lookup
- 2-hop
- 3-hop
- 4+-hop
- temporal queries
- causal queries
- no-match queries

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
- change-type slices
- metric family slices

## Reporting Guidance

When publishing benchmark numbers:
- name the dataset and sample size
- state whether the run is deterministic or `real_llm`
- show the exact formulas used
- report baseline and lift, not only threshold pass/fail
- label tracks as `measured`, `partial`, `skipped`, or `real_llm`
- avoid aggregate suite claims that mix deterministic and model-dependent evidence

## Notes

The current offline suite passes end-to-end in this environment. The remaining skips are environment-dependent benchmark paths rather than benchmark-logic failures.
