# Semantica Benchmark Suite

## Purpose

This document defines how Semantica benchmarks the effectiveness of context graphs, decision intelligence, and semantic layers using real datasets and real-world scenarios.

The suite is intentionally hybrid:
- **Offline deterministic core** — all quality metrics computed from committed real-world fixture data, no synthetic graph factories for headline numbers
- **Manual real-LLM auxiliary layer** — prompt-time lift, policy grounding, and semantic-layer behavior gated behind `SEMANTICA_REAL_LLM=1`

Benchmarks are manual and offline by design. They are not part of CI and should not block merges. The effectiveness runner supports explicit run modes and emits a machine-readable JSON summary for each run.

---

## Current Validation Status

Latest offline deterministic run (April 2026):

```bash
pytest benchmarks/context_graph_effectiveness/ -m "not real_llm" -q
```

Equivalent runner command with summary artifact:

```bash
python benchmarks/benchmarks_runner.py --effectiveness --effectiveness-mode offline \
  --effectiveness-report-json benchmarks/results/effectiveness_offline.json
```

Interpretation of run labels:
- `passed`: track or scenario completed and met its threshold assertion
- `skipped`: optional component or API not available in current environment
- `deselected`: `real_llm` tracks excluded from the offline run

---

## Dataset Inventory

All fixtures live under `benchmarks/context_graph_effectiveness/fixtures/`.

### Pillar 1 — Context Graph

| Dataset | Source | Records | Used In |
|---|---|---|---|
| ATOMIC causal pairs | Allen AI ATOMIC | 500 pairs | Track 3 — Causal Chains |
| e-CARE causal pairs | e-CARE Causal Reasoning Evaluation | 200 pairs | Track 3 — Causal Chains |
| TimeQA | TimeQA (temporal QA) | 150 records | Track 2 — Temporal Validity |
| MetaQA 1/2/3-hop | MetaQA movie KB | 200+150+100 QA + 100-movie KB | Track 17 — Extended Multi-hop |
| WebQSP | WebQuestions SP | 200 QA | Track 17 — Extended Multi-hop |
| HotpotQA | HotpotQA (CC BY SA) | 30 records | Track 17 — Extended Multi-hop |
| 2WikiMultihopQA | 2WikiMultihopQA (Apache) | 20 records | Track 17 — Extended Multi-hop |
| DBLP-ACM pairs | DeepMatcher (DBLP-ACM) | 2,224 pairs | Track 10 — Deduplication |
| Amazon-Google pairs | DeepMatcher | ~1,300 pairs | Track 10 — Deduplication |
| Abt-Buy pairs | DeepMatcher | ~1,100 pairs | Track 10 — Deduplication |
| Decision Intelligence | UCI German Credit + TREC CT 2022 + CUAD + IBM HR + ecommerce patterns | **120 records, 24/domain** | Track 4 — Decision Intelligence |
| CoNLL-2003 NER | CoNLL-2003 | 50 records | Track 14 — Semantic Extraction |
| ACE-2005 RE | ACE-2005 | 30 pairs | Track 14 — Semantic Extraction |
| WN18RR triples | WN18RR | 101 triples | Track 16 — Graph Integrity |
| FB15k-237 triples | FB15k-237 | 88 triples | Track 16 — Graph Integrity |
| COPA | COPA (causal reasoning) | 30 records | Track 18 — Abductive Reasoning |
| WIQA | WIQA (process chains) | 30 records | Track 18 — Abductive Reasoning |
| Retrieval eval | Graph-native query types | 70 records | Track 1 — Retrieval |

### Pillar 2 — Semantic Layer

| Dataset | Source | Records | Used In |
|---|---|---|---|
| Jaffle Shop metrics | dbt-labs/jaffle_shop + MetricFlow | **16 metrics, 35 NL queries** | Tracks 21–25 |
| Metric change pairs | Governed metric change scenarios | **30 before/after pairs, 8 change types** | Track 24 — Governance Impact |
| Hybrid metric graph | Policy + causal + metric graph | 1 graph fixture | Track 23 — Hybrid Reasoning |
| Agentic traces | Multi-turn conversation traces | 10 traces | Track 25 — Agentic Consistency |

---

## Real-Data Coverage by Track

### Pillar 1 — Context Graph (Tracks 1–20)

**Track 1 — Retrieval**
- Dataset: 70 retrieval eval records (direct_lookup, multi_hop, temporal, causal, no_match query types)
- Baselines: lexical, embedding, traversal, hybrid
- Key metrics: Precision@k, Recall@k, Hit@1, MRR, MAP@5, nDCG@5

**Track 2 — Temporal Validity**
- Dataset: TimeQA 150 records — real entity names, real temporal intent labels (before/after/at), real validity windows
- Synthetic graphs retained only for API edge cases (cycle, competing window)
- Key metrics: temporal precision ≥ 0.90, temporal recall ≥ 0.80, stale injection < 0.05, future injection < 0.05, rewriter accuracy ≥ 0.85

**Track 3 — Causal Chains**
- Datasets: ATOMIC (500 pairs) and e-CARE (200 pairs) — all quality metrics derived from real causal data
- Tests: pairwise recall (100 pairs), precision from e-CARE correct-cause graph, multi-hop chain (10 pairs chained via LEADS_TO), root cause identification, spurious edge suppression, counterfactual (withheld pair), full 500-node graph scale recall
- SyntheticGraphFactory used only for cycle-detection edge case
- Key metrics: causal chain recall ≥ 0.80, causal chain precision ≥ 0.85

**Track 4 — Decision Intelligence**
- Dataset: 120 records across 5 domains (lending, healthcare, legal, HR, ecommerce) — 24 records per domain
  - Lending: UCI German Credit attribute patterns (DTI 15–55%, credit score 580–800, credit amount $5k–$200k)
  - Healthcare: TREC CT 2022 eligibility criteria (HbA1c, BMI, comorbidities, trial exclusion logic)
  - Legal: CUAD contract clauses and LEDGAR regulatory patterns (IP licensing, GDPR, ADEA, export control)
  - HR: IBM HR Attrition patterns (tenure, performance rating, KPIs, PIP, FMLA)
  - Ecommerce: fraud detection, return policy, seller verification, high-value order review
- Predictor is graph-derived only — no oracle flags (`has_conflicting_policies`, `boundary_case`, `has_overturned_precedent`) are read at inference time
- Hard slices: 20 boundary cases, 12 conflicting policy cases, 13 overturned precedent cases
- Key metrics: decision accuracy beats baseline, precedent MRR ≥ 0.70, policy compliance ≥ 0.90

**Track 5 — Decision Quality Delta** (`real_llm` gated)
- Measures LLM accuracy with vs. without context graph
- Key metrics: decision accuracy delta > 0, hallucination rate delta > 0, citation groundedness ≥ 0.60

**Track 6 — KG Algorithms**
- Key metrics: community NMI ≥ 0.80, link predictor AUC ≥ 0.70

**Track 7 — Reasoning Quality**
- Datasets: Datalog recursive inference, Allen interval algebra, SPARQL via rdflib, latency on 40-node chain
- Key metrics: explanation completeness ≥ 0.90, Rete inference precision ≥ 0.95, Allen accuracy = 1.0

**Track 8 — Provenance Integrity**
- Key metrics: provenance lineage completeness = 1.0, checksum integrity = 1.0

**Track 9 — Conflict Resolution**
- Key metrics: conflict detection recall ≥ 0.85, conflict detection precision ≥ 0.90

**Track 10 — Deduplication Quality**
- Datasets: DBLP-ACM (2,224 pairs), Amazon-Google, Abt-Buy — DeepMatcher published baselines
- Key metrics: duplicate detection F1 ≥ 0.85 (DeepMatcher DBLP-ACM baseline)

**Track 11 — Embedding Quality**
- Key metrics: semantic coherence delta > 0, hash fallback stability = 1.0

**Track 12 — Change Management**
- Key metrics: snapshot fidelity = 1.0, version diff correctness = 1.0

**Track 13 — Skill Injection** (`real_llm` gated)
- Key metrics: skill activation rate ≥ 0.70

**Track 14 — Semantic Extraction**
- Datasets: CoNLL-2003 NER (50 records), ACE-2005 RE (30 pairs), event detection subset
- Key metrics: NER F1 ≥ 0.60, relation extraction F1 ≥ 0.60, event detection recall ≥ 0.65

**Track 15 — Context Quality**
- Key metrics: context relevance ≥ 0.70, noise ratio < 0.30, signal-to-context ratio ≥ 2.0

**Track 16 — Graph Structural Integrity**
- Datasets: WN18RR (101 triples), FB15k-237 (88 triples)
- Key metrics: graph triple retrieval rate ≥ 0.95, relation type coverage ≥ 0.90

**Track 17 — Extended Multi-hop**
- Datasets: HotpotQA (30 records), 2WikiMultihopQA (20 records), MetaQA (200+150+100 QA + 100-movie KB)
- MetaQA KB graph built from real movie knowledge base — directors, actors, genres as linked nodes
- Tests: 1-hop, 2-hop, 3-hop answer reachability on the real KB; bridge and comparison recall from HotpotQA; path completeness from 2WikiMultihop
- Key metrics: bridge recall ≥ 0.65, comparison recall ≥ 0.70, 4-hop recall ≥ 0.60

**Track 18 — Abductive Reasoning**
- Datasets: COPA (30 records), WIQA (30 records)
- Key metrics: abductive cause accuracy ≥ 0.60, abductive effect accuracy ≥ 0.55, deductive chain recall ≥ 0.65

**Track 19 — Entity Linking**
- Key metrics: entity linker precision ≥ 0.80, entity linker recall ≥ 0.75

**Track 20 — Composite SES Score**
- Formula: `SES_v2 = 0.7 × ContextGraphScore + 0.3 × SemanticLayerScore`
- Context graph components: retrieval hit rate, decision accuracy, dedup F1, NER F1
- Semantic layer components: metric exactness@1, cross-turn metric consistency
- Key metrics: SES_v2 ≥ 0.72, domain minimum ≥ 0.50

### Pillar 2 — Semantic Layer (Tracks 21–25)

**Track 21 — Semantic Metric Exactness**
- Dataset: Jaffle Shop 16 metrics, 35 NL queries (dbt Semantic Layer / MetricFlow format)
- Metrics: total_revenue, order_count, customer_lifetime_value, average_order_value, churn_rate, ltv_cac_ratio, new_customer_count, refund_rate, gross_margin, repeat_purchase_rate, net_promoter_score, support_ticket_volume, avg_resolution_time, inventory_turnover, customer_acquisition_cost, active_customers
- Key metrics: metric exactness@1 ≥ 0.85, dimension conformance ≥ 0.90, alias resolution ≥ 0.80, semantic layer coverage ≥ 0.90

**Track 22 — NL → Governed Decision** (`real_llm` gated)
- Offline proxy: verifies prompt structure contains metric definition, threshold, observed value
- Key metrics: governed decision accuracy via weekly `benchmark_real_llm.yml`

**Track 23 — Metric-Graph Hybrid Reasoning**
- Dataset: hybrid_metric_graph.json — policies + causal edges + metric nodes
- Key metrics: hybrid recall ≥ 0.75, policy-metric compliance ≥ 0.85, causal root accuracy ≥ 0.70

**Track 24 — Governance Impact & Change Propagation**
- Dataset: 30 before/after metric change pairs covering all 8 change types:
  expression_restatement, expression_and_filter, filter_added, window_tightened, filter_broadened, threshold_raised, filter_exclusion_added, time_window_added
- Registry maps 37 decision IDs to their governing metric and threshold
- Key metrics: metric change impact score ≥ 0.95 (GDPR/SOX SLA), decision drift rate ≤ 0.02 (production SLA), impact precision ≥ 0.85, change type coverage ≥ 0.80

**Track 25 — Agentic Semantic Consistency**
- Dataset: 10 multi-turn agentic conversation traces
- Tests: metric expression does not silently drift across turns, policy thresholds stay stable, explicit updates are detectable, same metric + value + threshold → same decision
- Key metrics: cross-turn consistency ≥ 0.90, threshold stability ≥ 0.95, trace buildability = 1.0

---

## SES_v2 Formula

```
SES_v2 = 0.7 × ContextGraphScore + 0.3 × SemanticLayerScore
```

| Component | Pillar | Metric Used |
|---|---|---|
| retrieval_hit_rate | Context Graph | Hit@1 on hybrid retrieval |
| decision_accuracy | Context Graph | Structured predictor accuracy vs. baseline |
| duplicate_detection_f1 | Context Graph | F1 on DBLP-ACM pairs |
| ner_f1 | Context Graph | NER F1 on CoNLL-2003 |
| semantic_metric_exactness | Semantic Layer | Exactness@1 on 35 NL queries |
| cross_turn_metric_consistency | Semantic Layer | Consistency rate across agentic traces |

Threshold: SES_v2 ≥ 0.72, domain minimum ≥ 0.50.

---

## Threshold Reference

All thresholds are evidence-based. Sources are listed in `thresholds.py`.

| Threshold | Value | Basis |
|---|---|---|
| causal_chain_recall | ≥ 0.80 | KG-RAG literature baseline |
| causal_chain_precision | ≥ 0.85 | KG-RAG literature baseline |
| temporal_precision | ≥ 0.90 | Production SLA |
| temporal_recall | ≥ 0.80 | Production SLA |
| stale_context_injection_rate | < 0.05 | Production SLA |
| duplicate_detection_f1 | ≥ 0.85 | DeepMatcher DBLP-ACM published score |
| decision_precedent_mrr | ≥ 0.70 | Dense retrieval baseline |
| metric_exactness@1 | ≥ 0.85 | dbt Semantic Layer 2025 accuracy lift |
| metric_change_impact_score | ≥ 0.95 | GDPR/SOX auditability SLA |
| decision_drift_rate | ≤ 0.02 | Production SLA |
| cross_turn_metric_consistency | ≥ 0.90 | Agentic governed-decision production SLA |
| ses_composite (SES_v2) | ≥ 0.72 | Weighted 0.7×CG + 0.3×SL |

---

## Principles

- Every quality metric is derived from real dataset fixtures — no synthetic graph factories for headline numbers.
- Labeled fixtures are the source of truth for scoring.
- The predictor under test must not read ground truth oracle fields at inference time.
- Thresholds are regression floors traceable to published baselines or production SLAs.
- Major tracks report baselines, slice breakdowns, and sample sizes.
- Mock LLMs are acceptable for API-shape tests only, never for effectiveness claims.
- Tracks that cannot yet be measured honestly are marked `partial` or `skipped`.
- Published results are derived from measured artifacts, not hand-edited pass/fail claims.

---

## Core Metrics And Formulas

### Classification Metrics

Used in: deduplication, conflict detection, policy compliance, semantic-layer exactness.

```
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
Accuracy  = (TP + TN) / (TP + TN + FP + FN)
```

### Ranking Metrics

Used in: retrieval, precedent retrieval, multi-hop KGQA.

```
Precision@k = |R_k ∩ Rel| / |R_k|
Recall@k    = |R_k ∩ Rel| / |Rel|
Hit@k       = 1 if R_k ∩ Rel is non-empty, else 0
MRR         = (1 / |Q|) * Σ_i (1 / rank_i)
MAP@k       = mean of per-query average precision at k
nDCG@k      = DCG@k / IDCG@k
```

### Decision Metrics

```
Decision Accuracy      = correct_decisions / total_decisions
Policy Compliance Rate = compliant_decisions / applicable_policy_cases
Abstain Correctness    = correct_abstentions / no-policy_cases
Conflict Handling Rate = correct_conflict_resolutions / conflict_cases
Precedent MRR          = (1 / |Q|) * Σ_i (1 / rank_i)
```

### Temporal Metrics

A node is valid at time `t` when `valid_from ≤ t` and `(valid_until is None or t < valid_until)`.

```
Temporal Precision    = valid_retrieved / total_retrieved
Temporal Recall       = valid_retrieved / total_valid_relevant
Stale Injection Rate  = stale_retrieved / total_retrieved
Future Injection Rate = future_retrieved / total_retrieved
```

### Causal Metrics

```
Causal Precision = correctly_retrieved_causal_nodes / retrieved_causal_nodes
Causal Recall    = correctly_retrieved_causal_nodes / expected_causal_nodes
Root Accuracy    = correct_root_predictions / total_cases
```

### Calibration Metrics

```
Brier Score = mean((predicted_probability - observed_label)²)
ECE         = Σ_bins (bin_weight × |bin_accuracy - bin_confidence|)
```

### Provenance And Change Metrics

```
Lineage Completeness   = recovered_lineage_hops / expected_lineage_hops
Checksum Integrity     = verified_entities / total_entities
Snapshot Fidelity      = correctly_restored_items / expected_items
Change Impact Score    = correctly_identified_impacts / expected_impacts
Decision Drift Rate    = changed_decisions / affected_decisions
```

### Semantic Layer Metrics

```
Metric Exactness@1     = correct_top_metric / total_queries
Alias Resolution Rate  = correct_alias_resolutions / alias_queries
Dimension Conformance  = correct_dimension_choices / checked_queries
Cross-turn Consistency = consistent_followup_answers / multi_turn_traces
```

### Real-LLM Auxiliary Metrics

```
Decision Accuracy Delta   = accuracy_with_context - accuracy_without_context
Hallucination Rate Delta  = hallucination_without - hallucination_with_context
Skill Activation Rate     = activated_skill_cases / total_skill_cases
Citation Groundedness     = grounded_citations / cited_claims
```

---

## Slice Definitions

Retrieval slices: direct_lookup, 2-hop, 3-hop, 4+-hop, temporal, causal, no-match

Decision slices: lending, healthcare, legal, hr, ecommerce, boundary_cases, conflicting_policy_cases, overturned_precedent_cases, no_applicable_policy_cases

Semantic-layer slices: time-grain queries, alias-heavy queries, change-type slices (8 types), metric family slices

---

## Baseline Definitions

Offline baselines:
- **lexical**: keyword/name-overlap retrieval only
- **embedding**: embedding-only retrieval, no graph structure
- **traversal**: raw BFS reachability without ranking fusion
- **flat metric text**: match against metric names, labels, aliases, descriptions as plain text
- **no semantic layer**: heuristic metric guessing without governed structure

Real-LLM baselines:
- **no-context**: user prompt only
- **flat-context**: plain text context block
- **graph context**: graph-derived or governed structured context

For major tracks, report: metric value, threshold floor, baseline value, absolute lift, relative lift, sample size, slice breakdown.

---

## Deterministic vs. Real-LLM Separation

### Offline deterministic core

Tracks: retrieval, temporal validity, causal chains, decision intelligence, deduplication, provenance, semantic metric exactness, governance impact, hybrid metric graph, agentic consistency.

Requirements:
- All assertions derived from real outputs and labeled fixtures
- No hardcoded benchmark numbers used as result values
- No oracle flags read at inference time
- Reproducible locally with no API keys

### Manual real-LLM auxiliary layer

Tracks: decision quality delta (Track 5), skill injection (Track 13), NL governed decision (Track 22).

Requirements:
- Gated behind `SEMANTICA_REAL_LLM=1`
- Fixed prompts and fixed model configuration
- Compare at least two prompt conditions
- No mock output used as evidence of lift

---

## Run Commands

Offline deterministic benchmarks:

```bash
pytest benchmarks/context_graph_effectiveness/ -m "not real_llm" -q
```

Full effectiveness run with JSON report:

```bash
python benchmarks/benchmarks_runner.py --effectiveness --effectiveness-mode offline \
  --effectiveness-report-json benchmarks/results/effectiveness_offline.json
```

Core pillar tracks only:

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

Real-LLM auxiliary tracks:

```bash
SEMANTICA_REAL_LLM=1 ANTHROPIC_API_KEY=... \
  pytest benchmarks/context_graph_effectiveness/ -m "real_llm" -q
```

---

## Track Status Reference

| Label | Meaning |
|---|---|
| `measured` | Metric derived from real outputs and labeled fixtures |
| `partial` | Some real computation exists; needs expansion or audit |
| `skipped` | Intentionally not evaluated in current environment |
| `real_llm` | Manual auxiliary benchmark; excluded from offline totals |

---

## Reporting Template

When publishing results, include:
- track name and pillar
- dataset name, source, and sample size
- run mode (offline deterministic / real_llm)
- formula used
- threshold floor and basis
- baseline value and method
- measured value
- absolute lift and relative lift
- slice breakdown
- open limitations or skips

Conference-facing framing:
- Lead with causal chain traversal, temporal validity, and decision intelligence — these are graph-native capabilities that pure RAG cannot replicate
- Support with deduplication F1 (published DeepMatcher baselines), metric exactness (dbt 2025 lift), and governance impact (GDPR/SOX SLA traceability)
- Separate deterministic evidence from auxiliary model-dependent lift
- Report SES_v2 as the single composite score: `0.7 × ContextGraph + 0.3 × SemanticLayer ≥ 0.72`
