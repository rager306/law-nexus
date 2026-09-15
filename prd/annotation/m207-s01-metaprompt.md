# M207 S01 — safe metaprompt contract (`m207-s01-metaprompt/v1`)

**Status:** `[bounded]` annotation/evidence contract, harness-side only.
**Milestone:** M207-b2i96m / S01 / T03
**Codebook:** `prd/annotation/m207-s01-codebook.md` (frozen by T01; this contract
never redefines the slot space).
**Closed schemas:** `prd/annotation/m207-s01-schemas.json`
(`m207-s01-annotation-schemas/v1`, subsection `schemas.prompt_packet`).
**Executable gate:** `uv run python scripts/m207_s01_prompt_packet.py check`
(marker `M207_S01_PROMPT_PACKET_OK`).
**Emitter:** `scripts/m207_s01_prompt_packet.py` →
`prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl` (one packet per pilot
case, 40 lines).
**Placement:** D466 — the prompt boundary lives in the harness (`scripts/`) plus
data under `prd/annotation/`; no product crate, no new Rust code.

This document is the **boundary contract** of the pilot metaprompt: what a packet
may contain, what it may never contain, what its output type is, and why that
output cannot become a product claim. It is the executable half of
`assessment/28` §6 (prompt boundary conformance) and §8.9 (prompt isolation) for
this pilot. It contains **no suggestions and no annotations**: S01 fabricates no
prompt output, no span and no label.

## 1. Scope: no model is invoked in this slice

The pilot proves the **safety of the boundary**, not the quality of suggestions.

- `model_invoked` is `false` in every packet, and no model is called anywhere in
  S01. No `AnnotationSuggestion` instance is produced, stored or scored.
- A packet is a *prepared input* for a boundary that is deliberately not
  executed here. The artifact `m207-s01-prompt-packets.jsonl` demonstrates that
  the input can be assembled without predicted-answer leakage.
- Running a model, collecting suggestions and comparing them with human codings
  is **not** this slice's work and is not claimed by it.
- Human coding, coder provenance, adjudication and agreement remain S02; the
  per-aspect rates (span, slot, scope, binding, abstention, false-authority)
  remain S03. Binding boundary: `assessment/28` §8.10 keeps R035/R070/N2 open.

## 2. Packet contents

A packet carries exactly these closed keys, and nothing else:

| Key | Meaning |
|---|---|
| `packet_id` | deterministic id `m207-s01-packet-NNN`, aligned with the case order |
| `case_id` | the pilot case from the T02 case manifest |
| `codebook_ref` | `prd/annotation/m207-s01-codebook.md` — the decision space lives there |
| `source_anchor` | doc path + `sha256` + block index + `byte_len` (§3) |
| `fragment_text` | the frozen decoded block text **as written** |
| `span` | `{start, end}` in fragment bytes, half-open, UTF-8 aligned |
| `alternative_classes` | the closed codebook decision poles (identical for every case) |
| `decision_space` | decision values, the eight-slot space and the abstention values |
| `output_type` | exactly `AnnotationSuggestion` |
| `authority` | exactly `none` |
| `suggestion_status` | exactly `none-provided` |
| `model_invoked` | exactly `false` |
| `non_claims` | the codebook non-claim set, pinned by value |

`fragment_text` is source, not answer: it is byte-for-byte the frozen fixture
block of `ConsultantWordMlBlockDecoder` (Consultant ≠ Garant). The gate verifies
the text against the frozen bytes, so a packet can never carry a manufactured
reading of the source.

`span` is the **whole** frozen decoded block (`start = 0`, `end = byte_len`).
Any narrowed window would need a predicate over the text, and every such
predicate is distant supervision; the frozen `lawref_seed.json` sidecar (rule-seed
spans with filled slots) must never reach a packet.

## 3. Source anchor

`source_anchor` is bound to the frozen M199 seed and carries exactly:

| Anchor key | Meaning |
|---|---|
| `doc_path` | repository-relative source path: the full consru export (`consru_export/consru_export/exports/...`) or the tracked Consultant member of the 44-FZ cluster (`law-source/consultant/...`, M199 §13) |
| `source_sha256` | the document hash declared by the frozen M199 manifest |
| `block_index` | the source block index of the fragment |
| `byte_len` | byte length of the frozen decoded fragment |

An anchor is a *reference into the frozen frame*, never a new provenance claim:
the pilot asserts no official-publication provenance and no amendment provenance
(R070 stays open).

## 4. Alternatives and the closed decision space

`alternative_classes` enumerates the closed decision poles a coder may choose
from (`reference_decision`, `slot_presence`, `scope`, `binding`). It is identical
for every case, so publishing it leaks nothing about a particular fragment.

`decision_space` restates the closed space without per-case content:
the two reference-decision values, the **eight** M199 §5 slot keys, and the three
abstention values. A ninth slot is rejected fail-closed (`NINTH_SLOT`), exactly
as in the codebook and the frozen M199 protocol.

Alternatives are **decision poles**, not candidate answers: the packet never
carries a candidate span, a filled slot value or a suggested reading of the
fragment.

## 5. Forbidden packet content

A packet may never carry, at any nesting depth:

- predicted answers or gold in any spelling: keys/values named `label`,
  `expected`, `answer`, `predicted`, `prediction`, `gold`, `capture`, and their
  camelCase or snake_case compounds (`gold_label`, `predicted_answer`, ...);
- rule-seed captures: `rule_seed`, `rule_seed_span`, `seed_span`, `ds_span`,
  `seed_slots`, or any reference to `lawref_seed.json`;
- the codings of another coder: `coder_id`, `coder_pass`, `submission_id`, an
  adjudication record, or an agreement statistic — human coding does not exist in
  S01 and must not be simulated;
- product output: any path under `crates/**`, any Rust source reference, or a
  pointer to a product prediction; the product is not a packet source
  (`assessment/28` §8.9);
- absolute paths, `..` segments, backslash paths or any path that escapes the
  repository.

Enforcement: the gate scans every packet recursively for forbidden keys, scans
the serialized payload for forbidden substrings, and checks that every authored
path value lives under an allowed prefix. Non-claims are pinned by value, so the
codebook's own `gold`/`label` wording inside `non_claims` is not a leak — a
changed `non_claims` value is a drift failure.

## 6. Output contract: `AnnotationSuggestion` only

The only permitted output type at this boundary is `AnnotationSuggestion`. Such
an output:

- **cannot** drive an FSM transition (no state, guard or transition reads it);
- **cannot** create a legal fact — no `SemanticFieldClaim`, `ReferenceBinding`,
  `OfficialIdentityClaim`, act-tree node or `LawRef` product type;
- **cannot** be gold: gold requires independent human coding plus coder
  provenance, which is S02;
- **cannot** count as a coder, as a second pass or as human acceptance;
- **cannot** become an authority: `authority` is `none` and
  `suggestion_status` is `none-provided` in every packet, and the gate rejects
  any other value (`AUTHORITY_CLAIM`).

## 7. Prompt isolation from the product

`assessment/28` §8.9 requires provable isolation: *removing all prompt/model
facilities leaves product results byte-identical.* Structurally:

- no file under `crates/**` references `m207-s01`, `prd/annotation/` or the
  packet artifact (T04 verifier asserts this over the whole crate tree);
- no product crate has a build, test or runtime dependency on the codebook, the
  schemas, the case manifest or the packets;
- S01 adds no Rust code and no new crate (D466), so there is nothing for the
  product to depend on.

Isolation is therefore a structural property of the layout, not an agreement.

## 8. Lifecycle markers and non-claims

Every packet carries the codebook non-claims verbatim, and the pilot keeps the
lifecycle markers:

| Marker | Value | Meaning |
|---|---|---|
| `human_adoption` | `pending` | no human has adopted the pilot |
| `runtime_stop_active` | `true` | runtime remains stopped |
| `selected_d388_gates` | `none` | no D388 gate is selected by this work |
| `requirement_status_effect` | `unchanged` | R035/R070/R074 stay active |
| `review_disposition_effect` | `unchanged` | review dispositions are untouched |

The markers live in the codebook/schema/manifest lifecycle blocks; the packets
carry the matching `non_claims` and are themselves evidence that the prompt
boundary holds without any model.

## Machine-readable metaprompt contract

The block below is the machine-readable half of this contract. The executable
gate (`scripts/m207_s01_prompt_packet.py`) parses it, compares it with
`prd/annotation/m207-s01-schemas.json` (`schemas.prompt_packet`), with the frozen
codebook contract, and with every emitted packet, and fails closed on any drift.
Edit this block and the schema together, or not at all.

```json
{
  "metaprompt_id": "m207-s01-metaprompt/v1",
  "schema_id": "m207-s01-prompt-packet/v1",
  "codebook": "prd/annotation/m207-s01-codebook.md",
  "packet_closed_keys": [
    "packet_id",
    "case_id",
    "codebook_ref",
    "source_anchor",
    "fragment_text",
    "span",
    "alternative_classes",
    "decision_space",
    "output_type",
    "authority",
    "suggestion_status",
    "model_invoked",
    "non_claims"
  ],
  "anchor_closed_keys": ["doc_path", "source_sha256", "block_index", "byte_len"],
  "span_closed_keys": ["start", "end"],
  "decision_space": {
    "decision_values": ["reference", "not_a_reference"],
    "slot_space": [
      "marker_chain",
      "hier_nums",
      "date",
      "doc_no",
      "law_code",
      "anaphora",
      "range",
      "quoted_enum"
    ],
    "abstention_values": ["not-abstained", "ambiguous", "insufficient-context"]
  },
  "output_contract": {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": false
  },
  "forbidden_keys": ["label", "expected", "answer", "prediction", "gold", "capture"],
  "forbidden_seed_keys": ["seed_span", "rule_seed_span", "rule_seed", "ds_span", "seed_slots"],
  "forbidden_substrings": [
    "label",
    "expected",
    "answer",
    "prediction",
    "predicted",
    "gold",
    "capture",
    "rule_seed",
    "seed_span",
    "ds_span",
    "lawref_seed",
    "crates/",
    "coder_id",
    "coder_pass",
    "submission_id",
    "adjudicat",
    "AnnotationSuggestion:"
  ],
  "allowed_path_prefixes": [
    "prd/annotation/",
    "prd/migration/rust-evidence/",
    "consru_export/consru_export/exports/",
    "law-source/consultant/"
  ],
  "fixed_string_values": {
    "codebook_ref": "prd/annotation/m207-s01-codebook.md",
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": false
  },
  "case_count_range": [20, 40],
  "required_sections": [
    "1. Scope: no model is invoked in this slice",
    "2. Packet contents",
    "3. Source anchor",
    "4. Alternatives and the closed decision space",
    "5. Forbidden packet content",
    "6. Output contract: AnnotationSuggestion only",
    "7. Prompt isolation from the product",
    "8. Lifecycle markers and non-claims",
    "Machine-readable metaprompt contract"
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
