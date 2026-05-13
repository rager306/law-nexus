---
source: "Assessment of imported Habr article"
source_document: "prd/research/habr_legal_rag_17_iterations_scaling_wall.md"
source_url: "https://habr.com/ru/articles/1014758/"
status: "research-assessment"
non_authoritative: true
created_at: "2026-05-13T06:03:00+00:00"
notes: "This assessment classifies transferable ideas for LegalGraph Nexus architecture. It does not validate product retrieval quality, legal-answer correctness, FalkorDB runtime behavior, parser completeness, or generated-Cypher safety."
---

# Assessment: Legal RAG Iteration Experience and Applicability to LegalGraph Nexus

## Executive Summary

The Habr article is a useful engineering case study for Legal RAG evaluation discipline, citation/grounding strategy, and scaling failure analysis. Its strongest transferable lesson for LegalGraph Nexus is not a specific model, prompt, or framework, but a proof pattern: validate output format and citation units first, measure grounding separately from answer correctness, change one variable per iteration, and test retrieval degradation at production-like corpus scale.

The article should remain bounded, non-authoritative research input. It does not prove any LegalGraph Nexus product behavior and must not close proof gates for parser completeness, FalkorDB production runtime, embedding quality, Legal KnowQL/generated Cypher safety, or legal-answer correctness.

## Most Relevant Observations from the Article

1. **Grounding dominates answer quality when it is a multiplier.** In the reported competition, good answer extraction still produced a near-zero total score when page-level grounding was wrong.
2. **Output-format validation was the largest early win.** Removing `.pdf` from `doc_id` increased grounding and total score dramatically. This is directly analogous to validating LegalGraph citation IDs, SourceBlock IDs, EvidenceSpan offsets, and temporal edition identifiers before retrieval optimization.
3. **Citation unit must match evaluation/consumer expectations.** The article used page-level retrieval because the scorer evaluated `(doc_id, page_number)`. LegalGraph should similarly align retrieval units with legal citation and provenance units, not arbitrary chunks.
4. **Hybrid retrieval is useful but insufficient alone.** BM25 + embeddings + RRF improved retrieval, but failed under scale because flat page-level search diluted precision across 300 documents.
5. **Document-level routing becomes mandatory at scale.** The final-stage failure shows that page-level search over the full corpus is fragile. LegalGraph should route by document, act type, edition, temporal validity, article/part/clause, jurisdiction/source, and then retrieve within the narrowed scope.
6. **Precision matters even under recall-heavy metrics.** Extra citation pages caused measurable grounding loss. For LegalGraph, citation-safe answers should prefer minimal sufficient evidence over broad context dumping.
7. **Deterministic fast paths beat LLM extraction for typed facts.** Regex/rule-based extraction for numbers, dates, booleans, and structured comparisons improved speed and reliability. This matches LegalGraph's deterministic-first principle.
8. **Post-LLM verification is essential.** Checking whether an answer appears in cited evidence caught hallucinated numbers/names. LegalGraph should require answer-to-evidence verification before any legal answer is presented.
9. **Domain guardrails are learned from evaluation data.** The article's adversarial/null handling and domain overrides were impactful but brittle. LegalGraph should encode such rules only from verified Russian legal fixtures, not from general intuition.
10. **Scale tests must be synthetic before product claims.** The warmup pipeline lost 42% when moving from 30 to 300 documents. LegalGraph needs noise-injection and corpus-scaling tests before claiming retrieval quality.

## Applicability to LegalGraph Nexus

### Applicable Now as Architecture Principles

| Idea | LegalGraph Application | Why Safe Now |
| --- | --- | --- |
| Format-first validation | Add validators for source IDs, citation IDs, EvidenceSpan offsets, legal unit identifiers, temporal edition identifiers, and answer schemas. | This is deterministic validation, not a runtime quality claim. |
| Citation-unit alignment | Define retrieval/evidence units around `SourceBlock` / `EvidenceSpan` / legal hierarchy units instead of arbitrary chunks. | Matches existing citation-safe retrieval direction. |
| Deterministic-first typed answers | Dates, numbers, references, article numbers, act metadata, validity intervals, and amendment relationships should be extracted/verified algorithmically before LLM use. | Consistent with project guardrail that LLM output is non-authoritative. |
| Minimal sufficient evidence | Rank evidence to minimize irrelevant spans; avoid over-citing just because recall seems desirable. | Reduces legal hallucination and citation noise. |
| Post-generation verification | Require answer claims to be traceable to cited evidence spans before display/export. | Reinforces non-authoritative LLM boundary. |
| One-change-per-iteration eval logging | Treat retrieval experiments as auditable runs with inputs, configs, metrics, and regressions. | Planning/process improvement, no product overclaim. |
| Synthetic scaling tests | Duplicate/noise legal fixtures to test retrieval dilution before product corpus claims. | Safe proof design for future gates. |

### Proof-Gated Candidates

| Candidate | Required LegalGraph Proof Before Adoption |
| --- | --- |
| BM25 + local embeddings + RRF hybrid retrieval | Benchmark on Russian legal fixtures with local/open-weight embeddings only; record model revision/checksum, dimensions, no managed API fallback, retrieval quality metrics, and failure cases. |
| Cross-encoder reranking | Local runtime feasibility proof, latency envelope, model provenance, and evidence that reranking improves citation precision without dropping required recall. |
| Article/section index-first retrieval | Parser proof that article/part/clause boundaries are extracted reliably from Consultant/Garant source formats and mapped to stable SourceBlocks/EvidenceSpans. |
| Smart continuation across pages/blocks | Verification that continuation logic respects Russian legal structure and does not merge neighboring articles, amendments, notes, or unrelated editions. |
| Adversarial/no-answer detection | Fixture-based proof for legal questions where the source corpus genuinely lacks the answer; must define how empty evidence is represented. |
| Answer-type-specific page/span caps | Retrieval-quality benchmark proving cap choices improve evidence precision without hiding necessary legal context. |
| LLM citation parsing | Safety proof that model-produced citations are only suggestions and are validated against deterministic evidence IDs before use. |

### Not Adopted Directly

| Article Idea | Reason Not Directly Adopted |
| --- | --- |
| Page-level retrieval as the core unit | Russian legal sources and LegalGraph architecture need legal-structure-aware evidence units; pages may be unavailable, unstable, or less meaningful than article/clause/source spans. |
| Competition-specific `doc_id` / `page_number` assumptions | LegalGraph needs its own canonical IDs and provenance schema. |
| Claude/Sonnet/Haiku routing | Provider/model choices are not architecture evidence and may conflict with local/offline constraints. |
| Generic adversarial fallback text | Russian legal answering needs policy-specific no-answer behavior grounded in source coverage and legal safety. |
| Specific DIFC regexes and domain rules | They are jurisdiction-specific and must not be copied into Russian legal parsing. |
| Treating leaderboard scores as product metrics | Competition metrics are useful inspiration but not sufficient for LegalGraph product readiness. |

## Experience Evaluation

The article demonstrates strong practical iteration discipline under constraints, especially after the early output-format mistake. The author's most valuable experience is not the final score but the debugging sequence: identify the score component that dominates, inspect exact output artifacts, make targeted fixes, track regressions, and analyze scale failure after the fact.

The weakest part of the experience is also instructive: too much was learned through submission feedback rather than a local eval set. For LegalGraph, this argues for building local golden fixtures before optimizing retrieval or prompts. Another important lesson is that several “reasonable” fixes regressed the score because the evaluation protocol was misunderstood. In LegalGraph terms: we must define our own evaluation protocol before optimizing against it.

## Recommended Architectural Influence

### 1. Add a Retrieval Quality Proof Harness

A future retrieval proof should evaluate at least:

- source/document routing accuracy;
- legal unit routing accuracy: act → edition → article/part/clause/source span;
- evidence precision/recall/F-beta over SourceBlock/EvidenceSpan identifiers;
- no-answer behavior;
- scale degradation under noisy/duplicated corpus growth;
- latency envelope for deterministic retrieval, embedding retrieval, reranking, and answer synthesis;
- regression history per change.

This maps primarily to `GATE-G011` and partially to `GATE-G008`.

### 2. Use Hierarchical Retrieval, Not Flat Search

Recommended retrieval order for LegalGraph:

1. **Source and corpus filter:** Consultant/Garant, document type, authority, date/version, active/archived status.
2. **Temporal/legal routing:** validity interval, amendment chain, edition, supersession/conflict policy.
3. **Structure routing:** act → chapter/section → article → part/clause → SourceBlock/EvidenceSpan.
4. **Lexical/semantic retrieval inside narrowed scope:** BM25/keyword plus local embedding candidate generation.
5. **Rerank or deterministic evidence scorer:** prefer evidence containing both the answer and the legal unit reference.
6. **Answer verification:** any LLM output must be checked against cited evidence.

This directly addresses the article's final scaling failure.

### 3. Make Evidence Precision a Product Safety Requirement

LegalGraph should avoid a “cite many spans just in case” behavior. A citation-safe answer should expose minimal sufficient evidence plus diagnostics for omitted candidates. This is especially important in law, where extra irrelevant citations can mislead users even if the answer text is correct.

### 4. Keep LLMs Behind Deterministic Verification

LLMs can compose readable answers, but they should not choose final authority. For typed facts, temporal status, article references, and amendment relationships, deterministic extraction and graph traversal should be primary. LLM-generated citations should be treated as hints, then validated or discarded.

### 5. Treat Scale as a First-Class Architecture Risk

A proof that works on a small handpicked corpus should not be accepted as product retrieval quality. Add synthetic scale/noise fixtures early: duplicated similar acts, multiple editions, same article numbers across different laws, near-duplicate amendments, and ambiguous references.

## Impact on Current Gates

| Gate / Area | Impact |
| --- | --- |
| `GATE-G008` Product parser and retrieval readiness | Article suggests proof design, but does not validate parser/retrieval readiness. |
| `GATE-G011` Local embedding quality proof | Article supports testing hybrid local retrieval, but no model or quality claim transfers. |
| `GATE-G015` FalkorDBLite to Docker migration | No direct runtime migration evidence. |
| `GATE-G005` Temporal conflict policy | Article reinforces need for temporal/document routing, but does not solve Russian same-date multi-edition conflicts. |
| `GATE-GENERATED-CYPHER-SAFETY` | No direct generated-Cypher safety evidence. |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | Reinforces local model discipline, but does not validate any embedding model. |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | No direct access-control evidence. |

## Proposed Next Slice if We Apply This Research

If this research is turned into implementation planning, the safest next slice is:

**Offline Citation Retrieval Evaluation Harness**

Goal: build a deterministic, local benchmark over a small set of verified Russian legal fixtures that scores retrieval over stable evidence IDs before any LLM answer generation.

Expected proof:

- fixture set with known source/evidence IDs;
- schema validator for retrieval outputs;
- baseline lexical retrieval;
- optional local embedding candidate generation behind a supply-chain record;
- metrics for precision, recall, F-beta, no-answer handling, and scale/noise degradation;
- failure report with examples, not just aggregate scores.

This should precede product GraphRAG, FalkorDB runtime algorithm adoption, GraphRAG-SDK adoption, UDF/FLEX usage, or answer-generation claims.

## Bottom Line

Use the article as a strong warning and proof-design guide: Legal RAG fails first at grounding, citation format, and scale. For LegalGraph Nexus, the transferable architecture is deterministic, hierarchical, citation-unit-aware retrieval with measured evidence precision and post-LLM verification. Do not import the article's provider choices, competition-specific scoring assumptions, or jurisdiction-specific rules as product architecture.
