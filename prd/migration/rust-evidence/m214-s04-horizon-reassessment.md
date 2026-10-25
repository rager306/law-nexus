# M214 S04 horizon reassessment

Status: `[bounded]` receipt audit over S01-S04. Recommendations `[proposed]`.
No requirement closure, no C5 promotion, no downstream auto-start.

This is the S04 remainder reconciliation: it records what the document-scoped
NPA analysis pipeline delivered, what stays open on the R1000 / M208 horizon,
and the explicit non-claims that bound the corpus acceptance. It is the
human-readable counterpart of the machine report `m214-s04-corpus-acceptance.json`
(verdict `pass`) and must not drift from it. Contract authority stays
`prd/architecture/npa-analysis-jsonl-contract.md`.

## What S01-S04 delivered

| slice | deliverable | receipt |
|---|---|---|
| S01 | source-bound analysis mapping seam + contract (`analysis_source_mapping.rs`) | `m214-s01-source-mapping.json` |
| S02 | NPA analysis record schema + wire export | `m214-s02-analysis-export.json` |
| S03 | context family, JSONL read-back, independent verifier | `m214-s03-context-verify.json` |
| S04 | pinned provider/work-family stratified corpus sample (N=400, seed 20308) + separated acceptance report + durable battery | `m214-s04-corpus-acceptance.json`, `m214-s04-acceptance-battery.json` |

S04 acceptance result: 400/400 entries `verified_ok`, 0 refusals, 0 limit
events, tamper probe 12/12 detected with 0 false negatives, `verdict=pass`,
within the declared 4 GiB / 3600000 ms budget. The report keeps
`structural_integrity`, `semantic_adjudication`, `limits`, `resources`,
`corpus_breadth` and `horizon` separate and never merges them. Raw per-entry
evidence stays count/hash-only in the JSONL and adjudication packet.

## Remaining horizon

- **R1000 stays active/unclosed.** S04 is a bounded, content-hash-pinned
  acceptance over a stratified sample, not corpus-wide acceptance. No
  requirement is closed by receipt presence (D638). `r1000_status=active`.
- **Display-cleaning (D638) remains.** The cleaned/source projection is
  consumed, not re-adjudicated; display cleaning stays a remaining item.
- **M208-wrz6fg stays parked.** The pre-M214 temporal plan stays in
  `214-RESEARCH.md`; resuming or reformulating M208 needs its own decision.
  `m208_status=parked`.
- **D650 stale binding needs a decision-store action.** D651 replaced D650's
  executive priority, but the D651 -> D650 supersession edge is not yet
  recorded in the decision store. Until then D650 remains historical planning
  context and must not be read as the live M214 binding.
- **M215-M220 stay parked** (D651/D652). Each needs a verified input contract
  before execution; no temporal/retrieval/graph work auto-starts from S04.

## Semantic adjudication boundary (D667 / D668)

`semantic_adjudication` is structural-only: `semantic_reference_status=absent`,
`promotion=false`, adjudication status `not_attempted`. No independent
semantic/legal reference compatible with the `law-nexus/npa-analysis-*` JSONL
exists, so no semantic rate is claimed and R1000 is never promoted from
receipt presence. Stratification is provider + work-family (D668), never
inferred year/type: `not_year_type_stratified=true` and `coverage_claim=null`.

## Explicit non-claims

- no corpus-wide accuracy claim;
- no source authenticity claim;
- no legal-effect claim;
- the full corpus sweep is not a semantic oracle;
- count/hash only - no decoded corpus text enters tracked evidence.

## Next-horizon readiness

S04 proves a bounded document-scoped pipeline and its independent verifier; it
does not prove retrieval, temporal typing, embeddings/graph materialization or
access control. The parked M215-M220 queue must present verified input contracts
before a reassessment can lift their park. Nothing in this document authorizes
that lift.
