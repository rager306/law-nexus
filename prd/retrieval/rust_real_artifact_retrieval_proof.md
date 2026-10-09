---
title: "Rust Real-Artifact Retrieval Proof Contract"
status: "contract-draft"
non_authoritative: true
owner: "M216-8dps6e/S03"
contract_version: "real-artifact-retrieval/rust-v1"
requirement: "R034"
validator_contract: "prd/retrieval/rust_retrieval_output_validator_contract.md"
prior_art:
  - "prd/archive/retrieval-era/real_artifact_retrieval_proof.md"
  - "prd/archive/retrieval-era/real_artifact_evidence_mapping.md"
  - "prd/archive/retrieval-era/offline_citation_retrieval_contract.md"
  - "prd/archive/retrieval-era/retrieval_output_validator_contract.md"
  - "prd/retrieval/rust_offline_citation_retrieval_contract.md"
vocabulary_authority: "prd/temporal-legal-model.md#3"
created_at: "2026-10-09"
---

# Rust Real-Artifact Retrieval Proof Contract

This contract freezes the Rust-only real-artifact retrieval proof built on the
M213 cleaned projection. It reformulates the archived M013 Python-era
real-artifact proof in Rust, composes with the S01 output-ID validator
(`retrieval-output-validator/rust-v1`) and the S02 offline citation-safe
retrieval contract (`offline-citation-retrieval/rust-v1`), and binds the proof to
exactly one pinned real Consultant WordML document driven through the enabled
M213 cleaned-projection pipeline. It is `contract-draft`, `non-authoritative`,
and owned by `M216-8dps6e/S03`.

Contract version string: `real-artifact-retrieval/rust-v1`.

## Boundary

- The deliverable is a deterministic, fail-closed offline citation retrieval
  proof over ONE real slice document, run through the enabled pipeline and then
  the S02 offline retrieval surface plus the S01 validator handoff.
- It makes no network call, starts no service, loads no product API, calls no
  embedding model or LLM, and reads no FalkorDB runtime. There is no product
  surface and no runtime service.
- The proof is a consuming integration test (`crates/ln-query/tests/`), not a
  new vocabulary module. It adds no crate dependency and mints no production
  schema.
- The only source artifact is the single pinned real Consultant WordML document
  below; the resolution graph is derived from its cleaned projection, never from
  a local constant or a synthetic fixture.

## Pinned real slice document

Exactly ONE real Consultant WordML document is declared and pinned by content:

| Field | Value |
| --- | --- |
| Path | `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml` |
| sha256 | `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d` |
| Bytes | 193726 |
| Provenance | tracked `law-source/consultant/*.xml` fixture vault (real Consultant Plus export, not the full corpus) |

The proof reads the document with `std::fs::read` (never `include_str!`), builds
the path from `env!("CARGO_MANIFEST_DIR")` joined with
`../../law-source/consultant/<file>`, and after `capture` asserts both the byte
length and that `package.manifest().source.sha256` equals the pinned sha256. A
content drift panics with an explicit re-pin message; it is never re-pinned
silently and a new hash is never accepted.

### Document swap clause

A swap to another tracked `law-source/consultant/*.xml` document is allowed only
if a required case class (see "Required class coverage") cannot be derived from
the pinned document. A swap MUST still use exactly one document, MUST record the
new document's sha256 and byte length in the consuming test, and MUST record the
swap and its justification in this contract. No second document may be added to
the proof.

## Enabled pipeline

The pinned document is driven through the enabled M213 cleaned-projection
pipeline, unchanged:

```
capture -> gate_reader(SupportedWordml) -> build_projection
        -> export_cleaned_projection(Complete) -> read_cleaned_wire -> build_nav_index
```

The reader gate MUST classify the pinned document as `ReaderSourceClass::SupportedWordml`;
a different gate class is a failure, not a fallback. The projection is
`export_cleaned_projection(..., WireCompletion::Complete, ...)` and is read back
through `read_cleaned_wire`, so the proof consumes the same cleaned wire the
product pipeline produces. The graph resolver is
`ln_query::retrieval_offline::ProjectionGraphResolver::new` over that cleaned
projection.

## Case derivation rules

The case corpus is deterministic and derived from the projection (mirroring the
S02 `CorpusSpec` / `case` helpers in `crates/ln-query/tests/retrieval_offline.rs`).
No case carries raw decoded legal text:

| Derivation rule | Closed selector / payload | Required observed result |
| --- | --- | --- |
| Pick a marker with exactly one matching segment in the projection and issue an `exact_node_address` query for that segment address. | segment id | `selected` (`exact_node_address_match`) |
| Pick a closed `marker_kind` token with exactly one matching segment in the projection. | `view:<kind>` / `segment:<kind>` / `semantic:<value>` / `reference:<type>` | `selected` (`marker_kind_match`) |
| Pick a closed kind/value token absent from the projection. | closed token | `scoped_no_answer` (`scoped_no_candidate`) |
| Pick a closed `marker_kind` token with more than one matching segment in the projection. | closed token | `rejected` (`ambiguous_candidate_set`) |
| Build a candidate whose envelope carries a forbidden payload field class. | forbidden field name | `rejected` (`unsafe_payload_rejected`) |
| Build a candidate whose evidence span id is not resolvable by the projection graph. | unresolvable id token | `rejected` (`unresolved_candidate_evidence`) |

Selectors are closed tokens evaluated by the production walk; the corpus stays
data-only. No ranking score, embedding distance, LLM confidence, graph score, or
legal relevance score is allowed.

## Required class coverage

Every declared class MUST be covered by at least one authored case:

1. `exact_node_address` selected (one candidate),
2. `marker_kind` selected (one candidate),
3. `scoped_no_answer` (a closed kind/value absent from the projection),
4. `ambiguous_lookup` (>1 candidate),
5. `invalid_candidate` with a forbidden payload field,
6. unresolved evidence-span rejection.

## Fail-closed demo invariant

The demo invariant is absolute: **an unresolvable citation is always rejected,
and no accepted outcome is emitted without a resolvable citation.** The proof
asserts it directly. Selection, scope, edition validity, supersession, and
identifier resolution all fail closed: an unknown identifier resolves to
`None`/`Unresolved`, an out-of-window edition does not resolve, and no repair,
inference, best-effort match, downgrade, or arbitrary candidate choice is
authorized. The cleaned projection is borrowed and never mutated (no-repair
invariant).

## Proof assertions

`run_offline_citation_retrieval_cases` and `run_offline_citation_retrieval_proof`
are both exercised, and the proof asserts:

- the fail-closed demo invariant;
- `mismatch_count == 0`;
- every declared class covered;
- determinism: two runs produce identical outcomes;
- origin control: the resolver evidence-span id set equals the `NavIndex`
  segment addresses;
- redaction: no raw decoded document text appears in any outcome, diagnostic, or
  summary (asserted with sentinel fragments from the real document);
- the projection is not mutated.

## Bounded evidence schema

The proof prints a bounded summary (never raw document text) with exactly these
fields:

| Field | Meaning |
| --- | --- |
| `pinned_sha256` | the pinned document sha256 |
| `total` | number of cases run |
| `selected` | selected outcomes |
| `scoped_no_answer` | scoped no-answer outcomes |
| `rejected` | rejected outcomes |
| `validator_accepted` | validator-accepted citation-backed outcomes |
| `validator_rejected` | validator rejections |
| `mismatch_count` | observed-vs-expected disagreements (must be `0`) |
| `diagnostic_code_inventory` | sorted, de-duplicated, closed set of proof and validator diagnostic codes |

The bounded evidence is recorded in the tracked register
`prd/migration/rust-evidence/m216-retrieval-evid-register.json`. The register is
standalone and non-authoritative; it does not write, repair, or regenerate the
frozen architecture registry.

Run the proof:

```bash
cargo test -p ln-query --offline --test real_artifact_retrieval -- --nocapture
```

## D537 consistency

Decision D537 freezes `prd/architecture/architecture_items.jsonl` and
`prd/architecture/architecture_edges.jsonl`: they MUST NOT be written,
regenerated, or repaired by this work. The retrieval EVID retarget is therefore
recorded as a standalone tracked register
(`prd/migration/rust-evidence/m216-retrieval-evid-register.json`; decision D721,
precedent `prd/migration/rust-evidence/m209-s01-r035-gate-register.json`). The
frozen-registry retarget is deferred to the authorized RC28-F19 reconciliation;
this contract never mutates the frozen registry or clears the D7 missing-anchor
quarantine.

## Non-claims

This real-artifact proof is bounded evidence for R034 on ONE pinned document. It
does not prove or claim:

- corpus coverage: one real document is not the corpus
  (`consru_export/consru_export/exports/` is the full corpus);
- product retrieval quality, ranking, precision, recall, or reranking;
- legal-answer correctness, legal interpretation authority, or LLM authority;
- parser completeness;
- runtime / FalkorDB / vector / embedding / rerank readiness;
- citation-safe production retrieval readiness;
- production temporal graph completeness or a final production ID schema.

The archived M013/Python real-artifact work and its R034 Python validation remain
prior art, not authority. Proof-local identifiers carried by the validator
envelope are never production IDs.

## Vocabulary non-promotion

No `prd/temporal-legal-model.md` §3 row is created, amended, or promoted by this
contract (decision D714). In particular the §3 `SourceBlock` row stays
`deferred-undefined`: the `SourceBlockId` envelope token and the S03 resolver
mapping (D719) are proof-local and do not infer a future evidence-domain
`SourceBlock` entity. The envelope tokens do not promote the domain vocabulary
(D714/D719).

## Implementation handoff

- Tracked proof contract: `prd/retrieval/rust_real_artifact_retrieval_proof.md`.
- Consuming proof: `crates/ln-query/tests/real_artifact_retrieval.rs`.
- Retrieval EVID register: `prd/migration/rust-evidence/m216-retrieval-evid-register.json`.
- Verify: `cargo test -p ln-query --offline --test real_artifact_retrieval -- --nocapture`,
  plus `cargo fmt --all --check` and `cargo check --workspace --offline`.
