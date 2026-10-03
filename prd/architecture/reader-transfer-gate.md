# Reader transfer gate — root-bound classification and typed refusal

**Status:** `[bounded]`
**Owning slice:** M212-c25p2o / S04 — `crates/ln-decode/src/reader_gate.rs`
(`reader_gate`); inline tests `reader_gate::tests`
**Consumer batteries:** `crates/ln-decode/tests/reader_projection_diverse.rs`
(independent recomputation and unsupported accounting) and
`crates/ln-decode/tests/reader_projection_diverse_tamper.rs` (resealed semantic
tamper), both planned under S04 T03/T04
**Fixture manifest:** `prd/architecture/reader-fixture-manifest.md` (S04 T01,
frozen) — the 12 tracked self-authored fixtures and the provenance audit
**Upstream contract:** `prd/architecture/reader-view-contract.md` (S02, frozen)
and `prd/architecture/reader-projection-contract.md` (S03)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0029 (requisites-anchored member
assembly — anchor boundary), D602/D328 (serde stays module-scoped to
`source_package`), D634 (independent verifier recomputes from the substrate),
D635 (fixture provenance), D636 (root-bound gate classification), D637 (S04
boundary)
**Lifecycle ceiling:** this gate is a bounded fail-closed classification over
already-captured decoded source. It is **not** an R1000 closure artifact, not a
corpus coverage or completeness claim, not source authenticity, and not expert
legal gold. It closes no requirement. R1000 stays active.

## 1. Purpose

The reader profile `reader_wordml_profile/v1` accepts a WordML document whose
root is `wordDocument` in one of the three WordML namespaces. Every other
captured source must be **explicitly refused** rather than silently promoted to
reader support. `reader_gate` is that durable surface: one total classifier plus
a typed refusal. It is not test glue and it is not re-implemented per battery.

The gate reads only `source_package` records (root element record) and the
reader contract's namespace set. It never re-parses XML, never builds the
projection, and carries no reader-view semantics.

## 2. Profile pin

```rust
pub const GATE_READER_PROFILE: &str = READER_PROFILE; // "reader_wordml_profile/v1"
pub const READER_ROOT_LOCAL: &str = "wordDocument";
```

The gate pins the same provider profile as the S02 contract
(`reader_contract::READER_PROFILE`), so a profile rename breaks the gate rather
than silently diverging. Provider-bounded: Consultant WordML only, no universal
XML or Garant support.

## 3. Classification table

Classification is **root-bound** (D636). The root is the first element record in
the pre-order element list; text records and foreign children never change the
class.

| `ReaderSourceClass` | root condition (checked in order) | `gate_reader` | Fixture |
|---|---|---|---|
| `supported_wordml` | local = `wordDocument`, namespace ∈ `WORDML_NAMESPACES` | `Ok` | the nine positive fixtures |
| `empty_source` | no element record exists | `Err` | inline test only |
| `namespace_absent` | root has no namespace (unbound or empty declaration) | `Err` | `negative-namespace-absent.xml` |
| `source_not_wordml` | namespaced root, local ≠ `wordDocument` | `Err` | `negative-not-wordml.xml` |
| `unsupported_schema` | local = `wordDocument`, namespace ∉ `WORDML_NAMESPACES` | `Err` | `negative-unsupported-schema.xml` |

Rule order is load-bearing and fail-closed: **no element records** ⇒
`empty_source`; **no namespace** ⇒ `namespace_absent`; **wrong local** ⇒
`source_not_wordml`; **wrong namespace** ⇒ `unsupported_schema`; otherwise
`supported_wordml`. Both the class and the refusal are a closed vocabulary with
`as_str` / `from_wire` (`reader_contract` style, `UnknownToken` on anything
else), so a wire token outside the set fails closed.

## 4. Divergence from the iteration-16 scratch rule

The gitignored iteration-16 prototype (`tmp/pageindex/iteration16`,
`authoritative: false`) treated **any unrecognised namespace URI** in the
document as `unsupported_schema`. That rule is **not** ported (D636). The Rust
reader profile already models foreign-namespaced children as `foreign_element`
references (S02 `role_of_tag`; S03 `ReaderReferenceType::ForeignElement`), and
the S03 mixed fixture itself declares `urn:law-nexus:foreign`. Applying the
scratch rule would misclassify a supported document as unsupported.

The Rust rule is therefore **root-bound**: only the root element decides
support, and a foreign child of a valid `wordDocument` stays
`supported_wordml`. The negative `unsupported_schema` fixture
(`crates/ln-decode/tests/fixtures/reader/diverse/negative-unsupported-schema.xml`)
pins a `wordDocument` **root** in a non-WordML namespace, which is the correct
negative control for the root-bound rule.

The scratch prototype is a characterization source only, never an oracle, and
the non-transfer of its real-corpus rows is recorded in the fixture manifest.

## 5. Gate semantics

- **Total.** `classify_source` never indexes and never assumes a well-formed
  document; an empty slice is `empty_source`.
- **Fail-closed.** `gate_reader` returns `Ok` only for
  `ReaderSourceClass::SupportedWordml`; every other class is a typed
  `GateRefusal { kind, detail }`. An unsupported source cannot be silently
  promoted to reader support.
- **Structural detail only.** `GateRefusal::detail` names the root local name
  and/or namespace. It never carries decoded text; the absence of decoded source
  text in the refusal is asserted by an inline test.
- **No re-parse.** Classification uses `ElementRecord::clark_tag` exactly as
  the substrate recorded it (`{namespace}local`), not a second XML read.
- **Independence.** The gate does not call `reader_projection::build_projection`
  and does not read the projection's content seal; unsupported accounting rests
  on the substrate, not on the artifact under test (D634).

## 6. S04 boundary

S04 delivers: audited diverse fixtures (manifest, T01), this root-bound gate
with its typed refusal (T02), and unsupported-case accounting through the
independent recomputation and resealed semantic-tamper batteries (T03/T04).

Deliberately **not** delivered by S04 (remaining work, R1000 active, D637): the
full reader wire manifest/footer/metrics, read-back/exporter, Hold/TextOnly
handling, navigation links, and `source_completion`. The S03 contract's §6
"later" column listed wire/read-back as tentative; S04 keeps the authoritative
sketch scope instead of silently expanding it.

## 7. Non-claims

- The gate is not corpus coverage and not randomness; it classifies the 12
  frozen self-authored fixtures plus inline synthetic controls (INV-22).
- It makes no source-authenticity claim and no legal-completeness claim.
- It does not claim universal XML or Garant support; the profile stays
  provider-bounded Consultant WordML.
- Fixtures are non-legal synthetic XML; raw decoded legal text is never logged
  or quoted by the gate or its tests.
- Reserved / bookkeeping IDs are not touched; no milestone or requirement state
  is changed here.

## 8. Verification surface

- `crates/ln-decode/src/reader_gate.rs` inline unit tests: each of the five
  classes; all three WordML namespaces; a foreign child staying
  `supported_wordml`; an empty slice as `empty_source`; the closed wire
  vocabulary round-trip plus `UnknownToken`; refusal detail carrying no decoded
  text; and the absence of a serialization or XML-parser dependency.
- `cargo test -p ln-decode --offline --lib reader_gate`,
  `cargo fmt --all --check`, and
  `cargo clippy -p ln-decode --offline --all-targets -- -D warnings`.
- `uv run python scripts/verify-adr-conformance.py`.

---
