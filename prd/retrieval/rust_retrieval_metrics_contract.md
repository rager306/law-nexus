---
title: "Rust Retrieval Metrics Contract"
status: "contract-draft"
non_authoritative: true
owner: "M216-8dps6e/S04"
contract_version: "retrieval-metrics/rust-v1"
requirement: "R034"
validator_contract: "prd/retrieval/rust_retrieval_output_validator_contract.md"
prior_art:
  - "prd/archive/retrieval-era/local_retrieval_quality_benchmark_contract.md"
  - "prd/archive/retrieval-era/local_retrieval_quality_benchmark_proof.md"
  - "prd/archive/retrieval-era/representative_retrieval_runtime_benchmark_contract.md"
  - "prd/archive/retrieval-era/representative_retrieval_runtime_benchmark_proof.md"
  - "prd/archive/retrieval-era/local_retrieval_runtime_boundary_contract.md"
  - "prd/retrieval/rust_offline_citation_retrieval_contract.md"
  - "prd/retrieval/rust_real_artifact_retrieval_proof.md"
vocabulary_authority: "prd/temporal-legal-model.md#3"
created_at: "2026-10-09"
---

# Rust Retrieval Metrics Contract

This contract freezes the Rust-only retrieval **quality** and **runtime**
metrics recorded by slice S04 on the declared M216 retrieval slice. It
reformulates the archived M015/M016 Python-era quality and representative
runtime benchmark contracts in Rust, composes with the S02 offline citation-safe
retrieval contract (`offline-citation-retrieval/rust-v1`) and the S03
real-artifact retrieval proof (`real-artifact-retrieval/rust-v1`), and binds the
measurement to exactly three tracked documents driven through the enabled M213
cleaned-projection pipeline plus the S02 offline retrieval surface. It is
`contract-draft`, `non-authoritative`, and owned by `M216-8dps6e/S04`.

Contract version string: `retrieval-metrics/rust-v1`.

Report schema version string: `retrieval-metrics/rust-v1`.

## Boundary

- The deliverable is a bounded, deterministic **slice-level** metrics report:
  quality metrics (selection correctness) plus a reproducible structural runtime
  profile, with a separate non-asserted host-boundary wall-clock observation.
- The metrics are recorded over a **declared slice of three tracked documents**,
  not over the corpus. They measure correctness of *this* slice's declared cases
  and the *structure* of the offline pipeline work; they are not product
  retrieval quality, not corpus coverage, and not a runtime/throughput claim.
- It makes no network call, starts no service, loads no product API, calls no
  embedding model or LLM, and reads no FalkorDB runtime. There is no product
  surface and no runtime service.
- The computation surface is a serde-free library module
  (`crates/ln-query/src/retrieval_metrics.rs`) with no new crate dependency and
  no `io`/network/time inside the library; wall-clock is measured by the caller
  (the integration test), never by the library.
- Every emitted value is a counter, a ratio, or a closed string. No raw decoded
  legal text, prompt, vector, secret, or generated answer prose is ever emitted
  (see Redaction).

## Declared slice documents

Exactly THREE tracked documents are declared and pinned by content:

| Document | sha256 | Read as |
| --- | --- | --- |
| `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml` (real Consultant Plus WordML; 193726 bytes) | `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d` | `std::fs::read` (never `include_str!`) |
| `crates/ln-decode/tests/fixtures/reader/mixed-wordml.xml` | `d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db` | `include_str!` |
| `crates/ln-decode/tests/fixtures/reader/diverse/navigation-demo.xml` | `b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0` | `include_str!` |

The captured `package.manifest().source.sha256` is checked against the pin for
every document; a byte-length or sha256 drift panics with an explicit re-pin
message, never a silent re-pin. This is bounded slice proof over three documents,
not corpus coverage.

## Closed quality metric set

The quality metric set is closed: exactly the six metrics below, computed by
`ln_query::retrieval_metrics::compute_retrieval_quality_metrics` from a case list
(`&[OfflineRetrievalCase]`) and its run outcomes (`&[OfflineCaseOutcome]`),
joined by `case_id`.

Observed result class from an `OfflineCaseOutcome` (the only observables are the
closed `validator_verdict` and `selection_reason`):

```
observed_class(outcome) =
    Selected        if outcome.validator_verdict == Some(OutputVerdict::Accepted)
    ScopedNoAnswer  if outcome.validator_verdict == Some(OutputVerdict::AcceptedScopedNoAnswer)
    Rejected        otherwise   // Some(Rejected) or None (proof-level rejection)
```

| Metric | Numerator | Denominator |
| --- | --- | --- |
| `selection_accuracy` | outcomes where `observed_class == expected_result` | `total_cases` |
| `positive_selection_rate` | outcomes where `case.expected_result == Selected` AND `observed_class == Selected` | `positive_cases` = cases with `expected_result == Selected` |
| `scoped_no_answer_accuracy` | outcomes where `case.expected_result == ScopedNoAnswer` AND `observed_class == ScopedNoAnswer` | `scoped_cases` = cases with `expected_result == ScopedNoAnswer` |
| `ambiguous_rejection_rate` | outcomes where `case.query_kind == AmbiguousLookup` AND `selection_reason == AmbiguousCandidateSet` AND `observed_class == Rejected` | `ambiguous_cases` = cases with `query_kind == AmbiguousLookup` |
| `unsafe_rejection_rate` | outcomes where `case.query_kind == InvalidCandidate` AND `selection_reason == UnsafePayloadRejected` AND `observed_class == Rejected` | `unsafe_cases` = cases with `query_kind == InvalidCandidate` |
| `unresolvable_citation_rejection_rate` | outcomes where `selection_reason == UnresolvedCandidateEvidence` AND `observed_class == Rejected` | `unresolvable_cases` = outcomes with `selection_reason == UnresolvedCandidateEvidence` |

A zero denominator yields the metric value `0.0` as closed behavior (never a
panic, never a fabricated 1.0). The case-class counters (`total_cases`,
`positive_cases`, `scoped_cases`, `ambiguous_cases`, `unsafe_cases`,
`unresolvable_cases`) and `mismatch_count` are reported alongside the six
metrics.

The complete declared classification coverage is required: the corpus must
exercise every `OfflineExpectedResult` class (`selected`, `scoped_no_answer`,
`rejected`) and every rejection class named above (`ambiguous_lookup`,
`invalid_candidate`, unresolved evidence), so no metric denominator is empty on
the declared slice.

## Runtime profile

The runtime profile is closed and **structural** (reproducible counters), not a
wall-clock claim:

| Counter | Source |
| --- | --- |
| `documents_processed` | number of declared slice documents driven through the enabled pipeline |
| `projected_views` | total view nodes across the documents' cleaned projections |
| `projected_segments` | total segment nodes across the documents' cleaned projections |
| `resolver_evidence_spans` | total evidence spans minted by the per-document `ProjectionGraphResolver` |
| `cases_run` | total declared cases run |

The structural profile is reproducible: two runs over the same declared slice
must produce an equal `RetrievalRuntimeProfile`. It carries no timing, throughput,
or service claim.

## Host-boundary wall-clock observation

The caller (integration test) may measure host wall-clock with
`std::time::Instant` over `N` iterations and record a
`RetrievalObservedTiming { iterations, elapsed_ms_min, elapsed_ms_median,
reproducible: false, asserted: false }`. It is reported in the metrics report as
`observed_timing: Option<RetrievalObservedTiming>`.

- `reproducible: false` — host-boundary timing is environment-dependent and is
  NOT reproducible evidence.
- `asserted: false` — the test never asserts a timing threshold; the timing is
  an observation, never a gate.
- This observation is explicitly separated from the reproducible structural
  runtime profile and from any runtime/FalkorDB readiness claim.

## Thresholds

All six quality metrics carry a threshold of `1.0` on the declared slice. The
`RetrievalMetricThreshold` comparison returns the list of breaches; a non-empty
breach list is a failure. `mismatch_count` must be `0`. Runtime structural
counters are compared for reproducibility (equality across two runs), not against
a threshold. Host-boundary timing has no threshold.

## Runtime-honesty boundary

- There is no ranker, no scoring, and no candidate ranking in the offline
  retrieval surface, so `mrr`, `recall@k`, `precision@k`, and any rank-gain
  metric are **excluded** from this contract. They cannot be computed truthfully
  here.
- There are no embeddings and no FalkorDB runtime in this surface, so wall-clock
  timing is **not** runtime/FalkorDB readiness and is not local embedding
  quality.
- The structural runtime profile describes the work the offline pipeline did over
  the declared slice; it is not throughput, latency, or scalability.

## Bounded report schema

`RetrievalMetricsReport` is the only observable surface:

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | `&'static str` | `"retrieval-metrics/rust-v1"` |
| `kind` | `RetrievalMetricKind` | closed: `quality` \| `runtime` |
| `boundary` | `RetrievalMetricBoundary` | closed: `slice` |
| `quality` | `RetrievalQualityMetrics` | six ratios + seven counters |
| `runtime_profile` | `RetrievalRuntimeProfile` | five structural counters |
| `observed_timing` | `Option<RetrievalObservedTiming>` | `reproducible: false`, `asserted: false` |
| `non_claims` | `&'static [&'static str]` | the closed non-claims list below |

Closed reproducibility marker:
`RetrievalMetricReproducibility` = `reproducible` \| `host_boundary_observed_unasserted`.

Forbidden payload classes (must never appear in the report, its diagnostics, or
any printed line): raw decoded legal text, document/prompt text, embeddings or
vectors, secrets/credentials, and generated answer prose. Only counters, ratios,
closed kinds/codes, and `&'static` non-claim strings are permitted. The printed
bounded report (`--nocapture`) carries only counters and ratios.

## Redaction

No raw decoded legal text, prompt, vector, secret, or generated answer prose is
emitted by the metrics module, the proof test, the durable proof artifact, the
EVID register, or any diagnostic. A sentinel check in the consuming test asserts
that known sentinel fragments of the declared documents never appear in the
report or diagnostics.

## Decision compatibility

- **D537** — the frozen architecture registry
  (`prd/architecture/architecture_items.jsonl`,
  `prd/architecture/architecture_edges.jsonl`) is neither written, regenerated,
  nor repaired by these metrics; the D7 missing-anchor quarantine is not cleared.
  S04 closure is recorded in the standalone retrieval EVID register (D721
  precedent); the frozen-registry retarget stays deferred to RC28-F19.
- **D714** — no `prd/temporal-legal-model.md` §3 vocabulary row is minted or
  promoted; the metrics use only existing closed retrieval vocabulary.
- **D719** — the `SourceBlock` row stays `deferred-undefined`; resolver
  identifiers remain proof-local and are never promoted to a domain entity.

## Non-claims

- Does not prove product retrieval quality.
- Does not prove legal-answer correctness.
- Does not prove ranking, `mrr`, `recall@k`, or embedding quality.
- Does not prove parser completeness.
- Does not prove runtime, throughput, latency, or FalkorDB readiness.
- Does not prove corpus coverage; three declared documents are not the corpus.
- Does not close `GATE-G008` or `GATE-G011`.
- Does not clear the D7 missing-anchor quarantine.
- Does not write, regenerate, or repair the frozen architecture registry (D537).
- Host-boundary wall-clock timing is `reproducible: false` and `asserted: false`
  and is never a product or readiness claim.

## Revisable

The declared slice documents, the closed metric set, the thresholds, the runtime
profile, and the non-claims are revisable only by a later milestone that owns the
metric scope; they are fixed for S04.
