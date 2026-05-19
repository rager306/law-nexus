---
milestone: M025-50be7n
slice: S01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Local Semantic Scoring Iteration Contract

## Purpose

M025 turns the M024 safe-token scoring result into a controlled local semantic scoring improvement loop. The goal is not to validate retrieval quality in one step. The goal is to change exactly one representation layer per cycle, measure the delta against M024, and decide whether the change should be accepted, revised, rejected, or blocked.

## Source baseline

The immutable comparison floor for M025 is M024:

```text
prd/research/ontology_architecture_requirements/43-m024-final-verification-report.md
prd/research/ontology_architecture_requirements/semantic_observed_retrieval_scoring_proof.json
```

M024 scoring mode:

```text
local_user_bge_m3_safe_token_similarity_v1
```

M024 runtime boundary:

```text
model_id: deepvk/USER-bge-m3
runtime_status: confirmed_runtime
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
network_used: false
```

M024 baseline metrics:

```text
mrr: 0.875
recall_at_1: 0.75
recall_at_3: 1.0
positive_with_distractor_relevant_first: 0.0
runtime_boundary_confirmed: 1.0
```

M024 threshold failures:

```text
mrr
recall_at_1
positive_with_distractor_relevant_first
```

## Iteration hypothesis

M024 proved that local USER-bge-m3 can score safe token-bag strings, but safe token bags were too weak to rank the positive-with-distractor case correctly. M025 tests whether safe typed descriptors carry more semantic signal than ID-heavy token bags without persisting raw legal text, raw query text, raw vectors, or expected answers.

Initial representation change for the first M025 cycle:

```text
safe_token_bag_v1 -> safe_semantic_descriptor_v1
```

The descriptor layer may use only bounded, typed fields such as:

```text
topic_class
obligation_type
actor_role
document_scope
temporal_status
citation_granularity
procurement_phase
query_intent
candidate_role
```

The descriptor layer must not use free-text summaries, generated answer prose, raw source text, raw query text, expected relevance labels, expected ranks, or expected answer lists.

## One-change-per-cycle rule

Each M025 scoring cycle may change exactly one representation layer or scoring rule. The first cycle changes only the representation from safe token bags to safe typed descriptors.

A cycle must not simultaneously change:

- representation schema;
- model/runtime;
- fixture cases;
- metric definitions;
- expected answer labels;
- ranking tie-break rules;
- graph filters;
- threshold policy.

If more than one change is needed, the milestone must record the current cycle disposition first, then plan a follow-up cycle.

## Allowed scoring runtime

Allowed:

```text
deepvk/USER-bge-m3
local_files_only=true
observed_vector_dimension=1024
```

Forbidden:

```text
managed embedding APIs
GigaChat or GigaEmbeddings runtime
network model fetch during scoring
raw vector persistence
provider payload persistence
fallback to a different model without a new contract
```

## Forbidden scoring inputs and outputs

Scoring inputs must exclude:

- raw legal text;
- raw query text;
- source excerpts;
- raw vectors;
- provider or external payloads;
- generated legal-answer prose;
- generated query or Cypher text;
- secrets;
- absolute paths;
- `.gsd/exec` durable anchors;
- expected labels;
- expected ranks;
- expected candidate lists;
- expected rejected-candidate lists;
- expected diagnostic lists.

Scoring outputs may persist only:

- case ID;
- query ID;
- candidate ID;
- descriptor/scoring input ID;
- scoring mode;
- observed rank;
- rounded scalar similarity score;
- diagnostic codes;
- non-authoritative flags;
- aggregate metrics and deltas.

Raw vectors must remain process-local and ephemeral.

## Metrics and deltas

Every M025 scoring proof must report:

```text
mrr
recall_at_1
recall_at_3
positive_with_distractor_relevant_first
runtime_boundary_confirmed
```

Every M025 scoring proof must also report deltas against M024:

```text
delta_mrr = current_mrr - 0.875
delta_recall_at_1 = current_recall_at_1 - 0.75
delta_recall_at_3 = current_recall_at_3 - 1.0
delta_positive_with_distractor_relevant_first = current_positive_with_distractor_relevant_first - 0.0
```

Primary improvement target:

```text
positive_with_distractor_relevant_first > 0.0
```

Secondary improvement targets:

```text
mrr > 0.875
recall_at_1 > 0.75
```

Regression guard:

```text
recall_at_3 must not drop below 1.0 unless the cycle is classified revise, reject, or blocked.
```

## Cycle dispositions

### accept

Use only if:

- runtime boundary is confirmed;
- safety verifier passes;
- no leakage or injected acceptance path is found;
- primary target improves;
- no critical regression is introduced;
- independent review does not request changes.

Accepted scope remains bounded. `accept` does not validate R035.

### revise

Use if:

- some metric improves but the primary target does not;
- safety is intact;
- the representation appears promising but needs exactly one follow-up change.

The next-cycle recommendation must name one and only one proposed change.

### reject

Use if:

- metrics do not improve or regress;
- the descriptor representation is too weak;
- improvements are attributable to leakage or self-confirming design.

Rejected representations must not be promoted into future scoring defaults.

### blocked

Use if:

- safe scoring cannot be performed without raw text;
- local runtime is unavailable;
- verifier detects leakage;
- meaningful metric comparison cannot be computed;
- independent review finds unresolved High/Critical issues.

Blocked cycles must persist diagnostics rather than weakening the contract.

## Required proof artifacts for each cycle

A complete cycle must include:

1. representation contract or schema;
2. safe input manifest;
3. verifier with fail-closed tests;
4. scorer proof JSON;
5. metric delta proof note;
6. iteration decision record;
7. independent proof review;
8. final verification report.

## Test and review requirements

Tests must prove rejection of:

- unknown descriptor fields;
- free-text descriptor values;
- raw legal/query text fields;
- raw vector fields;
- provider/external payload fields;
- expected labels/ranks/answer lists;
- generated prose/query/Cypher fields;
- unsafe absolute paths;
- `.gsd/exec` anchors;
- injected runtime or score payloads as acceptance proof paths.

Independent review must check:

- test substance;
- mocks and injected paths;
- self-confirming fixture risks;
- descriptor leakage;
- metric delta honesty;
- overclaim boundaries;
- R035/R038 lifecycle wording.

## Requirement boundaries

### R035

R035 remains active and not validated during M025 unless a separate stronger validation milestone is explicitly planned and passes. M025 can advance R035 only as bounded local scoring evidence.

### R038

R038 is applied by requiring independent review before closeout. R038 remains active as a standing process requirement for future proof-heavy milestones.

## Non-claims

M025 does not claim:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- legal interpretation authority;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness;
- managed embedding API authorization.

## S02 handoff

S02 must create `safe_semantic_descriptor_v1` schema and manifest using bounded descriptors only. S02 must treat this contract as authoritative for safety and iteration boundaries. If descriptors require raw text or answer labels to be meaningful, S02 must emit blocked diagnostics or defer the design rather than weakening this contract.

## Verification block

S01 verification must confirm that this contract contains:

- M024 baseline metrics;
- one-change-per-cycle rule;
- accepted descriptor hypothesis;
- allowed local runtime boundary;
- forbidden scoring inputs and outputs;
- metrics and deltas;
- accept/revise/reject/blocked dispositions;
- R035/R038 boundaries;
- non-claims;
- S02 handoff.
