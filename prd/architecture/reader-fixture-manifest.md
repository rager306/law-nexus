# Reader fixture manifest — diverse self-authored fixtures

**Status:** `[bounded]`
**Owning slice:** M212-c25p2o / S04 — diverse frozen fixtures and the reader transfer gate
**Fixture directory:** `crates/ln-decode/tests/fixtures/reader/diverse/` (12 tracked XML
plus the integrity pin `SHA256SUMS`)
**Consumer batteries:** `crates/ln-decode/tests/reader_projection_diverse.rs` (independent
recomputation and unsupported accounting) and
`crates/ln-decode/tests/reader_projection_diverse_tamper.rs` (resealed semantic tamper)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0029 (requisites-anchored member assembly —
anchor boundary), D631 (S02 reader coordinate base), D633 (S03 content seal and
resealed semantic-tamper semantics), D602/D328 (serde stays module-scoped to
`source_package`)
**Lifecycle ceiling:** this manifest is a bounded provenance and integrity record for a
small self-authored fixture set. It is **not** an R1000 closure artifact, not a corpus
coverage or completeness claim, not expert legal gold, and it carries no normative
legal text. R1000 stays active.

## 1. Purpose

S03 froze a single mixed WordML fixture (`fixtures/reader/mixed-wordml.xml`,
sha256 `d2fc1cd1…`) and proved the projection plus the independent verifier over it.
S04 needs a **diverse, frozen, audited** fixture set so that independent recomputation
and resealed semantic tampering are demonstrated across more than one document shape and
so that **unsupported source classes are explicitly accounted for** instead of being
silently promoted.

This manifest records the provenance audit, the transfer decision for every audited
candidate, the case-to-file mapping, and the typed reasons the real-corpus rows were
**not** transferred. The fixtures themselves are the tracked source of truth; they are
hand-maintained, never generated from the scratch prototype, and never used as an
oracle by the code under test.

## 2. Provenance audit

Audited sources (all under gitignored `tmp/pageindex/`, `.gitignore:97`):

| Source | Kind | `authoritative` | Classification |
|---|---|---|---|
| `iteration14/reader_fixtures.py` (20 cases) | hand-written synthetic XML builders | `false` | self-authored, explicitly non-legal, non-corpus |
| `iteration15/package_fixtures.py` (2 cases) | hand-written synthetic XML builders | `false` | self-authored, explicitly non-legal, non-corpus |
| `iteration16/corpus_manifest.json` + `CONTRACT.md` | frozen manifest/report over the real `consru_export/` corpus | `false` | real corpus rows (diagnostic only, never transferred) |
| `iteration17/*` | post-fix re-measurement over the same frozen corpus selection | `false` | real corpus evidence (diagnostic only, never transferred) |

Audit dimensions applied to every candidate:

- **provenance** — self-authored in-repo vs real Consultant export corpus bytes;
- **license** — self-authored fixtures fall under the repository's own terms; no SPDX
  `LICENSE`/`COPYING`/`NOTICE` file exists in the tree and no third-party corpus
  redistribution has been license-cleared, so corpus bytes are not transferable;
- **size** — the pinned rich corpus control `p-1` is 1,955,518 bytes, above the
  iteration-16 `per_source_cap` of 1,048,576 bytes (a further bounded-selection reason,
  not the primary non-transfer reason).

The iteration-16 classification rule ("any unrecognised namespace ⇒
`unsupported_schema`") applies to that scratch prototype's whole-document model. The
Rust reader profile `reader_wordml_profile/v1` is **root-bound** (T02,
`reader_transfer_gate`); foreign *children* are part of the supported profile and do not
change the source class. That structural divergence is documented in
`prd/architecture/reader-transfer-gate.md` and is the reason the negative
`unsupported_schema` fixture is root-bound rather than namespace-set-bound.

## 3. Transfer decisions

All 12 files below were transferred to the tracked fixture directory. Provenance is
self-authored synthetic XML (hand-written, no corpus bytes); license is the repository's
own terms (no separate SPDX file in the tree); decision is `transfer`.

| File (under `.../reader/diverse/`) | sha256 | bytes | Provenance | License | Decision |
|---|---|---:|---|---|---|
| `controls.xml` | `86440c8cf2f16b88f9da919c77f04e9a2487ed3a0032305dd195aaf48e40988f` | 1047 | self-authored synthetic (it14 controls) | repository terms | transfer |
| `unknown-wordml.xml` | `afdfbd3f50377e95d31e736a14cbb2d72d1b2cd13446c4a672ebbc2037a20232` | 661 | self-authored synthetic (it14 unknown elements) | repository terms | transfer |
| `residual-and-tails.xml` | `424f7f117255472e320a1d86adb2a63d8985b97b435a262e3d2403c2767a6834` | 678 | self-authored synthetic (it14 residual/tails) | repository terms | transfer |
| `encoding.xml` | `6eaff6f86c7c542f875065f1ba383e52b0bd0703576d5fc58f90d7316807dbb2` | 848 | self-authored synthetic (it14 encoding diversity + NBSP) | repository terms | transfer |
| `empty-structure.xml` | `84a17e721a37879a8bd3e424a991168639766ec02921892bdc8994e9fcddeec4` | 574 | self-authored synthetic (it14 empty structure) | repository terms | transfer |
| `notes-nested.xml` | `36d874f81bc456583687b6189d21ae2c7f5c3621a0373c6248cbe733e4fa9a75` | 1090 | self-authored synthetic (it14 notes/tables) | repository terms | transfer |
| `fields-revisions.xml` | `4e6ca62093eefb95fa49471b41de072a8e144ac2a867ffe894c0ce507ff17b0e` | 901 | self-authored synthetic (it14 fields + it15 revisions) | repository terms | transfer |
| `navigation-demo.xml` | `b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0` | 2162 | self-authored synthetic (it15 combined demo) | repository terms | transfer |
| `text-only.xml` | `e13b8c7424100989028d95bd4c37bfadcd3970972329d93624c8da384507c55f` | 509 | self-authored synthetic (it15 minimal) | repository terms | transfer |
| `negative-not-wordml.xml` | `bbc5cd34baa0627a4d892ee64db95acf9cf0e79472c743f3a6f8559cb360420d` | 428 | self-authored synthetic (S04 negative control) | repository terms | transfer |
| `negative-unsupported-schema.xml` | `72775bca9394d2e491945fbc6e0fdc8cbbf7747e71577832e276df9eed687ed7` | 495 | self-authored synthetic (S04 negative control) | repository terms | transfer |
| `negative-namespace-absent.xml` | `adb26741e000e46a4864ab059d1ec774f66b064fea6a827f6e9000df6a805504` | 404 | self-authored synthetic (S04 negative control) | repository terms | transfer |

The nine positive fixtures have a WordML `wordDocument` root in a namespace from
`reader_contract::WORDML_NAMESPACES` and are expected to classify as
`SupportedWordml`. The three negative fixtures are expected to classify as
`SourceNotWordml`, `UnsupportedSchema` and `NamespaceAbsent` respectively; see
`prd/architecture/reader-transfer-gate.md` for the classification table.

## 4. Case-to-file mapping (iteration 14 / 15 → tracked fixture)

Every iteration-14 and iteration-15 builder case is carried by exactly one tracked file.

| Scratch case | Tracked file |
|---|---|
| it14 `page_break`, `line_break_default`, `line_break_text_wrapping`, `carriage_return`, `last_rendered_page_break`, `foreign_tab` | `controls.xml` |
| it14 `invented_page_break`, `unknown_wordml_wrapper` | `unknown-wordml.xml` |
| it14 `residual_text`, `cell_paragraph_tail`, `whitespace_only` | `residual-and-tails.xml` |
| it14 `unicode_controls`, `multibyte_ranges` (plus a non-breaking-space case) | `encoding.xml` |
| it14 `empty_paragraph`, `empty_cell` | `empty-structure.xml` |
| it14 `note_in_cell`, `table_in_note`, `cell_in_note`, `nested_notes` | `notes-nested.xml` |
| it14 `fields`, it15 `navigation_demo` revision fragment | `fields-revisions.xml` |
| it15 `navigation_demo` | `navigation-demo.xml` |
| it15 `text_only` | `text-only.xml` |

Content edits made when consolidating (audit-driven, not semantic expansion):

- the it15 `navigation_demo` legal-sounding heading (`Статья 1. Предмет
  регулирования`) was replaced with the neutral synthetic label
  `Начало демонстрации навигации`; all remaining strings are synthetic navigation
  labels, not legal norms;
- encoding diversity is retained as non-legal strings (literal Cyrillic, a numeric
  character reference producing a combining mark after `e`, a literal astral emoji, and
  a numeric non-breaking space), never as legal text.

## 5. Non-transfers and typed non-transfer reasons

No real-corpus bytes were transferred. The iteration-16 frozen manifest carries 15 rows
over `consru_export/consru_export/exports` (the full parsed export; gitignored at
`.gitignore:133`): 14 rows with `bounded_disposition = built` and one pinned control
`p-1` with `bounded_disposition = excluded_per_source_size_cap`. Row ids, paths, byte
sizes and the frozen sha256 values are reproduced from
`tmp/pageindex/iteration16/corpus_manifest.json`; the corpus bytes themselves are **not**
copied, tracked, or redistributed.

Typed non-transfer reason vocabulary:

- `not_self_authored` — the row is real Consultant export content, not hand-written
  synthetic XML;
- `redistribution_unconfirmed` — no license-cleared redistribution exists for the
  third-party corpus bytes;
- `gitignored_corpus` — `consru_export/` is gitignored (`.gitignore:133`), so the bytes
  cannot be a tracked fixture;
- `scratch_manifest_only` — the row is recorded only in the gitignored iteration-16
  scratch manifest (`.gitignore:97`); that record is diagnostic evidence, not a
  transferable artifact;
- `exceeds_per_source_cap` — the pinned source is 1,955,518 bytes, above the
  iteration-16 `per_source_cap` of 1,048,576 bytes.

The typed reason for every iteration-16 row is
`not_self_authored; redistribution_unconfirmed; gitignored_corpus; scratch_manifest_only`;
`p-1` additionally carries `exceeds_per_source_cap`.

| Row | Role | Bytes | Corpus path | Frozen disposition | Typed non-transfer reason |
|---|---|---:|---|---|---|
| `s-npa-1` | stratified | 146119 | `consru_export/consru_export/exports/npa/decree_2020-09-14_558_rev-2024-07-08_a6d600ea.xml` | built | base (see vocabulary) |
| `s-npa-2` | stratified | 51440 | `consru_export/consru_export/exports/npa/decree_2021-11-15_657_rev-unknown_4687a99e.xml` | built | base (see vocabulary) |
| `s-npa-3` | stratified | 241034 | `consru_export/consru_export/exports/npa/decree_2024-01-27_73_rev-2026-03-16_4103c3bf.xml` | built | base (see vocabulary) |
| `s-xml-1` | stratified | 15364 | `consru_export/consru_export/exports/xml/law/100074/edition-9d2bae8b54bef059d81de10e.xml` | built | base (see vocabulary) |
| `s-xml-2` | stratified | 18201 | `consru_export/consru_export/exports/xml/law/100523/edition-61f53f457653211b01a13724.xml` | built | base (see vocabulary) |
| `s-xml-3` | stratified | 21343 | `consru_export/consru_export/exports/xml/law/100940/edition-3983a122eea33492924993b7.xml` | built | base (see vocabulary) |
| `s-courts-1` | stratified | 78195 | `consru_export/consru_export/exports/courts/acn/000166280-edition-84232bdf5e80b4c2d012dbae.xml` | built | base (see vocabulary) |
| `s-courts-2` | stratified | 99071 | `consru_export/consru_export/exports/courts/acn/000166305-edition-7e6e14131f3fab621a92f158.xml` | built | base (see vocabulary) |
| `s-courts-3` | stratified | 52767 | `consru_export/consru_export/exports/courts/acn/000166335-edition-8efbaf609f51f899874f4bec.xml` | built | base (see vocabulary) |
| `s-fas-1` | stratified | 76690 | `consru_export/consru_export/exports/fas/decision_2025-01-09_04-10-18-1-17-2025_rev-unknown_d9958419.xml` | built | base (see vocabulary) |
| `s-fas-2` | stratified | 74310 | `consru_export/consru_export/exports/fas/decision_2025-01-09_04-10-18-1-18-2025_rev-unknown_fea10a63.xml` | built | base (see vocabulary) |
| `s-fas-3` | stratified | 29936 | `consru_export/consru_export/exports/fas/decision_2025-01-09_25-44-104-1_rev-unknown_eb092d4a.xml` | built | base (see vocabulary) |
| `c-1` | existing_control | 46388 | `consru_export/consru_export/exports/npa/directive_2014-04-18_631-r_rev-unknown_fb593b64.xml` | built | base (see vocabulary) |
| `c-2` | existing_control | 102716 | `consru_export/consru_export/exports/npa/law_2018-06-29_174-fz_rev-unknown_1a7dab62.xml` | built | base (see vocabulary) |
| `p-1` | pinned_rich_control | 1955518 | `consru_export/consru_export/exports/npa/directive_2020-12-17_1-14287_rev-2026-05-06_12becbcc.xml` | excluded_per_source_size_cap | base + `exceeds_per_source_cap` |

## 6. Integrity pin

`SHA256SUMS` lists every tracked XML fixture with a path relative to the repository root,
so the pin verifies without a working-directory change:

```
sha256sum -c crates/ln-decode/tests/fixtures/reader/diverse/SHA256SUMS
```

The consumer batteries additionally pin each fixture's sha256 as a Rust constant and
assert it against the actual bytes, so a fixture edit fails the battery as well as the
pin. `reader_projection_diverse.rs` also asserts that the directory holds exactly twelve
`.xml` files.

## 7. Non-claims

- Bounded, hand-authored synthetic coverage; it is not corpus coverage, not randomness,
  and not a completeness claim (INV-22).
- The fixtures are non-legal synthetic XML; raw decoded legal text is never logged or
  quoted by the batteries.
- The scratch prototype (`tmp/pageindex/iteration14`, `iteration15`) is **not** an
  oracle; the per-fixture expectations are handwritten from the fixture XML.
- The iteration-16 / iteration-17 manifest and report are `authoritative: false`
  diagnostic records; their sha256 values are cited here only as provenance evidence for
  the non-transfer decision, never as content.
- The fixture audit covers only the iteration-14 and iteration-15 self-authored builders
  plus the iteration-16 / iteration-17 corpus records named above. It makes no claim
  about any other corpus subset.
