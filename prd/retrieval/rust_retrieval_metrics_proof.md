---
title: "Rust Retrieval Metrics Proof"
status: "proof"
non_authoritative: true
owner: "M216-8dps6e/S04"
contract: "prd/retrieval/rust_retrieval_metrics_contract.md"
report_schema_version: "retrieval-metrics/rust-v1"
requirement: "R034"
proof_command: "cargo test -p ln-query --offline --test retrieval_metrics -- --nocapture"
created_at: "2026-10-09"
---

# Rust Retrieval Metrics Proof

This is the consuming, reproducible proof recorded by slice S04 on the declared
M216 retrieval slice. It reformulates the archived Python-era quality and
representative-runtime benchmark proofs in Rust and binds them to the S02
offline citation-safe retrieval surface over the enabled M213 cleaned-projection
pipeline. It is `non-authoritative` and owned by `M216-8dps6e/S04`.

- Contract: `prd/retrieval/rust_retrieval_metrics_contract.md`
  (`retrieval-metrics/rust-v1`).
- Computation surface: `crates/ln-query/src/retrieval_metrics.rs`
  (serde-free, no new crate dependency, no `io`/network/time in the library).
- Consuming test: `crates/ln-query/tests/retrieval_metrics.rs`.
- Proof command: `cargo test -p ln-query --offline --test retrieval_metrics -- --nocapture`.

## Declared slice documents (pinned by content)

Exactly three tracked documents are declared and pinned by sha256. The captured
`package.manifest().source.sha256` is checked against the pin for every document;
a byte-length or sha256 drift panics with an explicit re-pin message, never a
silent re-pin.

| Document | sha256 | Read as |
| --- | --- | --- |
| `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml` (real Consultant Plus WordML; 193726 bytes) | `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d` | `std::fs::read` (never `include_str!`) |
| `crates/ln-decode/tests/fixtures/reader/mixed-wordml.xml` | `d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db` | `include_str!` |
| `crates/ln-decode/tests/fixtures/reader/diverse/navigation-demo.xml` | `b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0` | `include_str!` |

Each document is driven through the enabled pipeline
(`capture -> gate_reader(SupportedWordml) -> build_projection ->
export_cleaned_projection(Complete) -> read_cleaned_wire -> build_nav_index`),
then `ProjectionGraphResolver` is derived from the cleaned projection, and a
deterministic per-document corpus of eight cases covers every declared class.

## Observed bounded report

Observed values from the declared slice (counters and ratios only). This is a
slice-level observation over three documents, not corpus coverage.

```
retrieval_metrics_report/rust-v1
schema_version = retrieval-metrics/rust-v1
kind = quality
boundary = slice
documents_processed = 3
projected_views = 329
projected_segments = 345
resolver_evidence_spans = 345
cases_run = 24
quality.total_cases = 24
quality.positive_cases = 6
quality.scoped_cases = 6
quality.ambiguous_cases = 3
quality.unsafe_cases = 3
quality.unresolvable_cases = 3
quality.mismatch_count = 0
quality.selection_accuracy = 1.000000
quality.positive_selection_rate = 1.000000
quality.scoped_no_answer_accuracy = 1.000000
quality.ambiguous_rejection_rate = 1.000000
quality.unsafe_rejection_rate = 1.000000
quality.unresolvable_citation_rejection_rate = 1.000000
quality.threshold_breaches = 0
refused_as_product_claim = true
observed_timing.iterations = 5
observed_timing.elapsed_ms_min = 6
observed_timing.elapsed_ms_median = 7
observed_timing.reproducible = false
observed_timing.asserted = false
```

Every quality metric meets its `1.0` threshold and `mismatch_count` is `0`.
All six case-class counters are non-zero, so no metric denominator is empty on
the declared slice. The host-boundary wall-clock line is a **single host
observation** (environment-dependent, `reproducible = false`,
`asserted = false`); the numeric milliseconds are illustrative of one machine
run and are never asserted or treated as evidence of a threshold.

## What the proof establishes

- Six closed quality metrics (`selection_accuracy`,
  `positive_selection_rate`, `scoped_no_answer_accuracy`,
  `ambiguous_rejection_rate`, `unsafe_rejection_rate`,
  `unresolvable_citation_rejection_rate`) computed by
  `ln_query::retrieval_metrics::compute_retrieval_quality_metrics` from the
  declared cases and their S02 run outcomes, joined by `case_id`.
- A reproducible structural runtime profile
  (`documents_processed`, `projected_views`, `projected_segments`,
  `resolver_evidence_spans`, `cases_run`): two independent pipeline builds over
  the declared slice produce an equal
  `RetrievalRuntimeProfile`.
- Origin control: for every document the resolver's evidence-span segment set
  equals the `NavIndex` segment-address set, with one evidence span per segment
  node and a unique citation-key resolution per segment.
- Demo invariant: an unresolvable citation is always `rejected` with the
  fail-closed `unresolved_evidence_span` code, and a rejection reason never emits
  an accepted answer or a scoped no-answer.
- Determinism and purity: two runs produce identical cases, outcomes, metrics,
  and profile; the borrowed cleaned projection is not mutated.
- Redaction: no sentinel fragment of any declared document appears in the report,
  the quality metrics, the runtime profile, or the non-claims.

## Boundaries (honest non-claims)

- The metrics are **slice-level**: three declared documents, not the corpus.
- They are **not** product retrieval quality and **not** legal-answer correctness.
- There is no ranker/scoring, so `mrr`, `recall@k`, `precision@k`, and any
  rank-gain metric are excluded; they cannot be computed truthfully here.
- There are no embeddings and no FalkorDB runtime, so wall-clock timing is not
  runtime/FalkorDB readiness and not local embedding quality.
- The structural runtime profile is not throughput, latency, or scalability.
- Host-boundary wall-clock timing is `reproducible = false` and
  `asserted = false`; it is never a product or readiness claim.
- Does not prove parser completeness; does not close `GATE-G008` or
  `GATE-G011`; does not clear the D7 missing-anchor quarantine; does not prove
  corpus coverage.

## Redaction

No raw decoded legal text, prompt, vector, secret, or generated answer prose is
emitted by the metrics module, this proof, or any diagnostic. Sentinel fragments
of each declared document are asserted present in the source and asserted absent
from the report's observable surface, so the redaction check cannot pass
vacuously.

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

## Revisable

The declared slice documents, the closed metric set, the thresholds, the runtime
profile, and the non-claims are revisable only by a later milestone that owns the
metric scope; they are fixed for S04.
