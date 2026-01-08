# Document/Sentence Conflict and Contradiction Detection: Research Synthesis

## Executive Summary

This report synthesizes research findings from 15+ papers on document/sentence conflict and contradiction detection. The papers cover diverse approaches including RAG-based systems, Natural Language Inference (NLI), claim decomposition, knowledge graphs, and factual consistency evaluation. Key insights are organized to provide actionable recommendations for upgrading conflict/contradiction detection systems.

---

## 1. Core Paradigms for Conflict Detection

### 1.1 Decompose-Then-Verify Paradigm

The dominant approach across multiple papers is **Decompose-Then-Verify**:

1. **Decompose** complex text into atomic claims/facts
2. **Verify** each claim independently against a knowledge source
3. **Aggregate** verification results for final judgment

**Key implementations:**
- **FactScore**: Decomposes text into atomic facts, verifies each against Wikipedia
- **VeriScore**: Claims tied to source sentences for better traceability
- **FacTool**: Tool-augmented verification for diverse domains
- **SAFE (Search-Augmented Factuality Evaluator)**: Uses search APIs for verification

### 1.2 Knowledge Conflict Detection in RAG Systems

**CLEAR Framework** (2510.12460) provides critical insights:

- **Hierarchical Knowledge Integration**: LLMs integrate retrieved evidence at multiple levels:
  - Token-level attention
  - Sentence-level semantic binding
  - Passage-level contextual weighting

- **Latent Conflict Signals**: Knowledge conflicts manifest as detectable patterns in hidden states
  - MLP probes can classify conflict types from internal representations
  - Hidden states contain richer conflict information than attention patterns alone

- **Key Finding**: LLMs tend to **amplify irrelevant context** that aligns with parametric knowledge, leading to hallucinations

**CLEAR's Three-Component Architecture:**
```
1. Fine-grained Knowledge Pruning
   - Removes conflicting/irrelevant information at token/sentence level

2. Hidden-State Probing
   - Binary classifier on hidden states to detect conflicts
   - Achieves 93.1% F1 on ConFiQA QA benchmark

3. Conflict-Aware Fine-Tuning
   - Attention guidance loss to prefer faithful context
   - Trains model to prioritize retrieved knowledge appropriately
```

### 1.3 Information-Theoretic Perspective (Swin-VIB)

**Key Insight** (2504.12982): Conflict resolution depends on **information difference** between conflicting and supplementary evidence:

```
When |ΔI| is large → LLMs confidently resolve preferences
When |ΔI| is small → High uncertainty, inconsistent behavior
```

**Swin-VIB Architecture:**
- Variational Information Bottleneck integrated into transformer decoder
- Sliding window processing for long contexts
- Adapts retrieved information based on conflict magnitude

---

## 2. Claim Decomposition Methods

### 2.1 Decomposition Quality Metrics (DecMetrics - 2509.04483)

Three critical metrics for evaluating decomposition quality:

| Metric | Definition | Purpose |
|--------|------------|---------|
| **COMPLETENESS** | Coverage of original claims | Ensures no information loss |
| **CORRECTNESS** | Faithfulness to source | Prevents fabrication |
| **SEMANTIC ENTROPY** | Non-redundancy measure | Avoids duplicate claims |

**DecModel**: Lightweight T5-based models (80M-780M params) trained with RL using these metrics as rewards. Achieves competitive results with much smaller models than GPT-4.

### 2.2 Common Decomposition Errors (2411.02400)

Four major error types that degrade verification performance:

1. **Omission**: Missing important claims from original text
2. **Ambiguity**: Vague or unclear claims requiring context
3. **Over-Decomposition**: Breaking claims too finely, losing meaning
4. **Alteration of Original Meaning**: Distorting claims during decomposition

**Mitigation strategies:**
- Explicit decomposition guidelines
- Multi-pass verification
- Decontextualization before decomposition

### 2.3 Decontextualization and Decomposition (DnD - 2412.13175)

**Joint DnD approach:**
1. Decontextualize: Make each claim self-contained
2. Decompose: Break into atomic facts
3. Verify: Check each atomic fact

**DNDSCORE** combines these steps for more accurate factuality scoring.

### 2.4 Evaluation Framework for Claim Extraction (2502.04955)

Six dimensions for evaluating claim extraction:

| Dimension | Description |
|-----------|-------------|
| **Atomicity** | Single fact per claim |
| **Fluency** | Grammatical correctness |
| **Decontextualization** | Self-contained meaning |
| **Faithfulness** | True to source |
| **Focus** | Claims match checkworthy content |
| **Coverage** | All important claims extracted |

**Ffact Score** = Harmonic mean of Focus and Coverage

**FEVERFact Dataset**: 17K atomic claims with gold annotations

---

## 3. NLI-Based Approaches

### 3.1 Grounded Factuality Classification (2410.09455)

Maps factuality problem to **multi-label entailment**:

```
Classes: Entailment (E), Neutral (N), Contradiction (C)

Sentence Types:
- Grounded: All claims entailed by source (EE...E)
- Ungrounded: At least one contradiction (contains C)
- Partially grounded: Mix of E and N
```

**Architecture:**
- 4B parameter model fine-tuned on synthetic data
- Outperforms classifier-based and prompting approaches
- Handles multi-sentence factuality assessment

### 3.2 AMR-Based Verification (AMREx - 2411.01343)

**Abstract Meaning Representation** for explainable fact verification:

```python
# Similarity formula
f(sA, sB) = λ * Smatch_P(gA, gB) + (1-λ) * Cosine_SBERT(sA, sB)

# Where:
# Smatch_P = Structural similarity of AMR graphs
# Cosine_SBERT = Textual semantic similarity
# λ = Weighting parameter (typically 0.5)
```

**Advantages:**
- Produces explainable node mappings
- Combines structural and semantic similarity
- Better handles complex multi-hop reasoning

### 3.3 Soft-NLI Factuality (2509.18901)

Replaces hard label aggregation with **soft probability scores**:

```
score = P(entail) / (P(entail) + P(contradict))
```

Improves calibration and handles uncertainty better than binary labels.

---

## 4. Knowledge Graph Approaches

### 4.1 Context Graph to Claim (CG2C - 2501.17144)

**FactCG Framework** for multi-hop claim verification:

```
Pipeline:
1. Build context graph from source documents
2. Extract relevant subgraphs for each claim
3. Generate synthetic training data via LLM
4. Train verifier on CG2C data

Key Finding: LLM-generated claims require 2-4 hop reasoning
```

**Advantages:**
- Handles complex reasoning chains
- Generates high-quality synthetic training data
- Improves multi-hop verification accuracy

### 4.2 FactKG (Knowledge Graph Verification)

Uses knowledge graphs to:
- Ground claims to entities
- Verify relationships against structured data
- Provide explainable verification paths

---

## 5. Factual Consistency Metrics

### 5.1 Atomic Fact-Based Scoring (2408.15171)

**Error taxonomy for atomic facts:**

| Error Type | Code | Description |
|------------|------|-------------|
| Predicate Error | PredE | Wrong action/relation |
| Entity Error | EntE | Wrong named entity |
| Circumstantial Error | CircE | Wrong time/location/manner |
| Coreference Error | CorefE | Incorrect pronoun resolution |
| Link Error | LinkE | Wrong connection between facts |
| Out-of-Article Error | OutE | Information not in source |
| Grammatical Error | GramE | Malformed claim |

### 5.2 Benchmark Datasets

| Dataset | Size | Focus | Key Features |
|---------|------|-------|--------------|
| **FActScore** | 500+ | Biography | Atomic fact verification |
| **WICE** | 1.8K | Wikipedia | Claim entailment |
| **FEVERFact** | 17K | Claims | Atomic decomposition |
| **ConFiQA** | - | QA | Knowledge conflict detection |
| **FaithEval** | - | RAG | Faithfulness evaluation |
| **Claim2Atom** | Aggregated | Multi-domain | Decomposition quality |

---

## 6. Practical Recommendations

### 6.1 System Architecture for Conflict Detection

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Documents/Sentences                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 1: Claim Decomposition                    │
│  - Use DecModel or fine-tuned T5 for atomic decomposition   │
│  - Apply decontextualization (DnD approach)                 │
│  - Validate: COMPLETENESS, CORRECTNESS, SEMANTIC ENTROPY    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 2: Conflict Detection                     │
│  - Hidden-state probing (CLEAR approach)                    │
│  - NLI-based classification (Grounded Factuality)           │
│  - AMR-based structural comparison (for explainability)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 3: Conflict Resolution                    │
│  - Information-theoretic confidence scoring (Swin-VIB)      │
│  - Multi-hop reasoning for complex conflicts (CG2C)         │
│  - Attention guidance for faithful generation               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage 4: Output & Explanation                   │
│  - Conflict type classification                              │
│  - AMR node mapping for explainability                      │
│  - Confidence scores with uncertainty quantification        │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Key Implementation Strategies

#### For High Accuracy:
1. **Use hidden-state probing** (CLEAR) for detecting latent conflicts
2. **Implement soft-NLI scoring** instead of hard labels
3. **Apply multi-hop reasoning** for complex document conflicts
4. **Combine structural (AMR) and semantic (SBERT) similarity**

#### For Efficiency:
1. **Use lightweight DecModel** (T5-based) for decomposition
2. **Apply sliding window processing** (Swin-VIB) for long documents
3. **Cache frequently verified claims** for repeated comparisons
4. **Use hierarchical verification** (quick filter → detailed analysis)

#### For Explainability:
1. **Generate AMR graphs** for both documents
2. **Provide node-level mapping** showing conflicting elements
3. **Output confidence intervals** not just point estimates
4. **Track reasoning chains** for multi-hop conflicts

### 6.3 Training Data Generation

1. **Synthetic data via CG2C**: Build context graphs, generate claims requiring multi-hop verification
2. **Error injection**: Systematically inject PredE, EntE, CircE errors for training
3. **Contrastive pairs**: Generate conflicting/supporting claim pairs
4. **Difficulty levels**: Create easy (1-hop) to hard (4-hop) examples

### 6.4 Evaluation Protocol

```python
# Recommended evaluation metrics
metrics = {
    # Decomposition Quality
    "completeness": coverage_score,
    "correctness": faithfulness_score,
    "semantic_entropy": redundancy_score,

    # Conflict Detection
    "precision": conflict_precision,
    "recall": conflict_recall,
    "f1": conflict_f1,

    # Overall System
    "ffact_score": harmonic_mean(focus, coverage),
    "auc_roc": ranking_quality,
    "calibration_error": confidence_accuracy,
}
```

---

## 7. Key Takeaways

1. **Decompose-Then-Verify is the dominant paradigm** - Break text into atomic claims before verification

2. **Hidden states contain rich conflict signals** - Use probing classifiers on LLM internal representations

3. **Decomposition quality directly impacts verification accuracy** - Invest in high-quality decomposition

4. **Multi-hop reasoning is essential** - LLM-generated claims often require 2-4 hop verification

5. **Soft probabilities outperform hard labels** - Use Soft-NLI for better calibration

6. **Explainability requires structural analysis** - AMR graphs provide interpretable conflict explanations

7. **Information difference determines resolution confidence** - Large |ΔI| leads to confident conflict resolution

8. **Lightweight models can be competitive** - T5-based DecModel achieves good results with 80M-780M params

---

## 8. References

| Paper ID | Title | Key Contribution |
|----------|-------|------------------|
| 2510.12460 | CLEAR: Probing Latent Knowledge Conflict | Hidden-state probing, attention guidance |
| 2509.04483 | DecMetrics | COMPLETENESS, CORRECTNESS, SEMANTIC ENTROPY |
| 2504.12982 | Swin-VIB | Information-theoretic conflict accommodation |
| 2411.01343 | AMREx | AMR-based explainable verification |
| 2412.13175 | DNDSCORE | Joint decontextualization and decomposition |
| 2502.04955 | Claim Extraction for Fact-Checking | FEVERFact dataset, Ffact score |
| 2410.09455 | Grounded Factuality Classification | NLI-based multi-label approach |
| 2509.18901 | Soft-NLI Factuality | Soft probability scoring |
| 2501.17144 | FactCG | CG2C for multi-hop reasoning |
| 2411.02400 | Decomposition Dilemmas | Decomposition error taxonomy |
| 2408.15171 | Atomic Facts for Summarization | Atomic fact error types |
| 2504.00180 | RAG Contradiction Detection | RAG-specific challenges |
| 2506.08500 | Knowledge Conflict in RAG | Conflict types in retrieval |
| 2508.15253 | Faithful RAG | Faithfulness evaluation |
| 2502.08080 | NLI Factuality | NLI-based approaches |

---

*Report generated: January 2026*
*Based on analysis of 15+ papers from arXiv on document conflict and contradiction detection*
