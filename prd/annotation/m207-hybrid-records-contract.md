# M207 hybrid records wire contract

Status: [proposed]. Verification-harness contract for the D519 automated
successor. Not gold, not human annotation, not a frozen S01/S02/S03/S04
schema, not S03 metrics, not parser `SourceBlockRecord`, and not a Rust
product type.

Owning slice: M207 S05 (Python repository-control harness, ADR-0007).
First Rust series consumption: M211 S02 / M207 S06. This file does not
implement parsing and does not discharge any frozen M207 pin.

## Purpose

Give the first Rust series a **versioned, source-local, fail-closed**
occurrence / field / provenance / relation envelope that a Python
verification CLI can validate without a human pilot.

The in-tree synthetic evaluator
(`scripts/m207_hybrid_eval_experiment.py`, schema
`m207-hybrid-synthetic-experiment/v1`) remains a separate engineering
fixture. It is not an external records file, not Rust output, and not a
human store.

Executable gate:

```text
uv run python scripts/m207_hybrid_eval_experiment.py --validate-records PATH
```

Default `--check` / explicit `--write` still only concern the synthetic
experiment JSON. `--validate-records` is read-only: it never writes PATH,
never writes the synthetic artifact, and never writes frozen S01–S04
stores. Combining it with `--write` is a usage error.

Marker on success: `M207_HYBRID_RECORDS_OK`. Invalid input exits non-zero
with machine-readable JSON on stdout and `FAIL <CODE>: …` on stderr. The
validator is fail-closed for *every* rejection path: an unexpected
exception while handling records input is mapped to a `MALFORMED_REF`
diagnostic instead of escaping as a traceback with empty stdout.

## Version

| Field | Value |
|---|---|
| `schema` | `m207-hybrid-records/v1` |
| `schema_version` | integer `1` |

Any other `schema` string or `schema_version` is `UNSUPPORTED_VERSION`.
In particular `m207-hybrid-synthetic-experiment/v1` is not this contract.

## Serialization boundary (D328)

Wire format is **UTF-8 JSON**, one object per file.

Canonical bytes (deterministic roundtrip):

```text
json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
```

encoded as UTF-8 without BOM.

| Side | Rule |
|---|---|
| Python harness | stdlib `json` only. No new dependency. |
| Future Rust emitter (M211) | emit this JSON with a stdlib / hand-rolled writer. **Do not add `serde` / `serde_json`** (D328: workspace `ln-decode` stays serde-free). A later justified serde dependency is a separate decision, not implied by this contract. |
| Reader | Python validator in this slice. Rust product must not grow a second domain model of these records here. |

JSON object key order is not semantically significant; canonical dumps
sort keys so byte-identity checks are stable.

## Provenance origin

Closed set:

- `synthetic` — engineering fixture authored in the harness. Not human.
- `rust-runtime` — bytes emitted by a Rust series exporter. Not human.

Anything else, including `human-reviewed`, `machine`, or omitted, is
`PROVENANCE_FORBIDDEN` or `MALFORMED_REF`. Synthetic fixtures must not be
relabelled as `rust-runtime`. Human stores stay out of this envelope.

## Envelope (closed required keys)

Required:

- `schema`
- `schema_version`
- `provenance_origin`
- `documents`
- `bundles`

Optional (if present, must be honest):

- `lifecycle` — `["proposed"]` for this slice
- `authoritative` — `false`
- `is_gold` — `false`
- `not_human` — `true`
- `not_s03_metrics` — `true`
- `source_validation` — see below
- `alignment_policy` — currently `local-anchor-identity-v1`
- `limits`, `non_claims`

Unknown required-key absence is `MALFORMED_REF`. This envelope must not
carry S03 rate keys, coder submissions, or raw legal corpus text.

Honesty keys are **enforced**, not advisory. When a key from the optional
list is present the validator compares it against the fixed value above and
raises `MALFORMED_REF` on any mismatch. So a structurally valid payload
carrying `is_gold=true`, `not_human=false`, `lifecycle=["validated"]`, or
`alignment_policy="best-match"` is refused instead of emitting
`M207_HYBRID_RECORDS_OK`. An omitted honesty key is still accepted; the
contract does not fabricate the claim on the caller's behalf.

### Closed allow-list

The envelope is **closed per level** — not just at the top. Every object
listed below admits exactly its documented keys, and any other key is
`MALFORMED_REF`:

| Level | Allowed keys |
|---|---|
| envelope (top) | the required and optional keys listed above |
| document | `document_id`, `fragments` |
| fragment | `fragment_id`, `byte_length`, `source_utf8` |
| bundle | `bundle_id`, `construction`, `focus_id`, `context_status`, `declared_region`, `context_only`, `occurrences`, `relations` |
| occurrence | `id`, `anchors`, `unresolved`, `unresolved_reason`, `fields` |
| `fields` container | `kind`, `date`, `number` |
| field slot | `value`, `source` |
| relation | `id`, `rel`, `from`, `to` |
| anchor | `fragment_id`, `start`, `end` |

Named forbidden keys are refused with an explicit reason rather than a
generic one: S03 rate keys (`false_authority`, `span_rate`, `slot_rate`,
`scope_rate`, `binding_rate`, `abstention_rate`, `aspect_rates`),
coder-submission shapes (`submissions`, `coder_id`, `coder`,
`adjudication`, `adjudications`), and raw legal corpus text
(`corpus_excerpt`, `raw_text`, `legal_text`, `source_text`,
`corpus_text`, `raw_legal_text`). A closed envelope prevents the future
Rust emitter from silently ignoring — or being forced to model — an
untyped tail, and keeps the two forbidden classes out of the wire entirely.

The synthetic experiment schema `m207-hybrid-synthetic-experiment/v1` is a
separate fixture and is **not** validated against these allow-lists.

## Documents and fragments

`documents` is a non-empty array. Each document:

- `document_id` — non-empty string, unique in the file
- `fragments` — non-empty array

Each fragment:

- `fragment_id` — non-empty string, **globally unique** in the file
- `byte_length` — integer `>= 0` (catalog size in UTF-8 bytes)
- `source_utf8` — optional JSON string. When present, the validator
  encodes it as UTF-8 and **checks** `len(bytes) == byte_length` and
  every cited span against those bytes. When absent, the fragment is
  **metadata-only**: bounds are checked against `byte_length` only.
  The validator must not claim byte-content validation for that
  fragment.

A fragment belongs to exactly one document. Anchors name `fragment_id`
only; document membership is recovered from this catalog.

Coordinates are **half-open UTF-8-aligned file-byte ranges**
`[start, end)` local to the fragment, the same shape as the synthetic
experiment (`{fragment_id, start, end}`). They are **not** ADR-0017
`TextAnchor`, **not** ADR-0010 `EvidenceSpan` / `EvidenceAnchor`, and
**not** parser `SourceBlockRecord`.

## Bundles

Each bundle reuses the synthetic experiment bundle object:

- `bundle_id`, `construction`, `focus_id`, `context_status`
- `declared_region`, `context_only`
- `occurrences` with `id`, `anchors`, `unresolved`, `unresolved_reason`,
  `fields.{kind,date,number}.{value,source}`
- `relations` with `id`, `rel`, `from`, `to`

Types are checked before any catalog lookup: `bundle_id`,
`construction`, `context_status` and `focus_id` are non-empty strings;
`declared_region` and `context_only` are arrays of non-empty strings;
`unresolved` is a boolean and `unresolved_reason` is `null` or a string.
A type error is a machine-readable `MALFORMED_REF` JSON diagnostic, never an
uncaught traceback.

`kind` remains a **working label**, not adopted legal TYPE vocabulary.

Additional envelope rules, beyond the synthetic bundle shape:

1. Every cited `fragment_id` (occurrence anchors and field `source`
   anchors) must exist in the document catalog (`DANGLING_EDGE` if not).
2. `0 <= start < end <= byte_length`. A span that is half-open-invalid
   in the bundle shape is `MALFORMED_REF`; a shape-valid span that
   exceeds the catalog length is `INVALID_BOUNDS`.
3. When `source_utf8` is supplied, both endpoints must sit on UTF-8 code
   point boundaries of those bytes (`INVALID_BOUNDS` if they split a
   code point). When it is not supplied, the validator records
   `source_validation=metadata-only` (or `mixed`) and does **not** claim
   real UTF-8 content checks.
4. All fragment ids cited by one bundle, including field sources, must
   map to **one** `document_id` (`CROSS_DOC_REF` otherwise). v1 does not
   encode cross-document relations.
5. Relation `from` / `to` and `focus_id` must name occurrences in the
   same bundle (`DANGLING_EDGE`).
6. Two occurrences in the same bundle that share the same complete
   anchor-key are `AMBIGUOUS_DUPLICATE`. Alignment remains local-anchor
   identity; the validator does not pick a best match by `kind` / date /
   number.

## Source-validation honesty

Derived from **referenced** fragments:

| Derived | Meaning |
|---|---|
| `bytes-present` | every referenced fragment supplied `source_utf8` and passed byte checks |
| `metadata-only` | no referenced fragment supplied `source_utf8` |
| `mixed` | some referenced fragments have bytes, some do not |

If the envelope sets `source_validation`, it must equal the derived
value. Claiming `bytes-present` without bytes is
`SOURCE_CLAIM_WITHOUT_BYTES`.

## Protected paths

The records CLI may read a caller-supplied PATH. It must refuse PATH when
that path is the tracked synthetic experiment JSON or a frozen S01–S04
annotation / evidence pin (`PROTECTED_PATH`). Refusal is fail-closed
before schema parse of those bytes as hybrid records.

## Diagnostics

Closed codes used by the validator:

| Code | When |
|---|---|
| `UNSUPPORTED_VERSION` | `schema` / `schema_version` not v1 of this contract |
| `MISSING_INPUT` | PATH does not exist |
| `MALFORMED_REF` | not UTF-8 JSON, missing keys, unknown or forbidden keys, dishonest honesty key, wrong value type, duplicate ids, catalog self-inconsistency |
| `INVALID_BOUNDS` | span exceeds catalog length or splits UTF-8 when bytes are present |
| `CROSS_DOC_REF` | one bundle cites fragments from more than one document |
| `DANGLING_EDGE` | missing fragment, focus, or relation endpoint |
| `AMBIGUOUS_DUPLICATE` | duplicate complete anchor-key inside a bundle |
| `PROVENANCE_FORBIDDEN` | origin outside `{synthetic, rust-runtime}` |
| `SOURCE_CLAIM_WITHOUT_BYTES` | claimed byte validation without `source_utf8` |
| `PROTECTED_PATH` | PATH is the synthetic artifact or a frozen store |
| `USAGE` | `--validate-records` combined with `--write` |

Stdout JSON object (canonical key order): `status` (`ok` \| `invalid`),
`marker`, `schema`, `schema_version`, `provenance_origin`,
`source_validation`, `documents`, `fragments`, `bundles`, `diagnostics`
(array of `{code, detail}`).

## Non-claims

- `M207_HYBRID_RECORDS_OK` is not acceptance evidence, not gold, and not a
  discharged M207 pin; it only reports that the bytes satisfy this contract.
- Does not measure legal correctness.
- Does not adopt TYPE / label inventory.
- Does not release a human pilot or rewrite frozen S01–S04.
- Does not treat synthetic expected records as Rust output.
- Does not treat metadata-only catalogs as UTF-8 content proof.
- Does not add a serde dependency or a Rust crate in this slice.
- Does not merge this envelope with parser record schemas.
