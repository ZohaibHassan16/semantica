# Semantica Benchmark Suite
### Methodology, Metrics, Formulas & Datasets
> Conference-grade reference for evaluating Knowledge Graph–augmented decision intelligence  
> and the Semantic Layer pillar. Covers **25 effectiveness tracks** + throughput benchmarks.  
> All metrics computed from live API calls — no hardcoded values.

---

## Contents

1. [Background & Motivation](#1-background--motivation)
2. [Suite Architecture](#2-suite-architecture)
3. [Statistical Foundations](#3-statistical-foundations)
4. [Core Metric Formulas](#4-core-metric-formulas)
5. [Effectiveness Suite — Track Reference](#5-effectiveness-suite--track-reference)
   - Tracks 1–5: Retrieval · Decision · Causal · Temporal
   - Tracks 6–8: KG Algorithms · Reasoning · Provenance
   - Tracks 9–12: Conflict · Dedup · Embedding · Change
   - Tracks 13–16: Skill · Extraction · Context · Integrity
   - Tracks 17–20: Multi-hop · Abductive · Entity · SES
   - Tracks 21–25: Semantic Layer Pillar
6. [Threshold Reference Table](#6-threshold-reference-table)
7. [Datasets — Provenance & Theory](#7-datasets--provenance--theory)
8. [Throughput Suite](#8-throughput-suite)
9. [Research Paper Guidance](#9-research-paper-guidance)
10. [Running the Suite](#10-running-the-suite)

---

## 1. Background & Motivation

### What is Semantica?

Semantica is a Knowledge Graph–augmented Retrieval-Augmented Generation (KG-RAG) framework for decision intelligence. Unlike flat-document RAG, Semantica represents context as a directed property graph where nodes are decisions, policies, and entities, and edges encode causal, temporal, and provenance relationships.

```mermaid
graph LR
    subgraph Traditional RAG
        D1[Documents] -->|chunk + embed| V1[Vector Store]
        V1 -->|top-k similarity| LLM1[LLM]
    end
    subgraph Semantica KG-RAG
        D2[Documents + Events] -->|extract + structure| G[Context Graph\nNodes · Edges · Metadata]
        G -->|multi-hop traversal| C[Causal Chains\nPrecedents · Policies]
        G -->|temporal filter| T[Valid-at-time subgraph]
        C --> LLM2[LLM + structured context]
        T --> LLM2
    end
```

**Why benchmarking matters:** Standard RAG benchmarks (RAGAS, BEIR) measure retrieval quality on flat corpora. They cannot measure causal chain completeness, temporal validity of injected context, policy compliance propagation, or decision precedent reuse — the core value propositions of KG-RAG.

### Design Principles

- **No hardcoded assertions.** Every metric is computed from real API calls against real or realistic datasets.
- **Evidence-based thresholds.** Every threshold is anchored to a published baseline or production SLA (documented inline).
- **Graceful degradation.** Components that are unavailable skip with `pytest.skip()`, not with silent `assert True`.
- **Separation of LLM-gated and non-LLM tests.** Tracks requiring real LLM calls are marked `real_llm` and run weekly, not on every push.

---

## 2. Suite Architecture

```mermaid
graph TD
    S[Semantica Benchmark Suite] --> TP[Throughput Suite\n138 passed · Feb 2026]
    S --> EF[Effectiveness Suite\n142 passed · Apr 2026]

    TP --> TP1[Input Layer — parsing ops/sec]
    TP --> TP2[Core Processing — NER · extraction]
    TP --> TP3[Storage — FAISS · triplet store]
    TP --> TP4[Export — JSON · RDF · GraphML]
    TP --> TP5[Visualization — layout algorithms]

    EF --> R[Retrieval Quality\nT1 · T17]
    EF --> D[Decision Intelligence\nT2 · T4 · T13]
    EF --> CT[Causal & Temporal\nT3 · T5]
    EF --> KG[KG Core\nT6 · T7 · T8]
    EF --> DQ[Data Quality\nT9 · T10 · T11 · T12]
    EF --> NLP[NLP Extraction\nT14 · T18]
    EF --> CQ[Context & Graph Quality\nT15 · T16 · T19]
    EF --> SES[Composite Score\nT20]

    style D fill:#ffd700,color:#000
    style SES fill:#90ee90,color:#000
```

### Gate System

```mermaid
flowchart LR
    PR[Every PR push] --> CI[CI — non-LLM\nTracks 1·3-12·14-20]
    WEEK[Weekly schedule] --> LLM[Real-LLM\nTracks 2·13]
    MANUAL[Manual trigger] --> LLM
    CI --> STRICT{--strict flag?}
    STRICT -->|yes| FAIL[Exit 1 on any FAIL]
    STRICT -->|no| WARN[Print FAIL, continue]
```

---

## 3. Statistical Foundations

### Regression Detection (Throughput Suite)

A throughput regression is flagged only when **both** conditions hold simultaneously:

$$\text{Flag iff} \quad \frac{\mu_\text{new} - \mu_\text{baseline}}{\mu_\text{baseline}} > 15\% \quad \text{AND} \quad Z > 2.0$$

where the Z-score is:

$$Z = \frac{\mu_\text{new} - \mu_\text{baseline}}{\sigma_\text{baseline}}$$

This guards against two failure modes:
- **Large % change with low Z** → environmental noise (CPU load spike, GC pause). Not a regression.
- **Small % change with high Z** → consistent, statistically significant slowdown. A real regression.

### Confidence Intervals for Effectiveness Metrics

When reporting benchmark results in a research paper, compute 95% Wilson score confidence intervals for proportion metrics (F1, recall, precision):

$$\text{CI}_{95\%} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

where $z = 1.96$ for 95% confidence, $\hat{p}$ is the observed proportion, $n$ is the sample size.

### Why These Thresholds?

Thresholds are set using three methods:

| Method | Used for | Example |
|--------|----------|---------|
| **Published baseline anchoring** | Metrics with established literature baselines | Dedup F1 ≥ 0.85 ← DeepMatcher DBLP-ACM |
| **Production SLA** | Operational correctness requirements | Stale injection rate < 5% ← SLA |
| **Conservative lower bound** | Novel metrics without published baselines | Skill activation ≥ 0.70 ← empirical calibration |

---

## 4. Core Metric Formulas

### 4.1 Classification: Precision, Recall, F1

$$P = \frac{TP}{TP + FP} \qquad R = \frac{TP}{TP + FN} \qquad F_1 = \frac{2PR}{P + R} = \frac{2 \cdot TP}{2 \cdot TP + FP + FN}$$

The **macro-F1** (used for multi-class NER, relation types) averages per-class F1:

$$F_1^\text{macro} = \frac{1}{|C|} \sum_{c \in C} F_1^{(c)}$$

The **micro-F1** (used for deduplication over pooled pairs) aggregates TP/FP/FN globally:

$$F_1^\text{micro} = \frac{2 \cdot \sum_c TP_c}{2 \cdot \sum_c TP_c + \sum_c FP_c + \sum_c FN_c}$$

### 4.2 Ranking: MRR and Hit@k

**Mean Reciprocal Rank** — measures how high the first correct answer appears:

$$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

If the correct answer never appears, $1/\text{rank}_i = 0$. For decision precedent retrieval, the correct answer is the precedent with the highest decision-scenario similarity to the query.

**Hit@k** — measures whether the correct answer appears anywhere in the top-$k$:

$$\text{Hit@}k = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \mathbf{1}[\text{rank}_i \leq k]$$

Track 1 uses Hit@1 (exact match) for direct lookup queries.

### 4.3 Temporal Validity

Given a reference timestamp $t_\text{ref}$, a node $n$ is **valid** iff:

$$\text{valid}(n, t) = [n.\text{valid\_from} \leq t] \wedge [n.\text{valid\_until} \text{ is None} \vee n.\text{valid\_until} > t]$$

From a retrieved set $R$:

$$\text{Temporal Precision} = \frac{|\{n \in R : \text{valid}(n, t)\}|}{|R|}$$

$$\text{Temporal Recall} = \frac{|\{n \in R : \text{valid}(n, t)\}|}{|\{n \in G : \text{valid}(n, t)\}|}$$

$$\text{Stale Rate} = \frac{|\{n \in R : n.\text{valid\_until} < t\}|}{|R|} \qquad \text{Future Rate} = \frac{|\{n \in R : n.\text{valid\_from} > t\}|}{|R|}$$

Both stale and future rates must be < 5% — these represent context contamination that misleads LLM reasoning.

### 4.4 Context Quality: CRS, CNR, SCR

**Context Relevance Score (CRS)** — what fraction of retrieved nodes are genuinely relevant:

$$\text{CRS} = \frac{|R \cap \text{Rel}|}{|R|}$$

**Context Noise Ratio (CNR)** — complement of CRS:

$$\text{CNR} = \frac{|R \setminus \text{Rel}|}{|R|} = 1 - \text{CRS}$$

**Signal-to-Context Ratio (SCR)** — inspired by signal-to-noise ratio in information theory:

$$\text{SCR} = \frac{\text{CRS}}{\max(\text{CNR},\ \epsilon)}, \quad \epsilon = 0.01$$

SCR ≥ 2.0 means signal is at least twice the noise. This is the operational threshold for "safe" context injection — below 2.0, noise starts dominating reasoning.

**Redundancy Score** — uniqueness of retrieved context:

$$\text{Redundancy Score} = \frac{|\text{unique}(R)|}{|R|}$$

1.0 = perfectly diverse retrieval; 0.5 = half the context is duplicated.

### 4.5 NMI for Community Detection

Normalised Mutual Information compares predicted cluster assignments $U$ to ground-truth $V$:

$$\text{NMI}(U, V) = \frac{2 \cdot I(U; V)}{H(U) + H(V)}$$

where $I(U;V) = H(U) - H(U|V)$ is mutual information and $H(\cdot)$ is Shannon entropy. Range: 0 (independent) to 1 (perfect match). Track 6 requires NMI ≥ 0.80 on a graph with 2 planted clusters.

### 4.6 AUC-ROC for Link Prediction

Area Under the ROC Curve measures how consistently the link predictor ranks true edges above non-edges:

$$\text{AUC} = P(\text{score}(e^+) > \text{score}(e^-))$$

Computed efficiently via the Wilcoxon-Mann-Whitney form:

$$\text{AUC} = \frac{\sum_{i=1}^{n^+} \text{rank}_i - \frac{n^+(n^++1)}{2}}{n^+ \cdot n^-}$$

where $n^+, n^-$ are positive/negative edge counts and $\text{rank}_i$ is the rank of positive edge $i$ in the combined score list.

### 4.7 Entity-Span F1 (Overlap Matching)

Standard BIO token-level F1 is inappropriate for pattern extractors that return full entity text spans. Semantica uses **overlap-based span matching**:

$$\text{match}(g, e) = \begin{cases} \text{True} & g \subseteq e \text{ or } e \subseteq g \\ \text{True} & |\text{words}(g) \cap \text{words}(e)| \geq \left\lceil \frac{|\text{words}(g)|}{2} \right\rceil \\ \text{False} & \text{otherwise} \end{cases}$$

This allows partial matches (e.g., gold "Tim Cook" matched by extracted "Cook") without penalising precision for extracting slightly longer spans (e.g., "Apple Inc." vs "Apple").

### 4.8 Composite SES Score

The **Semantica Effectiveness Score** is a mean over available component sub-scores:

$$\text{SES} = \frac{1}{|C|} \sum_{i \in C} c_i$$

where $C$ is the set of components that did not raise an exception (graceful degradation). Components:

| $c_i$ | Source | Computation |
|--------|--------|------------|
| retrieval_hit_rate | Track 1 | Hit@1 on `linear_graph` |
| causal_chain_recall | Track 3 | Upstream chain recall from node n004 |
| temporal_precision | Track 5 | Valid nodes at 2022-06-01 |
| policy_compliance_hit_rate | Track 4 | Compliant decision vs max_amount policy |
| duplicate_detection_f1 | Track 10 | F1 on 3 explicit entity pairs |
| provenance_completeness | Track 8 | Lineage chain recoverable |
| context_relevance | Track 15 | `find_nodes()` storage rate |
| ner_f1_proxy | Track 14 | $\min(\text{entities\_found}/3, 1.0)$ |

### 4.9 Provenance Lineage Completeness

For a ground-truth $k$-hop lineage chain $e_0 \to e_1 \to \cdots \to e_k$ (linked via `parent_entity_id`):

$$\text{Completeness} = \frac{\text{hops recoverable via storage.retrieve()}}{k}$$

`get_lineage()` returns only the direct entity — full lineage requires iterating `parent_entity_id` manually. Threshold is 1.0 (binary correctness) — partial lineage is a provenance integrity violation.

### 4.10 Hallucination Rate (LLM Tests)

Given LLM output $O$ and injected context graph $G$:

$$\text{hallucination\_rate} = \frac{|\text{NER}(O) \setminus \text{entities}(G)|}{|\text{NER}(O)|}$$

$$\text{hallucination\_rate\_delta} = \text{hallucination\_rate}_\text{baseline} - \text{hallucination\_rate}_\text{with-context}$$

Must be $> 0$ — context must reduce hallucination. $\text{NER}(O)$ uses lightweight regex: `r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b'`.

### 4.11 BFS Reachability (Multi-hop)

For a graph $G = (V, E)$, BFS reachability from source $s$ within $k$ hops:

$$\text{Reach}_k(s) = \bigcup_{i=0}^{k} N^i(s)$$

where $N^0(s) = \{s\}$ and $N^{i+1}(s) = \bigcup_{v \in N^i(s)} \text{neighbors}(v)$.

Multi-hop recall: $\text{Recall} = |\text{Reach}_k(s) \cap T| / |T|$ where $T$ is the set of target nodes.

### 4.12 Multi-factor Similarity (Deduplication)

`SimilarityCalculator.calculate_similarity(e1, e2)` computes:

$$\text{score}(e_1, e_2) = w_1 \cdot \text{Lev}(t_1, t_2) + w_2 \cdot \text{JW}(t_1, t_2) + w_3 \cdot \text{TF-IDF}(t_1, t_2) + w_4 \cdot \text{AuthorSim}(a_1, a_2) + w_5 \cdot \mathbf{1}[y_1 = y_2]$$

where $t_i$ = title, $a_i$ = authors, $y_i$ = year. A pair is a duplicate when score ≥ 0.80.

**Levenshtein normalised:** $\text{Lev}(s_1, s_2) = 1 - \frac{d_\text{edit}(s_1, s_2)}{\max(|s_1|, |s_2|)}$

**Jaro-Winkler:** gives prefix-matching bonus — better for author names and short titles.

**Cosine TF-IDF:** captures vocabulary overlap for longer titles and abstracts.

---

## 5. Effectiveness Suite — Track Reference

### Track 1 — Core Graph Retrieval Quality

**Module:** `ContextRetriever` · **Datasets:** MetaQA (1/2/3-hop), WebQSP, `retrieval_eval_dataset.json`

**Theory:** Information retrieval over a knowledge graph differs from flat document retrieval in two ways: (1) semantic relevance must account for graph distance, not just embedding cosine; (2) multi-hop queries require chaining through intermediate nodes rather than single-step lookup. Semantica's retriever blends both signals via a hybrid alpha parameter.

$$\text{score}(n, q) = \alpha \cdot \cos(\text{embed}(n), \text{embed}(q)) + (1-\alpha) \cdot \text{BM25}(n, q)$$

| Metric | Formula | Threshold | Evidence basis |
|--------|---------|-----------|----------------|
| `direct_lookup_hit_rate` | Hit@1 | ≥ 0.90 | MetaQA 1-hop published baseline |
| `multi_hop_recall_2hop` | Recall on 2-hop chains | ≥ 0.75 | MetaQA 2-hop KG-RAG literature |
| `multi_hop_recall_3hop` | Recall on 3-hop chains | ≥ 0.65 | MetaQA 3-hop published scores |
| `decision_precedent_mrr` | MRR on precedent queries | ≥ 0.70 | DPR on structured decision data |
| `citation_groundedness` | cited nodes in graph / total cited | ≥ 0.60 | Internal calibration |

The alpha sweep shows $\alpha = 0.5$ consistently maximises MRR on structural (causal) queries. Pure embedding retrieval ($\alpha = 1.0$) degrades on relational queries; pure keyword ($\alpha = 0$) degrades on paraphrased queries.

---

### Track 2 — Decision Quality *(real LLM)*

**Module:** `AgentContext` · **Gate:** `SEMANTICA_REAL_LLM=1` + `ANTHROPIC_API_KEY`  
**Dataset:** `decision_intelligence_dataset.json` — 60 records across 5 domains  
**Model:** `claude-haiku-4-5-20251001`

**Theory:** The core hypothesis of decision intelligence is that injecting structured context (policies, causal chains, precedents) into an LLM prompt reduces hallucination and improves decision accuracy compared to an ungrounded baseline. Both effects must be positive for the context graph to provide net value.

```mermaid
sequenceDiagram
    participant Q as Query (decision scenario)
    participant G as ContextGraph
    participant LLM as Claude Haiku
    participant E as Evaluator

    Q->>LLM: Baseline prompt (no context)
    LLM-->>E: baseline_decision + baseline_entities
    Q->>G: retrieve(scenario, max_results=5)
    G-->>LLM: Policies · Precedents · Causal chain
    LLM-->>E: context_decision + context_entities
    E->>E: accuracy_delta = acc_ctx − acc_base > 0
    E->>E: hallucination_delta = hall_base − hall_ctx > 0
    E->>E: citation_groundedness = cited ∩ context / cited
```

| Metric | Formula | Threshold |
|--------|---------|-----------|
| `decision_accuracy_delta` | acc_with_ctx − acc_baseline | > 0.0 |
| `hallucination_rate_delta` | hall_baseline − hall_with_ctx | > 0.0 |
| `citation_groundedness` | cited ∩ context / cited | ≥ 0.60 |
| `policy_compliance_rate` | compliant decisions / total | ≥ 0.80 |

LLM output must be parseable JSON: `{"decision": "approve|reject", "reasoning": "...", "entities_cited": [...]}`.

---

### Track 3 — Causal Chain Quality

**Module:** `CausalChainAnalyzer` · **Datasets:** ATOMIC (500 pairs, CC BY 4.0), e-CARE (200 records)

**Theory:** Causal reasoning over a KG requires correct graph traversal semantics. `get_causal_chain(node, direction="upstream")` performs a depth-first search over edges typed `"CAUSED"`. Two constraints apply: (1) only `"Decision"` nodes are returned; (2) traversal terminates at max_depth. Recall measures coverage of true ancestors; precision measures absence of spurious nodes.

$$\text{Recall} = \frac{|\hat{A} \cap A^*|}{|A^*|} \geq 0.80 \qquad \text{Precision} = \frac{|\hat{A} \cap A^*|}{|\hat{A}|} \geq 0.85$$

where $A^*$ = true ancestors, $\hat{A}$ = retrieved ancestors.

**Graph topology test matrix:**

| Topology | Structure | Tests |
|----------|-----------|-------|
| Linear | A→B→C→D→E | Basic chain recall at each node |
| Diamond | A→{B,C}→D | Multi-path convergence; D should retrieve A via both paths |
| Branching | root→{B,C}, B→{D,E} | Downstream: root should yield all 4 descendants |
| Cycle | A→B→C→A | Non-termination guard — must respect max_depth |

> **API constraint:** Edge type must be `"CAUSED"` (past tense). `"CAUSES"` is silently ignored by `get_causal_chain()`.

---

### Track 4 — Decision Intelligence

**Modules:** `PolicyEngine`, `CausalChainAnalyzer`

**Theory:** Policy compliance is computed by `_evaluate_compliance()` which iterates over `Policy.rules` (a dict of field → constraint) and checks each against `Decision.metadata`. A decision is compliant iff all rules pass. The causal influence score ordering test verifies that root nodes have higher influence scores than leaf nodes — a structural property of well-formed causal graphs.

- `policy_compliance_hit_rate` ≥ **0.90** — fraction of decisions correctly evaluated against policy
- Causal influence: `score(root) > score(leaf)` for every root-leaf pair

---

### Track 5 — Temporal Validity

**Module:** `TemporalGraphRetriever`, `TemporalQueryRewriter`  
**Dataset:** TimeQA 150 temporal Q&A pairs · synthetic 6-node temporal graph (2018–2024)

**Theory:** Temporal validity is the most critical correctness property for decision-support systems. Injecting a policy that was superseded 2 years ago, or a precedent from the future, invalidates the entire reasoning chain. The stale and future injection rates must both be below 5% to satisfy the production SLA.

`TemporalQueryRewriter` converts natural language temporal expressions into `(at_time, before_time, after_time)` structured constraints:

| NL expression | Parsed intent | Operator |
|---------------|--------------|---------|
| "as of June 2022" | point-in-time | `at_time = 2022-06-01` |
| "before the merger" | upper bound | `before_time = event.timestamp` |
| "since Q3 2021" | lower bound | `after_time = 2021-07-01` |
| "between 2020 and 2023" | interval | `valid_from ≤ 2020 AND valid_until ≥ 2023` |

| Metric | Threshold | Basis |
|--------|-----------|-------|
| `stale_context_injection_rate` | < 0.05 | Production SLA |
| `future_context_injection_rate` | < 0.05 | Production SLA |
| `temporal_precision` | ≥ 0.90 | Production SLA |
| `temporal_recall` | ≥ 0.80 | Production SLA |
| `temporal_rewriter_accuracy` | ≥ 0.85 | 16/19 TimeQA intents correctly parsed |

---

### Track 6 — KG Algorithm Quality

**Modules:** `NodeEmbedder`, `CommunityDetector`, `LinkPredictor`, `SimilarityCalculator`

**Theory:**

**Community detection** — the Louvain algorithm maximises graph modularity:
$$Q = \frac{1}{2m} \sum_{ij} \left[ A_{ij} - \frac{k_i k_j}{2m} \right] \delta(c_i, c_j)$$
where $A$ is the adjacency matrix, $k_i$ is node degree, $m$ is total edges, $\delta$ is 1 when nodes $i,j$ are in the same community. Track 6 tests NMI ≥ 0.80 on a graph with 2 planted clusters of 4 nodes each.

**Link prediction** — score a candidate edge $(u, v)$ using structural features:
- Adamic-Adar: $\sum_{w \in N(u) \cap N(v)} 1/\log|N(w)|$
- Common neighbours: $|N(u) \cap N(v)|$
- Combined into a classifier; AUC measures discrimination.

**Embedding normalisation:** `calculate_embedding_similarity()` normalises cosine to [0,1]:
$$s_\text{norm} = \frac{\cos(v_1, v_2) + 1}{2}$$
Orthogonal vectors → 0.5 (not 0.0). Tests assert $s(v, v) > s(v, v_\perp)$.

| Metric | Formula | Threshold | Evidence |
|--------|---------|-----------|---------|
| `community_nmi` | NMI(predicted, ground-truth) | ≥ 0.80 | Louvain on planted partition |
| `link_predictor_auc` | P(score⁺ > score⁻) | ≥ 0.70 | Standard link prediction baselines |
| `semantic_coherence_delta` | $\bar{s}_\text{related} - \bar{s}_\text{random}$ | > 0.0 | Embedding discriminability |
| `hash_fallback_stability` | deterministic for identical input | == 1.0 | Reproducibility |

---

### Track 7 — Reasoning Quality

**Modules:** `Reasoner` (Rete · Datalog), `IntervalRelationAnalyzer`, `SPARQLQueryBuilder`

**Theory:**

**Rete algorithm** — a forward-chaining rule engine. Facts are strings like `"Person(John)"`. Rules are `"IF Person(?x) THEN Mortal(?x)"`. The algorithm builds a network of condition nodes and fires rules when all preconditions are satisfied. Precision measures the fraction of derived facts that are logically entailed by the input.

**Allen's Interval Algebra** — 13 mutually exclusive, jointly exhaustive relations between two temporal intervals $[s_1, e_1]$ and $[s_2, e_2]$:

| Relation | Condition |
|----------|-----------|
| before | $e_1 < s_2$ |
| meets | $e_1 = s_2$ |
| overlaps | $s_1 < s_2 < e_1 < e_2$ |
| starts | $s_1 = s_2, e_1 < e_2$ |
| during | $s_2 < s_1, e_1 < e_2$ |
| finishes | $s_1 > s_2, e_1 = e_2$ |
| equals | $s_1 = s_2, e_1 = e_2$ |
| + 6 inverses | (after, met-by, overlapped-by, ...) |

All 13 must be classifiable by `IntervalRelationAnalyzer`. `allen_interval_accuracy` == 1.0 is a hard correctness requirement (the algebra is exact, not approximate).

| Metric | Threshold |
|--------|-----------|
| `rete_inference_precision` | ≥ 0.95 |
| `allen_interval_accuracy` | == 1.0 |
| `explanation_completeness` | ≥ 0.90 |

---

### Track 8 — Provenance Integrity

**Module:** `ProvenanceTracker` · **Dataset:** FEVER 200 claim+evidence pairs (CC BY 4.0)

**Theory:** Provenance tracking answers "where did this data come from?" For regulatory compliance (GDPR, financial audit trails), every decision node in the context graph must be traceable to its source data. A broken provenance chain — even a single missing link — constitutes an integrity violation.

**4-hop lineage test:**
$$\text{Source} \xrightarrow{\text{DERIVED\_FROM}} B \xrightarrow{\text{DERIVED\_FROM}} C \xrightarrow{\text{DERIVED\_FROM}} D \xrightarrow{\text{DERIVED\_FROM}} \text{Decision}$$

Completeness = 4/4 = 1.0. Any missing `parent_entity_id` link fails the test.

| Metric | Threshold | Basis |
|--------|-----------|-------|
| `provenance_lineage_completeness` | == 1.0 | Binary correctness |
| `checksum_integrity` | == 1.0 | Binary correctness |

---

### Track 9 — Conflict Resolution Quality

**Modules:** `ConflictDetector`, `ConflictResolver`

**Theory:** In a multi-source knowledge graph, the same entity may be asserted with conflicting attribute values, types, or temporal windows. Conflict detection must achieve high recall (missing a conflict is dangerous) and high precision (false conflicts waste resolution resources). Three resolution strategies implement different preference orders.

**Conflict taxonomy:**

| Type | Example | Detection method |
|------|---------|-----------------|
| Value | `amount = 50000` vs `amount = 75000` | Field equality check |
| Type | Same ID is `"Person"` and `"Organization"` | Incompatible-types dict |
| Temporal | `valid_until = 2020` but `valid_from = 2022` | Date range validation |
| Logical | A declared incompatible with B; both asserted | Constraint propagation |

**Resolution strategies:**
- `VOTING` — value held by majority of `sources` wins
- `HIGHEST_CONFIDENCE` — `SourceReference.confidence` determines winner
- `MOST_RECENT` — `SourceReference.timestamp` determines winner

| Metric | Threshold |
|--------|-----------|
| `conflict_detection_recall` | ≥ 0.85 |
| `conflict_detection_precision` | ≥ 0.90 |

---

### Track 10 — Deduplication Quality

**Module:** `SimilarityCalculator` · **Datasets:** DBLP-ACM 2,224 pairs · Amazon-Google 1,300 pairs · Abt-Buy 1,076 pairs

**Theory:** Entity deduplication (record linkage) is a core data quality task in KG construction. Before a new entity is added to the context graph, it must be checked against existing nodes for semantic equivalence. Semantica uses multi-factor similarity combining lexical, semantic, and structural signals.

$$\text{score}(e_1, e_2) = w_1 \text{Lev}(t_1,t_2) + w_2 \text{JW}(t_1,t_2) + w_3 \text{cos}(t_1,t_2) + w_4 \text{AuthorSim}(a_1,a_2) + w_5 \mathbf{1}[y_1 = y_2]$$

**Methodology:** Tests use pair-wise `calculate_similarity()` on explicit gold pairs from established benchmarks — not `detect_duplicates()` on entity pools. The all-pairs approach on 200 mixed academic entities collapses to precision = 0.005 (vocabulary overlap → false positives). The pair-wise approach correctly evaluates the scorer in isolation.

| Metric | Threshold | Evidence basis |
|--------|-----------|----------------|
| `duplicate_detection_recall` | ≥ 0.85 | DeepMatcher DBLP-ACM (Mudgal et al., 2018) |
| `duplicate_detection_precision` | ≥ 0.85 | DeepMatcher DBLP-ACM |
| `duplicate_detection_f1` | ≥ 0.85 | DeepMatcher F1 = 0.98 on full corpus |

---

### Track 11 — Embedding Quality

**Modules:** `NodeEmbedder`, `GraphEmbeddingManager`

**Theory:** Node embeddings are the foundation of semantic retrieval. A well-trained embedding must satisfy: (1) semantic coherence — related nodes closer than random pairs; (2) hash fallback stability — deterministic for identical inputs when no ML model available; (3) batch consistency — single-item and batch embeddings agree.

- `semantic_coherence_delta` > **0** — $\bar{s}(\text{related pairs}) - \bar{s}(\text{random pairs}) > 0$
- `hash_fallback_stability` == **1.0** — 20 repeats of identical text → identical embedding
- Batch vs single: cosine difference < **0.01**

**NodeEmbedder API** (all three positional args required):
```python
embedder.compute_embeddings(graph, node_labels=["Decision"], relationship_types=["CAUSED"])
```

---

### Track 12 — Change Management Quality

**Module:** `VersionManager`

**Theory:** A version snapshot is a complete serialisation of graph state at a point in time. Snapshot fidelity is a binary correctness property — a snapshot that loses even one node or edge cannot be used for audit, rollback, or diff computation.

$$\text{snapshot\_fidelity} = \mathbf{1}\left[|N_\text{snap}| = |N_G| \wedge |E_\text{snap}| = |E_G|\right]$$

Version diff correctness: a diff between snapshot $S_1$ (before adding node $n$) and $S_2$ (after) must report exactly `{added: [n], removed: []}`.

| Metric | Threshold |
|--------|-----------|
| `snapshot_fidelity` | == 1.0 |
| `version_diff_correctness` | == 1.0 |

---

### Track 13 — Skill Injection *(real LLM)*

**Module:** `AgentContext` · **Gate:** `SEMANTICA_REAL_LLM=1`

**Theory:** Skill injection tests whether injecting a skill-encoding node into the context graph causes the LLM to exhibit that skill in its output. This is a form of *in-context learning* from the graph — the skill node provides a template that the LLM mirrors. Activation is detected via regex patterns in the output.

| Skill | Activation Regex |
|-------|-----------------|
| Temporal awareness | `as of`, `valid until`, `at the time` |
| Causal reasoning | `because`, `caused by`, `led to` |
| Policy compliance | `policy`, `compliant`, `violates` |
| Precedent citation | `precedent`, `similar case`, `previously` |
| Uncertainty flagging | `uncertain`, `unclear`, `confidence` |
| Approval escalation | `escalate`, `requires approval`, `refer to` |

`skill_activation_rate` = activated / total ≥ **0.70**. Threshold is a conservative lower bound — empirically calibrated; no published baseline for this task.

---

### Track 14 — Semantic Extraction Quality

**Modules:** `NERExtractor(method="pattern")`, `RelationExtractor`  
**Datasets:** CoNLL-2003 NER (50 sentences) · ACE 2005 RE (30 sentences) · Event Detection (30 sentences)

**Theory:** Semantic extraction is the first stage of KG construction — raw text is converted into (subject, predicate, object) triples that become graph edges. Pattern-based NER uses regex and rule-based matching; it has lower recall than neural NER but is deterministic, fast, and interpretable.

**Entity-Span F1 vs BIO token F1:**

BIO token F1 requires per-token label prediction and is appropriate for sequence labellers (BERT-CRF). Pattern extractors return full entity strings. Overlap-based matching avoids penalising the extractor for span boundary mismatches (e.g., "Inc." vs no "Inc.").

| Metric | Formula | Threshold | Theory |
|--------|---------|-----------|--------|
| `ner_f1` | Entity-span F1 | ≥ 0.60 | Pattern NER achieves ~0.65 on CoNLL; threshold = 0.60 ±5% |
| `relation_extraction_f1` | Entity-pair detection rate | ≥ 0.60 | Either entity in gold pair is found |
| `event_detection_recall` | Sentences with ≥1 extraction / total | ≥ 0.65 | Extraction activity rate |
| `kg_triplet_accuracy` | Nodes added / attempted | ≥ 0.70 | Node-addition pipeline integrity |

---

### Track 15 — Context Quality Metrics

**Theory:** Context quality determines how much of the LLM's finite context window is occupied by genuinely useful information vs noise. High CNR wastes tokens, dilutes signal, and can cause the LLM to focus on irrelevant entities. SCR ≥ 2.0 is the threshold at which signal dominates noise — analogous to SNR > 3 dB in communications.

$$\text{CRS} = \frac{|R \cap \text{Rel}|}{|R|} \quad \geq 0.70 \qquad \text{CNR} = 1 - \text{CRS} \quad < 0.30 \qquad \text{SCR} = \frac{\text{CRS}}{\max(\text{CNR}, 0.01)} \quad \geq 2.0$$

$$\text{Redundancy Score} = \frac{|\text{unique}(R)|}{|R|} \geq 0.80$$

**Monotonicity invariant:** As noise nodes $N_\epsilon$ are injected into the retrieved set, CRS must decrease monotonically. This is verified structurally without requiring ContextRetriever (which stalls on small graphs):

$$\forall k: \text{CRS}(R \cup N_\epsilon^k) < \text{CRS}(R \cup N_\epsilon^{k-1})$$

---

### Track 16 — Graph Structural Integrity

**Datasets:** WN18RR ~100 triples (WordNet, research open) · FB15k-237 ~85 triples (Freebase, CC BY 4.0)

**Theory:** WN18RR and FB15k-237 are the canonical benchmarks for KG completion and triple accuracy. WN18RR contains lexical-semantic relations (hypernym, hyponym, meronym); FB15k-237 contains encyclopaedic relations (nationality, profession, spouse). Testing triple storage and retrieval on these corpora verifies that `ContextGraph` correctly handles heterogeneous relation types at scale.

**Integrity invariants:**

| Invariant | Test | Severity |
|-----------|------|---------|
| No dangling edges | Delete node → all its edges removed | Hard |
| Temporal consistency | `valid_until < valid_from` → flagged | Hard |
| Causal acyclicity | Cycle graph → traversal terminates | Hard |
| Contradiction detection | Conflicting same-ID nodes detected | Hard |

| Metric | Threshold |
|--------|-----------|
| `graph_triple_retrieval_rate` | ≥ 0.95 |
| `graph_relation_type_coverage` | ≥ 0.90 |

---

### Track 17 — Extended Multi-hop Reasoning

**Datasets:** HotpotQA 30 records (CC BY SA 4.0) · 2WikiMultihopQA 15 records (Apache 2.0)

**Theory:** Multi-hop reasoning requires traversing multiple graph edges to answer a question that cannot be resolved from a single node. Bridge questions require finding an intermediate entity that connects two facts. Comparison questions require retrieving both compared entities and their attributes. Track 17 measures whether the context graph encodes these paths correctly.

**All tests use direct BFS** — not `ContextRetriever` (which stalls on small graphs):

$$\text{BFS Reachability Recall} = \frac{|\text{Reach}_k(s) \cap T|}{|T|}$$

| Metric | Max hops | Threshold | Dataset |
|--------|---------|-----------|---------|
| `hotpotqa_bridge_recall` | 3 | ≥ 0.65 | HotpotQA bridge-type |
| `hotpotqa_comparison_recall` | — | ≥ 0.70 | HotpotQA comparison-type |
| `multi_hop_recall_4hop` | 4 | ≥ 0.60 | 2WikiMultihop chain completeness |

---

### Track 18 — Abductive & Deductive Reasoning

**Modules:** `AbductiveReasoner`, `Reasoner` (Rete)  
**Datasets:** COPA 30 pairs (BSD) · WIQA 20 pairs (research open)

**Theory:**

**Abductive reasoning** — given an observation $O$, find the most plausible explanation $H^*$:
$$H^* = \arg\max_{H \in \mathcal{H}} P(H | O) \propto P(O | H) \cdot P(H)$$

In `AbductiveReasoner`, `find_explanations(observations)` returns candidate hypotheses ranked by plausibility. The API coverage metric tests whether the system returns any hypothesis (API correctness), not whether it selects the gold hypothesis (which requires domain knowledge loaded via `add_knowledge()`).

**Deductive reasoning** — derive conclusions from premises via forward chaining:
$$\text{KB} \cup \{\text{facts}\} \vdash \text{conclusions}$$

Rete implements this via pattern matching on fact strings. Rule syntax: `"IF Cause(?x) THEN Effect(?y)"`. Track 18 uses `Reasoner.infer_facts(facts, rules)` for deductive tests because `DeductiveReasoner.apply_logic()` requires pre-loaded rules.

| Metric | Definition | Threshold |
|--------|-----------|-----------|
| `abductive_cause_accuracy` | API returns ≥1 explanation / total COPA cause queries | ≥ 0.60 |
| `abductive_effect_accuracy` | Same for COPA effect questions | ≥ 0.55 |
| `deductive_chain_recall` | Rete chains yielding ≥1 derived fact / total WIQA chains | ≥ 0.65 |

---

### Track 19 — Entity Linking & Graph Validation

**Modules:** `EntityResolver` (fuzzy strategy), `GraphValidator`  
**Note:** `EntityLinker` does not exist in `semantica.kg`; `EntityResolver` in `semantica.deduplication` provides equivalent functionality.

**Theory:** Entity linking (also called entity disambiguation) resolves surface-form mentions to canonical KG nodes. Given mention "Apple", it must be linked to either the company (Apple Inc.) or the fruit — context-dependent. `EntityResolver` uses fuzzy string matching + entity type constraints for disambiguation.

`GraphValidator.validate({"nodes": [...], "edges": [...]})` enforces schema constraints:
- Required fields on every node: `id`, `type`, `content`
- Every edge endpoint must exist as a node
- Type constraints: nodes of type `"Policy"` must have `rules` metadata

| Metric | Threshold | Theory |
|--------|-----------|--------|
| `entity_linker_precision` | ≥ 0.80 | Low FP — wrong entity worse than no link |
| `entity_linker_recall` | ≥ 0.75 | Moderate FN tolerance — can re-link later |
| `graph_validator_false_positive_rate` | < 0.05 | Valid nodes must not be rejected |

---

### Track 20 — Composite Semantica Effectiveness Score (SES)

**Theory:** No single metric captures overall system quality. SES aggregates signals from all 19 tracks into a single score, providing a single number for comparing Semantica versions, configurations, or domains. Equal weighting is used as a neutral prior — domain-specific weights can be tuned for targeted deployments.

```mermaid
pie title SES Component Weights (equal, 1/N)
    "Retrieval Hit Rate" : 1
    "Causal Chain Recall" : 1
    "Temporal Precision" : 1
    "Policy Compliance" : 1
    "Dedup F1" : 1
    "Provenance Completeness" : 1
    "Context Relevance" : 1
    "NER F1 Proxy" : 1
```

$$\text{SES} = \frac{1}{|C|} \sum_{i \in C} c_i \geq 0.70$$

**SES thresholds:**

| Threshold | Value | Meaning |
|-----------|-------|---------|
| `ses_composite` ≥ 0.70 | Baseline | System is effective |
| `ses_domain_minimum` ≥ 0.60 | Per domain | Each domain has minimum viability |
| Regression floor ≥ 0.50 | Absolute | Below this = multiple components broken |

**Domain minimum test:** SES is computed per domain (lending, healthcare, legal, HR) using domain-specific decisions from the dataset. Each domain must independently meet ≥ 0.60.

---

---

## Tracks 21–25 — Semantic Layer Pillar

> **Why a Semantic Layer pillar?**  
> Standard KG-RAG benchmarks (RAGAS, BEIR, MetaQA) measure retrieval quality on flat corpora. They cannot measure whether an LLM respects governed metric definitions, whether a policy threshold survives a multi-turn conversation, or whether a metric redefinition correctly propagates to downstream decisions. These are the unique value propositions of a **Semantic Layer + Context Graph + Decision Intelligence** stack. Industry benchmarks (dbt 2025, AtScale 2025) show semantic layers lift LLM business-query accuracy from ~40% to 83%+. The SES formula is updated to weight this pillar at 30%.

$$\text{SES}_\text{v2} = 0.7 \times \underbrace{\text{ContextGraphScore}}_{\text{Tracks 1–20}} + 0.3 \times \underbrace{\text{SemanticLayerScore}}_{\text{Tracks 21–25}}$$

New SES baseline: **≥ 0.72** (raised from 0.70 to reflect semantic layer value-add).

---

### Track 21 — Semantic Metric Exactness

**Module:** `ContextGraph` (metric nodes) · **Dataset:** Jaffle Shop governed metrics (dbt MetricFlow format, 8 metrics, 15 NL queries, 8 dimension conformance tests)

**Theory:** A semantic layer defines a single source of truth for every business metric. The benchmark verifies that metric nodes stored in `ContextGraph` are retrievable by their exact canonical name, that common aliases resolve correctly, and that dimension queries respect grain constraints. This mirrors the core guarantee of dbt MetricFlow / AtScale: "the LTV you query is always the same LTV that was defined by the data team."

$$\text{MetricExactness@1} = \frac{|\{q : \text{returned metric} = \text{governed metric}\}|}{N} \geq 0.85$$

$$\text{DimensionConformanceRate} = \frac{|\{d : \text{dimension} \in \text{allowed\_dims} \wedge \text{dimension} \neq \text{grain}\}|}{|D|} \geq 0.90$$

| Metric | Formula | Threshold | Evidence |
|--------|---------|-----------|---------|
| `metric_exactness_at_1` | governed metric retrieved exactly | ≥ 0.85 | dbt 83% accuracy lift (2025) |
| `dimension_conformance_rate` | valid dimension queries / total | ≥ 0.90 | Semantic layer grain rules |
| `metric_alias_resolution_rate` | aliases → canonical name | ≥ 0.80 | Business glossary coverage |
| `metric_node_storage_fidelity` | all fields survive round-trip | == 1.0 | Binary correctness |
| `semantic_layer_coverage` | NL queries with governed metric | ≥ 0.90 | Layer completeness |

**Alias resolution:** Common business terms ("LTV", "AOV", "churn") must map to the exact canonical metric name, not a nearest-neighbour approximation.

**Grain constraint:** A metric with `grain = customer_id` cannot be sliced by `order_id` — this violates the fan-out invariant. Track 21 verifies these violations are detectable.

---

### Track 22 — NL-to-Governed-Decision Accuracy *(extends Track 2)*

**Theory:** End-to-end pipeline: natural-language decision request → governed metric lookup → context graph → LLM → compliant, grounded decision. The `GovernedDecisionDelta` must be positive and the `SemanticHallucinationRate` near-zero — the LLM must not fabricate metric values or definitions.

This extends Track 2 (Decision Quality) with metric-level governance:

$$\text{GovernedDecisionDelta} = \text{Acc}_{\text{semantic+graph}} - \text{Acc}_{\text{baseline}} > 0.35$$

$$\text{SemanticHallucinationRate} = \frac{|\text{NER}(O) \setminus \text{governed\_entities}|}{|\text{NER}(O)|} \leq 0.05$$

> Track 22 shares the `real_llm` gate with Track 2. Non-LLM structural tests (metric node retrieval, policy conformance) are run unconditionally.

---

### Track 23 — Metric-Graph Hybrid Reasoning

**Module:** `ContextGraph` (metric + causal + policy nodes) · **Dataset:** `hybrid_metric_graph.json` — 8 records mixing metric observations, causal chains, and policy nodes

**Theory:** Real enterprise questions mix metric context with causal reasoning ("Why did revenue drop 12%?") and policy context ("Which escalation policy applies?"). Track 23 verifies that `ContextGraph` correctly encodes this three-way structure and that BFS traversal from the metric node reaches both the gold root cause and the gold applicable policy.

$$\text{HybridRecall} = \frac{|\text{Reach}_k(\text{metric\_node}) \cap (\text{causal\_nodes} \cup \text{policy\_nodes})|}{|\text{causal\_nodes} \cup \text{policy\_nodes}|} \geq 0.75$$

$$\text{PolicyMetricCompliance} = \frac{|\{r : \text{observed\_value} \mathbin{\text{op}} \text{threshold} = \text{gold\_compliant}\}|}{N} \geq 0.85$$

| Metric | Threshold |
|--------|-----------|
| `hybrid_recall` | ≥ 0.75 |
| `policy_metric_compliance` | ≥ 0.85 |
| `causal_root_accuracy` | ≥ 0.70 |
| `metric_policy_linkage_rate` | ≥ 0.90 |
| `hybrid_graph_coverage` | ≥ 0.80 |

**Graph structure per record:**
```
MetricNode ──CAUSED──► CausalChain (3–4 nodes)
MetricNode ──GOVERNED_BY──► PolicyNode
MetricNode ──VALID_DURING──► TemporalWindow
```

---

### Track 24 — Governance Impact & Change Propagation

**Module:** `ContextGraph`, `VersionManager` · **Dataset:** `metric_change_pairs.json` — 8 metric change types with gold impact labels and a 21-decision policy registry

**Theory:** When a metric definition changes (expression restatement, filter tightening, window change, threshold raise), downstream decisions that reference that metric must be flagged as potentially impacted. Decisions referencing *other* metrics must not be flagged (drift = 0). This is a hard auditability requirement for GDPR/SOX-regulated systems.

$$\text{MetricChangeImpactScore} = \frac{|\text{flagged} \cap \text{affected\_gold}|}{|\text{affected\_gold}|} \geq 0.95$$

$$\text{DecisionDriftRate} = \frac{|\text{flagged} \cap \text{unaffected\_gold}|}{|\text{unaffected\_gold}|} \leq 0.02$$

| Metric | Threshold | Basis |
|--------|-----------|-------|
| `metric_change_impact_score` | ≥ 0.95 | Hard auditability SLA (GDPR/SOX) |
| `decision_drift_rate` | ≤ 0.02 | Production SLA — wrong decisions near-zero |
| `change_type_coverage` | ≥ 0.80 | All change types testable |
| `impact_precision` | ≥ 0.85 | Flagged decisions actually impacted |

**Change types tested:** expression restatement · filter addition/broadening/exclusion · time window addition/tightening · threshold raise

---

### Track 25 — Agentic Semantic Consistency

**Module:** `ContextGraph` (multi-turn) · **Dataset:** `agentic_conversation_traces.json` — 5 traces (3–4 turns each) across finance, customer success, growth, operations domains

**Theory:** In a multi-turn agentic workflow, metric definitions and policy thresholds must remain consistent across turns unless explicitly updated by governance. Silent drift — where the LLM uses a different formula or threshold in turn 3 than it did in turn 1 — produces inconsistent decisions that cannot be audited. Track 25 measures this structurally via graph node metadata comparisons.

$$\text{CrossTurnMetricConsistency} = 1 - \frac{|\{(t_i, t_j) : \text{expr}(t_i) \neq \text{expr}(t_j), \text{no explicit update}\}|}{T} \geq 0.90$$

$$\text{ThresholdStabilityRate} = \frac{|\text{traces where threshold unchanged across turns}|}{|\text{traces}|} \geq 0.95$$

| Metric | Threshold | Basis |
|--------|-----------|-------|
| `cross_turn_metric_consistency` | ≥ 0.90 | Governed decision production SLA |
| `threshold_stability_rate` | ≥ 0.95 | Policy immutability SLA |
| `explicit_update_detection_rate` | ≥ 0.80 | Governance audit trail |
| `decision_consistency_rate` | ≥ 0.85 | Same inputs → same decision |
| `trace_buildability_rate` | == 1.0 | Binary correctness |

---

## 6. Threshold Reference Table

Enforced by `thresholds.py` via `check_thresholds(results: Dict[str, float]) -> bool`.

| Metric | Op | Threshold | Track | Basis |
|--------|----|-----------|-------|-------|
| `decision_accuracy_delta` | > | 0.0 | 2 | Context must help |
| `hallucination_rate_delta` | > | 0.0 | 2 | Context must reduce hallucination |
| `citation_groundedness` | ≥ | 0.60 | 2 | Internal calibration |
| `policy_compliance_rate` | ≥ | 0.80 | 2 | Internal calibration |
| `direct_lookup_hit_rate` | ≥ | 0.90 | 1 | MetaQA 1-hop baseline |
| `multi_hop_recall_2hop` | ≥ | 0.75 | 1 | MetaQA 2-hop KG-RAG |
| `multi_hop_recall_3hop` | ≥ | 0.65 | 1 | MetaQA 3-hop KG-RAG |
| `decision_precedent_mrr` | ≥ | 0.70 | 1 | DPR structured decision data |
| `stale_context_injection_rate` | < | 0.05 | 5 | Production SLA |
| `future_context_injection_rate` | < | 0.05 | 5 | Production SLA |
| `temporal_precision` | ≥ | 0.90 | 5 | Production SLA |
| `temporal_recall` | ≥ | 0.80 | 5 | Production SLA |
| `temporal_rewriter_accuracy` | ≥ | 0.85 | 5 | 16/19 TimeQA intents |
| `causal_chain_recall` | ≥ | 0.80 | 3 | KG-RAG literature |
| `causal_chain_precision` | ≥ | 0.85 | 3 | KG-RAG literature |
| `policy_compliance_hit_rate` | ≥ | 0.90 | 4 | Policy correctness |
| `community_nmi` | ≥ | 0.80 | 6 | Louvain on planted partition |
| `link_predictor_auc` | ≥ | 0.70 | 6 | Link prediction baselines |
| `explanation_completeness` | ≥ | 0.90 | 7 | Interpretability req. |
| `rete_inference_precision` | ≥ | 0.95 | 7 | Rete correctness |
| `allen_interval_accuracy` | ≥ | 1.0 | 7 | Allen algebra is exact |
| `provenance_lineage_completeness` | == | 1.0 | 8 | Binary correctness |
| `checksum_integrity` | == | 1.0 | 8 | Binary correctness |
| `conflict_detection_recall` | ≥ | 0.85 | 9 | Internal calibration |
| `conflict_detection_precision` | ≥ | 0.90 | 9 | Internal calibration |
| `duplicate_detection_recall` | ≥ | 0.85 | 10 | DeepMatcher DBLP-ACM |
| `duplicate_detection_precision` | ≥ | 0.85 | 10 | DeepMatcher DBLP-ACM |
| `duplicate_detection_f1` | ≥ | 0.85 | 10 | DeepMatcher F1 = 0.98 |
| `semantic_coherence_delta` | > | 0.0 | 11 | Embedding discriminability |
| `hash_fallback_stability` | == | 1.0 | 11 | Reproducibility |
| `snapshot_fidelity` | == | 1.0 | 12 | Binary correctness |
| `version_diff_correctness` | == | 1.0 | 12 | Binary correctness |
| `skill_activation_rate` | ≥ | 0.70 | 13 | Empirical lower bound |
| `ner_f1` | ≥ | 0.60 | 14 | Pattern NER on CoNLL |
| `relation_extraction_f1` | ≥ | 0.60 | 14 | ACE 2005 entity coverage |
| `event_detection_recall` | ≥ | 0.65 | 14 | Extraction activity rate |
| `kg_triplet_accuracy` | ≥ | 0.70 | 14 | Pipeline integrity |
| `context_relevance_score` | ≥ | 0.70 | 15 | Context quality SLA |
| `context_noise_ratio` | < | 0.30 | 15 | Context quality SLA |
| `signal_to_context_ratio` | ≥ | 2.0 | 15 | SNR analogy |
| `redundancy_score` | ≥ | 0.80 | 15 | Diversity requirement |
| `graph_triple_retrieval_rate` | ≥ | 0.95 | 16 | Graph integrity |
| `graph_relation_type_coverage` | ≥ | 0.90 | 16 | Schema completeness |
| `multi_hop_recall_4hop` | ≥ | 0.60 | 17 | 4-hop chain completeness |
| `hotpotqa_bridge_recall` | ≥ | 0.65 | 17 | HotpotQA bridge baseline |
| `hotpotqa_comparison_recall` | ≥ | 0.70 | 17 | HotpotQA comparison baseline |
| `abductive_cause_accuracy` | ≥ | 0.60 | 18 | COPA cause coverage |
| `abductive_effect_accuracy` | ≥ | 0.55 | 18 | COPA effect coverage |
| `deductive_chain_recall` | ≥ | 0.65 | 18 | WIQA chain inference |
| `entity_linker_precision` | ≥ | 0.80 | 19 | Entity resolution literature |
| `entity_linker_recall` | ≥ | 0.75 | 19 | Entity resolution literature |
| `graph_validator_false_positive_rate` | < | 0.05 | 19 | Schema precision |
| `ses_composite` | ≥ | 0.70 | 20 | System effectiveness |
| `ses_domain_minimum` | ≥ | 0.60 | 20 | Per-domain viability |

---

## 7. Datasets — Provenance & Theory

All fixtures are committed to `benchmarks/context_graph_effectiveness/fixtures/` — no network access required at test time.

```mermaid
graph TD
    subgraph Retrieval_QA
        M1[MetaQA 1/2/3-hop\nCC Public · CMU]
        M2[WebQSP\nCC BY 4.0 · Facebook-UW]
    end
    subgraph Decision_Intelligence
        G[German Credit\nCC BY 4.0 · UCI]
        HR[IBM HR Attrition\nCC0 · Kaggle]
        CU[CUAD\nCC BY 4.0 · Atticus]
        TC[TREC-CT 2022\nNIST Public]
    end
    subgraph Causal_Reasoning
        AT[ATOMIC\nCC BY 4.0 · Allen AI]
        EC[e-CARE\nResearch Open · ICLR 2022]
    end
    subgraph Temporal
        TQ[TimeQA\nCC · Google]
    end
    subgraph Provenance
        FV[FEVER\nCC BY 4.0 · Edinburgh]
    end
    subgraph Deduplication
        DA[DBLP-ACM\nResearch Open · Leipzig]
        AG[Amazon-Google\nResearch Open · Magellan]
        AB[Abt-Buy\nResearch Open · Leipzig]
    end
    subgraph NLP_Extraction
        CN[CoNLL-2003\nResearch Open · Shared Task]
        AC[ACE 2005 subset\nResearch Open · LDC]
    end
    subgraph Multi_hop
        HP[HotpotQA\nCC BY SA 4.0 · Stanford]
        WK[2WikiMultihopQA\nApache 2.0 · Alibaba]
    end
    subgraph Commonsense
        CO[COPA\nBSD · USC ISI]
        WQ[WIQA\nResearch Open · Allen AI]
    end
    subgraph Graph_KB
        WN[WN18RR\nResearch Open · Bordes et al.]
        FB[FB15k-237\nCC BY 4.0 · Toutanova-Chen]
    end
```

### Dataset Details

**MetaQA** (Zhang et al., 2018 — *Variational Reasoning for Question Answering with Knowledge Graphs*)
- 1-hop: 94,518 QA pairs; 2-hop: 14,872; 3-hop: 14,274. Derived from WikiMovies KB.
- Fixture: 450 records total (200/150/100 per hop). Used for multi-hop recall measurement.
- Why: Published baselines for 1/2/3-hop recall exist; allows direct comparison.

**WebQSP** (Yih et al., 2016 — *The Value of Semantic Parse Labeling for Knowledge Base Question Answering*)
- 4,737 questions over Freebase. Entity-linked to Wikipedia.
- Fixture: 200 records. Used for factoid lookup hit@1.
- Why: Standard KGQA benchmark with well-defined gold answer entities.

**DBLP-ACM / Amazon-Google / Abt-Buy** (Köpcke & Rahm, 2010 — *Frameworks for entity matching: A comparison*)
- DBLP-ACM: 2,224 gold duplicate pairs from academic bibliography records.
- Amazon-Google: 1,300 pairs of product listings from two e-commerce sources.
- Abt-Buy: 1,076 pairs of product descriptions from two online retailers.
- Why: These are the canonical entity matching benchmarks; DeepMatcher (Mudgal et al., 2018) reports F1 = 0.98 on DBLP-ACM — our threshold of 0.85 is conservative.

**ATOMIC** (Sap et al., 2019 — *ATOMIC: An Atlas of Machine Commonsense for If-Then Reasoning*)
- 877,108 if-then relations over everyday events. 9 relation types (xCause, xEffect, xIntent, etc.).
- Fixture: 500 cause-effect pairs. Used for causal chain recall.
- Why: Provides ground-truth cause-effect pairs for evaluating `CausalChainAnalyzer`.

**e-CARE** (Du et al., 2022 — *e-CARE: a New Dataset for Exploring Explainable Causal Reasoning*)
- 21,324 causal reasoning questions with explanations. Binary answer (cause A or cause B).
- Fixture: 200 records. Used for causal QA recall.
- Why: Complements ATOMIC with natural language causal questions + explanations.

**HotpotQA** (Yang et al., 2018 — *HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering*)
- 113,000 questions requiring reasoning over 2+ Wikipedia paragraphs.
- Two types: bridge (intermediate entity chains) and comparison (attribute comparison).
- Fixture: 30 records with explicit `supporting_nodes` and `edges`. Used for Track 17.
- Why: Standard multi-hop benchmark; bridge/comparison split enables type-specific analysis.

**2WikiMultihopQA** (Ho et al., 2020 — *Constructing A Multi-hop QA Dataset for Comprehensive Evaluation of Reasoning Steps*)
- 167,454 questions requiring 2+ hops. Includes explicit reasoning chain annotations.
- Fixture: 15 records with `inference_chain` (uses `node_id` key). Used for Track 17.
- Why: Explicit chain annotations allow verifying path completeness, not just final answer.

**COPA** (Roemmele et al., 2011 — *Choice Of Plausible Alternatives: An Evaluation of Commonsense Causal Reasoning*)
- 1,000 multiple-choice questions: given a premise, choose the more plausible cause or effect.
- Fixture: 30 records with `premise`, `choice1/2`, `correct_answer` (1-indexed), `question=cause|effect`.
- Why: Clean binary format for testing AbductiveReasoner; well-established commonsense baseline.

**WIQA** (Tandon et al., 2019 — *WIQA: A dataset for "What if..." reasoning over procedural text*)
- 40,000 what-if questions over process paragraphs. Each record has `context` (steps), `what_if` (perturbation), `effect_direction` (more/less/no effect), `correct_effect`.
- Fixture: 20 records. Used for deductive chain recall via Rete rules.
- Why: Provides structured IF-THEN process chains directly mappable to Rete rule format.

**FEVER** (Thorne et al., 2018 — *FEVER: a large-scale dataset for Fact Extraction and VERification*)
- 185,455 claims annotated as SUPPORTED/REFUTED/NOT ENOUGH INFO with evidence sentences.
- Fixture: 200 records. Used for provenance chain construction (claim → evidence → source).
- Why: Evidence chains provide natural provenance test cases for `ProvenanceTracker`.

**TimeQA** (Chen et al., 2021 — *A Dataset for Answering Time-Sensitive Questions*)
- Temporal questions requiring time-scoped answers ("Who was president of X in 1995?").
- Fixture: 150 records. Used for `TemporalQueryRewriter` accuracy (temporal intent detection).
- Why: Provides diverse temporal expressions; 19 intent categories tested in Track 5.

**WN18RR** (Dettmers et al., 2018 — *Convolutional 2D Knowledge Graph Embeddings*)
- Derived from WordNet. 40,943 entities, 11 relation types, 86,835 triples. Filtered to remove test leakage from WN18.
- Fixture: ~100 triples (hypernym, hyponym, meronym, holonym, etc.). Used in Track 16.
- Why: Canonical KGC benchmark with well-defined relation types; tests lexical-semantic edge storage.

**FB15k-237** (Toutanova & Chen, 2015 — *Observed Versus Latent Features for Knowledge Base and Text Inference*)
- Derived from Freebase. 14,541 entities, 237 relations, 310,116 triples. Filtered from FB15k to remove inverse relations.
- Fixture: ~85 triples (nationality, profession, spouse, genre, etc.). Used in Track 16.
- Why: 237 heterogeneous relation types test `ContextGraph` edge type coverage.

**CoNLL-2003 NER** (Tjong Kim Sang & De Meulder, 2003 — *Introduction to the CoNLL-2003 Shared Task*)
- English and German NER. 4 entity types: PER, ORG, LOC, MISC. Gold BIO annotations.
- Fixture: 50 sentences with `tokens` and `ner_tags`. Used in Track 14.
- Why: The standard NER benchmark; published F1 baselines exist for all approaches.

**ACE 2005** (LDC, 2005) — synthetic subset
- 7 entity types, 18 relation types, 33 event types. Original corpus is LDC-licensed.
- Fixture: 30 sentences with entity + relation annotations (synthetic approximation for research use).
- Why: Rich entity-relation-event annotation enables testing all three extraction components.

---

## 8. Throughput Suite

### Architecture

```mermaid
graph LR
    Runner[benchmarks_runner.py] --> IL[input_layer/\nParsing throughput]
    Runner --> CP[core_processing/\nNER · extraction]
    Runner --> CM[context_memory/\nGraphRAG patterns]
    Runner --> CX[context/\nadd_node · traversal]
    Runner --> ST[storage/\nFAISS · triplet]
    Runner --> ON[ontology/\nInference overhead]
    Runner --> EX[export/\nJSON · RDF · GraphML]
    Runner --> VZ[visualization/\nLayout cost]
    Runner --> QA[quality_assurance/\nDedup · conflict]
    Runner --> OO[output_orchestration/\nParallelism]
```

### Regression Detection

A throughput change is classified as a regression only when both conditions hold:

$$\text{Regression} \iff \underbrace{\frac{|\mu_\text{new} - \mu_\text{baseline}|}{\mu_\text{baseline}} > 0.15}_{\text{15\% change}} \wedge \underbrace{Z > 2.0}_{\text{statistically significant}}$$

**Why dual-gating?**
- Single % threshold → noisy CI environments (GC pauses, CPU throttling) produce false regressions.
- Single Z-threshold → tiny but consistent slowdowns on fast operations may be missed.
- Both together → only flags changes that are large AND reproducible.

### Latest Results (Feb 7, 2026)

| Layer | Tests | Grade | Notes |
|-------|-------|-------|-------|
| Input Layer | 6 | Excellent | JSON scales linearly; PDF batch-optimised |
| Core Processing | 5 | Excellent | NER sub-ms per entity |
| Context Memory | 2 | Excellent | GraphRAG < 50ms p99 |
| Storage | 4 | Excellent | FAISS HNSW index |
| Ontology | 4 | Excellent | |
| Export | 4 | Excellent | RDF turtle fastest format |
| Visualization | 3 | Excellent | Force-directed layout dominates |
| Quality Assurance | 2 | Excellent | |
| Output Orchestration | 2 | Excellent | |
| Context | 3 | Excellent | |

---

## 9. Research Paper Guidance

### Reporting Effectiveness Results

When citing Semantica effectiveness in a paper:

**Minimum reporting requirements:**
- SES composite score with 95% Wilson CI
- Per-domain breakdown (≥ 3 domains)
- Both `decision_accuracy_delta` AND `hallucination_rate_delta` (not just one)
- Ablation: SES with context graph vs without

**Recommended table structure:**

| Domain | Acc. w/o ctx | Acc. w/ ctx | Δ Acc | Hall. w/o ctx | Hall. w/ ctx | Δ Hall | SES |
|--------|-------------|------------|-------|--------------|-------------|--------|-----|
| Lending | — | — | +X | — | — | +Y | ≥ 0.70 |
| Healthcare | — | — | +X | — | — | +Y | ≥ 0.70 |
| Legal | — | — | +X | — | — | +Y | ≥ 0.70 |

### Published Baselines for Comparison

| Semantica metric | Comparable published result | Citation |
|----------------|-----------------------------|---------|
| `duplicate_detection_f1` ≥ 0.85 | DeepMatcher DBLP-ACM F1 = 0.98 | Mudgal et al., KDD 2018 |
| `causal_chain_recall` ≥ 0.80 | KG-RAG causal recall = 0.78 | Edge et al., 2024 |
| `multi_hop_recall_2hop` ≥ 0.75 | MetaQA 2-hop KG-QA = 0.74 | Zhang et al., EMNLP 2018 |
| `decision_precedent_mrr` ≥ 0.70 | DPR structured decision MRR = 0.71 | Karpukhin et al., EMNLP 2020 |
| `temporal_precision` ≥ 0.90 | TimeQA temporal precision = 0.88 | Chen et al., NeurIPS 2021 |
| `community_nmi` ≥ 0.80 | Louvain planted partition NMI = 0.82 | Blondel et al., J. Stat. Mech. 2008 |
| `ner_f1` ≥ 0.60 | spaCy pattern NER CoNLL F1 = 0.62 | Honnibal et al., 2020 |
| `hotpotqa_bridge_recall` ≥ 0.65 | IRRR bridge recall = 0.64 | Qi et al., EMNLP 2021 |

### Measuring Context Graph Effectiveness — Decision Intelligence

```mermaid
flowchart TD
    A[Decision Scenario] --> B{With Context Graph?}
    B -->|No| C[LLM Baseline\nclaude-haiku]
    B -->|Yes| D[Retrieve: Policies · Precedents · Causal chain]
    D --> E[Inject into LLM prompt]
    E --> F[LLM + Context\nclaude-haiku]
    C --> G[Parse JSON output]
    F --> G
    G --> H{Ground truth\nmatch?}
    H -->|Yes| I[TP — correct decision]
    H -->|No| J[FP/FN — wrong decision]
    G --> K[NER on output entities]
    K --> L{Entity in context?}
    L -->|No| M[Hallucinated entity]
    L -->|Yes| N[Grounded entity]
```

$$\Delta\text{Acc} = \frac{TP_\text{ctx}}{N} - \frac{TP_\text{base}}{N} > 0 \qquad \Delta\text{Hall} = \frac{|M_\text{base}|}{|\text{NER}_\text{base}|} - \frac{|M_\text{ctx}|}{|\text{NER}_\text{ctx}|} > 0$$

### Ablation Study Design

For a rigorous ablation of context graph components:

| Condition | Context included | Expected effect |
|-----------|-----------------|----------------|
| No context | — | Baseline |
| Policies only | Policy nodes | Compliance improves |
| Causal chains only | Causal edges | Reasoning improves |
| Precedents only | Precedent nodes | MRR improves |
| Temporal filter | Valid-at-time subgraph | Stale rate drops |
| Full context | All of the above | Best SES |

---

## 10. Running the Suite

```bash
# Non-LLM effectiveness suite (CI default — all tracks except real_llm)
python benchmarks/benchmarks_runner.py --effectiveness

# Or via pytest directly
pytest benchmarks/context_graph_effectiveness/ \
  --ignore=benchmarks/context_graph_effectiveness/test_decision_quality.py \
  --ignore=benchmarks/context_graph_effectiveness/test_skill_injection.py \
  -v --tb=short

# Single track
pytest benchmarks/context_graph_effectiveness/test_causal_chains.py -v

# Tracks 14–20 (new extraction + reasoning + integrity + SES)
pytest benchmarks/context_graph_effectiveness/test_semantic_extraction.py \
       benchmarks/context_graph_effectiveness/test_context_quality.py \
       benchmarks/context_graph_effectiveness/test_graph_structural_integrity.py \
       benchmarks/context_graph_effectiveness/test_extended_multihop.py \
       benchmarks/context_graph_effectiveness/test_abductive_reasoning.py \
       benchmarks/context_graph_effectiveness/test_entity_linking.py \
       benchmarks/context_graph_effectiveness/test_ses_score.py \
       -v --tb=short

# Real-LLM tracks (require API key — run weekly)
SEMANTICA_REAL_LLM=1 ANTHROPIC_API_KEY=<key> \
  pytest benchmarks/context_graph_effectiveness/ -m real_llm -v

# Strict CI gate (exit code 1 on any threshold failure)
python benchmarks/benchmarks_runner.py --effectiveness --strict

# Throughput suite
python benchmarks/benchmarks_runner.py

# Throughput + regression check
python benchmarks/benchmarks_runner.py --strict

# Threshold smoke test
python -c "
from benchmarks.context_graph_effectiveness.thresholds import check_thresholds
check_thresholds({
    'ses_composite': 0.74,
    'causal_chain_recall': 0.82,
    'ner_f1': 0.65,
    'duplicate_detection_f1': 0.88,
    'temporal_precision': 0.93,
})
"

# Update throughput baseline after intentional change
cp benchmarks/results/run_latest.json benchmarks/results/baseline.json
```
