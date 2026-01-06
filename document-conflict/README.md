# Document Conflict Detection in RAG Systems

> Collection of 37 papers on knowledge conflict detection, contradiction resolution, and NLP techniques for RAG systems.

## Table of Contents
- [Section 1: Core Conflict Detection in RAG](#section-1-core-conflict-detection-in-rag)
- [Section 2: NotebookLM & RAG Architecture](#section-2-notebooklm--rag-architecture)
- [Section 3: Atomic Fact Decomposition](#section-3-atomic-fact-decomposition)
- [Section 4: Knowledge Graph for Conflict Resolution](#section-4-knowledge-graph-for-conflict-resolution)
- [Section 5: NLI-based Contradiction Detection](#section-5-nli-based-contradiction-detection)
- [Section 6: Document-level Claim Extraction & Fact-Checking](#section-6-document-level-claim-extraction--fact-checking)
- [Section 7: Multi-Document Summarization & Conflict](#section-7-multi-document-summarization--conflict)
- [Section 8: RAG Surveys & Benchmarks](#section-8-rag-surveys--benchmarks)
- [NLP Pipeline Overview](#nlp-pipeline-overview)
- [Key Techniques Summary](#key-techniques-summary)

---

## Section 1: Core Conflict Detection in RAG

### 1.1 DRAGged into Conflicts (June 2025)
**Detecting and Addressing Conflicting Sources in Search-Augmented LLMs**

| Field | Value |
|-------|-------|
| ArXiv | [2506.08500](https://arxiv.org/abs/2506.08500) |
| Authors | Arie Cattan, Alon Jacovi, Ori Ram, Jonathan Herzig, et al. |

**Contributions:**
- First general approach for addressing wide range of knowledge conflicts
- **CONFLICTS Benchmark**: Expert-annotated examples with conflict taxonomy
- Taxonomy: Freshness conflicts, Opinion conflicts, Source reliability conflicts

**Method:** Explicit conflict reasoning prompting before answering

---

### 1.2 CLEAR: Probing Latent Knowledge Conflict (Oct 2025)
**Probing Latent Knowledge Conflict for Faithful Retrieval-Augmented Generation**

| Field | Value |
|-------|-------|
| ArXiv | [2510.12460](https://arxiv.org/abs/2510.12460) |

**Key Findings:**
- Conflicts manifest at **sentence-level factual representations**
- Hidden states have **discriminative features** for conflict detection
- Irrelevant context amplified when aligned with parametric knowledge

**CLEAR Framework (3 stages):**
```
1. Decomposition → Sentence-level knowledge units
2. Localization  → Hidden-state probing for conflict signals
3. Guided Integration → Conflict-aware fine-tuning
```

---

### 1.3 MADAM-RAG (April 2025)
**Retrieval-Augmented Generation with Conflicting Evidence**

| Field | Value |
|-------|-------|
| ArXiv | [2504.13079](https://arxiv.org/abs/2504.13079) |

**Handles 3 problems simultaneously:**
- Ambiguity (ambiguous queries)
- Misinformation (false information)
- Noise (irrelevant documents)

**Multi-Agent Debate Approach:**
```python
for round in debate_rounds:
    agent_responses = [agent.reason(docs) for agent in agents]
    aggregator.collate(agent_responses)
    aggregator.filter_misinformation()
    aggregator.disambiguate_entities()
```

**Results:** +11.40% on AmbigDocs, +15.80% on misinformation suppression

---

### 1.4 Swin-VIB (April 2025)
**Accommodate Knowledge Conflicts in Retrieval-augmented LLMs**

| Field | Value |
|-------|-------|
| ArXiv | [2504.12982](https://arxiv.org/abs/2504.12982) |

**Theory:** Knowledge conflicts defined via **conditional entropy**

**Framework:**
```
Retrieved Info → Variational Information Bottleneck → Adapted Info → LLM → Response
```

**Key Finding:**
- Large conflict → Model confident (low uncertainty)
- Small/ambiguous conflict → High generation uncertainty

**Results:** +11.14% EM score on open-ended QA

---

### 1.5 Contradiction Detection in RAG (March 2025)
**LLMs as Context Validators for Improved Information Consistency**

| Field | Value |
|-------|-------|
| ArXiv | [2504.00180](https://arxiv.org/abs/2504.00180) |

**Contradiction Types Simulated:**
- Temporal contradictions (dates)
- Numerical contradictions (numbers)
- Entity contradictions (objects)
- Negation contradictions
- Semantic contradictions

**Finding:** Chain-of-Thought improves some models but **hurts** others

---

### 1.6 CARE-RAG (July 2025)
**Conflict-Aware and Reliable Evidence for RAG**

| Field | Value |
|-------|-------|
| ArXiv | [2507.01281](https://arxiv.org/abs/2507.01281) |

**Handles 2 conflict types:**
1. **Inter-context conflict**: Between retrieved documents
2. **Parametric conflict**: Between context and LLM internal knowledge

**Approach:** Synthesize all evidence based on conflict identification before generation

---

### 1.7 CARE: Conflict-Aware Soft Prompting (Aug 2025)
**Conflict-Aware Soft Prompting for Retrieval-Augmented Generation**

| Field | Value |
|-------|-------|
| ArXiv | [2508.15253](https://arxiv.org/abs/2508.15253) |

**Method:** Selectively incorporate external context only when LLM lacks sufficient knowledge

**Results:** +5.01% with Mistral, +6.13% with LLaMA over standard RAG

---

## Section 2: NotebookLM & RAG Architecture

### 2.1 NotebookLM (April 2025)
**An LLM with RAG for Active Learning and Collaborative Tutoring**

| Field | Value |
|-------|-------|
| ArXiv | [2504.09720](https://arxiv.org/abs/2504.09720) |

**Architecture:**
- Backbone: **Gemini 1.5 Pro**
- Capacity: 50 sources/notebook, 200,000 words/source
- **Citation mechanism**: Explicit passage-citation for audit

**Performance:**
- Lung cancer staging: 86% correct TNM staging, 95% citation accuracy
- Pancreatic cancer: 70% staging accuracy, 92% retrieval accuracy

**Limitations:**
- Can shift cited opinions into factual declarations
- "Attribution drift" - unsupported contextual characterizations

---

## Section 3: Atomic Fact Decomposition

### 3.1 DnDScore (Dec 2024)
**Decontextualization and Decomposition for Factuality Verification**

| Field | Value |
|-------|-------|
| ArXiv | [2412.13175](https://arxiv.org/abs/2412.13175) |

**Pipeline:**
```
Text → Decompose into atomic subclaims → Decontextualize → Verify against source
```

---

### 3.2 AFEV (June 2025)
**Fact in Fragments: Deconstructing Complex Claims via LLM-based Atomic Fact Extraction**

| Field | Value |
|-------|-------|
| ArXiv | [2506.07446](https://arxiv.org/abs/2506.07446) |

**Method:** Iteratively decompose complex claims → Fine-grained retrieval → Adaptive reasoning

---

### 3.3 JEDI (Sept 2025)
**Extractive Fact Decomposition for Interpretable NLI in one Forward Pass**

| Field | Value |
|-------|-------|
| ArXiv | [2509.18901](https://arxiv.org/abs/2509.18901) |

**Advantage:** Encoder-only architecture (no generative LLM needed)
- Joint decomposition + inference in single forward pass

---

### 3.4 NLI under the Microscope (Feb 2025)
**What Atomic Hypothesis Decomposition Reveals**

| Field | Value |
|-------|-------|
| ArXiv | [2502.08080](https://arxiv.org/abs/2502.08080) |

**Applications of atomic decomposition:**
- Factual precision assessment
- Claim verification
- Multihop QA

---

### 3.5 Decomposition Dilemmas (Nov 2024)
**Does Claim Decomposition Boost or Burden Fact-Checking Performance?**

| Field | Value |
|-------|-------|
| ArXiv | [2411.02400](https://arxiv.org/abs/2411.02400) |

**Key Finding:**
- Decomposition **helps weak verifiers**
- Decomposition **hurts strong verifiers**
- **Conflicting claims** benefit most from decomposition (+20%)

---

### 3.6 Atomic Fact Decomposition for QA (Oct 2024)
**Atomic Fact Decomposition Helps Attributed Question Answering**

| Field | Value |
|-------|-------|
| ArXiv | [2410.16708](https://arxiv.org/abs/2410.16708) |

---

### 3.7 DecMetrics (Sept 2025)
**Structured Claim Decomposition Scoring for Factually Consistent LLM Outputs**

| Field | Value |
|-------|-------|
| ArXiv | [2509.04483](https://arxiv.org/abs/2509.04483) |

---

## Section 4: Knowledge Graph for Conflict Resolution

### 4.1 Graphusion (Oct 2024)
**A RAG Framework for KG Construction with Global Perspective**

| Field | Value |
|-------|-------|
| ArXiv | [2410.17600](https://arxiv.org/abs/2410.17600) |

**3-Step Framework:**
```
Step 1: Extract seed entities (topic modeling)
Step 2: LLM candidate triplet extraction
Step 3: Fusion module:
        ├── Entity Merging (same entity, different names)
        ├── Conflict Resolution (contradicting triplets)
        └── Novel Triplet Discovery
```

**Results:** +9.2% accuracy on subgraph completion

---

### 4.2 GraphCheck (Feb 2025)
**Knowledge Graph-Powered Fact-Checking**

| Field | Value |
|-------|-------|
| ArXiv | [2502.16514](https://arxiv.org/abs/2502.16514) |

**Pipeline:**
```
Source Document → KG Extraction → GNN Processing → Soft Prompts → LLM Fact-Check
```

**Advantage:** Single-inference call (not pairwise comparison)
**Results:** +7.1% improvement over baselines

---

### 4.3 KG-RAG4SM (Jan 2025)
**Knowledge Graph-based RAG for Schema Matching**

| Field | Value |
|-------|-------|
| ArXiv | [2501.08686](https://arxiv.org/abs/2501.08686) |

**Solves:** Semantic ambiguities and conflicts in domain-specific mapping

**Retrieval Methods:**
- Vector-based retrieval
- Graph traversal-based retrieval
- Query-based retrieval
- Hybrid approach with ranking

---

### 4.4 RAKG (April 2025)
**Document-level Retrieval Augmented Knowledge Graph Construction**

| Field | Value |
|-------|-------|
| ArXiv | [2504.09823](https://arxiv.org/abs/2504.09823) |

**Innovation:** RAG evaluation metrics for KGC task

---

### 4.5 Efficient KG for Large-Scale RAG (July 2025)

| Field | Value |
|-------|-------|
| ArXiv | [2507.03226](https://arxiv.org/abs/2507.03226) |

**Covers:** LightRAG, FastGraphRAG, MiniRAG - lightweight graph representations

---

### 4.6 LLM-empowered KG Construction Survey (Oct 2025)

| Field | Value |
|-------|-------|
| ArXiv | [2510.20345](https://arxiv.org/abs/2510.20345) |

**KARMA Framework:** Multi-agent design with specialized agents for:
- Schema alignment
- Conflict resolution
- Quality evaluation

---

### 4.7 LLMs Meet Knowledge Graphs for QA (May 2025)

| Field | Value |
|-------|-------|
| ArXiv | [2505.20099](https://arxiv.org/abs/2505.20099) |

**Key insight:** KG can reconcile knowledge conflicts from multiple documents

---

### 4.8 Ontology Learning and KG for RAG (Nov 2025)

| Field | Value |
|-------|-------|
| ArXiv | [2511.05991](https://arxiv.org/abs/2511.05991) |

**Problem solved:** Eliminates redundant/conflicting entities in text-based ontology learning

---

## Section 5: NLI-based Contradiction Detection

### 5.1 Straightforward Pipeline for Entailment/Contradiction (Aug 2025)

| Field | Value |
|-------|-------|
| ArXiv | [2508.17127](https://arxiv.org/abs/2508.17127) |

**Pipeline:**
```python
1. Attention aggregation → Find candidate sentences
2. Pretrained NLI model → Classify [Entailment | Contradiction]
```

---

### 5.2 Factually Consistent Summarization via RL (June 2023)

| Field | Value |
|-------|-------|
| ArXiv | [2306.00186](https://arxiv.org/abs/2306.00186) |

**Method:** RL with reference-free textual entailment rewards

---

### 5.3 AMREx (Nov 2024)
**AMR for Explainable Fact Verification**

| Field | Value |
|-------|-------|
| ArXiv | [2411.01343](https://arxiv.org/abs/2411.01343) |

**Labels:**
- `Supports` → Entailment
- `Refutes` → Contradiction
- `NEI` → Neutral
- `ConflictingEvidence` → Both supporting AND refuting evidence

---

### 5.4 FactCG (Jan 2025)
**Enhancing Fact Checkers with Graph-Based Multi-Hop Data**

| Field | Value |
|-------|-------|
| ArXiv | [2501.17144](https://arxiv.org/abs/2501.17144) |

**Problem:** Conventional NLI datasets not suited for document-level reasoning

---

### 5.5 Measuring Summarization Factuality in RAG (Aug 2024)

| Field | Value |
|-------|-------|
| ArXiv | [2408.15171](https://arxiv.org/abs/2408.15171) |

**Finding:** Pre-trained entailment models simpler and more effective than fine-tuning LLM

---

## Section 6: Document-level Claim Extraction & Fact-Checking

### 6.1 Document-level Claim Extraction (ACL 2024)
**Document-level Claim Extraction and Decontextualization for Fact-Checking**

| Field | Value |
|-------|-------|
| ArXiv | [2406.03239](https://arxiv.org/abs/2406.03239) |

**2-Stage Process:**
```
Step 1: Extractive Summarization → Identify check-worthy sentences
Step 2: Decontextualization → Rewrite for standalone understanding
```

---

### 6.2 Face the Facts! (Dec 2024)
**Evaluating RAG-based Pipelines for Professional Fact-Checking**

| Field | Value |
|-------|-------|
| ArXiv | [2412.15189](https://arxiv.org/abs/2412.15189) |

**Finding:** LLM-based retrievers outperform but struggle with heterogeneous knowledge bases

---

### 6.3 Claim Extraction for Fact-Checking (Feb 2025)
**Data, Models, and Automated Metrics**

| Field | Value |
|-------|-------|
| ArXiv | [2502.04955](https://arxiv.org/abs/2502.04955) |

**Method:** NLI models sentence-by-sentence scanning

---

### 6.4 VERITAS-NLI (Oct 2024)
**Validation Through Automated Scraping and NLI**

| Field | Value |
|-------|-------|
| ArXiv | [2410.09455](https://arxiv.org/abs/2410.09455) |

**Combines:** Web scraping + State-of-the-art NLI models

---

### 6.5 Evidence-backed Fact Checking with RAG (Aug 2024)

| Field | Value |
|-------|-------|
| ArXiv | [2408.12060](https://arxiv.org/abs/2408.12060) |

**Pipeline:**
```
Claim → RAG retrieve top-3 docs → Extract evidence → ICL → Verify
```

---

### 6.6 Numerical Fact-Checking Benchmark (Oct 2025)

| Field | Value |
|-------|-------|
| ArXiv | [2510.22055](https://arxiv.org/abs/2510.22055) |

**Finding:** Decomposition excels at **conflicting claims** (+20% relative gain)

---

## Section 7: Multi-Document Summarization & Conflict

### 7.1 MetaSumPerceiver (July 2024)
**Multimodal Multi-Document Evidence Summarization for Fact-Checking**

| Field | Value |
|-------|-------|
| ArXiv | [2407.13089](https://arxiv.org/abs/2407.13089) |

**Label Mapping:**
```
Supported → Entailment
NEI → Neutral
Refuted → Contradiction
```

---

### 7.2 Multilingual Summarization with Factual Consistency (Dec 2022)

| Field | Value |
|-------|-------|
| ArXiv | [2212.10622](https://arxiv.org/abs/2212.10622) |

**Method:** Textual Entailment models for factual consistency

---

## Section 8: RAG Surveys & Benchmarks

### 8.1 RAG Evaluation Survey (April 2025)
**Comprehensive Survey in Era of LLMs**

| Field | Value |
|-------|-------|
| ArXiv | [2504.14891](https://arxiv.org/abs/2504.14891) |

---

### 8.2 Systematic Review of RAG Systems (July 2025)
**Progress, Gaps, and Future Directions**

| Field | Value |
|-------|-------|
| ArXiv | [2507.18910](https://arxiv.org/abs/2507.18910) |

**Note:** 1,200+ RAG papers on arXiv in 2024 alone

---

### 8.3 RAG and Beyond (Sept 2024)
**How to Make LLMs use External Data More Wisely**

| Field | Value |
|-------|-------|
| ArXiv | [2409.14924](https://arxiv.org/abs/2409.14924) |

---

## NLP Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENT CONFLICT PIPELINE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PREPROCESSING                                                │
│     ├── Text Normalization                                       │
│     ├── Sentence Segmentation (SpaCy)                           │
│     └── Entity Extraction (NER)                                  │
│                                                                  │
│  2. ATOMIC DECOMPOSITION                                         │
│     ├── Complex Claim → Atomic Facts (DnDScore, AFEV, JEDI)     │
│     ├── Decontextualization                                      │
│     └── Coreference Resolution                                   │
│                                                                  │
│  3. KNOWLEDGE GRAPH CONSTRUCTION                                 │
│     ├── Entity Linking (Graphusion)                              │
│     ├── Relation Extraction                                      │
│     └── Conflict Resolution (entity merging, triplet conflicts) │
│                                                                  │
│  4. CONFLICT DETECTION                                           │
│     ├── NLI Model (entailment/contradiction)                    │
│     ├── Hidden State Probing (CLEAR)                            │
│     └── Multi-agent Debate (MADAM-RAG)                          │
│                                                                  │
│  5. RESOLUTION                                                   │
│     ├── Source Reliability Scoring                              │
│     ├── Temporal Recency Check                                  │
│     ├── Information Bottleneck (Swin-VIB)                       │
│     └── User Verification Request                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Techniques Summary

| Technique | Papers | Use Case |
|-----------|--------|----------|
| **Atomic Decomposition** | DnDScore, AFEV, JEDI | Break claims into verifiable units |
| **Hidden State Probing** | CLEAR | Detect conflict signals in LLM internals |
| **Multi-Agent Debate** | MADAM-RAG | Resolve conflicts through deliberation |
| **Knowledge Graph** | Graphusion, GraphCheck | Entity merging, triplet conflict resolution |
| **NLI Classification** | AMREx, FactCG | Entailment/Contradiction/ConflictingEvidence |
| **Information Bottleneck** | Swin-VIB | Filter noise, preserve relevant signal |
| **Decontextualization** | Doc-level Claim Extraction | Make claims standalone for verification |

---

## Quick Start

```bash
# Download all papers
python scripts/arxiv_downloader.py document-conflict/arxiv_links.txt 1

# Convert to text
python3 scripts/pdf_to_txt_converter.py --collection document-conflict
```

---

## Citation

If you use this collection, please cite the original papers accordingly.
