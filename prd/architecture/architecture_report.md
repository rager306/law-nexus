# Architecture Graph Report

This report is derived, non-authoritative, and generated from the S02 architecture JSONL registry.
These graph/report outputs do not validate product/runtime/legal claims; PRD, GSD, ADR, source, and runtime evidence remain the source of truth.
Current orphans, unresolved proof gates, contradictions, and risk rows are findings for S04 or later verifier work, not automatic S03 build failures.

## Summary

| Field | Value |
| --- | --- |
| Nodes | 23 |
| Edges | 17 |
| Non-authoritative | true |
| Missing layers | 3 |
| Unresolved proof gates | 4 |
| Orphan findings | 3 |
| Contradiction edges | 0 |
| High/critical-risk nodes | 15 |

## Layer Coverage

| Layer | Node Count |
| --- | ---: |
| api-product | 0 |
| architecture-governance | 7 |
| generated-cypher | 1 |
| graph-runtime | 2 |
| legal-evidence | 0 |
| observability-operability | 0 |
| parser-ingestion | 3 |
| retrieval-embedding | 3 |
| security-safety | 3 |
| temporal-model | 1 |
| workflow-governance | 3 |

### Missing Layers

- api-product
- legal-evidence
- observability-operability

## Findings for S04

### Unresolved Proof Gates

| ID | Layer | Owner | Risk | Verification |
| --- | --- | --- | --- | --- |
| GATE-G005 | temporal-model | future-temporal-proof | high | A future proof slice defines and verifies same-date/multi-edition conflict policy. |
| GATE-G008 | parser-ingestion | future-parser-retrieval-proof | high | Golden tests pass on real legal source fixtures and retrieval expectations. |
| GATE-G011 | retrieval-embedding | future-retrieval-quality-proof | high | Retrieval quality benchmark passes under local/open-weight embedding constraints. |
| GATE-G015 | graph-runtime | future-runtime-migration-proof | medium | Migration runbook is executed against bounded fixtures and runtime diagnostics. |

### Orphan Findings

| ID | Rule |
| --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | isolated-node |
| S05-OLD-PROJECT-PRIOR-ART | isolated-node |
| S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED | isolated-node |

### Contradictions

| Edge ID | From | To | Status | Rationale |
| --- | --- | --- | --- | --- |
| _None_ |  |  |  |  |

### High and Critical Risk Nodes

| ID | Risk | Type | Layer | Status | Proof Level |
| --- | --- | --- | --- | --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | high | assumption | architecture-governance | active | source-anchor |
| CHECK-ARCHITECTURE-EXTRACTOR | high | workflow_check | workflow-governance | active | static-check |
| DEC-D031 | high | decision | architecture-governance | active | source-anchor |
| GATE-G005 | high | proof_gate | temporal-model | active | none |
| GATE-G008 | high | proof_gate | parser-ingestion | active | none |
| GATE-G011 | high | proof_gate | retrieval-embedding | active | none |
| M001-ARCHITECTURE-ONLY-GUARDRAIL | critical | workflow_check | architecture-governance | out-of-scope | source-anchor |
| REQ-R009 | high | requirement | workflow-governance | active | source-anchor |
| REQ-R017 | high | requirement | generated-cypher | active | source-anchor |
| REQ-R022 | critical | requirement | security-safety | active | source-anchor |
| REQ-R028 | critical | requirement | security-safety | out-of-scope | source-anchor |
| REQ-R029 | high | requirement | architecture-governance | active | source-anchor |
| RISK-OVERCLAIM-RUNTIME | critical | risk | security-safety | active | source-anchor |
| S05-OLD-PROJECT-PRIOR-ART | high | evidence | parser-ingestion | bounded-evidence | source-anchor |
| S05-PARSER-ODT-BOUNDARY | high | evidence | parser-ingestion | bounded-evidence | real-document-proof |

## Invalid Records

| ID | Rule | Value |
| --- | --- | --- |
| _None_ |  |  |

## Non-Claims Boundary

| Field | Value |
| --- | ---: |
| Nodes with non-claims | 23 |
| Total non-claims | 64 |

### Nodes with Non-Claims

| ID | Count |
| --- | ---: |
| ASSUMP-PRD-SOURCE-TRUTH | 1 |
| CHECK-ARCHITECTURE-EXTRACTOR | 1 |
| DEC-D031 | 1 |
| DEC-D032 | 1 |
| GATE-G005 | 1 |
| GATE-G008 | 2 |
| GATE-G011 | 2 |
| GATE-G015 | 1 |
| M001-ARCHITECTURE-ONLY-GUARDRAIL | 6 |
| REQ-R001 | 7 |
| REQ-R009 | 7 |
| REQ-R010 | 7 |
| REQ-R017 | 4 |
| REQ-R022 | 3 |
| REQ-R028 | 3 |
| REQ-R029 | 1 |
| RISK-OVERCLAIM-RUNTIME | 1 |
| S04-FALKORDB-RUNTIME-BOUNDED | 3 |
| S05-OLD-PROJECT-PRIOR-ART | 2 |
| S05-PARSER-ODT-BOUNDARY | 3 |
| S07-FIXED-PRD-CONSISTENCY | 1 |
| S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED | 3 |
| S10-USER-BGE-M3-BASELINE | 3 |
