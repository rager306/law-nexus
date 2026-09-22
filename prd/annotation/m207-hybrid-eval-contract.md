# M207 hybrid evaluation contract

Status: [proposed]. Verification-harness contract for the D519 automated
successor. Not gold, not human annotation, not a frozen S01/S02/S03/S04
schema, not S03 metrics, not parser quality, and not a Rust product type.

Owning slice: M207 S06 (Python repository-control harness, ADR-0007).
First Rust series consumption: M211 S02 / M207 S06. This file implements
nothing; it fixes the reporting surface of the evaluator so a future reader
cannot mistake a differential number for parser quality.

The wire contract for the *inputs* stays in
`prd/annotation/m207-hybrid-records-contract.md`; this document covers only
the *evaluation* mode that consumes two already-validated records files.

## Purpose

Give the harness a **read-only, denominator-explicit** evaluation of two
validated `m207-hybrid-records/v1` files, together with two non-differential
evidence classes, without ever presenting a score as parser quality, human
gold, or an S03 rate.

Executable gate:

```text
uv run python scripts/m207_hybrid_eval_experiment.py --evaluate-records EXPECTED PREDICTED
```

## Version and identification

| Field | Value |
|---|---|
| `schema` | `m207-hybrid-eval-report/v1` |
| `schema_version` | integer `1` |
| marker | `M207_HYBRID_EVAL_OK` |
| status | `ok` \| `invalid` \| `unstable` |
| `reference_role` | `harness-expected` |
| `alignment_policy` | `local-anchor-identity-v1` |
| `lifecycle` | `["proposed"]` |
| `evidence_classes` | `["differential", "metamorphic"]` |

`M207_HYBRID_EVAL_OK` reports that the report has the documented shape and
that every published plane carries an explicit denominator. It is **not**
acceptance evidence, not a review gate, not a discharged M207 pin, and it
does not close R038. `reference_role` states that the EXPECTED file is a
harness reference: it is not gold, not human, and not S03.

## CLI surface

```text
--evaluate-records EXPECTED PREDICTED
```

Read-only. The mode validates both files against `m207-hybrid-records/v1`,
pairs bundles, scores the planes, runs the metamorphic properties, and
prints one JSON report to stdout. It never writes EXPECTED, PREDICTED, the
synthetic artifact, or any frozen S01–S04 store.

The following combinations are `USAGE` (exit 2), refused before any parse:

- `--evaluate-records` together with `--write`
- `--evaluate-records` together with `--check`
- `--evaluate-records` together with `--validate-records`

`--write-report` (persisting the report as a tracked artifact) is explicitly
**out of this slice**. There is no tracked "gold report" and none may be
added under `prd/migration/rust-evidence/` by this contract.

## Exit codes and markers (D523)

Differential score values never affect the exit code: a poor score is still
a successful run. Only harness integrity and input validity move the exit
code.

| `status` | marker | exit | when |
|---|---|---|---|
| `ok` | `M207_HYBRID_EVAL_OK` | 0 | both inputs valid and every metamorphic property passed or none was measured |
| `unstable` | `null` | 1 | at least one metamorphic property was `failed`; the full differential block is still printed |
| `invalid` | `null` | 1 | a records diagnostic on either side, or a missing/unreadable input |
| `invalid` (`USAGE`) | `null` | 2 | a forbidden flag combination |

A measurement tool that exits non-zero because measured quality is poor
cannot serve as a regression gate, while a harness-integrity failure must
not be reported as a successful run. A failed property nulls the marker but
still prints the differential planes, so the operator sees both the broken
property and the measurements.

On `invalid`, `differential` is `null`, `metamorphic` is a shape-only
container with no executed property, and no plane value appears anywhere in
the report. The diagnostic detail names the side (`expected` / `predicted`)
on which the failure was seen.

## Evidence classes (three, kept separate)

| Class | Surface | Proves | Must not claim |
|---|---|---|---|
| synthetic regression | `--check` against the pinned synthetic artifact | the synthetic fixture still renders byte-identical to the tracked file | not Rust output — synthetic fixtures are authored in the harness and M211 S02 has not run |
| differential | `differential` object of the eval report | two validated v1 records files agree on explicit planes and denominators | not parser quality, not human gold, not S03 metrics, not Rust parity (a `rust-runtime` origin is a label, not proof) |
| metamorphic | sibling `metamorphic` object of the same report | harness-local scorer invariants hold without a second label as truth | not parser quality, not a review gate; verdicts are never averaged into differential planes |

The differential number is never parser quality and never human gold. The
synthetic fixtures must not be presented as Rust emitter output.

S03 rates are **not** reused. The S03 machinery is green with every human
rate `not-measured` and `human_pilot_performed: false`; those rates are not
an evaluation of the parser and give no denominator to this mode.

## Report shape

Report keys: `schema`, `schema_version`, `status`, `marker`, `lifecycle`,
`authoritative`, `is_gold`, `not_human`, `not_s03_metrics`,
`alignment_policy`, `reference_role`, `evidence_classes`,
`expected_provenance_origin`, `predicted_provenance_origin`,
`differential`, `metamorphic`, `not_measured_policy`, `limits`,
`non_claims`, `diagnostics`.

Honesty keys are fixed values, not caller-supplied claims:

| Key | Value |
|---|---|
| `authoritative` | `false` |
| `is_gold` | `false` |
| `not_human` | `true` |
| `not_s03_metrics` | `true` |

`limits` and `non_claims` are published in every report so the reader does
not have to infer them from this document.

### Differential planes

`differential.planes.hybrid` publishes:

- `detection` — `{tp, fp, fn}` integer counts
- `field_value` — measured ratio over field slots
- `provenance` — measured ratio over field sources
- `relation_e2e` — relation block with `tp` / `fp` / `fn` / `expected_n` / `predicted_n`
- `relation_conditional` — measured ratio, conditioned on expected relations
- `unresolved` — measured ratio
- `ambiguity_groups` — integer count
- `bundle_exact` — measured ratio over matched bundles
- `occurrence_expected`, `bundles`

`differential.planes.local_focus` is a **secondary** diagnostic plane; it is
not the headline metric and it hides missing members (synthetic 4/13 against
the hybrid 9/13). `differential.planes.exact_bundle` repeats the hybrid
`bundle_exact` block so no reader has to reach through two levels.

### Metamorphic properties

Four named harness-local scorer properties, executed by default:

- `alignment_invariant_to_record_order`
- `labels_do_not_drive_matching`
- `empty_denominator_is_not_measured`
- `duplicate_anchor_key_is_rejected`

Each row carries `name`, `status` (`passed` / `failed` / `not-measured`),
`correct`, `denominator`, `value`, `detail`. A row with a zero denominator is
`not-measured` and is never counted as passed. The aggregate `verdict` is
`not-measured` when no property executed. A property that raises is recorded
as `failed`, never as a traceback.

## Pairing policy

Bundles are paired by `bundle_id` **only**. No best-match, no label-driven or
date/number-driven rematch.

`differential.bundle_alignment` reports:

- `matched` — sorted ids present on both sides
- `expected_only` — bundle FN (present in EXPECTED, absent in PREDICTED)
- `predicted_only` — bundle FP
- `expected_bundles`, `predicted_bundles` — integer totals

Unmatched ids are **never** passed to `score_pair`; an unmatched bundle is an
explicit bundle FN/FP, never scored against an empty partner. Bundle
alignment does not manufacture synthetic pairs.

## `not-measured` rule

A zero denominator yields `value: null` and `status: "not-measured"`.

A `not-measured` block contributes nothing to any numerator or denominator
and is never coerced into perfect accuracy. An empty denominator is **not**
100% accuracy and **not** zero errors. The exact policy text is published in
`not_measured_policy` on every report.

## Ambiguity semantics on the records path

`ambiguity_groups == 0` means *no validated pair contained a duplicate
anchor-key*. It does **not** mean ambiguity quality is perfect. A duplicate
anchor-key inside a bundle stays a diagnostic (`AMBIGUOUS_DUPLICATE`);
`validate_hybrid_records` is not weakened to make a file scoreable. The
`duplicate-anchor-ambiguous` synthetic scenario remains a regression for the
synthetic path only.

## Closed diagnostic set

The evaluator and the records validator share one closed code vocabulary.
The block below is machine-readable: one code per line between the two
markers, and the doc-code test compares this set with (`==`) the module's
`EVAL_DIAGNOSTICS` in both directions.

```text
<!-- eval-diagnostics:begin -->
USAGE
MISSING_INPUT
PROTECTED_PATH
DUPLICATE_BUNDLE_ID
UNSUPPORTED_VERSION
MALFORMED_REF
INVALID_BOUNDS
CROSS_DOC_REF
DANGLING_EDGE
AMBIGUOUS_DUPLICATE
PROVENANCE_FORBIDDEN
SOURCE_CLAIM_WITHOUT_BYTES
<!-- eval-diagnostics:end -->
```

`PROTECTED_PATH` is fail-closed: the tracked synthetic experiment JSON, the
S03 evaluation report, the other frozen S01–S04 annotation / evidence pins,
and the protected directory prefixes are refused on **either** side before
any parse.

## Known limitations

- No size cap on `m207-hybrid-records/v1` input (inherited from S05). The
  operator is a local operator evaluating their own records; this is not
  hardened against an external adversarial vector.
- Duplicate `bundle_id` across bundles is caught in the **evaluator**,
  because the v1 validator does not check uniqueness of `bundle_id` between
  bundles. This is a candidate for a v2 contract, not an extension of v1
  (D521 keeps v1 as byte-contract satisfaction only).
- `local_focus` is a secondary plane and hides missing members; the hybrid
  plane is the one that keeps them.
- The report is not persisted. There is no tracked eval artifact in this
  slice.

## Non-claims

- `M207_HYBRID_EVAL_OK` is not acceptance evidence, not gold, not a review
  gate, and not a discharged M207 pin.
- Does not measure legal correctness and does not admit parser quality.
- Does not reuse or re-derive S03 human-pass rates.
- Does not treat the EXPECTED file as human gold; it is a harness reference.
- Does not treat a synthetic fixture as Rust emitter output.
- Does not read or rewrite protected frozen S01–S04 or S03 stores.
- Does not add a dependency, a Rust crate, or a Rust-side consumer; the mode
  stays harness-local (R064).
- Does not release a human pilot or substitute for the human gate (D519).
