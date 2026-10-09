---
title: "Rust Offline Citation-Safe Retrieval Contract"
status: "contract-draft"
non_authoritative: true
owner: "M216-8dps6e/S02"
contract_version: "offline-citation-retrieval/rust-v1"
prior_art:
  - "prd/archive/retrieval-era/offline_citation_retrieval_contract.md"
  - "prd/archive/retrieval-era/real_artifact_evidence_mapping.md"
validator_contract: "prd/retrieval/rust_retrieval_output_validator_contract.md"
vocabulary_authority: "prd/temporal-legal-model.md#3"
requirement: "R034"
created_at: "2026-10-09"
---

# Rust Offline Citation-Safe Retrieval Contract

This contract freezes the Rust-only offline citation-safe retrieval proof built
on the M213 cleaned projection. It reformulates the archived M014 Python-era
offline retrieval contract in Rust and composes with the S01 output-ID validator
(`retrieval-output-validator/rust-v1`). It is `contract-draft`,
`non-authoritative`, and owned by `M216-8dps6e/S02`.

Contract version string: `offline-citation-retrieval/rust-v1`.

## Boundary

- The deliverable is deterministic, fail-closed offline citation retrieval over a
  cleaned projection plus the validator handoff. It selects candidate evidence
  nodes, builds validator-compatible output envelopes, and runs them through
  `ln_query::retrieval_output::validate_retrieval_output`.
- It makes no network call, starts no service, loads no product API, calls no
  embedding model or LLM, and reads no FalkorDB runtime. There is no product
  surface and no runtime service.
- The vocabulary lives in `crates/ln-query/src/retrieval_offline.rs`. The module
  is serde-free and adds no crate dependency; the `ln-query -> ln-decode` edge is
  already in the workspace allowlist.
- The only source is the M213 cleaned projection read back from a pinned reader
  fixture; the resolution graph is derived from that projection, never from a
  local constant.

## Declared fixture slice

The proof is bounded to the two sha256-pinned synthetic, non-legal reader
fixtures driven through the enabled pipeline
`capture -> gate_reader(SupportedWordml) -> build_projection ->
export_cleaned_projection(Complete) -> read_cleaned_wire -> build_nav_index`:

| Fixture | sha256 |
| --- | --- |
| `ln-decode/tests/fixtures/reader/mixed-wordml.xml` | `d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db` |
| `ln-decode/tests/fixtures/reader/diverse/navigation-demo.xml` | `b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0` |

The captured `manifest.source.sha256` is checked against the pin; a drift is a
failure, never a silent re-pin. This is bounded proof over self-authored
fixtures, not corpus coverage.

## Closed dictionaries

Query kind (`RetrievalQueryKind`), exactly five:

| Query kind | Rule |
| --- | --- |
| `exact_node_address` | Select by an explicit `NavIndex` node address. |
| `marker_kind` | Deterministic `NavIndex` walk by closed view/segment/reference kind criteria. |
| `scoped_no_candidate` | No candidate exists inside the declared proof scope. |
| `ambiguous_lookup` | More than one candidate satisfies the closed criteria. |
| `invalid_candidate` | The candidate carries a forbidden payload class. |

Selection reason (`OfflineSelectionReason`), exactly six:

| Selection reason | Rule |
| --- | --- |
| `exact_node_address_match` | The explicit node address resolved to one candidate. |
| `marker_kind_match` | The deterministic kind walk resolved to one candidate. |
| `scoped_no_candidate` | No candidate exists and a safe scoped no-answer is emitted. |
| `ambiguous_candidate_set` | More than one candidate; reject without arbitrary choice. |
| `unresolved_candidate_evidence` | The candidate cannot be bound to a complete evidence path; reject. |
| `unsafe_payload_rejected` | The candidate carries a forbidden payload class; reject. |

Expected result (`OfflineExpectedResult`), exactly three: `selected`,
`scoped_no_answer`, `rejected`.

No ranking score, embedding distance, LLM confidence, graph score, or legal
relevance score is allowed in candidate selection.

## Cleaned projection to proof-local resolution records

`ProjectionGraphResolver::new(&CleanedProjection)` derives the graph. The
mapping (decision D719) is:

| Proof-local record | Derivation |
| --- | --- |
| `SourceDocument` | One per projection, from `proj.source.sha256` (`SD-<sha256>`); its `source_corpus_id` is `CORPUS-<sha256>`. |
| `SourceBlock` | One per view node (`SB-<view_id>`), pointing at the projection's single source document. |
| `EvidenceSpan` | One per segment node (`EV-<segment_id>`), status `Active`, bound to its owning view's source block. |
| `LegalUnit` | One bounded proof-local anchor (`LU-<sha256>`) from the source snapshot identity. |
| `ActEdition` | One bounded proof-local anchor (`ED-<sha256>`) valid from `0001-01-01` with an open upper bound, so it covers any declared scope `as_of_date`. |
| `citation_key` | One per segment node (`CIT-<segment_id>`), resolving to exactly that segment's evidence span under the projection's single scope (`SCOPE-<sha256>`). |

All identifiers are validator-envelope proof-local tokens. They are never a
production schema and never a final ID format.

## Envelope handoff

A selected candidate is converted to a `RetrievalOutputEnvelope` and validated
by `validate_retrieval_output`. The envelope carries:

- `scope` with all six required fields (`scope_id`, `query_id`,
  `retrieval_run_id`, `as_of_date`, `source_corpus_id`,
  `validator_contract_version = VALIDATOR_CONTRACT_VERSION`);
- one `citations` entry whose `retrieval_output_id`, `citation_key`,
  `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`,
  and `act_edition_id` are all derived from the projection graph;
- `answer_claim_id` as `Missing`/`ExplicitNull` for a citation-only candidate;
- no forbidden payload field names.

`ambiguous_lookup` and `invalid_candidate` are resolved at proof level before the
validator handoff (`ambiguous_candidate_set` and `unsafe_payload_rejected`). An
`unresolved_candidate_evidence` binding carries an identifier the graph does not
resolve, so the validator rejects it with `unresolved_evidence_span` or
`orphaned_source_path`.

## Fail-closed rules

- An unknown identifier resolves to `None`/`Unresolved`.
- `resolve_valid_edition` returns an edition only inside its validity window.
- `is_superseded` is `false` for `Active` spans.
- No repair, inference, best-effort match, downgrade, or arbitrary choice among
  candidates is authorized.
- The projection is borrowed and never mutated (no-repair invariant).
- An answer without a resolvable citation or identifier is never emitted: the
  demo invariant is that an unresolvable citation always yields `rejected`.
- Diagnostics stay bounded: raw decoded fixture text never reaches a diagnostic,
  an outcome, or a summary.

## Non-claims

This contract does not prove or claim product retrieval quality, parser
completeness, citation-safe production retrieval readiness, legal-answer
correctness, LLM legal authority, runtime/FalkorDB/vector/rerank behavior,
production temporal graph completeness, or a final production ID schema. The
archived M014/Python work and its R034 Python validation remain prior art, not
authority. Retargeting the five blocked retrieval EVID rows is S03/S04 scope and
is out of scope here.

## Vocabulary non-promotion

No `prd/temporal-legal-model.md` §3 row is created, amended, or promoted by this
contract (decision D714). In particular the §3 `SourceBlock` row stays
`deferred-undefined`: the `SourceBlockId` envelope token is proof-local and does
not infer a future evidence-domain `SourceBlock` entity. The envelope tokens do
not promote the domain vocabulary (D714/D719).

## Implementation handoff

- Vocabulary, resolver, and proof runner: `crates/ln-query/src/retrieval_offline.rs`.
- Consuming proof: `crates/ln-query/tests/retrieval_offline.rs`.
- Verify: `cargo test -p ln-query --offline --lib retrieval_offline`,
  `cargo test -p ln-query --offline --test retrieval_offline`, plus
  `cargo fmt --all --check` and `cargo check --workspace --offline`.
