# Semantica Benchmark Results

## Executive Summary

- All quality metrics are computed from real committed datasets — no synthetic graphs for headline numbers.
- The offline deterministic core covers 25 tracks across 2 pillars and runs in under 15 seconds with no API keys.
- Real-LLM tracks (Tracks 5, 13, 22) are auxiliary and run only when `SEMANTICA_REAL_LLM=1` is set.
- The composite score is **SES_v2 = 0.7 × ContextGraphScore + 0.3 × SemanticLayerScore ≥ 0.72**.
- Results are reported by run mode and track. No aggregate claim mixes deterministic and model-dependent evidence.

---

## Validation Snapshot

### Full Offline Suite

```bash
pytest benchmarks/context_graph_effectiveness/ -m "not real_llm" -q
```

Last validated: **April 2026** (post real-data migration)

| Label | Count |
|---|---|
| passed | — run locally to get current count |
| skipped | environment-dependent paths (optional deps) |
| deselected | `real_llm` tracks excluded from offline run |

### Core Pillar Tracks Only

```bash
pytest benchmarks/context_graph_effectiveness/test_retrieval.py \
  benchmarks/context_graph_effectiveness/test_causal_chains.py \
  benchmarks/context_graph_effectiveness/test_temporal_validity.py \
  benchmarks/context_graph_effectiveness/test_decision_intelligence.py \
  benchmarks/context_graph_effectiveness/test_deduplication_quality.py \
  benchmarks/context_graph_effectiveness/test_governance_impact.py \
  benchmarks/context_graph_effectiveness/test_extended_multihop.py \
  benchmarks/context_graph_effectiveness/test_ses_score.py -q
```

---

## Measured Offline Track Results

### Pillar 1 — Context Graph

#### Track 1 — Retrieval

| Metric | Threshold | Basis |
|---|---|---|
| direct_lookup hit@1 | ≥ 0.90 | — |
| 2-hop recall@5 | ≥ 0.75 | — |
| 3-hop recall@5 | ≥ 0.65 | — |
| hybrid MRR | ≥ lexical MRR | lift required |
| no-match false-positive rate | ≤ 0.20 | — |

Dataset: 70 retrieval eval records (direct_lookup, multi_hop, temporal, causal, no_match).  
Baselines: lexical, embedding, traversal, hybrid.

---

#### Track 2 — Temporal Validity

| Metric | Threshold | Basis |
|---|---|---|
| temporal_precision | ≥ 0.90 | Production SLA |
| temporal_recall | ≥ 0.80 | Production SLA |
| stale_context_injection_rate | < 0.05 | Production SLA |
| future_context_injection_rate | < 0.05 | Production SLA |
| temporal_rewriter_accuracy | ≥ 0.85 | — |

Dataset: **TimeQA 150 records** — real entity names, real temporal intent labels (before/after/at), real validity windows.  
Tests: before-intent precision/recall, after-intent precision/recall, entity version disambiguation, rewriter accuracy across all 150 questions, windowless node coverage.

---

#### Track 3 — Causal Chains

| Metric | Threshold | Basis |
|---|---|---|
| causal_chain_recall | ≥ 0.80 | KG-RAG literature |
| causal_chain_precision | ≥ 0.85 | KG-RAG literature |

Datasets: **ATOMIC 500 pairs** (Allen AI), **e-CARE 200 pairs**.

Test coverage:
- Pairwise recall on 100 ATOMIC pairs
- Multi-hop chain: 10 pairs chained via LEADS_TO, 3-hop recall ≥ 0.75
- Root cause identification from terminal effect node (6-pair chain)
- Spurious edge suppression (5 distractors + UNRELATED edges, rate < 0.15)
- Counterfactual: withheld pair edge → effect must not be reachable
- Scale recall: full 500-node ATOMIC graph, 50-pair sample (seed=42)
- Full e-CARE precision on all 200 pairs
- Cycle detection edge case (topology-only, synthetic)

---

#### Track 4 — Decision Intelligence

| Metric | Threshold | Basis |
|---|---|---|
| decision_accuracy | beats baseline | lexical baseline |
| policy_compliance_rate | ≥ 0.90 | — |
| precedent_mrr | ≥ 0.70 | Dense retrieval baseline |
| precedent_hit@1 | ≥ 0.70 | — |
| abstain_correctness | ≥ 0.75 | — |
| conflict_handling_accuracy | ≥ 0.80 | — |
| overturned_precedent_accuracy | ≥ 0.80 | — |
| ECE | reported | calibration quality |

Dataset: **120 records, 24 per domain** across lending, healthcare, legal, HR, ecommerce.

Real-world sources:
- Lending: UCI German Credit (DTI 15–55%, credit score 580–800, amount $5k–$200k)
- Healthcare: TREC CT 2022 eligibility criteria (HbA1c, BMI, comorbidities, exclusion logic)
- Legal: CUAD contract clauses + LEDGAR regulatory patterns (IP licensing, GDPR, ADEA, export control)
- HR: IBM HR Attrition (tenure, perf rating, KPIs, PIP, FMLA, promotion criteria)
- Ecommerce: fraud detection, return policy, seller verification, high-value order review

Hard slices: 20 boundary cases, 12 conflicting policy cases, 13 overturned precedent cases.

Predictor is graph-derived only — oracle flags (`has_conflicting_policies`, `boundary_case`, `has_overturned_precedent`) are not read at inference time. Conflict and escalation signals come from precedent outcome spread and compliance check results.

---

#### Track 5 — Decision Quality Delta (`real_llm`)

| Metric | Threshold |
|---|---|
| decision_accuracy_delta | > 0.0 |
| hallucination_rate_delta | > 0.0 |
| citation_groundedness | ≥ 0.60 |
| policy_compliance_rate | ≥ 0.80 |

Run: `SEMANTICA_REAL_LLM=1 pytest ... -m real_llm`

---

#### Track 6 — KG Algorithms

| Metric | Threshold |
|---|---|
| community_nmi | ≥ 0.80 |
| link_predictor_auc | ≥ 0.70 |

---

#### Track 7 — Reasoning Quality

| Metric | Threshold | Basis |
|---|---|---|
| explanation_completeness | ≥ 0.90 | — |
| rete_inference_precision | ≥ 0.95 | — |
| allen_interval_accuracy | = 1.0 | — |
| datalog_latency_ms | < 500 | — |

Datasets: Datalog recursive inference (40-node chain), Allen interval algebra (3 cases), SPARQL via rdflib.

---

#### Track 8 — Provenance Integrity

| Metric | Threshold |
|---|---|
| provenance_lineage_completeness | = 1.0 |
| checksum_integrity | = 1.0 |

---

#### Track 9 — Conflict Resolution

| Metric | Threshold |
|---|---|
| conflict_detection_recall | ≥ 0.85 |
| conflict_detection_precision | ≥ 0.90 |

---

#### Track 10 — Deduplication Quality

| Metric | Threshold | Basis |
|---|---|---|
| duplicate_detection_f1 | ≥ 0.85 | DeepMatcher DBLP-ACM published score |
| duplicate_detection_precision | ≥ 0.85 | — |
| duplicate_detection_recall | ≥ 0.85 | — |

Datasets: DBLP-ACM (2,224 pairs), Amazon-Google (~1,300 pairs), Abt-Buy (~1,100 pairs).

---

#### Track 11 — Embedding Quality

| Metric | Threshold |
|---|---|
| semantic_coherence_delta | > 0.0 |
| hash_fallback_stability | = 1.0 |

---

#### Track 12 — Change Management

| Metric | Threshold |
|---|---|
| snapshot_fidelity | = 1.0 |
| version_diff_correctness | = 1.0 |

---

#### Track 13 — Skill Injection (`real_llm`)

| Metric | Threshold |
|---|---|
| skill_activation_rate | ≥ 0.70 |

---

#### Track 14 — Semantic Extraction

| Metric | Threshold |
|---|---|
| ner_f1 | ≥ 0.60 |
| relation_extraction_f1 | ≥ 0.60 |
| event_detection_recall | ≥ 0.65 |
| kg_triplet_accuracy | ≥ 0.70 |

Datasets: CoNLL-2003 NER (50 records), ACE-2005 RE (30 pairs), event detection subset.

---

#### Track 15 — Context Quality

| Metric | Threshold |
|---|---|
| context_relevance_score | ≥ 0.70 |
| context_noise_ratio | < 0.30 |
| signal_to_context_ratio | ≥ 2.0 |
| redundancy_score | ≥ 0.80 |

---

#### Track 16 — Graph Structural Integrity

| Metric | Threshold |
|---|---|
| graph_triple_retrieval_rate | ≥ 0.95 |
| graph_relation_type_coverage | ≥ 0.90 |

Datasets: WN18RR (101 triples), FB15k-237 (88 triples).

---

#### Track 17 — Extended Multi-hop

| Metric | Threshold | Basis |
|---|---|---|
| hotpotqa_bridge_recall | ≥ 0.65 | — |
| hotpotqa_comparison_recall | ≥ 0.70 | — |
| multi_hop_recall_4hop | ≥ 0.60 | — |
| MetaQA 1-hop recall | ≥ 0.65 | KB graph traversal |
| MetaQA 2-hop recall | ≥ 0.75 | KB graph traversal |
| MetaQA 3-hop recall | ≥ 0.65 | KB graph traversal |
| MetaQA KB node coverage | ≥ 0.95 | — |

Datasets:
- HotpotQA (30 records — bridge and comparison types)
- 2WikiMultihopQA (20 records)
- **MetaQA** — 200 (1-hop) + 150 (2-hop) + 100 (3-hop) QA pairs against a 100-movie knowledge base. Graph built from real KB: directors, actors, genres as linked nodes. Previously committed but untested; now fully wired.

---

#### Track 18 — Abductive Reasoning

| Metric | Threshold |
|---|---|
| abductive_cause_accuracy | ≥ 0.60 |
| abductive_effect_accuracy | ≥ 0.55 |
| deductive_chain_recall | ≥ 0.65 |

Datasets: COPA (30 records), WIQA (30 records).

---

#### Track 19 — Entity Linking

| Metric | Threshold |
|---|---|
| entity_linker_precision | ≥ 0.80 |
| entity_linker_recall | ≥ 0.75 |
| graph_validator_false_positive_rate | < 0.05 |

---

#### Track 20 — Composite SES Score (SES_v2)

| Metric | Threshold | Basis |
|---|---|---|
| ses_composite | ≥ 0.72 | Weighted 0.7×CG + 0.3×SL |
| ses_domain_minimum | ≥ 0.50 | — |

Formula: `SES_v2 = 0.7 × ContextGraphScore + 0.3 × SemanticLayerScore`

| Component | Pillar | Metric |
|---|---|---|
| retrieval_hit_rate | Context Graph | Hit@1 on hybrid retrieval |
| decision_accuracy | Context Graph | Structured predictor vs. baseline |
| duplicate_detection_f1 | Context Graph | F1 on DBLP-ACM pairs |
| ner_f1 | Context Graph | NER F1 on CoNLL-2003 |
| semantic_metric_exactness | Semantic Layer | Exactness@1 on 35 NL queries |
| cross_turn_metric_consistency | Semantic Layer | Consistency across agentic traces |

---

### Pillar 2 — Semantic Layer

#### Track 21 — Semantic Metric Exactness

| Metric | Threshold | Basis |
|---|---|---|
| metric_exactness_at_1 | ≥ 0.85 | dbt Semantic Layer 2025 accuracy lift |
| dimension_conformance_rate | ≥ 0.90 | — |
| metric_alias_resolution_rate | ≥ 0.80 | — |
| metric_node_storage_fidelity | = 1.0 | — |
| semantic_layer_coverage | ≥ 0.90 | — |

Dataset: **Jaffle Shop — 16 metrics, 35 NL queries** (dbt Semantic Layer / MetricFlow format).

Metrics covered: total_revenue, order_count, customer_lifetime_value, average_order_value, churn_rate, ltv_cac_ratio, new_customer_count, refund_rate, gross_margin, repeat_purchase_rate, net_promoter_score, support_ticket_volume, avg_resolution_time, inventory_turnover, customer_acquisition_cost, active_customers.

---

#### Track 22 — NL → Governed Decision (`real_llm`)

| Metric | Threshold |
|---|---|
| governed_decision_accuracy | measured per weekly run |

Offline proxy: verifies prompt structure contains metric definition, threshold, and observed value.  
Full evaluation: runs via `benchmark_real_llm.yml` weekly workflow.

---

#### Track 23 — Metric-Graph Hybrid Reasoning

| Metric | Threshold |
|---|---|
| hybrid_recall | ≥ 0.75 |
| policy_metric_compliance | ≥ 0.85 |
| causal_root_accuracy | ≥ 0.70 |
| metric_policy_linkage_rate | ≥ 0.90 |
| hybrid_graph_coverage | ≥ 0.80 |

Dataset: hybrid_metric_graph.json — policy nodes + causal edges + metric nodes with GOVERNS and AFFECTED_BY edges.

---

#### Track 24 — Governance Impact & Change Propagation

| Metric | Threshold | Basis |
|---|---|---|
| metric_change_impact_score | ≥ 0.95 | GDPR/SOX auditability SLA |
| decision_drift_rate | ≤ 0.02 | Production SLA |
| impact_precision | ≥ 0.85 | — |
| change_type_coverage | ≥ 0.80 | — |

Dataset: **30 before/after metric change pairs** covering all 8 change types — expression_restatement, expression_and_filter, filter_added, window_tightened, filter_broadened, threshold_raised, filter_exclusion_added, time_window_added.

Registry: 37 decision IDs mapped to their governing metric and threshold condition.  
Policy decisions link to 16 metrics across revenue, orders, customers, margin, support, inventory, acquisition.

---

#### Track 25 — Agentic Semantic Consistency

| Metric | Threshold | Basis |
|---|---|---|
| cross_turn_metric_consistency | ≥ 0.90 | Agentic production SLA |
| threshold_stability_rate | ≥ 0.95 | Agentic production SLA |
| explicit_update_detection_rate | ≥ 0.80 | — |
| decision_consistency_rate | ≥ 0.85 | — |
| trace_buildability_rate | = 1.0 | — |

Dataset: 10 multi-turn agentic conversation traces. Tests that metric expressions do not silently drift across turns and that policy thresholds remain stable unless explicitly updated.

---

## Measurement Policy

Results are valid only when:
- Assertions are derived from actual Semantica API outputs
- Fixtures under `benchmarks/context_graph_effectiveness/fixtures/` supply the ground truth
- Metric helpers (precision, recall, F1, Hit@k, MRR, MAP, nDCG, ECE, Brier) are used
- Oracle flags (`has_conflicting_policies`, `boundary_case`, `has_overturned_precedent`) are not read at inference time
- Run artifacts are captured via `--effectiveness-report-json` rather than manually edited

Not valid as benchmark evidence:
- Hardcoded metric values
- `assert True` / `assert value >= 0` style tests
- Mock-LLM output used as proof of effectiveness lift
- Silent passes when a component is unavailable

---

## Track Status Summary

| Track | Status | Dataset |
|---|---|---|
| T1 Retrieval | measured | 70 retrieval eval records |
| T2 Temporal Validity | measured | TimeQA 150 records |
| T3 Causal Chains | measured | ATOMIC 500 + e-CARE 200 |
| T4 Decision Intelligence | measured | 120 records / 5 domains |
| T5 Decision Quality Delta | real_llm | — |
| T6 KG Algorithms | measured | synthetic topology |
| T7 Reasoning Quality | measured | Datalog / Allen / SPARQL |
| T8 Provenance Integrity | measured | synthetic provenance |
| T9 Conflict Resolution | measured | synthetic conflict cases |
| T10 Deduplication | measured | DBLP-ACM 2,224 + Amazon-Google + Abt-Buy |
| T11 Embedding Quality | measured | — |
| T12 Change Management | measured | — |
| T13 Skill Injection | real_llm | — |
| T14 Semantic Extraction | measured | CoNLL-2003 + ACE-2005 |
| T15 Context Quality | measured | — |
| T16 Graph Structural Integrity | measured | WN18RR 101 + FB15k-237 88 |
| T17 Extended Multi-hop | measured | HotpotQA 30 + 2WikiMultihop 20 + MetaQA 450 QA |
| T18 Abductive Reasoning | measured | COPA 30 + WIQA 30 |
| T19 Entity Linking | measured | — |
| T20 SES Composite | measured | aggregated from T1/T4/T10/T14/T21/T25 |
| T21 Semantic Metric Exactness | measured | Jaffle Shop 16 metrics / 35 NL queries |
| T22 NL Governed Decision | real_llm | weekly CI |
| T23 Metric-Graph Hybrid | measured | hybrid_metric_graph.json |
| T24 Governance Impact | measured | 30 change pairs / 8 change types |
| T25 Agentic Consistency | measured | 10 conversation traces |

---

## Reporting Guidance

When publishing results:
- Name the dataset, source, and sample size
- State whether the run is offline deterministic or `real_llm`
- Show the formula used
- Report baseline value, measured value, and absolute lift — not only threshold pass/fail
- Label each track as `measured`, `partial`, `skipped`, or `real_llm`
- Do not mix deterministic and model-dependent evidence in a single aggregate claim

Conference-facing framing:
- Lead with **causal chain traversal** (ATOMIC/e-CARE recall ≥ 0.80), **temporal validity** (TimeQA precision ≥ 0.90), and **decision intelligence** (120-record 5-domain benchmark, graph-derived predictor) — these are graph-native capabilities pure RAG cannot replicate
- Support with **deduplication F1** (traceable to DeepMatcher DBLP-ACM), **metric exactness** (dbt 2025 lift), and **governance impact** (GDPR/SOX SLA traceability)
- Report **SES_v2 ≥ 0.72** as the single composite score: `0.7 × ContextGraph + 0.3 × SemanticLayer`
- Separate deterministic evidence from auxiliary model-dependent lift at all times
