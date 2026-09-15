# M207 S01 — frozen pilot annotation codebook (`m207-s01-codebook/v1`)

**Status:** `[bounded]` annotation/evidence contract, frozen **before** any coding.
**Milestone:** M207-b2i96m / S01 / T01
**Slot-space source:** M199 protocol §5 (`prd/migration/rust-evidence/m199-s01-annotation-protocol.md`).
The M199 slot space is reused verbatim: **no ninth slot is introduced** and the
M199 `schema_version` is **not** bumped (D467). Schema evolution means a new
`schema_version` under a new contract, never an extra key.
**Executable gate:** `uv run python scripts/m207_s01_schemas.py check`
(marker `M207_S01_SCHEMAS_OK`).
**Closed schema file:** `prd/annotation/m207-s01-schemas.json`
(`m207-s01-annotation-schemas/v1`, deliberately separate from
`npa-lawref-sample/v1`).

This document is an *instruction sheet for coders* plus a machine-readable
contract. It freezes the unit of coding, the closed slot space, the alternative
decision space, the abstention outcome, the submission format and the provenance
rule. It contains **no annotations**: S01 fabricates no coding, no span and no
label. Human coding, adjudication and agreement belong to S02; the per-aspect
error rates belong to S03.

## 1. Unit of coding

One coding unit = one **fragment-local span** over the **frozen decoded text** of
a single `npa-lawref` fragment.

- The text is the tracked fixture `crates/ln-decode/tests/fixtures/npa-lawref/
  <fragment>.txt`, i.e. `ConsultantWordMlBlockDecoder` decoded block text. A
  naive `w:t` join and Garant ODT are **not** valid sources (Consultant ≠ Garant).
- The span coordinate system is the fragment **file byte range**, half-open
  `[start, end)`, aligned to UTF-8 code-point boundaries. With `byte_len` equal
  to the fragment file's byte length, a valid span satisfies
  `0 <= start < end <= byte_len` and both endpoints are char boundaries.
- The lexeme is reconstructed by slicing the frozen bytes; the codebook never
  duplicates decoded text into a coding field.
- A fragment with no user reference is coded through the binary outcome, not by
  leaving the unit empty (see §2).
- The pilot never allocates new fragments: the draw stays strictly inside the
  frozen 180-fragment / 40-document M199 seed.

## 2. Closed slot space

The slot space is **closed**: exactly the M199 §5 slots plus the binary outcome.
No coder and no tool may invent a ninth slot. The executable gate compares this
list against the M199 protocol table itself, so drift is detected against the
frozen source, not against this prose.

| Slot | Type | Meaning as written |
|---|---|---|
| `marker_chain` | array of abbrev ids | marker chain as written (`st`, `stst`, `ch`, `p`, `pp`, `podp`, `abz`, `gl`, `razd`), in order |
| `hier_nums` | array of hier numbers | dotted hier numbers paired positionally with the chain |
| `date` | string or null | `dd.mm.yyyy` requisite when part of the reference |
| `doc_no` | string or null | document number token when part of the reference |
| `law_code` | string or null | lone `ФЗ` / `ФКЗ` law code when part of the reference |
| `anaphora` | string or null | **unresolved** anaphora marker, recorded and never resolved here |
| `range` | object or null | **unresolved** range endpoints as written, never expanded here |
| `quoted_enum` | string or null | quoted subpoint label when part of the reference |

Plus the binary outcome:

| Key | Type | Meaning |
|---|---|---|
| `not_a_reference` | boolean | the fragment contains no user reference at all |

That is `8 + 1 = 9` closed keys. A tenth key is a ninth slot and is rejected
fail-closed. `not_a_reference` is a **label about the source**, not a coder
failure state (see §4).

Fullword reference tails (`статьи`, `пункта`, `закона`, `года` adjacent to a hier
number or doc number) are coded through `marker_chain = []` plus the paired
`hier_nums` / `doc_no`; they are never retagged into the abbreviation chain.

## 3. Alternatives are a closed decision space

`alternative_classes` on a pilot case is the **closed set of codebook decisions**
the coder may choose from. It is an enumeration of decision poles, **not** a
predicted answer, not a candidate span and not a suggestion:

| Axis | Values |
|---|---|
| `reference_decision` | `reference`, `not_a_reference` |
| `slot_presence` | `slot_present`, `slot_absent` |
| `scope` | `scope_local`, `scope_inherited` |
| `binding` | `binding_explicit`, `binding_unresolved` |

The alternative classes carry no source-specific content. They are identical for
every case, so publishing them leaks nothing about a particular fragment. A case
manifest that ships *filled* slot values, seed spans or any candidate answer is
leakage and fails closed.

## 4. Abstention is a coder outcome

`abstention` is a **coder-level outcome**, separate from `not_a_reference`:

- `not-a-instance` of the reference decision is *not* the same as "the coder could
  not decide". `not_a_reference` states that the source contains no user
  reference; abstention states that the coder declines to commit.
- Closed abstention vocabulary: `not-abstained`, `ambiguous`,
  `insufficient-context`. It may never reuse a value from the decision
  vocabulary.
- Collapsing the two is a contract violation (`ABSTENTION_COLLAPSE`): it would
  make "coder could not decide" indistinguishable from "source has no reference"
  and would destroy the separate abstention measurement RC28-F15 requires.

Abstention is offered on every pilot case (`abstention_available: true`). S01
records that the outcome exists; it never fills it.

## 5. As-written discipline

Anaphora and range are recorded **as written** and are never resolved here:

- an anaphora (`настоящей`, `того же` class) is stored unresolved, never resolved
  to a canonical article/part/point anchor;
- a range is stored with its endpoints as written, never expanded into its
  members;
- no canonical `eId` path, no act-tree anchor and no clause segmentation is
  minted (D350 canonical half is out of scope).

Resolution and expansion are later work; the slots exist so that S02/S03 can
measure how much unresolved material the pilot actually contains.

## 6. Coder submission schema

The closed submission format (`m207-s01-coding-submission/v1`) carries, per coded
case, exactly: `case_id`, `decision`, `span` (`start`, `end`), `slots` (only the
eight closed slot keys), `abstention`. The submission header carries
`schema`, `schema_version`, `codebook`, `submission_id`, `coder_id`, `coder_pass`,
`provenance`, `cases`, `non_claims`, `lifecycle`.

- `provenance` is exactly `human-reviewed`; a machine pass may never be submitted
  in this format (rule-seed spans are distant supervision, never gold).
- `coder_id` is a pseudonym; no real identity, no PII enters a submission.
- Each of the two independent S02 passes is a separate submission file with its
  own `coder_pass`; a coder never sees the other pass before both are committed.
- S01 writes **no** submission file. The schema is frozen empty.

## 7. Lifecycle markers and non-claims

Every derived artifact of this pilot carries the lifecycle markers:

| Marker | Value | Meaning |
|---|---|---|
| `human_adoption` | `pending` | no human has adopted the pilot |
| `runtime_stop_active` | `true` | runtime remains stopped |
| `selected_d388_gates` | `none` | no D388 gate is selected by this work |
| `requirement_status_effect` | `unchanged` | R035/R070/R074 stay active |
| `review_disposition_effect` | `unchanged` | review dispositions are untouched |

Non-claims (the same required substrings are enforced inside
`m207-s01-schemas.json` by the executable gate):

1. **not official-publication provenance** — the pilot rests on a Consultant
   export draw, not a pravo.gov.ru record; **R070 stays open**;
2. **not amendment provenance** — spans do not establish which amendment
   introduced which text; **R070 stays open**;
3. **not LawRef / act-tree / clause segmentation** — no `LawRef` product type is
   minted and no clause tree is asserted;
4. **not the N2-gate acceptance decision** — a filled pilot is not an N2
   acceptance;
5. **not legal interpretation** — spans mark reference *shapes as written*, never
   legal meaning or applicability;
6. **not gold** — no artifact of S01 is a gold label; there are no labelled spans
   until independent human coding exists.

Additional honesty claims: S01 performs **no human pilot** and reports **no**
agreement; the pilot is not a second coder and not a product authority.

## 8. Boundary: S02 and S03 own adjudication, agreement and rates

- **S02 owns**: the two independent human coding passes, coder provenance,
  disagreement **adjudication**, and the **agreement** computation (α over the
  closed slots).
- **S03 owns**: the per-aspect error rates — span, slot, scope, binding,
  **abstention** and false-authority — together with provider and Work-family
  strata.
- **S01 owns**: this codebook, the closed schemas, the case draw, the prompt
  packet boundary and the fail-closed proof that none of them leaks a predicted
  answer.

Any S01 artifact that reports an α number, an adjudicated annotation or a
per-aspect rate is invalid by construction. A prompt or model output of any kind
is `AnnotationSuggestion` only: `authority: none`, `suggestion_status:
none-provided`, `model_invoked: false`. It cannot drive an FSM, create a legal
fact, supply human acceptance or count as a coder.

## Machine-readable codebook contract

The block below is the machine-readable half of this codebook. The executable
gate (`scripts/m207_s01_schemas.py`) parses it, compares it with
`prd/annotation/m207-s01-schemas.json` and with the frozen M199 protocol §5, and
fails closed on any drift. Edit this block and the schema together, or not at
all.

```json
{
  "codebook_id": "m207-s01-codebook/v1",
  "schema_id": "m207-s01-annotation-schemas/v1",
  "slot_space_source": "prd/migration/rust-evidence/m199-s01-annotation-protocol.md#5",
  "m199_schema_version_bump": false,
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
  "alternative_axes": [
    {
      "axis": "reference_decision",
      "values": ["reference", "not_a_reference"]
    },
    {
      "axis": "slot_presence",
      "values": ["slot_present", "slot_absent"]
    },
    {
      "axis": "scope",
      "values": ["scope_local", "scope_inherited"]
    },
    {
      "axis": "binding",
      "values": ["binding_explicit", "binding_unresolved"]
    }
  ],
  "abstention": {
    "values": ["not-abstained", "ambiguous", "insufficient-context"],
    "distinct_from": "not_a_reference",
    "owned_by": "coder"
  },
  "case_count_range": [20, 40],
  "work_family_cap": 4,
  "output_contract": {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": false
  },
  "boundaries": {
    "human_coding": "S02",
    "adjudication": "S02",
    "agreement": "S02",
    "per_aspect_rates": "S03"
  },
  "forbidden_keys": ["label", "expected", "answer", "prediction", "gold", "capture"],
  "forbidden_seed_keys": [
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots"
  ],
  "required_sections": [
    "1. Unit of coding",
    "2. Closed slot space",
    "3. Alternatives are a closed decision space",
    "4. Abstention is a coder outcome",
    "5. As-written discipline",
    "6. Coder submission schema",
    "7. Lifecycle markers and non-claims",
    "8. Boundary: S02 and S03 own adjudication, agreement and rates",
    "Machine-readable codebook contract"
  ],
  "non_claims": [
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not gold: no S01 span or slot is a gold label",
    "not a human pilot: S01 performs no coding and reports no agreement",
    "not product authority: prompt output is AnnotationSuggestion only"
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
