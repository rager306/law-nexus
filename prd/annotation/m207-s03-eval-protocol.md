# M207 S03 — frozen evaluation protocol for per-aspect rates (`m207-s03-eval-protocol/v1`)

**Status:** `[bounded]` evaluation/evidence contract, frozen **before** any metric is computed.
**Milestone:** M207-b2i96m / S03 / T01
**Frozen inputs:** `prd/annotation/m207-s01-codebook.md` (`m207-s01-codebook/v1`,
sha256-pinned), `prd/annotation/m207-s01-schemas.json` (`m207-s01-annotation-schemas/v1`,
sha256-pinned), `prd/migration/rust-evidence/m207-s01-pilot-cases.json` (40 frozen cases,
sha256-pinned), `prd/annotation/m207-s02-coder-protocol.md` (`m207-s02-coder-protocol/v1`,
sha256-pinned), `prd/annotation/m207-s02-schemas.json` (`m207-s02-annotation-schemas/v1`,
sha256-pinned), M199 protocol §5 (`m199-s01-annotation-protocol.md`, sha256-pinned).
**Submission form:** `m207-s01-coding-submission/v1` is reused **verbatim** (D475).
No ninth slot, no new submission key, no `schema_version` bump.
**Closed schema file:** `prd/annotation/m207-s03-schemas.json` (`m207-s03-eval-schemas/v1`).
**Executable gate:** `uv run python scripts/m207_s03_schemas.py check`
(marker `M207_S03_SCHEMAS_OK`); negative proof: `uv run python scripts/m207_s03_schemas.py selftest`.

This document is the frozen instruction sheet for the S03 evaluation unit plus its
machine-readable contract. It freezes *which aspects are measured*, *how each aspect is
derived from the already-frozen S02 axes*, *what the denominator of each aspect is*, *how
strata are published*, and *what may never be published*. It computes **no metric**: S03
fabricates no coding, no resolution, no rate and no stratum value. Two human coding passes
and a human adjudication are the only sources of the resolved reference; until they exist
every aspect and every stratum is published `not-measured` and the chain stops at exit 3.

The protocol is fixed **before** measurement on purpose. If the contract could still be
edited once numbers exist, a rate could be fitted to a result, and "0.0 / 1.0 without a
denominator" would be indistinguishable from a real measurement (RC28-F01).

## 1. Scope, framing and ownership

S03 owns the per-aspect error rates of the M207 pilot — `span`, `slot`, `scope`, `binding`,
`abstention` and `false_authority` (RC28-F15) — together with provider and Work-family
strata. It does not own the codings, the agreement or the adjudication (all three are S02),
and it does not own the corpus-scale run (S04).

The framing is **rater-vs-resolved-reference**: a human coding pass is compared with the
reference resolved from two independent passes plus a human adjudication. It is **not**
system quality and **not** gold:

- no model is invoked anywhere in M207 (`model_invoked` stays `false`), so a rate cannot
  describe a system;
- `is_gold` stays `false`, `promotion` stays `none`, `threshold` stays `null`,
  `classification` stays `not-authorized` and `human_acceptance` stays `null`: a resolved
  reference is an evaluation input, never an adopted gold label (D490);
- the reference is itself fallible human work on 40 frozen cases; the rates are descriptive
  of these raters against this reference, nothing more.

Ownership by construction: any S03 artifact that reports a model output, a gate decision, a
promoted label or a corpus-scale claim is invalid, and the executable gate rejects it.

## 2. Frozen inputs and admissibility

Admissible inputs, and nothing else:

| Input | Schema id | Role |
|---|---|---|
| `prd/migration/rust-evidence/m207-s01-pilot-cases.json` | `m207-s01-pilot-cases/v1` | the 40 frozen cases, `work_family`, `draw_stratum`, `byte_len` |
| human submissions under the S02 submission store | `m207-s01-coding-submission/v1` (reused verbatim) | the two independent passes |
| `prd/migration/rust-evidence/m207-s02-agreement-report.json` | `m207-s02-agreement-report/v1` | the frozen pre-adjudication agreement |
| `prd/migration/rust-evidence/m207-s02-disagreement-inventory.json` | `m207-s02-disagreement-inventory/v1` | the frozen disagreements |
| `prd/migration/rust-evidence/m207-s02-adjudication-record.json` | `m207-s02-adjudication-record/v1` | the human resolutions |
| `prd/migration/rust-evidence/m207-s02-pilot-receipt.json` | `m207-s02-pilot-receipt/v1` | the pilot receipt |

The submission form is **not** redefined here: `submission_schema_id` is exactly
`m207-s01-coding-submission/v1`, reused verbatim (D475), and S03 declares no slot key of its
own. The S02 human stores (`prd/annotation/m207-s02-submissions`,
`prd/annotation/m207-s02-adjudications`) are read-only inputs: the harness never creates,
edits, repairs or normalizes a submission or an adjudication, so an absent store stays absent
(`HUMAN_PILOT_ABSENT`) instead of being filled in by a machine.

Refused inputs (`PROXY_INPUT_REFUSED`): any producer or proxy surface presented as an
evaluation input — `npa-quality-receipts/v1`, any `npa-c5-*` manifest, the corpus-manifest
schema `law-nexus-npa-corpus-manifest/v1` (the id C5 and the sealed C3 holdout carry in their
`schema_version` field), `npa-lawref-seed/v1` with `provenance=rule-seed`, and the rule-seed
sidecar `crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json`. The sidecar sits next
to the 180 frozen `.txt` fragments S03 already counts, so it is the cheapest way a producer
could promote itself into a measurement: its spans are **not** a resolved reference and the
gate pins the refusal by name and by path. A proxy input is refused, never down-graded and
never averaged in.

Admissibility is also typed: an input whose `measurement_status` is anything other than
`independent-measured` is not an evaluation input.

## 3. Aspect table: six separately measured aspects

RC28-F15 requires span, slot, scope, binding, abstention and false-authority to be measured
**separately**, each with its own denominator. Two of the six cannot be read off an S02 axis
directly, and D490 fixes how they are derived:

- the frozen S02 axis space is closed at eleven axes (D467/D475): a ninth slot key and a
  `schema_version` bump are impossible;
- `scope` and `binding` are therefore **derived** from the frozen slots, and `false_authority`
  is derived from the frozen `reference_decision` axis. The derived table in
  `prd/annotation/m207-s03-schemas.json` is the only lawful source for those three aspects.

| Aspect | Source axes | Derived rule | Denominator |
|---|---|---|---|
| `span` | `span_exact` | pass coding vs resolved reference coding under the frozen M199 §8 rule (`start`, `end` and `decision` all equal) | units where both passes committed a coding, the reference is a reference, and the resolved span is one of the two committed spans |
| `slot` | the eight `slot_<key>` axes | per-key slot presence vs resolved reference presence; the published value is the aggregate over the eight closed keys | per key: units where both passes committed a coding and the reference is a reference; aggregate denominator = sum over the eight keys |
| `scope` | `slot_hier_nums`, `slot_doc_no`, `slot_law_code`, `slot_marker_chain` | a reference carrying its own target through `hier_nums`/`doc_no`/`law_code` is `scope_local`; a target arriving only through a non-empty `marker_chain` is `scope_inherited`; otherwise the unit is excluded | units where both passes committed a coding, the reference is a reference, and the reference derives a scope label |
| `binding` | `slot_anaphora`, `slot_range` | `anaphora` and `range` both absent with a present target is `binding_explicit`; a non-empty `anaphora` or `range` is `binding_unresolved`; otherwise the unit is excluded | units where both passes committed a coding, the reference is a reference, and the reference derives a binding label |
| `abstention` | `abstention` | pass abstention value vs resolved reference abstention value; abstention is a **separate outcome** and is never merged with `not_a_reference` | **all** units where both passes committed a coding, including units whose reference is `not_a_reference` |
| `false_authority` | `reference_decision` | the pass asserted `reference` while the resolved reference is `not_a_reference` — claimed authority with no resolved support | units where both passes committed a coding and the reference is `not_a_reference` (the population in which false authority can occur) |

Every aspect row in the frozen schema declares `derived_from`, `numerator`, `denominator`,
`denominator_units`, `units_excluded_reasons` and `value_kind`. The union of the six
`source_axes` sets is exactly the eleven frozen S02 axes — every axis is consumed by at least
one aspect and no aspect invents an axis. A missing aspect, an empty `denominator`, a
denominator unit outside the closed vocabulary, or an axis that no aspect consumes is
`ASPECT_TABLE_DRIFT`.

Excluded units never silently disappear: each exclusion carries a named reason from the
closed set `abstained | undisputed_missing | unresolved | not_derivable`, and an excluded
unit neither increases nor decreases a rate. `abstention` deliberately does **not** exclude
`abstained` units: abstention is the quantity being measured there, so folding it away would
be the `ABSTENTION_COLLAPSE` defect in a second guise.

## 4. Denominator rule: no value without a denominator

D489. Every published number has exactly this shape:

```
{ "measured": <int>, "denominator": <int>, "value": <float|null>, "measurement_status": <string> }
```

- `denominator == 0` → `value` is `null`, `measurement_status` is `not-measured` and the run
  reports `RATE_UNDEFINED`. It is **never** `0.0` and **never** `1.0`: an absent denominator
  is not a measurement and must not read like one (RC28-F01).
- `1.0` is legal only as a computed result with `measured > 0` and full coverage of the
  declared denominator. A `1.0` produced without that backing is
  `COMPUTED_PERFECT_UNBACKED`.
- a value is never imputed from a path, a file name, a case count or a neighbouring stratum.
- `DENOMINATOR_MISMATCH` fires when a published `denominator` disagrees with the unit
  population the frozen aspect rule implies.
- the invariant is machine-checked end to end: the presence of
  `prd/migration/rust-evidence/m207-s03-evaluation-report.json` implies the presence of a
  validated human reference, and a report without one is `REPORT_WITHOUT_HUMAN_DATA` while a
  human reference without a report is `REPORT_MISSING_WITH_HUMAN_DATA`.

## 5. Strata: provider and Work-family

Strata are published, not selected:

- **provider strata** are closed at `consultant | garant | unknown`. Provider attribution uses
  **declared roots only**; an unattributable case stays `unknown` and is never re-derived from
  digits in a file name or a substring of the full path (`PROVIDER_MISATTRIBUTED`,
  `METADATA_REDERIVED`). Case metadata is published **as-is**: the frozen
  `metadata_source = year = document_type = unknown` of all 40 cases stays `unknown`; S01
  refused to re-derive it and S03 must not re-introduce that defect (RC28-F02).
- **Work-family strata** carry `family_scope ∈ {holdout, dev}` and the frozen `draw_stratum`.
  The holdout is **family-granular**: a Work-family is wholly in the holdout or wholly in
  dev, never split, and the holdout is frozen by seed before any measurement. The Work-family
  cap of 4 and the 180-fragment seed are unchanged (`WORK_FAMILY_DOMINANCE`,
  `SEED_ENLARGED`).
- **every stratum appears in the report.** A stratum with zero units is published
  `not-measured` (`value: null`) and is **not** dropped: `PROVIDER_STRATUM_DROPPED` is the
  defect. The `garant` provider stratum has zero available units today; that is the expected
  honest `not-measured`, not an empty stratum to be deleted.
- quota justification is explicit: `quota <= availability` per stratum
  (`PROVIDER_QUOTA_UNJUSTIFIED` otherwise), and `availability` is the number of frozen cases
  the declared root actually attributes.
- the holdout slice is the demo slice; the dev slice is published separately, marked
  development-only and carries the `DEVELOPMENT_SLICE_NOT_EVALUATION` non-claim so a dev
  number is never read as independent evidence.

The vocabulary is frozen here; the concrete declared provider roots and the concrete
holdout/dev split are declared by the T02 manifest and pinned there. S03 does not bake a
provider counter into the frozen contract: with two declared roots the three
`law-source/consultant/**` cases are honestly `unknown`, and with a third declared root they
are `consultant`. Either way the stratum table must show the real distribution and no stratum
may be dropped or back-filled.

## 6. Typed publication and the human reference

`measurement_status ∈ {not-measured, proxy-measured, independent-measured}` and only
`independent-measured` may publish a value:

`independent-measured` requires **all** of:

1. two validated human submissions with `provenance = human-reviewed`;
2. `coder_pass` exactly `1` and `2`, with **distinct** `coder_id` (mutually blind, per S02);
3. a separate adjudication record whose entries resolve the frozen disagreements and whose
   `unresolved_count` is `0`;
4. the adjudication pinned to the frozen `pre_adjudication_agreement_sha256`, which must
   still match the sha256 of the frozen agreement report (`FROZEN_SOURCE_DRIFT` otherwise);
5. `is_gold = false`, `promotion = none`, `threshold = null`,
   `classification = not-authorized`, `human_acceptance = null`.

Anything less is `HUMAN_PILOT_ABSENT` at exit 3 with **no** metric artifact created, or a
named refusal (`PROVENANCE_NOT_HUMAN`, `UNRESOLVED_NONZERO`, `PROXY_INPUT_REFUSED`,
`CODER_PASS_INVALID`, `ONE_CODER_ONLY`). A partially validated pair is a refusal, not a low
rate.

The residual is organizational and is stated rather than papered over: `provenance` is a
recorded string, so a determined operator can hand-write two internally consistent envelopes.
S03's guarantee is narrower and exact — an empty store, a proxy artifact, a non-human
provenance or an unresolved adjudication cannot publish a measurement. The human gate stays
human.

## 7. Forbidden claims: gold, promotion, threshold, classification

Rejected by name, at any nesting depth, in any S03 artifact:

| Claim | Diagnostic |
|---|---|
| `is_gold` anything other than `false` | `IS_GOLD_CLAIM` |
| `human_acceptance` anything other than `null` (the reference promoted to accepted truth) | `GOLD_CLAIM` |
| `promotion` anything other than `none` | `PROMOTION_CLAIM` |
| `threshold` anything other than `null` | `THRESHOLD_REQUESTED` |
| `classification` anything other than `not-authorized` | `CLASSIFICATION_REQUESTED` |
| `authority` / `suggestion_status` outside `none` / `none-provided` | `AUTHORITY_CLAIM` |
| `legal_claim` / `n2_claim` anything other than `forbidden` | `AUTHORITY_CLAIM` |
| `model_invoked` anything other than `false` | `MODEL_INVOKED` |
| a predicted-answer key (`label`, `expected`, `answer`, `prediction`, `gold`, `capture`) or a rule-seed key | `LEAK_FORBIDDEN_KEY` |

`is_gold` is admitted **only** as a guard pinned `false`: declaring the guard is how the
contract forbids the claim, and declaring it `true` is the claim itself.

Because `expected` is a forbidden predicted-answer token in the frozen S01/S02 scanners, the
leakage report names its expectation field `required` (with `observed` and `status`): M207
keeps **one** leak scanner for all slices instead of two conventions.

## 8. Fail-closed diagnostics

Every S03 tool is fail-closed: a non-zero exit with a named, machine-distinguishable
diagnostic from the closed vocabulary in `$.diagnostics`, never a silent success and never a
fabricated artifact. The diagnostic table is closed: a tool that speaks a name outside it is
`DIAGNOSTIC_TABLE_DRIFT`.

The honesty core of this slice:

- with no human reference, the evaluation chain exits non-zero with `HUMAN_PILOT_ABSENT` and
  creates **no** evaluation report — "no denominator" is never reported as success and never
  as `1.0`;
- the machinery chain prints `M207_S03_MACHINERY_OK` when the offline contour is green and
  the human pilot is absent, and it never prints `M207_S03_VERIFY_OK`;
- `M207_S03_VERIFY_OK` is reachable only with the full human reference of §6, and the
  verifier's `guard_output` makes that marker unprintable from any verifier surface;
- a partial artifact without its validated stage is a defect (exit 1), not a blockage; an
  absent human reference is a blockage (exit 3), not a defect.

## 9. Lifecycle markers and non-claims

Every derived S03 artifact carries the lifecycle markers:

| Marker | Value | Meaning |
|---|---|---|
| `human_adoption` | `pending` | no human has adopted the pilot |
| `runtime_stop_active` | `true` | runtime remains stopped |
| `selected_d388_gates` | `none` | no D388 gate is selected by this work |
| `requirement_status_effect` | `unchanged` | R071/R077/R081/R064 stay as they are |
| `review_disposition_effect` | `unchanged` | review dispositions are untouched |

Non-claims, enforced as an exact frozen list by the executable gate:

1. **not gold** — no S03 artifact, aspect value or stratum rate is a gold label;
2. **not a promotion** — classification stays `not-authorized`, promotion stays `none`,
   threshold stays `null`;
3. **not a threshold** — no rate threshold, pass/fail cut-off or accept/reject decision is
   introduced;
4. **not a classification** — no classifier is fitted, no gate is selected and no D388 gate
   is scored;
5. **not system quality** — the measured agreement is rater-vs-resolved-reference;
6. **not a model evaluation** — no model is invoked anywhere in M207;
7. **not human acceptance** — no resolved reference becomes human-accepted truth;
8. **not a second measurement convention** — `npa-quality-receipts/v1`, `npa-c5-*` and
   `npa-lawref-seed/v1` inputs are refused;
9. **not official-publication provenance** — R070 stays open;
10. **not amendment provenance** — R070 stays open;
11. **not LawRef / act-tree / clause segmentation**;
12. **not the N2-gate acceptance decision**;
13. **not legal interpretation**;
14. **not a product surface** — S03 stays an offline Python harness under `scripts/` and no
    `crates/**` file reads it (D466/D487);
15. **not an evaluation of the dev slice** — development-slice numbers are development-only.

## 10. Boundaries

S02 owns the two human passes, the kit, the submission contract, the agreement computation
and the separate adjudication record. S03 owns the derived per-aspect rates and the provider
and Work-family strata. S04 owns a fresh full corpus-scale run. S03 never edits the codebook,
the S01 schemas, the S01 case manifest, the S02 protocol or the S02 schemas; a byte of drift
in any of them is `FROZEN_SOURCE_DRIFT` and stops the gate.

Schema ids are disjoint by construction: the five S03 schemas are `m207-s03-*`, and no S03
schema id may collide with an S01 (`m207-s01-*`), S02 (`m207-s02-*`), `npa-c5-*` or
`npa-quality-*` id — otherwise S03 would become a second measurement convention. The single
deliberate exception is `submission_schema_id`, which *is* the S01 coding-submission form
reused verbatim and is therefore not an S03-owned id.

## Machine-readable protocol contract

The block below is the machine-readable half of this protocol. The executable gate
(`scripts/m207_s03_schemas.py`) parses it, compares it field-by-field with
`prd/annotation/m207-s03-schemas.json`, cross-checks both against the frozen S01 codebook /
S01 schemas / S01 case manifest / S02 protocol / S02 schemas / M199 §5, and fails closed on
any drift. Edit this block and the schema together, or not at all.

```json
{
  "protocol_id": "m207-s03-eval-protocol/v1",
  "schema_id": "m207-s03-eval-schemas/v1",
  "codebook": "prd/annotation/m207-s01-codebook.md",
  "submission_schema_id": "m207-s01-coding-submission/v1",
  "submission_schema_reused_verbatim": true,
  "slot_space_source": "prd/migration/rust-evidence/m199-s01-annotation-protocol.md#5",
  "slot_space": {
    "closed_keys": [
      "marker_chain",
      "hier_nums",
      "date",
      "doc_no",
      "law_code",
      "anaphora",
      "range",
      "quoted_enum"
    ],
    "binary_outcome": {
      "key": "not_a_reference",
      "type": "boolean"
    },
    "closed_key_count": 9
  },
  "input_axes": [
    "reference_decision",
    "span_exact",
    "abstention",
    "slot_marker_chain",
    "slot_hier_nums",
    "slot_date",
    "slot_doc_no",
    "slot_law_code",
    "slot_anaphora",
    "slot_range",
    "slot_quoted_enum"
  ],
  "aspect_table": [
    {
      "aspect": "span",
      "source_axes": [
        "span_exact"
      ],
      "derived_from": "m207-s02 agreement axis span_exact; the per-pass coding is compared with the resolved reference under the frozen M199 section-8 rule (start, end and decision all equal)",
      "numerator": "units where the pass coding equals the resolved reference coding on span_exact",
      "denominator": "units in which both passes committed a coding, the resolved reference is a reference, and the resolved reference names one of the two committed spans",
      "denominator_units": "committed_coding_with_resolved_reference_span",
      "units_excluded_reasons": [
        "abstained",
        "undisputed_missing",
        "unresolved",
        "not_derivable"
      ],
      "value_kind": "rate",
      "aggregate": false
    },
    {
      "aspect": "slot",
      "source_axes": [
        "slot_marker_chain",
        "slot_hier_nums",
        "slot_date",
        "slot_doc_no",
        "slot_law_code",
        "slot_anaphora",
        "slot_range",
        "slot_quoted_enum"
      ],
      "derived_from": "the eight m207-s02 slot_<key> agreement axes; per-pass slot presence is compared with the resolved reference slot presence for each closed slot key",
      "numerator": "per slot key, units where the pass slot presence equals the resolved reference presence; the published aspect value is the aggregate over the eight closed slot keys",
      "denominator": "per slot key, units in which both passes committed a coding and the resolved reference is a reference; the aggregate denominator is the sum over the eight closed slot keys",
      "denominator_units": "committed_coding_with_resolved_reference",
      "units_excluded_reasons": [
        "abstained",
        "undisputed_missing",
        "unresolved",
        "not_derivable"
      ],
      "value_kind": "rate",
      "aggregate": true
    },
    {
      "aspect": "scope",
      "source_axes": [
        "slot_hier_nums",
        "slot_doc_no",
        "slot_law_code",
        "slot_marker_chain"
      ],
      "derived_from": "D490 derived rule over the frozen slots (there is no ninth slot and no schema-version bump): a reference carrying its own target through hier_nums, doc_no or law_code is scope_local; a reference whose target arrives only through a non-empty marker_chain is scope_inherited; otherwise the unit is excluded",
      "numerator": "units where the pass-derived scope label equals the resolved-reference-derived scope label",
      "denominator": "units in which both passes committed a coding, the resolved reference is a reference, and the resolved reference derives a scope label (scope_local or scope_inherited)",
      "denominator_units": "resolved_reference_with_derived_scope",
      "units_excluded_reasons": [
        "abstained",
        "undisputed_missing",
        "unresolved",
        "not_derivable"
      ],
      "value_kind": "rate",
      "aggregate": false
    },
    {
      "aspect": "binding",
      "source_axes": [
        "slot_anaphora",
        "slot_range"
      ],
      "derived_from": "D490 derived rule over the frozen slots: anaphora and range both absent with a present target is binding_explicit; a non-empty anaphora or range is binding_unresolved; otherwise the unit is excluded",
      "numerator": "units where the pass-derived binding label equals the resolved-reference-derived binding label",
      "denominator": "units in which both passes committed a coding, the resolved reference is a reference, and the resolved reference derives a binding label (binding_explicit or binding_unresolved)",
      "denominator_units": "resolved_reference_with_derived_binding",
      "units_excluded_reasons": [
        "abstained",
        "undisputed_missing",
        "unresolved",
        "not_derivable"
      ],
      "value_kind": "rate",
      "aggregate": false
    },
    {
      "aspect": "abstention",
      "source_axes": [
        "abstention"
      ],
      "derived_from": "m207-s02 agreement axis abstention; abstention is a separate coder outcome that is never merged with not_a_reference (ABSTENTION_COLLAPSE)",
      "numerator": "units where the pass abstention value equals the resolved reference abstention value",
      "denominator": "all units in which both passes committed a coding, including units whose resolved decision is not_a_reference; abstention keeps its own denominator and is never folded into the other five aspects",
      "denominator_units": "committed_coding_pair",
      "units_excluded_reasons": [
        "undisputed_missing",
        "unresolved",
        "not_derivable"
      ],
      "value_kind": "rate",
      "aggregate": false
    },
    {
      "aspect": "false_authority",
      "source_axes": [
        "reference_decision"
      ],
      "derived_from": "derived from the m207-s02 reference_decision axis: a unit where the pass asserted reference while the resolved reference is not_a_reference, that is claimed authority with no resolved support",
      "numerator": "units where the pass asserts reference while the resolved reference is not_a_reference",
      "denominator": "units in which both passes committed a coding and the resolved reference is not_a_reference, the population in which false authority can occur",
      "denominator_units": "resolved_reference_is_not_a_reference",
      "units_excluded_reasons": [
        "abstained",
        "undisputed_missing",
        "unresolved",
        "not_derivable"
      ],
      "value_kind": "rate",
      "aggregate": false
    }
  ],
  "denominator_rule": {
    "publication_shape": [
      "measured",
      "denominator",
      "value",
      "measurement_status"
    ],
    "zero_denominator_value": null,
    "zero_denominator_measurement_status": "not-measured",
    "zero_denominator_diagnostic": "RATE_UNDEFINED",
    "imputed_zero_value_forbidden": true,
    "perfect_value": 1.0,
    "perfect_value_requires_full_coverage": true,
    "perfect_value_unbacked_diagnostic": "COMPUTED_PERFECT_UNBACKED",
    "excluded_unit_reason_values": [
      "abstained",
      "undisputed_missing",
      "unresolved",
      "not_derivable"
    ],
    "excluded_unit_effect": "neither increases nor decreases a measured value"
  },
  "strata_rule": {
    "provider_strata": [
      "consultant",
      "garant",
      "unknown"
    ],
    "provider_basis": "declared provider roots only; an undeclared or unattributable case stays unknown and is never re-derived from a path or a file name",
    "unknown_provider_value": "unknown",
    "family_scope_values": [
      "holdout",
      "dev"
    ],
    "draw_stratum_values_source": "frozen m207-s01-pilot-cases/v1 draw_stratum",
    "holdout_granularity": "work_family",
    "quota_rule": "quota <= availability",
    "every_stratum_present": true,
    "empty_stratum_publication": {
      "value": null,
      "measurement_status": "not-measured"
    },
    "stratum_drop_forbidden": true
  },
  "publication_contract": {
    "measurement_status_values": [
      "not-measured",
      "proxy-measured",
      "independent-measured"
    ],
    "admissible_measurement_status": "independent-measured",
    "independent_measured_requires": [
      "two_validated_human_submissions",
      "provenance_human-reviewed",
      "coder_pass_1_and_2",
      "distinct_coder_id",
      "separate_adjudication_record",
      "unresolved_count_zero",
      "pre_adjudication_agreement_sha256_pinned"
    ],
    "refused_input_schema_ids": [
      "npa-quality-receipts/v1",
      "npa-lawref-seed/v1",
      "law-nexus-npa-corpus-manifest/v1"
    ],
    "refused_input_schema_prefixes": [
      "npa-c5-"
    ],
    "refused_input_provenance_values": [
      "rule-seed"
    ],
    "refused_input_paths": [
      "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json"
    ],
    "refusal_diagnostic": "PROXY_INPUT_REFUSED",
    "framing": "rater-vs-resolved-reference",
    "framing_is_not": [
      "system-quality",
      "gold"
    ]
  },
  "input_admissibility": {
    "case_manifest_schema_id": "m207-s01-pilot-cases/v1",
    "submission_schema_id": "m207-s01-coding-submission/v1",
    "s02_derived_schema_ids": [
      "m207-s02-agreement-report/v1",
      "m207-s02-disagreement-inventory/v1",
      "m207-s02-adjudication-record/v1",
      "m207-s02-pilot-receipt/v1"
    ],
    "human_store_paths": [
      "prd/annotation/m207-s02-submissions",
      "prd/annotation/m207-s02-adjudications"
    ],
    "stores_are_read_only": true,
    "new_slot_keys_allowed": false
  },
  "output_contract": {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": false,
    "classification": "not-authorized",
    "promotion": "none",
    "threshold": null,
    "is_gold": false,
    "human_acceptance": null,
    "legal_claim": "forbidden",
    "n2_claim": "forbidden"
  },
  "forbidden_keys": [
    "label",
    "expected",
    "answer",
    "prediction",
    "gold",
    "capture"
  ],
  "forbidden_seed_keys": [
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots"
  ],
  "required_sections": [
    "1. Scope, framing and ownership",
    "2. Frozen inputs and admissibility",
    "3. Aspect table: six separately measured aspects",
    "4. Denominator rule: no value without a denominator",
    "5. Strata: provider and Work-family",
    "6. Typed publication and the human reference",
    "7. Forbidden claims: gold, promotion, threshold, classification",
    "8. Fail-closed diagnostics",
    "9. Lifecycle markers and non-claims",
    "10. Boundaries",
    "Machine-readable protocol contract"
  ],
  "non_claims": [
    "not gold: no S03 artifact, aspect value or stratum rate is a gold label",
    "not a promotion: classification stays not-authorized, promotion stays none and threshold stays null",
    "not a threshold: no rate threshold, pass/fail cut-off or accept/reject decision is introduced",
    "not a classification: no classifier is fitted, no gate is selected and no D388 gate is scored",
    "not system quality: the measured agreement is rater-vs-resolved-reference, never system quality",
    "not a model evaluation: no model is invoked anywhere in M207 and model_invoked stays false",
    "not human acceptance: no resolved reference becomes human-accepted truth (human_acceptance stays null)",
    "not a second measurement convention: npa-quality-receipts/v1, npa-c5-* and npa-lawref-seed/v1 inputs are refused",
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not a product surface: S03 stays an offline Python harness under scripts/ and no crates/** file reads it",
    "not an evaluation of the dev slice: development-slice numbers are development-only, never independent evidence"
  ],
  "lifecycle": {
    "human_adoption": "pending",
    "runtime_stop_active": true,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged"
  }
}
```
