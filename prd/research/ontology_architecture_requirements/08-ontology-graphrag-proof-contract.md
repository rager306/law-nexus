---
requirement: R035
gate: GATE-ONTOLOGY-GRAPHRAG-INTEGRATION
status: proof-contract-draft
owner: M020-ujbffl/S01
non_authoritative: true
created_at: 2026-05-17
---

# Ontology GraphRAG Proof Contract

## Purpose

This contract defines the bounded M020 proof spine for the `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` subset of R035. It exists to guide implementation work; it is not proof that the gate is satisfied.

The narrow proof target is: retrieval or query behavior can apply ontology-aware and temporal filters over source-backed records while preserving citation or evidence identifiers and non-authoritative answer boundaries.

This contract keeps the proof ceiling explicit. M020 may advance R035 with bounded evidence, but it must not imply full R035 validation, product retrieval quality, legal-answer correctness, parser completeness, FalkorDB production behavior, graph-vector or HNSW behavior, or pilot-scale readiness.

## Source-of-truth anchors

| Anchor | Role | Boundary |
| --- | --- | --- |
| `.gsd/REQUIREMENTS.md` R035 | Active requirement contract | R035 remains active until proof owners produce runtime, benchmark, real-document, legal-answer, parser-completeness, ontology-quality, graph-vector, or pilot-scale evidence as applicable. |
| `prd/research/ontology_architecture_requirements/05-ontology-proof-gates.md` | Gate contract | `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` requires integration proof, retrieval benchmark, generated-query safety checks, runtime smoke, citation validation, negative tests, query logs, filter traces, benchmark metrics, and failed-query diagnostics. |
| `prd/research/ontology_architecture_requirements/06-r035-evidence-audit.md` | Current R035 audit | M019 synchronized registry/view coverage only; no ontology runtime behavior or benchmark success was validated. |
| `prd/architecture/README.md` | Architecture verifier and promotion policy | Ontology GraphRAG claims require `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` and minimum `integration-test` proof; graph-vector/HNSW/hybrid retrieval claims require `runtime-smoke`. |
| `prd/architecture/claims_ledger.md` | Derived guardrail view | The R035 gate status table is non-authoritative and currently marks `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` as proposed with proof level below integration-test. |
| `prd/research/ontology_architecture_requirements/05-05-ontology-driven-graphrag-storage.md` | Research requirement input | Requires ontology and temporal graph filters plus citation-bound, non-authoritative answers, but leaves FalkorDB vector/HNSW and generated-Cypher proof needs open. |

## Existing surface inventory

| Surface | Candidate use in M020 | Classification | Verification command or evidence | Notes and limits |
| --- | --- | --- | --- | --- |
| `scripts/retrieval_output_validator.py` | Validate citation/evidence envelopes and fail closed on unresolved, wrong-edition, superseded, or unsafe outputs. | Usable now | `uv run python scripts/verify-retrieval-output-validator.py` and focused retrieval validator tests | Proves ID resolution behavior only; does not rank, retrieve, or validate legal answers. |
| `prd/retrieval/fixtures/real_artifact_retrieval_cases.json` with `scripts/verify-real-artifact-retrieval-proof.py` | Source-backed real-artifact-derived cases for citation and edition path validation. | Usable now | `uv run python scripts/verify-real-artifact-retrieval-proof.py` | Good S02 fixture base for evidence identity. Does not prove product retrieval quality or GATE-G008/GATE-G011 closure. |
| `prd/retrieval/fixtures/offline_citation_retrieval_cases.json` with `scripts/verify-offline-citation-retrieval-proof.py` | Deterministic offline candidate and scoped no-answer cases over tracked parser artifacts. | Usable now | `uv run python scripts/verify-offline-citation-retrieval-proof.py` | Useful for fail-closed retrieval selection patterns. Proof-local IDs are not production IDs. |
| `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json` and M016 benchmark proof | Representative local retrieval benchmark corpus and metric proof. | Usable with caution | `uv run python scripts/verify-representative-retrieval-runtime-benchmark.py --allow-runtime-blocker` | Existing proof reports `confirmed_runtime` and metrics, but keeps `GATE-G011` open. M020 may consume it as bounded input, not as product quality proof. |
| `prd/retrieval/local_retrieval_runtime_boundary_contract.md` and `scripts/check-local-retrieval-runtime.py` | Local open-weight runtime boundary for `deepvk/USER-bge-m3`. | Usable with caution | `uv run python scripts/check-local-retrieval-runtime.py` or existing M016 verifier command | Runtime proof must fail closed if environment changes. No managed API fallback, no raw vectors, no raw legal text. |
| `prd/parser/parser_staging_graph.json` and `prd/parser/parser_staging_graph.md` | Source document and source-block graph shape for deterministic graph/filter fixture construction. | Usable now | `uv run python scripts/build-parser-staging-graph.py --check` | NetworkX staging graph is non-authoritative and has expected unresolved Consultant references. It does not prove FalkorDB load or relation correctness. |
| `prd/parser/golden_cases.json` and parser golden proof artifacts | Bounded parser/retrieval cases for expected evidence, no-answer, and candidate-only relation handling. | Usable now | Parser golden evaluator/check commands from R032 evidence | Useful for negative cases and source-backed no-answer behavior. Does not prove parser completeness. |
| `prd/06_m002_cypher_safety_contract.md` and M002 tests | Generated-Cypher safety contract for read-only, evidence-returning, temporal-aware queries. | Usable as policy input | Focused generated-Cypher safety tests, if S03 touches query generation | M020 should avoid generated query execution unless it can validate the candidate. Generated Cypher remains non-authoritative. |
| `scripts/verify-architecture-graph.py`, `scripts/extract-prd-architecture-items.py`, `scripts/build-architecture-graph.py` | Static architecture currentness and overclaim checks. | Usable now | `uv run python scripts/verify-architecture-graph.py` | Passing verifier proves only static registry and claim-safety currentness. |
| `scripts/check-gsd-sync-drift.py` | R035/R036 lifecycle drift detection. | Usable now | `uv run python scripts/check-gsd-sync-drift.py --strict-exit-code` | Detects sync drift; does not validate runtime/product behavior. |
| FalkorDB graph-vector, HNSW, single-transaction graph plus vector behavior | Product-like graph-vector runtime proof. | Out of scope for S01 and blocked for M020 unless explicitly narrowed later | Requires separate capability/runtime evidence and likely `GATE-G015` or runtime-smoke proof | Do not claim this from fixture, NetworkX, or existing retrieval validator evidence. |
| BFO, GOST, OWL, Common Logic conformance | Formal ontology alignment proof. | Out of scope for M020 | Requires primary-standard review and formal subset proof | Not needed for the first ontology GraphRAG integration spine. |
| 1000-document pilot | Scale readiness proof. | Out of scope for M020 | Requires repeatable corpus manifest, run logs, anomaly triage, metrics, and quality sampling | Do not generalize M020 fixture or local proof into pilot readiness. |

## Accepted inputs

M020 proof commands may consume only repository-tracked, redacted, source-backed inputs unless a later slice records a narrower runtime exception:

- retrieval output validator fixtures and contracts under `prd/retrieval/`;
- real-artifact and offline citation retrieval case fixtures;
- parser staging graph and parser golden case artifacts;
- architecture verifier source anchors and derived views as diagnostics only;
- generated-Cypher safety contract and tests as policy inputs if query-like candidates are introduced;
- local retrieval runtime proof outputs only when the current command confirms safe local execution or returns a fail-closed blocker.

Accepted inputs must not include raw legal text, raw prompts, secrets, provider payloads, raw vectors, raw FalkorDB rows, untracked local corpora, or `.gsd/exec` paths as proof evidence.

## Expected outputs

A valid M020 proof output should be a compact tracked report or fixture result with:

- proof schema version and proof ID;
- repository-relative input fixture paths;
- accepted, rejected, scoped-no-answer, and mismatch counts;
- ontology filter and temporal filter status;
- citation or evidence validation status from the shared validator;
- stable diagnostic code inventory;
- redaction boundary statement;
- non-authoritative flag;
- gate disposition for `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` and R035.

Outputs must not include generated legal advice, free-form legal authority, raw source excerpts, raw queries, raw vectors, provider payloads, secrets, or absolute local paths.

## Proof ceiling

The intended M020 proof ceiling is `integration-test` for the bounded ontology filter plus temporal filter plus citation-preservation subset. If S02 or S03 uses fixtures only, the honest result is `fixture proof` or `unit-test` evidence that may advance planning but cannot satisfy the gate by itself. If local runtime is unavailable, a fail-closed blocker is a valid operational result, not a runtime proof.

M020 must not claim `runtime-smoke` for graph-vector, HNSW, hybrid retrieval, or FalkorDB production behavior unless a later slice runs and records a matching runtime command with safe diagnostics. M020 must not claim `production-observation` or pilot readiness.

## Candidate M020 proof subset

The safest first proof subset is fixture-first and integration-test oriented:

1. Build or reuse source-backed proof cases from real-artifact and offline citation retrieval fixtures.
2. Add an explicit ontology filter dimension that is bounded to known source-backed concepts, such as proof-local gate/category metadata, legal-evidence core class, or temporal status class.
3. Apply temporal filtering over edition/as-of metadata already represented in validator or retrieval cases.
4. Emit citation or evidence identifiers that pass the shared retrieval output validator.
5. Reject inactive, unsupported, ambiguous, missing-citation, unsafe-query, and forbidden-payload cases with stable diagnostics.
6. Record all outputs as non-authoritative proof artifacts with source IDs, counts, and diagnostic codes only.

If S02 or S03 can safely use the local `deepvk/USER-bge-m3` runtime proof, it may be an additional bounded input. It must not be required for the first fixture proof unless the command confirms `confirmed_runtime` in the current environment.

## Required negative cases

M020 must cover these failure classes before any lifecycle update:

| Negative case | Expected behavior |
| --- | --- |
| Inactive or wrong-edition evidence leaks into current-status retrieval | Reject or exclude with temporal diagnostic. |
| Output lacks required citation or evidence identifiers | Reject through retrieval output validator. |
| Ontology filter references unsupported gate or class | Reject or report unsupported ontology filter. |
| Generated query omits evidence path or temporal constraint | Reject before execution. |
| Candidate set is ambiguous | Reject without arbitrary tie-breaking. |
| Scoped no-answer contains hidden citations or global legal absence wording | Reject or accept only as scoped no-answer. |
| Raw legal text, prompts, provider payloads, raw vectors, raw FalkorDB rows, secrets, or legal advice appear in artifacts | Reject artifact as unsafe. |
| Proof report claims product retrieval quality, legal correctness, parser completeness, FalkorDB production behavior, graph-vector/HNSW behavior, pilot readiness, or LLM authority | Fail overclaim check. |

## Diagnostic requirements

Proof commands should emit compact JSON or Markdown summaries with only safe fields:

- schema version;
- proof ID;
- input fixture paths;
- total, accepted, rejected, and mismatch counts;
- ontology filter names or proof-local IDs;
- temporal filter status;
- citation/evidence validation status;
- diagnostic code inventory;
- non-authoritative flag;
- redaction booleans or explicit redaction statement;
- gate disposition saying `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` remains open unless the exact integration-test criteria are satisfied.

Diagnostics must not persist raw legal text, raw query text, prompts, provider payloads, raw vectors, raw FalkorDB rows, secrets, or generated legal advice.

## Verification commands

Baseline commands for M020 slices:

```bash
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python scripts/verify-real-artifact-retrieval-proof.py
uv run python scripts/verify-offline-citation-retrieval-proof.py
uv run python scripts/verify-retrieval-output-validator.py
```

Optional runtime or benchmark commands when the slice explicitly consumes M016 local retrieval evidence:

```bash
uv run python scripts/check-local-retrieval-runtime.py
uv run python scripts/verify-representative-retrieval-runtime-benchmark.py --allow-runtime-blocker
```

Generated-query safety checks must be added or reused if S03 introduces generated Cypher or query-like candidates.

## Lifecycle rule for R035

R035 must remain active unless S05 can point to tracked evidence showing the exact M020 subset met the required proof level. Even then, lifecycle text must be narrow, for example: bounded integration evidence for the ontology GraphRAG filter and citation-preservation subset. It must not say R035 is broadly validated unless all unrelated R035 gates also have accepted evidence.

## Non-claims

This contract does not validate R035.
This contract does not satisfy `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`.
This contract does not prove product retrieval quality.
This contract does not prove legal-answer correctness.
This contract does not prove parser completeness.
This contract does not prove FalkorDB production behavior.
This contract does not prove graph-vector or HNSW behavior.
This contract does not prove single-transaction graph plus vector semantics.
This contract does not prove generated-Cypher safety beyond existing M002 proof scope.
This contract does not prove BFO, GOST, OWL, Common Logic, LKIF, RusLegalCore, Akoma Ntoso, LegalDocML, or FRBR conformance.
This contract does not prove 1000-document or pilot-scale readiness.
This contract does not make LLM output legal authority.
