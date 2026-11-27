## Code Review Results

**Scope:** `base:22057641e19d712b2645892174507aa5697e01d6` -> working tree (standalone on `deps/upgrade-zip-quickxml-rusqlite-cves`; 11 files, 616 changed lines, 387 executable non-test lines)
**Intent:** Upgrade `zip` (`8.6` -> `9.8.2`), `quick-xml` (`0.36` -> `0.42.0`), and `rusqlite` (`0.37` -> `0.43.0`) to resolve all 11 security advisories, remove all baseline CVE ignores from `deny.toml` and `Justfile`, and adapt `ln-decode` XML/ODT decoders to `quick-xml` 0.42 (`Event::GeneralRef`, `&str` APIs, `resolver()`, `normalized_value`) and `zip` 9.8 (fallible `entry.name()`) without weakening fail-closed parsing or changing observable text semantics. (Confidence: explicit)
**Mode:** markdown report-only

**Reviewers:** correctness, security, project-standards, testing, maintainability
- security -- untrusted ZIP/XML/ODT parsing, entity expansion boundary, and CVE ignore removal
- project-standards -- `AGENTS.md` governs all 11 changed files (instruction-file fallback)
- testing -- changed decoder tests and new `Event::GeneralRef` / `normalized_value` / `entry.name()` error branches
- maintainability -- large diff (387 executable non-test lines) refactoring 4 XML/ODT decoder modules

### Triage Groups

| Group | Findings | Context | Preferred Resolution | Why |
|-------|----------|---------|----------------------|-----|
| `quick-xml` 0.42 entity and whitespace decoding in `ln-decode` (apply-queue) | #1, #3, #5 | Migrating `ln-decode` XML decoders to `quick-xml` 0.42 added three separate `GeneralRef` resolvers, switched `WordMLStreamingDecoder` run-edge trimming from XML ASCII whitespace to Unicode `str::trim()`, and left `source_package` named/unknown entity paths untested | Extract one shared `pub(crate)` entity resolver using `quick_xml::escape::resolve_xml_entity` (#3), narrow `WordMLStreamingDecoder` run-edge trimming to XML 1.0 ASCII whitespace (#1), then add `source_package_contract` tests for predefined and unknown entities (#5) | Removing the duplicate resolvers first avoids testing three copies and lands all `ln-decode` `quick-xml` 0.42 fixes together |

*(Ungrouped: `#2` -- decision-gate / policy alignment for `zip` manifest pin and ADR-0013 versions.)*

### P2 -- Moderate

| # | File | Issue | Reviewer | Confidence |
|---|------|-------|----------|------------|
| 1 | `crates/ln-decode/src/adapters.rs:343` | `WordMLStreamingDecoder` `run_buf.trim()` strips Unicode NBSP at run edges | correctness | 100 |
| 2 | `crates/ln-decode/Cargo.toml:9` | Unpinned `zip` 9.8 and stale ADR-0013 parser crate versions | project-standards | 75 |
| 3 | `crates/ln-decode/src/adapters.rs:72` | Duplicate XML entity resolver reimplements `quick-xml` helper | maintainability | 75 |
| 5 | `crates/ln-decode/src/source_package.rs:1546` | Missing predefined and unknown entity tests in `source_package` | testing | 75 |

- **#1** -- [Mechanical fix; `protected_subject: public-contract`; single reviewer, independently validated with measured incidence] Previously `quick-xml`'s `trim_text(true)` stripped only XML 1.0 ASCII whitespace (`' '`, `'\t'`, `'\r'`, `'\n'`) before entity unescaping. Using `run_buf.trim()` now strips Unicode NBSP (`U+00A0`, literal or `&#160;`) at `<w:t>` edges, gluing adjacent runs together and changing emitted `EvidenceAnchor` `end_offset` and `fingerprint` (`crates/ln-decode/src/adapters.rs:356-369`). Independent validation observed this exact precondition in 61 of 82 tracked `law-source/consultant/*.xml` fixtures (including `reshenie-soveta-evraziiskoi-ekonomicheskoi-komissii-...--1e5dc26f.xml`). Replace `run_buf.trim()` with `run_buf.trim_matches([' ', '\t', '\r', '\n'])` (or track literal-text-only edge trimming if explicit `&#32;` at run edges must also be preserved) and add a unit test in `adapters::tests` asserting `&#160;` at `<w:t>` boundaries stays in anchor length and fingerprint.
- **#2** -- [Decision / policy alignment; single reviewer, independently validated] Both `crates/ln-decode/Cargo.toml:9` and `crates/ln-testkit/Cargo.toml:33` relaxed `zip` from exact `=8.6.0` to caret `9.8` while `Cargo.lock` resolves `9.8.2`, allowing future `cargo update` runs to advance across `9.x` minor releases despite ADR-0013's exact-pin rule (`doc/adr/0013-universal-multi-source-parser.md:269,296-297`). ADR-0013 and `prd/architecture/source-jsonl-contract.md:261` also still cite `zip = "=8.6.0"` and `quick-xml = "0.36"`. Decide whether to keep ADR-0013's exact-pin policy (recommended: pin `zip = "=9.8.2"` in both manifests) or explicitly amend ADR-0013 to allow caret `9.8`, and update ADR-0013 plus `prd/architecture/source-jsonl-contract.md` to record `quick-xml = "0.42"` and `zip = "=9.8.2"`.
- **#3** -- [Mechanical fix; single reviewer, independently validated] Three decoders (`crates/ln-decode/src/adapters.rs:72-84`, `crates/ln-decode/src/adapters/garant_odt.rs:358-376`, and `crates/ln-decode/src/source_package.rs:1537-1557`) each define their own `resolve_*_general_ref` function that hand-rolls the five predefined XML entities already provided by `quick_xml::escape::resolve_xml_entity` in `quick-xml` 0.42. Extract one `pub(crate) fn resolve_xml_general_ref(reference: &BytesRef<'_>) -> Option<Cow<'static, str>>` (for example in a small private `xml_ref` module in `crates/ln-decode/src/lib.rs`) using `reference.resolve_char_ref().ok()?` and `quick_xml::escape::resolve_xml_entity(reference.as_ref()).map(Cow::Borrowed)`, delete the three copies, and map `None` to each decoder's error type at call sites.
- **#5** -- [Mechanical test gap; single reviewer, independently validated] Zero tests in `crates/ln-decode/tests/source_package_contract.rs` or the 82 tracked `law-source/consultant/*.xml` fixtures pass predefined named XML entities or an undeclared entity without a DOCTYPE in element text to `source_package::capture`, leaving every named-entity arm and the fail-closed `MalformedXml` branch (`crates/ln-decode/src/source_package.rs:1546-1556`) unexercised. Add a contract test in `crates/ln-decode/tests/source_package_contract.rs` mirroring `crates/ln-decode/tests/garant_odt_block_decoder.rs:176` (`decodes_predefined_and_numeric_entities_and_rejects_unknown_entity`) asserting `capture()` decodes `&lt;`, `&gt;`, `&amp;`, `&quot;`, and `&apos;` in element text and rejects `<r>&unknown;</r>` with `ErrorKind::MalformedXml`.

### Actionable Findings

| # | File | Issue | Route | Notes |
|---|------|-------|-------|-------|
| 1 | `crates/ln-decode/src/adapters.rs:343` | `WordMLStreamingDecoder` `run_buf.trim()` strips Unicode NBSP at run edges | `gated_auto -> downstream-resolver` | `suggested_fix` present; mechanical fix; `requires_verification: true`; `protected_subject: public-contract` |
| 2 | `crates/ln-decode/Cargo.toml:9` | Unpinned `zip` 9.8 and stale ADR-0013 parser crate versions | `manual -> downstream-resolver` | `suggested_fix` present; confirm exact-pin vs ADR amendment before editing; `requires_verification: true` |
| 3 | `crates/ln-decode/src/adapters.rs:72` | Duplicate XML entity resolver reimplements `quick-xml` helper | `gated_auto -> downstream-resolver` | `suggested_fix` present; mechanical dedup (~40 lines removed); `requires_verification: true` |
| 5 | `crates/ln-decode/src/source_package.rs:1546` | Missing predefined and unknown entity tests in `source_package` | `gated_auto -> downstream-resolver` | `suggested_fix` present; mechanical contract test; `requires_verification: true` |

### Coverage

- **Standards criteria:** Supplied via `AGENTS.md` instruction-file fallback (no `CODING_STANDARDS.md` present).
- **Review policy:** None discovered at base (`REVIEW.md` absent); 0 findings removed or regraded by policy.
- **Settlement suppression:** Not evaluated (no plan discovered in Stage 2b).
- **Pre-review verification:** Parent orchestrator verified full workspace Tier-1 `just gate` (including all `ln-testkit` `rusqlite` port contracts) and Tier-3 `just release` (`cargo audit --no-fetch bin` with zero ignores) prior to review.
- **Cross-model peer:** Not selected (`peer.selected: false`); 0 findings skipped validation via cross-model corroboration.
- **Stage 5 synthesis:** 5 raw findings from 5 reviewers (0 malformed returns, 0 malformed findings, 0 suppressed below anchor 75, 0 demoted for missing `first_evidence`, `first_evidence_backfilled: 0`). One narrower testing-only finding (`#4`, `ConsultantWordMlBlockDecoder` entity/attribute coverage) was demoted to testing gaps under the one-umbrella-per-subsystem rule, leaving 4 primary actionable findings (`#1`, `#2`, `#3`, `#5`). Two reviewer-local test-execution-limit notes (`project-standards`, `testing`) were excluded from residual risks because Tier-1 `just gate` and Tier-3 `just release` were already verified by the parent orchestrator.
- **Stage 5b validation:** 1 independent validator batch covering all 4 selected findings (`#1`, `#2`, `#3`, `#5`; 0 shortcut-skipped). All verdicts landed inside the wait bound: 4 confirmed (`#1` classified `public-contract` with incidence directly measured across 61/82 tracked Consultant XML fixtures; `#2`, `#3`, `#5` unprotected), 0 rejected, 0 unresolved, 0 malformed, 0 failed, 0 protected-subject reclassifications, 0 degraded blockers.
- **Removable surface:** ~40 lines / 3 files across finding #3 (signal only, not a target).
- **Failed / timed-out reviewers:** None.
- **Residual risks:**
  - `quick-xml` 0.42 `NsReader` enforces new default caps of 128 in-scope namespace bindings (`DEFAULT_MAX_NAMESPACE_BINDINGS`) and 65,535 nesting depth (`u16::MAX`), so `source_package::capture` (`crates/ln-decode/src/source_package.rs:715,732`) returns `ErrorKind::MalformedXml` before `Limits::max_attrs_per_element` (default 1024) or raised `Limits::max_depth` (>65,535) are reached; retaining the 128-binding cap is intentional for the `quick-xml` DoS advisories.
  - `zip` 9.8.2 makes local-file-header vs central-directory consistency checks (`RUSTSEC-2026-0548`) opt-in via `ZipArchive::validate_header_consistency()` or `ZipReadOptions::enforce_header_consistency(true)`. `crates/ln-decode/src/adapters/garant_odt_package.rs` does not use `ZipStreamReader` or filesystem extraction, so the extraction exploit does not apply, but without opting into header consistency checks a crafted ZIP polyglot ODT with divergent local and central-directory headers can still be accepted and parsed differently from streaming viewers.
  - `crates/ln-decode/src/adapters/garant_odt_package.rs:65-67` maps `entry.name()` `Err` to `BlockDecodeErrorKind::InvalidPackage`, but `zip` 9.8.2 `ZipFile::enclosed_name()` calls `self.name().ok()?` first, so an invalid UTF-8 entry name fails on line 62 with `UnsafePackageEntry` and leaves line 67 unreachable.
  - The branch has uncommitted working-tree changes; per `AGENTS.md` GitNexus rules, run `detect_changes({scope: "all"})` before committing.
- **Testing gaps:**
  - `ConsultantWordMlBlockDecoder` (`crates/ln-decode/src/adapters.rs:76,246-254`; `crates/ln-decode/tests/consultant_wordml_block_decoder.rs`, `entity_decode.rs`): tests cover `&#167;` and `&unknown;` in `<w:t>` plus an unclosed attribute quote, but do not directly assert decoding of the five predefined XML entities (`&lt;`, `&gt;`, `&amp;`, `&quot;`, `&apos;`) in `<w:t>` or `normalized_value` entity decoding / `MalformedInput` rejection inside `<w:pStyle w:val="..."/>` (demoted from single-subsystem testing finding `#4`).
  - `WordMLStreamingDecoder::decode` (`crates/ln-decode/src/adapters.rs:332-346`): no test exercises unknown/malformed `Event::GeneralRef` skipping or multi-run paragraphs asserting exact decoded text/fingerprint (`handles_multiple_text_runs_in_single_paragraph` only asserts `emissions.len() == 1`).
  - `GarantOdtBlockDecoder` (`crates/ln-decode/src/adapters/garant_odt.rs:394,420`): no test in `garant_odt_block_decoder.rs` exercises `normalized_value` entity decoding or `MalformedInput` rejection inside `text:style-name` or `text:c` attributes.
  - `odt_package_contract.rs`: no test exercises a ZIP entry with a non-UTF-8 filename under `zip` 9.8.2's fallible `entry.name()` / `enclosed_name()` API.

---

### Verdict

> **Verdict:** Ready with fixes
>
> **Reasoning:** Zero P0/P1 blockers exist and all 11 CVEs and baseline ignores are cleared with full Tier-1 `just gate` and Tier-3 `just release` passing. Fix `#1` before merge: it is a confirmed `public-contract` regression where `WordMLStreamingDecoder`'s `run_buf.trim()` strips Unicode NBSP (`U+00A0`) at `<w:t>` edges and alters `EvidenceAnchor` length/fingerprint on 61 of 82 tracked Consultant fixtures. Address `#3` (deduplicate entity resolver), `#5` (`source_package` entity contract tests), and `#2` (`zip = "=9.8.2"` pin + ADR-0013/contract doc sync) in the same pass.
>
> **Fix order:** #3 extract shared `pub(crate)` XML entity resolver -> #1 narrow `WordMLStreamingDecoder` run trimming to XML 1.0 ASCII whitespace + regression test -> #5 add `source_package_contract` entity tests -> #2 pin `zip = "=9.8.2"` and update ADR-0013 / `source-jsonl-contract.md`

### Actionable Findings Summary

- **#1** [P2] `crates/ln-decode/src/adapters.rs:343` -- `WordMLStreamingDecoder` `run_buf.trim()` strips Unicode NBSP at run edges | response: mechanical fix (`gated_auto`) | `suggested_fix`: yes | confidence: 100
- **#3** [P2] `crates/ln-decode/src/adapters.rs:72` -- Duplicate XML entity resolver reimplements `quick-xml` helper | response: mechanical dedup (`gated_auto`) | `suggested_fix`: yes | confidence: 75
- **#5** [P2] `crates/ln-decode/src/source_package.rs:1546` -- Missing predefined and unknown entity tests in `source_package` | response: mechanical test (`gated_auto`) | `suggested_fix`: yes | confidence: 75
- **#2** [P2] `crates/ln-decode/Cargo.toml:9` -- Unpinned `zip` 9.8 and stale ADR-0013 parser crate versions | response: policy/ADR alignment (`manual`) | `suggested_fix`: yes | confidence: 75

Run artifacts: `/tmp/compound-engineering-0/ce-code-review/20261128-032532-e924d13d`

---

### Post-Review Resolution (Applied Locally Before Commit)

All four confirmed findings (`#1`, `#2`, `#3`, `#5`) plus the `ConsultantWordMlBlockDecoder` predefined-entity / attribute testing gap were resolved locally on `deps/upgrade-zip-quickxml-rusqlite-cves` before pushing PR #7:

1. **#3:** Extracted `pub(crate) fn resolve_xml_general_ref` in `crates/ln-decode/src/xml_ref.rs` backed by `BytesRef::resolve_char_ref` and `quick_xml::escape::resolve_xml_entity`, deleting the three duplicate resolvers in `adapters.rs`, `adapters/garant_odt.rs`, and `source_package.rs`.
2. **#1:** Narrowed `WordMLStreamingDecoder` run-edge trimming from Unicode `run_buf.trim()` to XML 1.0 ASCII whitespace `run_buf.trim_matches([' ', '\t', '\r', '\n'])` and added a unit regression test verifying `&#160;` (NBSP) preservation at `<w:t>` boundaries.
3. **#5 (+ WordML gap):** Added predefined-entity and fail-closed unknown-entity tests to `crates/ln-decode/tests/source_package_contract.rs` and `crates/ln-decode/tests/consultant_wordml_block_decoder.rs`.
4. **#2:** Pinned `zip = "=9.8.2"` in `crates/ln-decode/Cargo.toml` and `crates/ln-testkit/Cargo.toml` and updated `doc/adr/0013-universal-multi-source-parser.md` and `prd/architecture/source-jsonl-contract.md` to record `quick-xml = "0.42"` and `zip = "=9.8.2"`.
