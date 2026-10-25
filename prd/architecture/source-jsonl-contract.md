# Source-preserving JSONL package contract

**Status:** `[bounded]`
**Owning slice:** `crates/ln-decode/src/source_package.rs` (public module
`ln_decode::source_package`)
**Authority:** ADR-0013 (universal multi-source parser architecture),
ADR-0015 (hexagonal verification architecture), ADR-0011 (KOF-DA ownership,
HC-05 `ln-decode`)
**Lifecycle ceiling:** this is a bounded decoded-source capture/verify
capability. It is **not** an R1000 closure artifact, not a CST/AST, and not
expert legal gold. It does not close any requirement.

## 1. Purpose

One vertical capability: capture decoded content from supplied XML bytes into a
strict, versioned, LF-terminated JSONL package (`manifest` first,
`element`/`text` records, `footer` last), then read it back through a structural
package verifier. Source comparison uses the same capture algorithm; it is not
an independent XML oracle.

This is a **decoded source model**, not an XML lexical byte roundtrip, and it
carries **no XML byte coordinates**. It is the smallest useful carrier of
decoded element topology and decoded text for later, separately-owned slices.

## 2. Non-claims

- No legal completeness, source authenticity, corpus coverage, or citation
  resolution is claimed.
- `capture_status: "complete"` means the bounded capture policy completed over
  the supplied bytes. It is not a completeness or correctness judgment.
- `source_sha256` and the record seal are **integrity, not authenticity**: an
  actor controlling the bytes can recompute them.
- `verify_against_source` re-runs the same capture algorithm and compares
  structurally. It is **not independent proof**; the two implementations share
  an algorithm and therefore share any systematic defect.
- Comments, processing instructions, the XML declaration, CDATA boundaries,
  attribute order, entity syntax, and document-level text outside the root are
  **not preserved and not claimed**. The manifest `policies` block declares
  each exclusion and the verifier re-checks it.
- Name and attribute well-formedness is a **bounded parse subset**, not full
  XML/DTD/schema validation: element, attribute, and namespace-declaration names
  must satisfy the XML 1.0 `Name`/`QName` productions; a literal `<` is rejected
  in an attribute value; and a `--` sequence is rejected inside a comment.
  Processing-instruction targets and DTD/schema validity are out of scope.
- Reader / cleaning / literal-run projection, tokenization, JEV semantic
  identity, filesystem atomic publish, and CLI are **out of scope** for this
  slice.

## 3. Package layout

One UTF-8 JSONL document, LF-delimited, exactly one trailing LF:

```text
line 0        manifest   kind = "source_package_manifest"
lines 1..n-1  records    kind in { "element", "text" }   (elements first, then texts)
line n        footer     kind = "source_package_footer"
```

The reader rejects: a missing trailing LF, any carriage return, blank interior
lines, an empty package, a missing/misordered footer, a missing/misordered
manifest, a trailing record after the footer, and a truncated footer.

Canonical serialization is compact JSON with fixed struct field order.
Attribute and namespace-declaration maps are `BTreeMap`, so key order is
deterministic. There is no hash-map iteration order in any emitted artifact.

## 4. Records

### 4.1 element

| field | type | meaning |
|---|---|---|
| `kind` | `"element"` | closed discriminator |
| `schema` | `"law-nexus/source-package-element/v1"` | closed schema tag |
| `id` | `"e0".."eN"` | source-local id, pre-order |
| `parent` | `"e.."` or `null` | owning element id |
| `child_index` | `u64` or `null` | 0-based index among the parent's children |
| `depth` | `u64` | root `0`, child `parent.depth + 1` |
| `clark_tag` | string | `{uri}local` when namespace-bound, else `local` |
| `attrs` | map | Clark attribute name -> decoded value (unprefixed attrs stay unqualified) |
| `namespace_declarations` | map | prefix (`""` = default) -> uri, declared on this element only |
| `xml_space_declared` | `bool` or `null` | `xml:space` declared on this element (`preserve`/`default`) |
| `xml_space_effective` | `bool` | declared value, else inherited from parent, else `false` |
| `text_ref` | `"t.."` or `null` | this element's `text` fragment |
| `tail_ref` | `"t.."` or `null` | this element's `tail` fragment |

### 4.2 text

| field | type | meaning |
|---|---|---|
| `kind` | `"text"` | closed discriminator |
| `schema` | `"law-nexus/source-package-text/v1"` | closed schema tag |
| `id` | `"t0".."tM"` | source-local id, document order |
| `owner` | `"e.."` | owning element id |
| `slot` | `"text"` or `"tail"` | ElementTree-style text/tail slot |
| `value` | string | exact decoded Unicode text, whitespace and NBSP included |
| `chars` | `u64` | `value.chars().count()` |
| `bytes` | `u64` | `value.len()` (UTF-8) |

Text semantics follow ElementTree: `element.text` is the content before the
first child, `element.tail` is the content after the element and before its next
sibling. Adjacent `Text`/`CData` events in the same owner/slot are merged into a
single fragment (entities decode; CDATA boundaries do not survive, per policy).
Empty slots produce no record.

Nullable members are still **required JSON keys**: `parent`, `child_index`,
`xml_space_declared`, `text_ref`, `tail_ref` on an element, and
`records_seal_hash`/`manifest_hash` on a footer, must be present in a
serialized package. The value may be `null`; an *absent* key is a typed
`TypeMismatch` rejection.

### 4.3 manifest

Fixed fields: `kind`, `schema`
(`law-nexus/source-package-manifest/v1`), `version` (`1`), `model`
(`law-nexus/source-package-model/v1`), `profile`
(`source_package_decoded_text/v1`), `capability` (`source_package_jsonl`),
`capture_policy`, `source` (`{sha256, bytes}`), `limits`, `policies`,
`non_authoritative` (`true`).

### 4.4 footer

Fixed fields: `kind`, `schema` (`law-nexus/source-package-footer/v1`),
`version` (`1`), `capture_status` (`"complete"`), `completion_basis`,
`source_sha256`, `counts` (`elements`, `text_fragments`, `text_chars`,
`text_bytes`, `namespace_declarations`, `records`), `records_seal_hash`,
`manifest_hash`, `non_authoritative` (`true`).

## 5. Policies (declared and re-checked)

| policy | value |
|---|---|
| text scope | element `text` + `tail` slots only |
| document-level text | outside root: excluded, not claimed (non-whitespace rejects) |
| comments / PI / declaration | excluded metadata, not claimed |
| CDATA boundaries | not preserved |
| entities | predefined + numeric only; any DTD is rejected |
| binary payloads | **all decoded text retained, no exclusions** (first slice) |
| unknown/foreign elements | retained |
| namespaces | Clark-resolved; per-element declarations recorded |
| `xml:space` | declared + inherited recorded |
| raw XML lexical form | not preserved, not claimed |
| memory model | bounded whole-document in memory, not streaming |
| authenticity | integrity only, not authenticity |

Literal end-of-line normalization follows XML 1.0 section 2.11: `\r\n` and lone
`\r` in literal text and CDATA become `\n`; character references such as `&#13;`
are preserved. Literal TAB/LF/CR inside attribute values become a space before
unescaping (section 3.3.3); a character reference for whitespace (`&#9;`) keeps
its referenced character. `source_sha256` and `source.bytes` are computed over
the original, un-normalized input bytes.

Bounded namespace policy: element and attribute names are Clark-resolved by the
reader, and per-element declarations are recorded. Because the reader resolves
namespace bindings from the raw (undecoded) attribute bytes, a namespace
declaration whose value contains an entity reference or literal TAB/LF/CR is
rejected; this keeps the resolved Clark name and the recorded declaration
consistent. Only literal namespace URIs are accepted.

The `binData`-exclusion policy used by the iteration-13/15 scratch prototypes is
deliberately **not** adopted here: this first slice preserves all decoded text
under the caps rather than dropping any payload class. Unknown foreign elements
that share a local name with a known element are preserved by Clark tag.

## 6. Limits (hard fail-closed)

All limits are `u64`; `bool`/float JSON tokens are rejected by the typed
deserializer. Defaults: `max_input_bytes` 64 MiB, `max_package_bytes` 512 MiB,
`max_line_bytes` 64 MiB, `max_depth` 4096, `max_nodes` 2,000,000,
`max_text_fragments` 2,000,000, `max_text_bytes` 512 MiB, `max_records`
4,000,000, `max_attrs_per_element` 1024.

Capture rejects (typed, contextual, no decoded source text in the message):
oversized input, non-UTF-8 input, non-UTF-8 encoding declaration, any
`<!DOCTYPE>`, malformed XML, multiple roots, no root, unclosed elements,
non-whitespace document-level text, unbound prefixed names, duplicate
attributes/declarations, attribute-count, depth, node, fragment, text-byte and
record caps, and invalid `xml:space`. It also rejects any character outside the
XML 1.0 `Char` set (literal or reference-derived, in text, CDATA, attributes, or
declarations); element/attribute/namespace-declaration names outside the XML 1.0
`Name`/`QName` productions; a literal `<` in an attribute value before
unescaping; and a `--` sequence inside a comment. An XML declaration is
**optional**, but if present it must not be repeated, must be well-formed (a
missing or malformed `version` is rejected), must carry only
`version`/`encoding`/`standalone` without duplicates, and must appear at the
document start; a declaration version other than `1.0` (`1.1`/`2.0`) is rejected
(this slice does not claim XML 1.1).

`read_package`/`write_to` use per-field **effective limits** = `min(caller,
manifest)`; a caller cap is a ceiling and a manifest cap can only tighten it.
This holds for every limit, not just the package and line caps, and is enforced
before records are retained on the read path.

## 7. Verification surface

`Package::verify` (the source-free half) checks:

1. closed manifest/footer identity, schema, version, constants, policies;
2. source hash linkage and 64-hex shape;
3. record `kind`/`schema`, canonical `e0..`/`t0..` id sequence, duplicate ids;
4. exactly one root; every parent exists and is an element; `depth == parent + 1`;
   `child_index` contiguous per parent; element records in canonical pre-order;
5. text owner existence, `(owner, slot)` uniqueness, `chars`/`bytes` match;
6. text/tail document order re-derived from the element topology and reference
   presence (tail placement);
7. element `text_ref`/`tail_ref` resolve to the matching owner/slot;
8. footer counts recomputed from records; the effective limits enforced against
   the recomputed counts, depth, and per-element attribute+declaration count,
   before any topology/order walk;
9. `xml:space` inheritance coherence;
10. `records_seal_hash` (sha256 over canonical record JSON in file order) and
    `manifest_hash` (sha256 over manifest + seal + footer body) recomputed.

## 8. API

```rust
pub fn capture(xml: &[u8], limits: &Limits) -> Result<Package, SourcePackageError>;
pub fn read_package<R: BufRead>(reader: R, limits: &Limits) -> Result<Package, SourcePackageError>;
pub fn write_package<W: Write>(package: &Package, writer: &mut W, limits: &Limits)
    -> Result<(), SourcePackageError>;
pub fn verify_against_source(package: &Package, xml: &[u8], limits: &Limits)
    -> Result<SourceComparison, SourcePackageError>;

impl Package {
    pub fn verify(&self) -> Result<(), SourcePackageError>;
    pub fn to_jsonl(&self) -> Result<String, SourcePackageError>;
    pub fn write_to<W: Write>(&self, writer: &mut W, limits: &Limits)
        -> Result<(), SourcePackageError>;
}
```

`write_package`/`write_to` validate **before** writing anything; a mid-stream
writer error is surfaced, and a partially written stream never contains an
accepted footer. `to_jsonl` likewise verifies the package and checks its
declared export limits before producing any line, so it cannot emit a package
that would not read back. `Package::from_parts` and `Package::resign` are
`#[doc(hidden)]` diagnostic/test surfaces: they can hold deliberately
inconsistent parts, but they do not bypass validation on serialize.
`read_package` is incremental: it parses the manifest first,
computes the effective limits, reads each subsequent line under a hard byte cap,
counts records against the caps before retaining them, requires the footer to be
the final line (verified to EOF), and verifies before returning. Tree walks in
capture and verify are iterative, so depth is bounded by the caps rather than the
call stack.

## 9. Dependency justification

Added to `crates/ln-decode/Cargo.toml`:

| crate | license | why | offline |
|---|---|---|---|
| `serde` (derive) | MIT OR Apache-2.0 | strict typed records; `deny_unknown_fields`; `u64` rejects `bool` | cached in the local registry; locked in `Cargo.lock` |
| `serde_json` | MIT OR Apache-2.0 | the single JSON reader/writer; no hand-rolled JSON parser | cached; locked |
| `sha2` | MIT OR Apache-2.0 | SHA-256 source digest and record/manifest seals | cached; locked |

Alternatives: a hand-written JSON parser was rejected (strict duplicate-key /
type discipline would be re-implemented, error-prone, and outside the "no private
JSON parser" rule); the existing `domain::fingerprint_bytes` is a documented FNV
diagnostic explicitly "not integrity", so it cannot serve as an integrity seal.

`quick-xml 0.36` was already an `ln-decode` dependency and is reused for the
event stream; no existing decoder or lexer module was modified.

### Scoped revision of the D328 no-serde boundary

The old `acceptance_freeze_pins_hold` in
`crates/ln-decode/tests/npa_lawref_acceptance_contract.rs` prohibited serde
throughout the crate. D602 scopes a justified exception to the new
`source_package` capability: typed serialization and strict JSON validation
replace neither the historical hand-written fixture readers nor any lexer or
LawRef API. This document is the tracked rationale for the exception.

The freeze test still prohibits reporting dependencies (`clap`, `walkdir`,
`krippendorff`), keeps the LawRef vocabulary freeze, and now directly checks
that `lexer.rs`, `lawref.rs` and `lawref_resolve.rs` remain free of serde.
This is a scope correction, not removal of the prior behavior contract.

## 10. Evidence

`crates/ln-decode/tests/source_package_contract.rs` (integration): handwritten
XML/topology oracles (not produced by the module), namespace/Clark and
default-namespace-attribute cases, `xml:space` inheritance, NBSP/CDATA/entity
merging, unknown foreign same-local names, `rev`/`notes`/`tables` shapes,
fail-closed capture rejections, read/write roundtrip, LF/CR/duplicate-key/typed
tamper rejections, duplicate-id/dangling-parent/wrong-count/tail-placement
verification rejections, writer-validates-before-write and mid-stream-write
failure, `verify_against_source`, and an error-detail no-leak check.

Hostile-review regressions: deep (20,000) chains rejected by the default depth
cap and verified iteratively under a raised cap, iterative deep capture, caller
node/attribute caps enforced on read, manifest attribute cap enforced on verify,
first-line fail-fast on a non-manifest stream (instrumented reader), XML 1.0 EOL
and attribute-whitespace normalization with preserved character references,
XML `Char` rejection, XML declaration position/duplicate/version rejection,
namespace-declaration reference rejection, capture line-cap exportability, and
execution-limit-independent `verify_against_source`.

Name/attribute hardening (second independent review): XML 1.0
`Name`/`QName` rejection for `<1/>`, `<r><1/></r>`, `<r 1a="x"/>`, `<a/b/>`,
`<p:a:b/>`, `<:/>`, and a two-colon attribute name; acceptance of CJK/astral/
combining-mark/underscore `NCName` characters and a bound single-colon prefixed
name; a literal `<` in attribute values rejected while escaped `&lt;` is
accepted; a `--` sequence inside a comment rejected; every nullable element and
footer key required-present (absent key rejected as `TypeMismatch`, explicit
`null` accepted); and `to_jsonl` refuses to serialize unverified parts. A
parent-owned bounded real-corpus fixture (3167 elements / 295 text slots /
96161 UTF-8 chars / 193726 bytes) is compared against a parent-supplied
expected artifact as an external comparison, not as legal truth.

## 11. Out of scope

Reader/cleaning/literal-run projection, tokenization, JEV semantic identity,
filesystem atomic publish, CLI, and any CST/AST claim. No full-corpus run was
performed; evidence is fixture-bounded.
