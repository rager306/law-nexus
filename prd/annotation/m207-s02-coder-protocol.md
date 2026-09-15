# M207 S02 — frozen two-pass coding and adjudication protocol (`m207-s02-coder-protocol/v1`)

**Status:** `[bounded]` annotation/evidence contract, frozen **before** any human coding.
**Milestone:** M207-b2i96m / S02 / T01
**Frozen inputs:** `prd/annotation/m207-s01-codebook.md` (`m207-s01-codebook/v1`, sha256-pinned),
`prd/annotation/m207-s01-schemas.json` (`m207-s01-annotation-schemas/v1`, sha256-pinned),
`prd/migration/rust-evidence/m207-s01-pilot-cases.json` (40 frozen cases, sha256-pinned),
M199 protocol §5/§7/§8/§9/§10 (`m199-s01-annotation-protocol.md`, sha256-pinned).
**Submission form:** `m207-s01-coding-submission/v1` is reused **verbatim** (D475).
No ninth slot, no new submission key, no `schema_version` bump.
**Closed schema file:** `prd/annotation/m207-s02-schemas.json` (`m207-s02-annotation-schemas/v1`).
**Executable gate:** `uv run python scripts/m207_s02_schemas.py check`
(marker `M207_S02_SCHEMAS_OK`); negative proof: `uv run python scripts/m207_s02_schemas.py selftest`.

This document is the frozen instruction sheet for the S02 unit plus its
machine-readable contract. It freezes *who may code*, *in what order*, *with what
kit*, *how agreement is computed*, and *how adjudication is recorded separately*.
It contains **no annotations**: S02 fabricates no coding, no span, no agreement
number and no adjudicated value. Two human passes and a human adjudicator are the
only sources of S02 data; until they exist the slice is blocked, not partially
successful.

## 1. Scope and frozen inputs

S02 proves the offline, fail-closed machinery that accepts two independent human
codings of the 40 frozen S01 cases, computes agreement **before** adjudication,
and records adjudication **separately**. It does not measure per-aspect rates
(S03), does not promote gold, does not select a D388 gate and does not touch the
product runtime (D466).

Frozen surfaces, each sha256-pinned by the executable gate:

| Surface | Path | Role |
|---|---|---|
| S01 codebook | `prd/annotation/m207-s01-codebook.md` | unit of coding, closed slot space, abstention, as-written discipline |
| S01 schemas | `prd/annotation/m207-s01-schemas.json` | `m207-s01-coding-submission/v1` reused verbatim |
| S01 case manifest | `prd/migration/rust-evidence/m207-s01-pilot-cases.json` | the 40 cases, `work_family`, `byte_len` |
| M199 protocol | `prd/migration/rust-evidence/m199-s01-annotation-protocol.md` | §5 slot space, §7 independence, §8 span-exact rule, §9 α, §10 provenance |

Any drift in a frozen surface is `FROZEN_SOURCE_DRIFT` and stops the gate. S02 may
not edit the codebook, the S01 schemas, the case manifest or the M199 protocol.

## 2. Two independent passes

Two human passes code the same 40 cases independently:

- `coder_pass` is exactly `1` or `2`; any other value is `CODER_PASS_INVALID`.
- The passes are **mutually blind**: pass 2 never reads, imports, diffs or is shown
  any pass-1 artifact, and vice versa. Any cross-pass artifact (a shared
  worksheet, a merged file, a diff, a "review" of the other pass) is forbidden.
- Each pass is a **separate** submission file under the submission store, carrying
  its own `submission_id`, its own pseudonymous `coder_id` and its own
  `coder_pass`, and it satisfies `m207-s01-coding-submission/v1` exactly.
- Both passes must be committed **before** agreement is computed. Agreement over a
  partially committed pair is `ONE_CODER_ONLY`, not a low α.
- `provenance` is exactly `human-reviewed`. Rule-seed output, model output, a
  script and the same operator filling both envelopes under two pseudonyms are
  all outside what this machine can distinguish; the machine enforces the
  recorded provenance and the lifecycle markers, and the residual collusion risk
  is the accepted HARD HUMAN GATE risk (D474), not a software guarantee.
- The kit is the only authorized way a coder receives a case (see §6). A coder
  never sees `work_family`, never sees slot values, never sees a predicted
  decision and never sees the other pass.

Coder submissions are the only untrusted input of S02, and the machine only reads
them: no S02 script writes, repairs or normalizes a submission.

## 3. Order of operations: agreement before adjudication

The S02 order is fixed and machine-checked:

1. `pass_1` committed (submission file under the submission store);
2. `pass_2` committed (submission file under the submission store);
3. agreement computed over the two validated submissions and **frozen**: the
   agreement report carries the sha256 of both submissions and the
   `pre_adjudication: true` flag, and the disagreement inventory is written as a
   separate artifact;
4. adjudication recorded as a **separate** artifact, pinned to the frozen
   pre-adjudication agreement sha256.

Consequences the machine enforces:

- agreement can never be recomputed *after* adjudication and passed off as
  independent: the report is pinned to the submission digests, and adjudication
  pins the report digest, so any later mutation of the agreement report is
  detected as pin drift;
- adjudication never rewrites the pre-adjudication scores; it is append-only and
  supersession is expressed by an explicit `supersedes` reference to an existing
  adjudication id (`SUPERSEDES_UNKNOWN` otherwise);
- the adjudicated set is never gold (`is_gold` is pinned `false`; claiming
  otherwise is `GOLD_CLAIM` / `IS_GOLD_CLAIM`).

## 4. Span-exact rule

The M199 §8 span-exact rule is adopted unchanged. Two codings match on the
`span_exact` axis iff **`(start, end, decision)` are all equal**:

- byte-exact half-open `[start, end)` boundaries on the frozen decoded fragment;
- start and end are UTF-8 code-point boundaries (`SPAN_NOT_UTF8_BOUNDARY`);
- `0 <= start < end <= byte_len` (`SPAN_BEYOND_EOF`), where `byte_len` is the
  frozen fragment byte length pinned by the case;
- the same reference-vs-not decision: `not_a_reference` matches only
  `not_a_reference`;
- partial overlap, shifted boundaries and same-position/different-slot codings are
  disagreements, never matches.

`SPAN_NOT_ORIGIN` rejects a span outside the offered coding window. Agreement on
the `span_exact` axis therefore compares whole codings, not just offsets.

## 5. Abstention is a separate coder outcome

`abstention` is a coder-level outcome, disjoint from `not_a_reference` (codebook
§4):

- closed vocabulary: `not-abstained`, `ambiguous`, `insufficient-context`;
- it may never reuse a value from the decision vocabulary, and it is never merged
  with `not_a_reference`; any such merge is `ABSTENTION_COLLAPSE`;
- abstention is measured as its **own** agreement axis, with its own denominators
  (`units_excluded`, `abstained_units`), because RC28-F15 requires the abstention
  rate to stay measurable and separable from "the source has no reference";
- a unit where either pass abstained is excluded from the affected axis numerator
  and denominator and is reported explicitly — never silently dropped and never
  counted as agreement.

## 6. Coder kit and the frozen submission form

The coder kit (`m207-s02-coder-kit/v1`) is a deterministic projection of the
frozen S01 case manifest and is the only authorized case-delivery form:

- a kit case carries exactly: `case_id`, `fragment_id`, `fragment_path`,
  `fragment_sha256`, `byte_len`, `span_offered_for_coding`,
  `alternative_classes`, `abstention_available`;
- a kit case carries **no** `fragment_text` (decoded legal text is never
  duplicated into a tracked artifact — codebook §1, D478), **no** slot names,
  **no** slot values and **no** `work_family` (family is joined from the frozen
  case manifest by `case_id`, D480). Violations are `KIT_TEXT_INLINED`;
- the kit pins the source binding: the fragment file exists, its byte length
  equals the case `byte_len`, and its sha256 is recorded in the kit
  (`FRAGMENT_PIN_DRIFT` on mismatch);
- the two kits differ **only** in the header fields `coder_pass` and
  `submission_id`; regenerating either kit must be byte-identical
  (`KIT_CROSS_PASS_INVARIANT`);
- the kit embeds an empty `submission_template` whose `schema` is
  `m207-s01-coding-submission/v1`; a submission that is still the untouched
  template is `UNFILLED_SUBMISSION`;
- `alternative_classes` is the closed decision space of codebook §3 — an
  enumeration of poles, never a predicted answer.

The submission form itself is `m207-s01-coding-submission/v1`, reused verbatim
(D475). S02 declares `submission_schema_reused_verbatim: true` and adds no key to
it; redefining the form under an S02 id is `SUBMISSION_SCHEMA_DRIFT`.

## 7. Agreement computation and honest denominators

Agreement is computed, never asserted:

- metric: Krippendorff α (nominal, exactly two raters; Artstein & Poesio 2008) per
  axis, plus observed agreement per axis;
- axes: `reference_decision`, `span_exact`, `abstention`, and `slot_<name>` for
  each of the eight closed slots (slot presence: `slot_present` / `slot_absent`);
- honest denominators are printed, not implied: `units_total = 40`, `units_used`
  (both passes gave a non-abstained value on that axis), `units_excluded`,
  `abstained_units`. A denominator mismatch is `DENOMINATOR_MISMATCH`;
- when `units_used < 2` or expected disagreement `De = 0`, α is **null** with
  `AGREEMENT_UNDEFINED` and `measurement_status = undefined`. A missing or
  degenerate measurement never becomes `1.0`; `PERFECT_AGREEMENT_UNCOMPUTED`
  catches an α of 1 that is not backed by matching codings;
- `alpha = 1.0` is legal **only** as a computed result over matching units;
- the report is `pre_adjudication: true` with `classification: not-authorized`,
  `promotion: none`, `threshold: null`: no threshold, no pass/fail, no promotion
  and no per-aspect rate (that is S03) may appear. Attempts are
  `THRESHOLD_REQUESTED`, `CLASSIFICATION_REQUESTED`, `PROMOTION_CLAIM`;
- `work_family` enters only by join from the frozen case manifest, keeps the
  ceiling of 4 cases per Work family, and a violation is `WORK_FAMILY_DOMINANCE`.

The disagreement inventory is a **separate** artifact written before adjudication:
one entry per disagreeing `case_id` × `axis`, carrying the two observed values and
the joined `work_family`.

## 8. Adjudication is separate and never gold

Adjudication is a distinct human activity with a distinct input format
(`m207-s02-adjudication-input/v1`) and a distinct record
(`m207-s02-adjudication-record/v1`):

- an adjudication entry resolves exactly one `(case_id, axis)` that the
  disagreement inventory lists; anything else is
  `ADJUDICATION_NOT_A_DISAGREEMENT`;
- `resolution` must come from the closed per-axis resolution space derived from
  the codebook decision poles (`RESOLUTION_OUT_OF_SPACE` for anything else). On
  the `span_exact` axis the resolution names one of the two already-committed
  coder spans (`span_pass_1` / `span_pass_2`); the adjudicator never mints a third
  span and never invents a new decision value;
- `provenance` is exactly `human-reviewed`; a machine or model adjudication is
  `ADJUDICATOR_PROVENANCE_NOT_HUMAN`;
- `is_gold` is pinned `false` and `promotion` is pinned `none`; the record is
  `append_only: true`, supersession is an explicit `supersedes` reference
  (`SUPERSEDES_UNKNOWN` if the target id does not exist);
- disagreements that no human resolved stay visible and are counted
  (`unresolved_count`; a nonzero count is reported, not hidden as success);
- the record pins `pre_adjudication_agreement_sha256`, so an agreement report
  mutated after adjudication is detectable;
- the pilot receipt (`m207-s02-pilot-receipt/v1`) states `human_pilot_performed`,
  `coder_count`, `adjudicator_count`, `case_count`, both digests, `promotion: none`
  and the lifecycle markers.

`rationale` is free text and therefore bounded by this contract: at most 280
characters, single line, no decoded fragment text and no personal data beyond the
pseudonymous ids. A rationale that breaks the bound is `RATIONALE_NOT_BOUNDED`.
Bounding the field is the schema-level mitigation for the "free text channel"
residual of the S02 threat surface.

## 9. Store paths and pseudonyms

Store locations are fixed (D480):

| Store | Path | Written by |
|---|---|---|
| Human submissions | `prd/annotation/m207-s02-submissions` | humans only |
| Human adjudications | `prd/annotation/m207-s02-adjudications` | humans only |
| Derived evidence | `prd/migration/rust-evidence` | the S02 harness |

`--store` is not free-form: the store prefix is locked to `prd/annotation/` and
any other path — traversal, backslash, absolute path, symlink escape or an
unrelated relative directory — is `UNSAFE_PATH`. Both stores are read-only inputs
to the harness; the harness never creates, edits or deletes a submission or an
adjudication file.

`coder_id` and `adjudicator_id` are pseudonyms: no real name, no e-mail, no
institutional identifier, no PII. A test fixture or synthetic submission found in
a product store is `TEST_FIXTURE_IN_STORE`, and a non-human provenance is
`PROVENANCE_NOT_HUMAN`.

## 10. Fail-closed diagnostics

Every S02 tool is fail-closed: a non-zero exit with a named, machine-distinguishable
diagnostic, never a silent success and never a fabricated artifact. The S02
diagnostic vocabulary is declared in the schema (`$.diagnostics`) and is closed.

The honesty core of this slice:

- with no human submissions, `run` modes exit non-zero with `HUMAN_PILOT_ABSENT`
  and create **no** submission, agreement or adjudication artifact — "zero
  codings" is never reported as success;
- the machinery chain prints `M207_S02_MACHINERY_OK` when the offline contour is
  green **and** `human_pilot_performed` is `false`, and it never prints
  `M207_S02_VERIFY_OK`;
- `M207_S02_VERIFY_OK` requires two validated independent human submissions
  (`provenance=human-reviewed`, `coder_pass` 1 and 2, distinct `coder_id`),
  agreement computed and frozen before adjudication, and a separately recorded
  adjudication with a human adjudicator. Without them the slice stays blocked
  (`MACHINERY_GREEN_HUMAN_ABSENT`), which is a blocker, not a partial success.

## 11. Lifecycle markers, non-claims and boundaries

Every derived S02 artifact carries the lifecycle markers:

| Marker | Value | Meaning |
|---|---|---|
| `human_adoption` | `pending` | no human has adopted the pilot |
| `runtime_stop_active` | `true` | runtime remains stopped |
| `selected_d388_gates` | `none` | no D388 gate is selected by this work |
| `requirement_status_effect` | `unchanged` | R071/R077/R081/R064 stay as they are |
| `review_disposition_effect` | `unchanged` | review dispositions are untouched |

Non-claims, enforced as required substrings by the executable gate:

1. **not a human pilot** — S02 fabricates no coding and reports no agreement
   without two human submissions;
2. **not gold** — no S02 artifact, coded span or adjudicated resolution is a gold
   label;
3. **not a promotion** — classification stays `not-authorized`, promotion stays
   `none`;
4. **not a threshold** — no agreement threshold, pass/fail or accept/reject
   decision is introduced;
5. **not per-aspect rates** — span, slot, scope, binding and false-authority rates
   belong to S03;
6. **not official-publication provenance** — R070 stays open;
7. **not amendment provenance** — R070 stays open;
8. **not LawRef / act-tree / clause segmentation**;
9. **not the N2-gate acceptance decision**;
10. **not legal interpretation**;
11. **not product authority** — no coder kit, submission or adjudication drives
    the product runtime (D466);
12. **not a second product surface** — S02 stays an offline Python harness under
    `scripts/`.

Boundaries: S02 owns the two human passes, the kit, the submission contract, the
agreement computation and the separate adjudication record. S03 owns per-aspect
error rates and provider / Work-family strata. S04 owns a fresh full C4 run. Any
S02 artifact that reports a per-aspect rate, a gate decision or a promoted label
is invalid by construction.

## Machine-readable protocol contract

The block below is the machine-readable half of this protocol. The executable gate
(`scripts/m207_s02_schemas.py`) parses it, compares it field-by-field with
`prd/annotation/m207-s02-schemas.json`, checks both against the frozen S01
codebook / S01 schemas / S01 case manifest / M199 protocol, and fails closed on
any drift. Edit this block and the schema together, or not at all.

```json
{
  "protocol_id": "m207-s02-coder-protocol/v1",
  "schema_id": "m207-s02-annotation-schemas/v1",
  "codebook": "prd/annotation/m207-s01-codebook.md",
  "submission_schema_id": "m207-s01-coding-submission/v1",
  "submission_schema_reused_verbatim": true,
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
  "agreement_axes": [
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
  "resolution_space": {
    "by_axis": {
      "reference_decision": ["reference", "not_a_reference"],
      "span_exact": ["span_pass_1", "span_pass_2"],
      "abstention": ["not-abstained", "ambiguous", "insufficient-context"],
      "slot_marker_chain": ["slot_present", "slot_absent"],
      "slot_hier_nums": ["slot_present", "slot_absent"],
      "slot_date": ["slot_present", "slot_absent"],
      "slot_doc_no": ["slot_present", "slot_absent"],
      "slot_law_code": ["slot_present", "slot_absent"],
      "slot_anaphora": ["slot_present", "slot_absent"],
      "slot_range": ["slot_present", "slot_absent"],
      "slot_quoted_enum": ["slot_present", "slot_absent"]
    },
    "derived_from": "m207-s01-codebook/v1 alternative_classes plus the codebook abstention vocabulary",
    "span_axis_rule": "span_pass_1 and span_pass_2 name one of the two already-committed coder spans; the adjudicator never mints a third span",
    "new_values_allowed": false
  },
  "output_contract": {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": false,
    "classification": "not-authorized",
    "promotion": "none",
    "threshold": null
  },
  "store_paths": {
    "submissions": "prd/annotation/m207-s02-submissions",
    "adjudications": "prd/annotation/m207-s02-adjudications",
    "evidence": "prd/migration/rust-evidence",
    "allowed_prefix": "prd/annotation/",
    "store_prefix_lock": true,
    "prefix_diagnostic": "UNSAFE_PATH"
  },
  "pass_protocol": {
    "coder_pass_values": [1, 2],
    "independence": "mutually-blind",
    "cross_pass_artifact_sharing": "forbidden",
    "both_passes_committed_before": "agreement",
    "adjudication_after": "agreement_freeze"
  },
  "order_of_operations": [
    "pass_1_committed",
    "pass_2_committed",
    "agreement_computed_and_frozen",
    "adjudication_recorded_separately"
  ],
  "rationale_max_chars": 280,
  "forbidden_keys": ["label", "expected", "answer", "prediction", "gold", "capture"],
  "forbidden_seed_keys": [
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots"
  ],
  "required_sections": [
    "1. Scope and frozen inputs",
    "2. Two independent passes",
    "3. Order of operations: agreement before adjudication",
    "4. Span-exact rule",
    "5. Abstention is a separate coder outcome",
    "6. Coder kit and the frozen submission form",
    "7. Agreement computation and honest denominators",
    "8. Adjudication is separate and never gold",
    "9. Store paths and pseudonyms",
    "10. Fail-closed diagnostics",
    "11. Lifecycle markers, non-claims and boundaries",
    "Machine-readable protocol contract"
  ],
  "diagnostics": [
    "HUMAN_PILOT_ABSENT",
    "MACHINERY_GREEN_HUMAN_ABSENT",
    "NO_ADJUDICATION_INPUT",
    "UNFILLED_SUBMISSION",
    "TEST_FIXTURE_IN_STORE",
    "PROVENANCE_NOT_HUMAN",
    "CODER_PASS_INVALID",
    "DUPLICATE_CODER_ID",
    "DUPLICATE_SUBMISSION_ID",
    "UNKNOWN_CASE_ID",
    "SUBMISSION_CONFLICT",
    "NINTH_SLOT",
    "SLOT_SET_DRIFT",
    "SUBMISSION_SCHEMA_DRIFT",
    "LEAK_FORBIDDEN_KEY",
    "ABSTENTION_COLLAPSE",
    "SPAN_BEYOND_EOF",
    "SPAN_NOT_UTF8_BOUNDARY",
    "SPAN_NOT_ORIGIN",
    "AUTHORITY_CLAIM",
    "MODEL_INVOKED",
    "AGREEMENT_UNDEFINED",
    "ONE_CODER_ONLY",
    "DENOMINATOR_MISMATCH",
    "PERFECT_AGREEMENT_UNCOMPUTED",
    "CLASSIFICATION_REQUESTED",
    "THRESHOLD_REQUESTED",
    "GOLD_CLAIM",
    "PROMOTION_CLAIM",
    "IS_GOLD_CLAIM",
    "ADJUDICATION_NOT_A_DISAGREEMENT",
    "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
    "RESOLUTION_OUT_OF_SPACE",
    "RESOLUTION_SPACE_DRIFT",
    "RATIONALE_NOT_BOUNDED",
    "SUPERSEDES_UNKNOWN",
    "UNRESOLVED_NONZERO",
    "WORK_FAMILY_DOMINANCE",
    "FRAGMENT_PIN_DRIFT",
    "KIT_TEXT_INLINED",
    "KIT_CROSS_PASS_INVARIANT",
    "FROZEN_SOURCE_DRIFT",
    "SEED_ENLARGED",
    "PROMPT_ISOLATION_VIOLATION",
    "UNSAFE_PATH",
    "BATTERY_STALE",
    "BATTERY_WALLCLOCK_FORBIDDEN",
    "MISSING_ARTIFACT",
    "MISSING_SCHEMA",
    "MISSING_SECTION",
    "MISSING_NON_CLAIM",
    "MISSING_LIFECYCLE_MARKER",
    "EMPTY_SUITE",
    "SUBCLI_FAILURE",
    "S01_REGRESSION_FAILED",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "VOCABULARY_DRIFT",
    "ALTERNATIVE_DRIFT",
    "CASE_COUNT_OUT_OF_RANGE",
    "DIAGNOSTIC_TABLE_DRIFT"
  ],
  "non_claims": [
    "not a human pilot: S02 fabricates no coding and reports no agreement without two human submissions",
    "not gold: no S02 artifact, coded span or adjudicated resolution is a gold label",
    "not a promotion: classification stays not-authorized and promotion stays none",
    "not a threshold: no agreement threshold, pass/fail or accept/reject decision is introduced",
    "not per-aspect rates: span, slot, scope, binding and false-authority rates belong to S03",
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not product authority: no coder kit, submission or adjudication drives the product runtime",
    "not a second product surface: S02 stays an offline Python harness under scripts/"
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
