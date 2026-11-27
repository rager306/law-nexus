# Docs Audit

<!-- Written by the docs auditor ($gsd-path-docs-audit (Codex) or /gsd-path-docs-audit (Antigravity/Zed/Muse) or $gsd-path-inspect (Codex) or /gsd-path-inspect (Antigravity/Zed/Muse).
     Every verdict carries evidence; a verdict without evidence is a defect. -->

Repo root: /root/law-nexus
Audited: 2026-10-31
Audited HEAD: ef17106b96e22b01719fc12a28576d226a36d1b8
Alignment mode: no

## Summary

| Verdict | Count |
|---------|-------|
| verified | 132 |
| stale | 21 |
| aspirational | 0 |
| unverifiable | 0 |
| descriptive docs (no testable claims) | 310 |

Worst drift: the current-state document `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` still tells the reader "the live state is green ... re-confirmed by the newest main run 40822037565" while the newest `main` run — 41198873586 at the audited HEAD `ef17106b`, the M011 integration — concluded **failure**: the M011 ship skipped the pinned ship-time projection refresh, so `roadmap.md`/`roadmap.json` (and that document, plus the README status band) sit one milestone behind and the pointer suites are red locally and in CI.

Verification runs executed in the pre-created sidecar at the recorded clean HEAD (branch `gsd-path-verify/inspect-docs`): `cargo run -q -p ln-product-cli -- health` (the exact README command → status ok, exit 0 — `default-run` now set), `--bin law-nexus-inspect -- inspect` on the tracked 63-ФЗ XML (status ok, blocks=586), on an empty `.xml` (blocks: 0), on a `.txt` (Parse/UnsupportedFamily, exit 1), on a missing path (Io/ReadFailure, exit 1); `replay <f> <f>` same-file (diff 0/0, drafts 0); `replay` without arguments (usage line, exit 2); `subordinates resolution` on the tracked Garant PP_60 ODT (group `government_resolution`, 246 punkt units) and on a dateless filename copy (`skip_reason: no_document_date`); `reference-package build`/`check` over the measure-ed50 fixture with the recipe-built catalog (6 `wrote` lines exit 0; `check=ok` exit 0; flipped byte → named drift row exit 6; restored → exit 0; missing catalog / empty corpus → typed exit 3; unknown flag → exit 2; no-ed50 corpus → `measurement not applicable` + 4 artifacts); `cargo test -p ln-query --offline --test retrieval_metrics` (7 passed); `cargo test -p ln-product-cli --offline --test reference_package_cli` (8 passed); `cargo fmt --all --check` and `cargo check --workspace --offline` clean; `uv run --frozen python -m law_nexus_harness.governor` (72 pass / 0 error / 0 warn, exit 0); `uv run --frozen python -m law_nexus_harness preflight` (7 pass / 1 warn / 0 error; the warn is the absent local `.gitnexus/`); `uv run --frozen python scripts/verify-adr-conformance.py` (ok, 29 files); `python3 scripts/ai/path-run.py status` (exit 0); `uv run --frozen python scripts/m205_s04_reconciliation.py check` (OK); `ruff check`/`ruff format --check` on the phase-dispatch adapter (clean); `uv run --frozen pytest -q` full suite (34 failed, 970 passed, 12 skipped, 7 errors — decomposition in the README row); `tests/test_architecture_m171_alignment.py` (1 failed, the 325-line budget), `tests/test_m221_authority_reconciliation.py::test_source_bindings_resolve_and_match_disk` (failed, sha256 drift), `tests/test_project_state_roadmap_freshness.py` (2 failed), `tests/test_post_ship_pointers.py` (1 failed). GitHub CI facts re-checked live via `gh run view` (conclusions and head SHAs as cited; newest main run 41198873586 at `ef17106b` = failure). Git history/tag checks, the sha256 fixture↔corpus disjointness run (43,785 corpus files hashed on the primary checkout), the frozen GSD-Pi DB query, the `consru_export` counts, the vendored-runtime digest (via the installer's own `source_manifest` on the extracted archive in a disposable `/tmp` tree) and the `.deprecated`/vault/`.gitnexus` filesystem checks ran read-only. `cargo clippy/test --workspace` local runs were not repeated; CI run 41198873586 proved them green at this exact commit ("Rust clippy"/"Rust tests" steps).


## Doc: README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The workspace has 47 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, `ln-kb-ontology`, `ln-consultant-parser`, and proposed `ln-applicability` (fail-closed abstention kernel only)" (README.md:12-18) | structure | verified | Cargo.toml members list has 47 entries and `crates/` has 47 dirs; `ln-kb-ontology` and `ln-consultant-parser` are members and are now named in the map table (README.md:226-227); M011 T002 fixed the band |
| "Latest tracked product/design band: **M165**" (README.md:39) | status | stale | prd/project-state/data/roadmap.json (`generated_at` 2026-10-24) records `completed_milestone_groups` through "M224-M224" status complete; `current_milestone` = doc-consistency; the README band line is unchanged (untouched by M011) |
| "The current documentation/control baseline includes post-D150 assessments 13–18" (README.md:40) | status | stale | assessment/ holds 35 files 00–34; `assessment/34-rust-npa-foundation-readiness-audit.md` is the latest; line unchanged by M011 |
| "Retired ADR IDs **0001/0002/0003/0006** have no files under `doc/adr/`" (README.md:463) | structure | verified | doc/adr/ holds 27 ADR files 0004–0031 plus README.md, none for the retired IDs; governor `adr-retired-id-ban` pass in the live run (72 pass, exit 0) |
| "Governor ADR/lifecycle probes ... include: adr-truth-oracle-sync, adr-index-completeness, adr-doc-matrix-coverage, adr-structure-hygiene, adr-cross-surface-matrix, adr-retired-id-ban, active-surface-era-noise, archive-path-policy" (README.md:408-415) | feature | verified | all 8 named `check_id`s appear ok/pass in the live governor run in the sidecar (`pass_count`:72, `error_count`:0, exit 0) |
| "`cargo run -q -p ln-product-cli -- health` # release health smoke" (README.md:416) | command | verified | ran in sidecar → `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust",...}`, exit 0 — works as written now: crates/ln-product-cli/Cargo.toml gained `default-run = "law-nexus-inspect"` (M011 T001) |
| "`cargo run -q -p ln-product-cli -- inspect <path>` # structural + retrieval inspect" (README.md:417) | command | verified | ran in sidecar on the tracked 63-ФЗ XML → `{"phase":"Inspect","status":"ok",...,"blocks":586,"hierarchy_markers":345,...}`, exit 0 |
| "`uv run python -m law_nexus_harness governor` # process + ADR/lifecycle/retired-era probes" (README.md:395) | command | verified | sidecar run → `"pass_count":72,"error_count":0,"warn_count":0,...,"status":"ok"`, exit 0 |
| "`uv run python -m law_nexus_harness preflight`" (README.md:396) | command | verified | sidecar run → `"pass_count":7,...,"warn_count":1`, exit 0; the warn is `gitnexus-index-freshness` (the local `.gitnexus/` index is absent in a clean worktree) |
| "`uv run pytest -q` # full suite; CI process suite is a subset" (README.md:397) | command | verified | sidecar run → `34 failed, 970 passed, 12 skipped, 7 errors` in 415s; the +3 delta vs the 2026-10-30 audit is the projection staleness the M011 ship left behind (freshness ×2, post-ship pointers ×1); the rest decomposes as before: the M171 one-page budget, the M221 hash-pinned binding with its readiness battery, live governor/preflight scenario tests against this worktree's branch state, the unbuilt `ln-status` binary (7 errors), and gitignored local PI-skill tooling |
| "`uv run python scripts/verify-adr-conformance.py`" (README.md:398) | command | verified | sidecar run → `{"files_scanned": 29, "finding_count": 0, "status": "ok"}`, exit 0 |
| "M205/S04 ... `prd/architecture/m205-s04-docs-reconciliation.yaml`" (README.md:262-271) | structure | verified | the YAML exists; companion verifier `scripts/m205_s04_reconciliation.py` exists |
| "A Rust workspace of twenty exclusive `ln-*` capability crates (ADR-0011)" (README.md:58) | structure | verified | 20 owner crates and 20 `ln-hcNN-runner` crates counted under crates/ and all are workspace members; governor `hostile-baseline-aggregate`: "PASS 20/20; FAIL 0/20"; sampled new suite `cargo test -p ln-product-cli --offline --test reference_package_cli` → 8 passed |
| "Requires Python 3.13+ and [uv]" (README.md:381-383) | config | verified | pyproject.toml `requires-python = ">=3.13"`; `uv --version` → 0.12.13 |
| "MADR ADRs 0004–0023 (0001/0002/0003/0006 retired, not present)" — the `doc/adr/` Active-tree row (README.md:280) | structure | stale | doc/adr/ holds 27 ADRs 0004–0031; the README itself names ADR-0024..0031 further down (README.md:292-295); row untouched by M011 |
| "the executable 47-member inventory" (README.md:304) | structure | verified | same 47-member evidence as the band row; the three mentions (README.md:13,217,304) now agree |
| "`CHANGELOG.md` — Human-readable delivery history; not architecture authority" (README map row, README.md:254) | status | verified | head entry M211-hkknug S01 remains a dated revision-bound record whose named artifacts all resolve (npa_anchor.rs, npa_members_gold_parity.rs, anchor-parity-fixture.tsv, CI job `offline-contract-verifiers`) |

## Doc: AGENTS.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Current delivery state: `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` is the current-state document" superseding `POST-SHIP-STATE-2026-10-27.md` and `CUTOVER-READINESS-M001.md` (AGENTS.md:224-227) | status | verified | all three files exist; the supersession chain is recorded in each snapshot header; content-lag drift of the named document is recorded under its own section below (rows on the M011 record and the red run) |
| "Product behavior: PDD Kit in `product-model/`, orchestration off" (AGENTS.md:275) | structure | verified | `git ls-files product-model` → 28 tracked files; the model now covers the shipped reference-package surface (coverage.md names five subcommands; capability docs present) |
| Data Sources Map: "`consru_export/consru_export/exports/` ... 43,785 files, 3.7 GB" (AGENTS.md:404) | structure | verified | re-measured on the primary checkout: find → 43,785 *.xml; du → 3.7G (gitignored, .gitignore:153) |
| Data Sources Map: "law-source/consultant/ — Fragment of the corpus (122 XML files)" (AGENTS.md:405) | structure | stale | `git ls-files` → 82 tracked XML (81 document fixtures + the `Список документов (5).xml` list file); untouched by M011 |
| "Known issue: 2,478 artifact rows in the DB contain `../`-style paths" (AGENTS.md:413,415) | status | stale | read-only query on the frozen DB /root/.gsd/projects/3495c0714df3/gsd.db → 3,074 of 8,355 artifact rows have `../` in `path` (same as the 2026-10-25 and 2026-10-30 audits; the figure is still the 2026-08-31 assessment value) |
| GitNexus block: "This project is indexed by GitNexus as **law-nexus** (43047 symbols, 102234 relationships, 584 execution flows)" and "`node .gitnexus/run.cjs analyze --force --name law-nexus`" (AGENTS.md:355-398) | integration | stale | the local `.gitnexus/` exists on the primary checkout (local-excluded; absent in the sidecar — preflight warns `gitnexus-index-freshness`), but meta.json records nodes=43059, edges=102250, processes=584, indexedAt 2026-10-26, branch gsd-path/M001, lastCommit 2a0ead24 — the block numbers still disagree and the index predates M002–M011 |
| "`src/law_nexus_harness/workflow_state.py` is the only sanctioned adapter" (AGENTS.md:306) | structure | verified | file exists |
| "`scripts/ai/allspark`", "`scripts/ai/phase-dispatch.py`", "`.gsd-path/runtime.json`" (AGENTS.md:279,295,268) | structure | verified | all three exist (the launcher on the primary root; the script tracked; runtime.json records 1.6.2 @ digest 6f95a31e…) |
| "`/root/law-nexus/.gsd` is a symlink to `/root/.gsd/projects/3495c0714df3`" (AGENTS.md:316-317,411) | structure | verified | `os.readlink` → `/root/.gsd/projects/3495c0714df3` |
| "the live successor is `scripts/verify-source-snapshot-v2.py`" (AGENTS.md:324) | structure | verified | file exists |
| "the pointer suites in CI fail on the shipped tree when it is skipped" (AGENTS.md:273-274) | feature | verified | both suites are referenced in `.github/workflows/repository-quality.yml`; demonstrated live at this HEAD: the M011 ship skipped the projection refresh and both suites fail locally (freshness 2 failed; pointers 1 failed) and in CI (run 41198873586 at `ef17106b`, failed step "Product and architecture harness tests") |
| "How to write a slice: `.agents/skills/law-nexus-rust/` — the slice-writing and review guides live under that skill's `workflows/`" (AGENTS.md:330-331) | structure | verified | the directory exists under the skill; M011 T002 replaced the dangling `workflows/implement-rust-slice.md` pointer (ruling #22) |

## Doc: prd/ARCHITECTURE.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Foundation/ontology ADR lifecycle map (ADR-0004..0031 with `[bounded]`/`[proposed]`/`[validated]` tags) (prd/ARCHITECTURE.md:46-68) | status | verified | governor `adr-truth-oracle-sync` pass in the live run: "ARCHITECTURE cites required ADRs with matching lifecycle" over the 27 tracked ADRs |
| "20/20 hostile contracts have `[bounded]` synthetic Rust runtime PASS" (prd/ARCHITECTURE.md:25) | status | verified | 20 `ln-hcNN-runner` crates tracked; governor `hostile-baseline-aggregate`: "PASS 20/20; FAIL 0/20" in the live run |
| "`ln-consultant-parser` has 10 source modules including `lib.rs`, 64 integration test functions and 4 source-unit tests" (prd/ARCHITECTURE.md:133-135) | structure | stale | actual: 31 top-level src modules (incl. lib.rs, now with reference_layer.rs) plus 14 `src/bin/` binaries; 358 `#[test]` functions under tests/; 54 `#[test]` functions in src/*.rs; sentence untouched by M011 |
| "One page. If it grows, split detail into tracked focused PRD sub-docs" (one-page living oracle) (prd/ARCHITECTURE.md:326) | structure | stale | the file is 327 lines vs tracked budget 325; its own test fails: "living oracle grew to 327 lines (budget 325)" (reproduced in the sidecar) |
| "G1 ... anchor is 119 structural hierarchy markers on the tracked 435-ФЗ fixture (`EXPECTED_HIERARCHY_COUNT` in `crates/ln-decode/tests/consultant_real_tracer.rs`)" (prd/ARCHITECTURE.md:135-137) | feature | verified | constant = 119 at consultant_real_tracer.rs:17; the 435-ФЗ fixture `law-source/consultant/...-d71bf702.xml` is tracked |
| "a bounded Rust reference-capture runtime landed under M211 (npa_anchor/npa_typed/npa_link/npa_classify/npa_continuation, npa-integration-runner)" (prd/ARCHITECTURE.md:66) | structure | verified | all five modules exist in crates/ln-decode/src/; runner at crates/ln-decode/src/bin/npa-integration-runner.rs |
| "`python_archive/product/`", "`python_archive/acp_git_lex/`" (prd/ARCHITECTURE.md:275) | structure | verified | gitignored (.gitignore:27); both exist in the primary checkout; governor `archive-path-policy` pass |
| "Values 3772/3641/2619/502 ... come from gitignored `consru_export`; ... skip-capable when the export is absent" (prd/ARCHITECTURE.md:147) | config | verified | .gitignore:153 `consru_export/`; export present on primary (43,785 files), absent in the sidecar; governor `corpus-grounding`: "corpus absent; advisory corpus-grounding check skipped" in the sidecar run |
| "the observable product CLI `law-nexus-inspect`" (prd/ARCHITECTURE.md:128,255) | structure | verified | crates/ln-product-cli/Cargo.toml `[[bin]] name = "law-nexus-inspect"` plus `default-run`; dispatch covers health/inspect/replay/subordinates/reference-package (main.rs:746-773); live health run → status ok, exit 0 |
| KB ontology inventory (`ln-kb-ontology` write-set crate; `fold_membership_at`, `mint_work`/`compare_work_identities`, `try_push_node`/`try_push_edge`, `map_hierarchy_marker`, `fold_expression_presence`, `join_force_with_membership`, `DecodePrefixCatalog`, `legal_act_effect_day_to_ordinal`, product-cli `lift_extracted_hierarchy`) (prd/ARCHITECTURE.md:74-91) | feature | verified | all names resolve under crates/: fold_membership_at/try_push_*/fold_expression_presence in ln-kb-ontology/src, mint_work (ln-identity/src and ln-kb-ontology/src/frbr_bridge.rs), compare_work_identities in ln-identity/src, join_force_with_membership and legal_act_effect_day_to_ordinal in ln-temporal/src, map_hierarchy_marker in ln-consultant-parser/src/edition_timeline.rs, DecodePrefixCatalog in ln-decode/src/hierarchy.rs, lift_extracted_hierarchy in ln-product-cli/src/main.rs |
| "no live RuVector/TEI product path", "Historical FalkorDB is not active infrastructure" (prd/ARCHITECTURE.md:32-42,160) | status | verified | Cargo.lock has no ruvector/falkordb/pyo3 entries; governor `live-adapter-readiness` pass ("within evidence ceiling") |
| "**Consultant XML parser hardening** — `[bounded]` through M086–M105: 81 XML source files" (prd/ARCHITECTURE.md:282) | structure | verified | 82 tracked .xml under law-source/consultant/ = 81 document fixtures + the `Список документов (5).xml` list file |
| ADR-0031 row update: "**Module code exists at measurement level:** the Rust `reference_layer` module composes the artifact set ... exposed as the `law-nexus-inspect reference-package build\|check` composition, proven on the tracked measure-ed50 fixture under the 0/2/3/6 exit contract (5 reserved, not emitted). **Corpus-wide D5/D4 execution unproven:** ... no corpus-wide execution and no committed corpus-wide artifact" (prd/ARCHITECTURE.md:68) | status | verified | reference_layer.rs exists (EXIT_ARGV/EXIT_INPUT/EXIT_DRIFT, try_derive, run_check, measurement_applicable, no exit-5 emission); live sidecar probes: build → 6 `wrote` lines, exit 0; check → `check=ok artifacts byte-identical`, exit 0; flipped artifact byte → named drift row on stderr, exit 6; restored → exit 0; no-ed50 corpus → `measurement not applicable: corpus has no edition 50` + 4 core artifacts only; suite `cargo test -p ln-product-cli --offline --test reference_package_cli` → 8 passed; the committed prd/migration/rust-evidence/m217-reference-{pageindex,references}.json are single-act measurement artifacts (3003 nodes / 379 candidates), not corpus-wide |

## Doc: doc/adr/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Current ADRs" index 0004–0031 with per-ADR statuses/lifecycles | status | verified | unchanged: 27 ADR files on disk; every listed status matches the file frontmatter (0025/0026/0027 Accepted; 0028–0031 Proposed) and D098 tags; governor `adr-index-completeness` pass |
| ADR-0025..0031 index rows (table following the `fold_expression_presence`/`map_hierarchy_marker` comments) (doc/adr/README.md:64-74) | structure | stale | the 7 table rows still have no header/separator row — they directly follow two HTML comments after "## Retired Python-era records", so the index renders as plain pipe text, not a table (file untouched by M011) |
| "active ADR frontmatter uses canonical `supersedes` and `superseded_by` keys. The legacy misspelling `superseds` ... is rejected on active ADRs by Governor" (doc/adr/README.md:17-20) | config | verified | unchanged: frontmatter scan: only canonical keys (0005 `superseded_by: [ADR-0011#crate-map-only]`; 0011/0017 supersedes chained); governor `adr-supersession-graph` pass: "adr_nodes=27, supersession_edges=2, cycles=0" |
| "ADR-0001, ADR-0002 and ADR-0003 ... ADR-0006 ... local vault is gitignored, untracked" (doc/adr/README.md:57-63) | structure | verified | unchanged: no 0001/0002/0003/0006 files under doc/adr/; vault roots (.lex/, archive/, python_archive/) gitignored and present only on the primary checkout (governor `archive-path-policy` pass) |

## Doc: doc/adr-architecture-cross-matrix.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "## 1. Present ADR inventory" table enumerates 0004–0024 as the present ADR set (doc/adr-architecture-cross-matrix.md:7-24) | structure | stale | doc/adr/ contains 0025–0031 (7 further active ADRs); ADR-0025/0026/0027/0030/0031 are not mentioned anywhere in the matrix (0028/0029 only in passing); file untouched by M011 |

## Doc: CHANGELOG.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| M211-hkknug S01 entry: `ln-decode/src/npa_anchor.rs`; `tests/npa_members_gold_parity.rs` + TSV fixture `anchor-parity-fixture.tsv`; CI job `offline-contract-verifiers` (CHANGELOG.md:5-23) | structure | verified | npa_anchor.rs exists; crates/ln-decode/tests/npa_members_gold_parity.rs exists; crates/ln-decode/tests/fixtures/npa-members/anchor-parity-fixture.tsv exists; `.github/workflows/repository-quality.yml:364` defines job `offline-contract-verifiers` |
| Self-description (via README map): "Human-readable delivery history; not architecture authority" | status | verified | unchanged: content is dated, revision-bound milestone records; the head entries' file claims all resolve (checked above) |

## Doc: prd/PRODUCT.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Planning baseline: `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)" (prd/PRODUCT.md:4) | status | verified | unchanged: commit exists, dated 2026-08-11 ("chore: keep .agents/skills local-only (gitignored)") |
| "EA-02 tested revision: `37f82c4245642f7c1e9104f288db43df762178fe` (`assessment/02-product-contract.md`)" (prd/PRODUCT.md:5) | status | verified | unchanged: commit exists: "docs: establish product contract assessment package" |
| "`[proposed]` Product Contract; document state `ready-for-assessment`" (prd/PRODUCT.md:3) | status | verified | README.md:261-263 still frames EA-10 D150 as accepting the assessment packet without promoting the `[proposed]` documents; PRODUCT.md/REQUIREMENTS.md unchanged |

## Doc: prd/REQUIREMENTS.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Planning baseline: `60fd8245...` (2026-08-11)" (prd/REQUIREMENTS.md:5) | status | verified | unchanged: same commit as the PRODUCT.md row |
| "EA-02 tested revision: `37f82c42...`" (prd/REQUIREMENTS.md:6) | status | verified | unchanged: same commit as the PRODUCT.md row |
| "document state `ready-for-assessment`"; "`prd/ARCHITECTURE.md` currently labels the same design sequence L1–L7" (prd/REQUIREMENTS.md:4,10) | status | verified | ARCHITECTURE.md still uses L1–L7 for ADR-0016..0022 (Foundation ADR map row "Temporal legal ontology L1–L7"); both documents keep `[proposed]` |

## Doc: prd/temporal-legal-model.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "TL-G01–12 gates" | structure | verified | unchanged: TL-G01..TL-G12 all present; sorted unique = exactly G01–G12 |
| "explicit 14-area completeness matrix" (§14) | structure | verified | "## 14. Primary-critique contract completeness matrix" at prd/temporal-legal-model.md:384 |
| "EA-03 tested revision: `e1ac83a714e20a6b551d5305fc4fca9f29d91aa7`" (prd/temporal-legal-model.md:4) | status | verified | unchanged: commit exists: "docs: add temporal legal model crosswalk" |

## Doc: prd/parser/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Canonical artifacts: `prd/parser/schemas/*.json` (5), `profiles/{consultant_wordml,garant_odt}.yaml`, `examples/*.jsonl` (3), `odt_smoke_records.{json,md}` (prd/parser/README.md:13-20) | structure | verified | unchanged: all listed files exist with the stated counts (5 schemas, 2 profiles, 3 jsonl examples, both smoke records) |
| "the PP filename mismatch (`PP_60_27-02-2022.odt` stated vs `PP_60_27-01-2022.odt` observed) must remain visible" (prd/parser/README.md:35,136) | structure | verified | unchanged: law-source/garant/PP_60_27-01-2022.odt is the tracked file; no 27-02 variant tracked |
| "Large Python-era dumps ... relocated to `prd/archive/parser-dumps-era/` (gitignored archaeology)" (prd/parser/README.md:9,19) | structure | verified | .gitignore:136 `prd/archive/parser-dumps-era/`; vault absent from the clean sidecar checkout (untracked); governor `archive-path-policy` vault list `src/law_nexus_harness/governor.py:4800` |

## Doc: prd/retrieval/rust_retrieval_output_validator_contract.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Contract version string `retrieval-output-validator/rust-v1`, exported as `ln_query::retrieval_output::VALIDATOR_CONTRACT_VERSION`" | feature | verified | crates/ln-query/src/retrieval_output.rs:22 → `pub const VALIDATOR_CONTRACT_VERSION: &str = "retrieval-output-validator/rust-v1";` |

## Doc: prd/retrieval/rust_retrieval_metrics_proof.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Computation surface: `crates/ln-query/src/retrieval_metrics.rs`"; "Consuming test: `crates/ln-query/tests/retrieval_metrics.rs`" | structure | verified | unchanged: both files exist |
| "proof_command: `cargo test -p ln-query --offline --test retrieval_metrics`" | command | verified | re-ran in sidecar: "test result: ok. 7 passed; 0 failed" in 2.40s — the deterministic proof reproduces at HEAD |

## Doc: prd/project-state/roadmap.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Latest completed product milestone: M173, inspect PP_60 class-matched punkt proof" (roadmap.md:43-44) | status | stale | the doc's own data source prd/project-state/data/roadmap.json records `completed_milestone_groups` through "M224-M224" complete (generated_at 2026-10-24); the line is unchanged and the freshness framing below does not cover it |
| "Until native Path state exists and the bootstrap PR is accepted on the default branch, this projection keeps describing the **frozen legacy GSD-Pi milestone ledger**" (roadmap.md:9-16) | status | stale | the condition lapsed: native Path state exists and bootstrap PR #1 merged (`54a495cd`, 2026-10-25); the projection carries native shipped markers for M007 and M010 (roadmap.md:50-62) |
| "Initial front synchronization was frozen in EA-05 at `94d58ea`"; EA-09 packet `120d44b` (roadmap.md:7) | status | verified | unchanged: both commits exist ("docs: synchronize roadmap and readiness front"; "docs: record EA-09 independent desk assessment") |
| Active Direction Contract block (runtime=rust-only; python=repository-control-only; graph_vector=ruvector; ...) (roadmap.md:25-33) | config | verified | the 7-line block is identical in prd/ARCHITECTURE.md (Active Direction Contract); governor `architecture-direction-contract` pass |
| "Local GSD workflow marker: doc-consistency is the current milestone — shipped/archived/integrated (2026-10-29) on branch `gsd-path/M010` ... Current-state document: `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`" (roadmap.md:50-56) | status | stale | the recorded M010 facts still check out (ship `fd60893f`, integration `3a39fd70`, tag `milestone/010-doc-consistency`, run 40805352394 success), but "is the current milestone" is now false: M011 shipped/archived/integrated 2026-10-31 (ship `38abe687`, integration `ef17106b` — the audited HEAD, tag `milestone/011-reference-front-door`, archive `.project/archive/011-reference-front-door`, STATE.md shipped/done reference-front-door) and roadmap.md gained no M011 marker or history bullet; `test_project_state_roadmap_freshness.py` fails (test_native_marker_names_the_operational_milestone, test_every_archived_milestone_has_a_dated_history_bullet) |
| "Local GSD workflow marker (superseded 2026-10-28): ci-proof-inputs — ship commit `e311f0ed`, integration merge `50386e26` into `main`, tag `milestone/007-ci-proof-inputs`, archive `.project/archive/007-ci-proof-inputs`" (roadmap.md:57-60) | status | verified | unchanged: commit subjects/dates match ("ship: M007 — ci-proof-inputs"; "integrate: M007 — merge gsd-path/M007 into main"); tag exists; archive directory exists |

## Doc: law-source/consultant/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "82 XML-документа КонсультантПлюс" (tracked fixtures) (law-source/consultant/README.md:7) | structure | verified | unchanged: `git ls-files 'law-source/consultant/*.xml'` → 82 |
| "Плюс подкаталог `.deprecated/` (40 файлов) — ... остаётся на диске только как история" (law-source/consultant/README.md:9) | status | stale | `.deprecated/` still does not exist on the primary checkout; only the gitignore entry remains and the governor observes "ignored and untracked" |
| Corpus counts: "43 785 файлов, включая `npa/` 916, `fas/` 30 399, `courts/` 5 667, `xml/` 6 803" (law-source/consultant/README.md:15) | structure | verified | unchanged: primary-checkout find counts: 43,785 / 916 / 30,399 / 5,667 / 6,803 — exact |
| "Проверено по sha256: пересечение = 0 файлов" (fixture set disjoint from corpus) (law-source/consultant/README.md:16) | feature | verified | ran the check in this audit: sha256 of all 43,785 corpus files under consru_export/consru_export/exports/ vs the 82 tracked fixture hashes → intersection = 0 |
| "В корпусе — 118 редакций: `consru_export/.../npa/law_2013-04-05_44-fz/edition-NNNN_*.xml`" (law-source/consultant/README.md:19) | structure | verified | unchanged: `ls consru_export/consru_export/exports/npa/law_2013-04-05_44-fz \| wc -l` → 118 on the primary checkout |
| Canonical fixtures: `...-44-fz-...-f9c8ca4c.xml`, `Список документов (5).xml` (law-source/consultant/README.md:31-32) | structure | verified | unchanged: both files tracked under law-source/consultant/ |
| "Governor-проверка `law-source-fixture-guard` покрывает только маркер fixture vault в этом README (плюс состояние `.deprecated/` в `.gitignore`) — глоббинг каталога как корпуса она не замечает" (law-source/consultant/README.md:35) | feature | verified | governor `check_law_source_fixture_guard` (src/law_nexus_harness/governor.py:5118) reads only the README fixture-vault marker and the `.deprecated` .gitignore state; static sweep of src/, scripts/, tests/ finds no corpus glob of law-source/consultant (m207 scripts pin it as fixture-only), exactly as the README now states |
| "См. также: ... `prd/architecture/npa-skeleton-fsm.yaml`" (law-source/consultant/README.md:48) | structure | verified | unchanged: file exists |

## Doc: law-source/consultant/okf/index.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Portable Open Knowledge Format (OKF) catalogue of the XML legal-document sources in this directory" (81 linked documents) | structure | verified | unchanged: 81 links, all resolve to existing documents/*.md; 81 files on disk; zero orphans in either direction |

## Doc: docs/agent-stack/WORKFLOW.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Описание product behavior — PDD, `product-model/`" (ownership table, docs/agent-stack/WORKFLOW.md:14) | structure | verified | product-model/ populated with the PDD capability model at the baseline checkout: 28 Markdown files on disk, exactly the frozen inventory set (capabilities/, entities/, business-rules/, interfaces/, coverage.md) |
| "`.ai/path-run.json` — **настройка нашей обёртки**" with the profile block (schema 1, projectDir .project, worker scripts/ai/allspark-worker -p, capacity 1, childTimeoutSeconds 900, pollSeconds 5, maxAttempts 1) (docs/agent-stack/WORKFLOW.md:26-44) | config | verified | unchanged: the tracked-side `.ai/path-run.json` on the primary checkout matches the documented profile field-for-field; `scripts/ai/allspark-worker` exists |
| "`.gsd-path/runtime.json`" (docs/agent-stack/WORKFLOW.md:13) | config | verified | unchanged: file exists: `{"schema": "gsd-path/runtime/v1", "version": "1.6.2", "digest": "6f95a31e..."}` |

## Doc: docs/agent-stack/PHASE-ADAPTER.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "`scripts/ai/phase-dispatch.py` is the repo-owned glue" (docs/agent-stack/PHASE-ADAPTER.md:3) | structure | verified | file exists (608 lines) with its stub-child test suite `tests/test_phase_dispatch_adapter.py` |
| Header status: "The adapter is verified against deterministic stub children only. No real Allspark/model pilot has been run, no native phase gate has consumed its records, and the acceptance table in §8 below is **not yet satisfied**" (docs/agent-stack/PHASE-ADAPTER.md:10-14) | status | stale | still contradicted by the same document: §9 (line 247) says "PARTIALLY satisfied — Three rows were proven by a real-model pilot on 2026-10-25 (see §9.1)"; file untouched by M011 |
| "## 9. Acceptance status — PARTIALLY satisfied. Three rows were proven by a real-model pilot on 2026-10-25" + §9.1 pilot record (docs/agent-stack/PHASE-ADAPTER.md:247-296) | status | verified | unchanged: consistent with the archived dispatch records and with the doc's explicit non-proof list; the "What this pilot does NOT prove" boundaries are preserved |
| "uv run ruff check scripts/ai/phase-dispatch.py tests/test_phase_dispatch_adapter.py; uv run ruff format --check ..." (docs/agent-stack/PHASE-ADAPTER.md:304-305) | command | verified | both ran in the sidecar → "All checks passed!" / "2 files already formatted" |

## Doc: docs/agent-stack/POST-SHIP-STATE-2026-10-28.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Shipped-milestones table M001–M003 (ship `886a36a8`/`ba31ffb8`/`7786d5d3`, integration `4e0cd4db`/`f9061889`/`7e200294`, tags, archives) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:18-23) | structure | verified | all six commits exist with the exact subjects/dates; the three annotated tags resolve to the integration merges; the three `.project/archive/` directories exist |
| "bootstrap PR merge (`54a495cd`)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:15-16) | status | verified | commit exists: "Merge pull request #1 from rager306/chore/allspark-path-pdd-bootstrap" (2026-10-25) |
| CI red table: runs 40446077586 @`4e0cd4db`, 40533158703 @`f9061889`, 40632991938 @`7e200294` concluded failure (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:65-70) | status | verified | live `gh run view` → failure/failure/failure at exactly those head SHAs (re-checked in this audit) |
| "The last green `repository-quality` run on `main` then was run 40203533977 (2026-10-25, on the bootstrap merge `54a495cd`)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:61-63) | status | verified | live `gh run view 40203533977` → success at `54a495cd` |
| M001 delivered: M225 rerun `prd/migration/rust-evidence/m225-validation-rerun-m001.json` verdict `hermetic-pass-parity-unproven`; minimal PDD model in `product-model/`; GitNexus re-indexed (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:29-34) | status | verified | the JSON exists; product-model/ tracked (28 files); `.gitnexus/` present on the primary (indexedAt 2026-10-26) |
| "vendored at `.ai/vendor/gsd-path-1.6.2.tgz`, digest-verified against `.gsd-path/runtime.json` (`1.6.2@6f95a31e…`)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:36-37,152-153) | config | verified | the tgz is tracked and contains `gsd-path/scripts/install.py`; running the installer's own `source_manifest` over the extracted tree yields exactly `{"schema":"gsd-path/runtime/v1","version":"1.6.2","digest":"6f95a31e4b8a…d9f6f"}` matching `.gsd-path/runtime.json` (the digest is a runtime-manifest digest, not archive bytes); the restore itself was not executed (it writes a machine-local runtime store) |
| M005–M009 table (ship/integration per milestone) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:136-143) | structure | verified | all ten commits exist with matching subjects/dates (e890831e/121a2006, 7d1c62c2/3e047fe8, e311f0ed/50386e26, 63c7d07d/4dd35d25, 5e5fdaee/319a7b1a) |
| "40805352394 — `319a7b1a` (M009) — success — all four jobs" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:130-132) | status | verified | live `gh run view` → success at `319a7b1a` |
| "`prd/project-state/workflow-backend.json` `cutover` stays `false`" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:144-146) | status | verified | file content: `{"schema": 1, "backend": "gsd-path", "cutover": false}` |
| "## M004 continuation (superseded)" — "This section is dated history. M004–M010 shipped and integrated ... at the 2026-10-30 docs audit the workflow state is shipped/done M010 with M011 inspect active" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:95-103) | status | verified | M011 T002 reframed the section accurately: M004–M010 ship/integration commits and tags all verify; the M011-inspect-active sentence is explicitly dated to the 2026-10-30 audit and remains true as dated history (STATE.md at the audited HEAD has since moved to shipped/done reference-front-door — recorded as its own row below) |
| Non-claims: "Integrated `main` is green on `repository-quality` since the M009 integration (run 40805352394 at `319a7b1a`; re-confirmed by main run 40822037565 at `3a39fd70`, recorded 2026-10-30) — the pre-M005 red rows in the CI section above stay as dated history" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:207-211) | status | stale | the two cited runs are success (live `gh run view`), but the newest `main` run at the audited HEAD is 41198873586 at `ef17106b` (the M011 integration, 2026-10-31) and it concluded **failure** (failed step "Product and architecture harness tests" — the projection suites the M011 ship skipped refreshing); "is green" no longer describes integrated main |
| Fresh-session bootstrap commands (`tar -xzf .ai/vendor/gsd-path-1.6.2.tgz` + `install.py --runtime-restore`; `python3 scripts/ai/path-run.py status`; `uv run --frozen python -m law_nexus_harness.governor`; `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:158-200) | command | verified | path-run.py status ran in the sidecar (exit 0, honest state JSON naming the M011 shipped/done state); governor ran exit 0 (72 pass, 0 error, 0 warn); the vendored archive contains `gsd-path/scripts/install.py` and its pin algorithm reproduces the recorded digest (row above); the restore itself was not executed (writes a machine-local runtime store); the freshness expectation of step 4 is recorded as its own stale row below |
| CI-section intro: "The live state is green: see \"M005–M009: red CI cleared\" below — run 40805352394 at `319a7b1a` success, re-confirmed by the newest main run 40822037565 at `3a39fd70` success (recorded by the 2026-10-30 docs audit)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:54-58) | status | stale | runs 40805352394 and 40822037565 are success (live `gh run view`), but 40822037565 is no longer the newest main run: run 41198873586 at `ef17106b` (M011 integration, 2026-10-31) concluded **failure** — the live state on integrated main is red again |
| "Role: current-state document for the `law-nexus` repository" with the delivered record ending at M010 and "M011 inspect active" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:5-7,97-100) | status | stale | M011 shipped and integrated on 2026-10-31 (ship `38abe687` touching only `.project/`, integration `ef17106b` = the audited HEAD, tag `milestone/011-reference-front-door`, archive `.project/archive/011-reference-front-door`; STATE.md = shipped/done reference-front-door) and the document does not record it — the designated current-state document is one milestone behind the repository it describes |
| Fresh-session bootstrap step 4: "Run the roadmap freshness guard — expect all tests to pass" (`uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:191-196) | command | stale | sidecar run at the audited HEAD: `2 failed, 4 passed, 5 skipped` (test_native_marker_names_the_operational_milestone, test_every_archived_milestone_has_a_dated_history_bullet) — the expectation the document sets does not hold because the M011 ship skipped the projection refresh |

## Doc: docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The pointer suites (`tests/test_post_ship_pointers.py`, `tests/test_project_state_roadmap_freshness.py`) run in CI and fail on the shipped tree when this is skipped" (docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:19-20) | feature | verified | both test files are referenced in `.github/workflows/repository-quality.yml`; demonstrated live: M011 shipped without the refresh and both suites fail at `ef17106b` (freshness 2 failed, pointers 1 failed); CI run 41198873586 at `ef17106b` failed on the step running them |
| "the ship commit may only change `.project/`" (docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:17-18) | structure | verified | `git show --name-only fd60893f` → only `.project/...` paths; the M011 ship `38abe687` likewise touches only `.project/` paths (but no `docs:` projection refresh preceded it — the very skip this document exists to prevent) |

## Doc: .agents/skills/law-nexus-rust/SKILL.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Python product code is archived prior art under `python_archive/product/`" (SKILL.md:12) | structure | verified | unchanged: gitignored (.gitignore:27); exists in the primary checkout |
| References: `references/verification-matrix.md`, `doc/adr/0015-...`, `prd/temporal-legal-model.md` §3, `prd/architecture/temporal-vocabulary-contract.json` (SKILL.md:17,20,43,49) | structure | verified | unchanged: all referenced paths exist |
| "follow project GitNexus impact-analysis requirements" (SKILL.md:29) | structure | verified | the AGENTS.md GitNexus contract exists and the local `.gitnexus/` index is present on the primary checkout (index staleness is recorded as the AGENTS.md row / queue #38) |

## Doc: .agents/skills/law-nexus-rust/references/verification-matrix.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Default command set (`cargo fmt --all --check`, `cargo check/test/clippy --workspace --offline`, `uv run law-nexus-harness governor/preflight`, `uv run python scripts/verify-adr-conformance.py`) (verification-matrix.md:26-66) | command | verified | `law-nexus-harness` console script declared (pyproject.toml); fmt and `cargo check --workspace --offline` ran clean in the sidecar; governor/preflight/conformance executed here (README section); `cargo clippy/test --workspace` proven green at this exact commit by CI run 41198873586 steps "Rust clippy"/"Rust tests" at `ef17106b` |
| Contract suites `npa_corpus_sweep_contract`, `morphology_contract` (verification-matrix.md:31) | structure | verified | crates/ln-decode/tests/npa_corpus_sweep_contract.rs and morphology_contract.rs exist |
| "`scripts/m205_s04_reconciliation.py check` plus its subprocess adversarial suite (`scripts/test_m205_s04_reconciliation.py`)" (verification-matrix.md:101-102) | command | verified | ran in the sidecar: `uv run --frozen python scripts/m205_s04_reconciliation.py check` → "S04 verifier: OK", exit 0; the adversarial suite file exists |

## Doc: .agents/skills/law-nexus-rust/UPSTREAM.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Upstream `SKILL.md` SHA-256: `5a74070e...`" at pinned commit `fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9` (UPSTREAM.md:6,9) | status | verified | unchanged: fetched raw.githubusercontent.com at that commit → sha256 exact match `5a74070e740c8aacec1264adfc537daeab14c0f629bb604943295c08fd9252e6` |
| "Upstream `LICENSE` SHA-256: `663ce6f8...`" (UPSTREAM.md:10) | status | verified | unchanged: same fetch → sha256 exact match `663ce6f8f087dc366602ac34eefd4cf71a5d8db411359422298a1399a014a9d5` |
| "identifies itself as ... 265 rules"; "Upstream version in frontmatter: 1.5.1" (UPSTREAM.md:8,15) | status | verified | unchanged: fetched upstream SKILL.md frontmatter: version "1.5.1", "265 rules across 26 categories" |

## Doc: .agents/skills/law-nexus-subagent/SKILL.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Live discovery path is `~/.gsd/agent/agents/`, not project `.pi/agents` or `.gsd/agents`" (SKILL.md:10,13,51) | structure | verified | unchanged: /root/.gsd/agent/agents/ exists with `_CONTRACT.md` and role files incl. scout/reviewer/worker/researcher/tester/planner; no `.pi/` in the repository |

## Doc: prd/architecture/npa-analysis-jsonl-contract.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Tracked as an M221 authority-reconciliation source binding (hash-pinned companion) (`prd/architecture/m221-s05-docs-reconciliation.yaml` binds path+sha256) | status | stale | `pytest tests/test_m221_authority_reconciliation.py::test_source_bindings_resolve_and_match_disk` still fails: "PinContractError: sha256 drift for source binding: prd/architecture/npa-analysis-jsonl-contract.md" (reproduced in the sidecar; the M221 s05 readiness battery fails with it) |

## Doc: product-model/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "This directory is the **Product Model** of this repository ... plain Markdown tracked in Git" (product-model/README.md:1-6) | structure | verified | unchanged: `git ls-files product-model` → 28 tracked files (25 Markdown) |
| "use the `pdd-verify` skill ... `pdd-ideate` ... `pdd-map`" (product-model/README.md:14-22) | integration | verified | unchanged: the three PDD skills are installed at `.agents/skills/pdd-{verify,ideate,map}/` on the primary checkout (local skill tree; the `npx pdd-toolkit install` fallback is an installed-dependency command and was not run) |

## Doc: product-model/product.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "One binary, `law-nexus-inspect`, decodes a document file (Consultant WordML or Garant ODT) ... compares two editions ... or resolves the punkt structure of a subordinate act" (product-model/product.md:21-24) | feature | verified | main.rs dispatches health/inspect/replay/subordinates/reference-package (main.rs:746-773); live inspect on a Consultant XML and subordinates on a Garant ODT both returned status ok; the described behaviors all still exist (the fifth subcommand does not remove them) |
| "Only Consultant WordML (.xml) and Garant ODT (.odt) inputs are accepted" (product-model/product.md:32) | feature | verified | live probe: `inspect /tmp/aud-cli/probe.txt` → `{"phase":"Parse","status":"failed","kind":"UnsupportedFamily",...}`, exit 1 |
| "Retrieval ... exercised through `StubEmbedding`, the fail-closed stub of the embedding port" (product-model/product.md:31,14) | feature | verified | `struct StubEmbedding; impl EmbeddingPort for StubEmbedding` at main.rs:64-65; inspect report carries the retrieval count with status ok/unavailable/unexpected_result semantics; no semantic embedding dependency in Cargo.lock |

## Doc: product-model/business-rules/failures-are-typed-and-atomic.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "A command that cannot complete prints exactly one failure record naming its phase and kind and exits nonzero ... usage errors print the usage line and exit 2 before any input is read" (failures-are-typed-and-atomic.md:11-20; appliesTo: inspect-document, replay-edition, resolve-subordinates) | feature | verified | live probes: missing path → `{"phase":"Io","kind":"ReadFailure",...,"fingerprint":"fnv1a64:...","duration_ms":...}`, exit 1; `.txt` path → Parse/UnsupportedFamily, exit 1; `replay` without arguments → usage line, exit 2 (main.rs:101-106,755-781) |

## Doc: product-model/business-rules/reports-carry-explicit-non-claims.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The inspect, replay, and subordinates reports each end with a `non_claims` list" (reports-carry-explicit-non-claims.md:13; appliesTo: inspect-document, replay-edition, resolve-subordinates) | feature | verified | live tails: inspect report ends with the `non_claims` array (emitted at main.rs:553), replay with its four non-claims, subordinates with its fixture non-claims (main.rs:1291); present in every live probe output |

## Doc: product-model/business-rules/retrieval-is-deterministic-non-semantic.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The retrieval count ... comes from hash-derived vectors over the in-memory store, ranked by cosine similarity; ... a construction failure is a typed storage error, never a silent all-zero vector" (retrieval-is-deterministic-non-semantic.md:11-18) | feature | verified | StubEmbedding hash-derived vectors (main.rs:64-65); inspect report carries the retrieval count; no semantic embedding dependency in Cargo.lock |

## Doc: product-model/business-rules/runs-keep-nothing-between-runs.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Every command builds its stores in memory, prints its report, and exits; no document, count, vector, or graph node survives the process" (runs-keep-nothing-between-runs.md:11-20; appliesTo: check-health, inspect-document, replay-edition, resolve-subordinates) | feature | verified | main.rs builds per-run in-memory stores (InMemoryVectorStore/InMemoryGraphStore via ln-storage) and writes no files in the four scoped commands; the new reference-package capability is not in `appliesTo` and writes only the operator-requested `--out-dir` package (main.rs reference_package), so the scoped rule stays true as written |

## Doc: product-model/capabilities/check-health/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The health subcommand reads no input, prints one JSON status line, and exits 0" (check-health/capability.md:6-8) | feature | verified | unchanged: live run → `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust",...}`, exit 0 |

## Doc: product-model/capabilities/check-health/scenarios/health-ok.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The status line prints with `status: ok`, naming `law-nexus-inspect` and the Rust runtime, and the command exits 0" (health-ok.md:37-38) | feature | verified | unchanged: live probe output names binary law-nexus-inspect and runtime rust, exit 0 |

## Doc: product-model/capabilities/inspect-document/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Decode one act file and print a bounded JSON report ... blocks, hierarchy markers and their registry lifts, membership proposals, admits, and commits, the structural AST assembly with its oracle drift counters, text-CTV resolutions, the detected document group, reference, temporal, and deontic counts, one retrieval hit count, and the presence report ... in-memory adapters ... StubEmbedding ... every report ends with an explicit non-claims list" (inspect-document/capability.md:9-24) | feature | verified | live inspect on the tracked 63-ФЗ XML printed exactly these sections (blocks/hierarchy_markers/lifts/membership_*/... counters and the closing `non_claims` array); store wiring via the in-memory adapters (main.rs); StubEmbedding at main.rs:64-65 |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-consultant-document.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints with status ok: counted blocks, markers, lifts, membership, assembly, retrieval, ... and the non-claims list" for a Consultant WordML path (inspect-consultant-document.md:37-59) | feature | verified | unchanged: live run on the tracked 63-ФЗ XML: `{"phase":"Inspect","status":"ok",...,"source":{path,bytes,fingerprint},"family":"family:consultant-wordml","result":{"blocks":586,...}}` with non_claims, exit 0 |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-empty-input-is-explicit-zero.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints with status ok and `blocks: 0`; the empty result is visible" (inspect-empty-input-is-explicit-zero.md:30) | feature | verified | unchanged: live probe on a 0-byte `.xml` → `{"phase":"Inspect","status":"ok",...,"result":{"blocks":0,"hierarchy_markers":0,...}}` |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-refuses-unreadable-path.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "One typed failure record (phase Io, kind ReadFailure, message fingerprint, duration) prints and the command exits 1; no report follows" (inspect-refuses-unreadable-path.md:30-31) | feature | verified | live probe on a nonexistent path → `{"phase":"Io","status":"failed","kind":"ReadFailure",...,"fingerprint":"fnv1a64:2bfc07...","duration_ms":0}`, exit 1 |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-refuses-unsupported-family.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "One typed failure record (phase Parse, kind UnsupportedFamily) prints and the command exits 1; no decoding starts" (inspect-refuses-unsupported-family.md:30-31) | feature | verified | live probe on an existing `.txt` file → `{"phase":"Parse","status":"failed","kind":"UnsupportedFamily",...}`, exit 1 |

## Doc: product-model/capabilities/replay-edition/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "read the hierarchy markers of the seed and target files, diff the marker sets, turn the diff into attach and detach drafts ... verify by drift, missing, and phantom counters ... Missing arguments are a usage error before any file is read" (replay-edition/capability.md:9-19) | feature | verified | live same-file replay printed seed/target source blocks, `diff added:0 removed:0`, drafts 0 and verify counters, status ok; `replay` with no arguments → usage line, exit 2 (main.rs:755-757) |

## Doc: product-model/capabilities/replay-edition/scenarios/replay-refuses-missing-arguments.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The usage line prints on stderr and the command exits 2; nothing is read or processed" (replay-refuses-missing-arguments.md:13,30) | feature | verified | unchanged: live probe → `usage: law-nexus-inspect replay <seed-edition> <target-edition>`, exit 2 |

## Doc: product-model/capabilities/replay-edition/scenarios/replay-same-edition-zero-drift.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "when the seed equals the target, the diff, the drafts, and the verify counters are all zero" (replay-same-edition-zero-drift.md:53-54) | feature | verified | unchanged: live same-file replay on the tracked 402-ФЗ XML: `"diff":{"added":0,"removed":0},"drafts":{"total":0,...}` status ok, exit 0 |

## Doc: product-model/capabilities/resolve-subordinates/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "bind its document group from the kind the operator names ... collect its punkt units, mint fixture component identities ... A missing effect day is fail-closed: the report keeps the key and states the skip reason" (resolve-subordinates/capability.md:9-20) | feature | verified | live run on the tracked Garant PP_60 ODT: group `government_resolution`, `punkt_units:246`, fixture expression id, effect_day, non_claims; a dateless filename copy → `skip_reason: no_document_date` (main.rs:1233-1238), live-probed |

## Doc: product-model/capabilities/resolve-subordinates/scenarios/subordinates-bound-group-report.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints bounded JSON with the bound group ..., punkt unit and fixture identity counts, resolved and conflicting text versions, the effect day, and the non-claims list" (subordinates-bound-group-report.md:33,53) | feature | verified | unchanged: live probe output carried document_group, punkt_units/cc_punkts 246, ctv_resolved/conflict, effect_day and non_claims, status ok |

## Doc: product-model/capabilities/resolve-subordinates/scenarios/subordinates-missing-date-fails-closed.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints with status ok, `skip_reason: no_document_date`, and zero text-version counts" (subordinates-missing-date-fails-closed.md:13,33) | feature | verified | unchanged: live probe on a dateless copy of a tracked ODT → `"skip_reason":"no_document_date"` in the output |

## Doc: product-model/coverage.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The law-nexus-inspect binary, its five subcommands (health, inspect, replay, subordinates, reference-package), reports, and failure records" + "The reference-package build and check subcommands composing the ln-consultant-parser reference_layer (ADR-0031) over a corpus directory and a catalog" (coverage.md covered:, M011) | feature | verified | dispatch arms at main.rs:746-773 name exactly those five; live probes cover each (health ok; inspect/replay/subordinates reports; reference-package build/check with the 0/2/3/6 exit contract); reference_layer.rs implements the derivation |

## Doc: product-model/entities/document.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Information kept: Path, Byte size, Content fingerprint, Source family (entities/document.md:8-12) | feature | verified | every live report's `source` block prints exactly these fields — e.g. `"source":{"path":...,"bytes":813400,"fingerprint":"fnv1a64:..."},"family":"family:consultant-wordml"` (inspect probe) and the Garant ODT probe |

## Doc: product-model/entities/operator.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The product keeps no facts about the operator: there is no sign-in, no profile, and no session" (entities/operator.md:9) | structure | verified | no auth/session/operator code or fields in crates/ln-product-cli/src/ at the baseline (word-boundary sweep auth, session, operator, login, user, account over all 4 .rs files → 0 hits; only StructuralProfile document-structure code); reports carry only document facts |

## Doc: product-model/interfaces/terminal/interface.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "one binary, four subcommands": health, `inspect <path>`, `replay <seed-edition> <target-edition>`, `subordinates <resolution\|order> <path>` (interfaces/terminal/interface.md:1-10) | command | stale | main.rs now dispatches five subcommands — `reference-package <build\|check>` was added in M011 (main.rs:773; usage line at main.rs:776-780 lists it; coverage.md already records five); the interface inventory still lists four |

## Doc: product-model/interfaces/terminal/screens/document-report.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "the source block (path, bytes, fingerprint), the decoded family, the result counters, and the explicit non-claims list" (screens/document-report.md:13) | feature | verified | unchanged: matches the live inspect and subordinates outputs field-for-field |

## Doc: product-model/interfaces/terminal/screens/replay-report.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "the seed and target source blocks, the marker diff, the drafted changes, and the replay verify counters with their status" (screens/replay-report.md) | feature | verified | unchanged: matches the live replay output (`seed`/`target` blocks, `diff`, `drafts`, verify counters, status ok) |

## Doc: product-model/capabilities/reference-package/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Build and byte-check a reproducible ADR-0031 reference data package from a corpus directory and a catalog: `law-nexus-inspect reference-package build\|check --corpus-dir <dir> --catalog <path> --out-dir <dir>`" | command | verified | live sidecar probes on the measure-ed50 fixture: build → six `wrote <path> (<n> bytes)` lines, exit 0; check on the unmodified package → `check=ok artifacts byte-identical`, exit 0 |
| "Build ... writes only inside `--out-dir`: the corpus and the catalog stay byte-unchanged, a rebuild into the same directory is byte-identical, and unrelated files there are left alone" | feature | verified | `cargo test -p ln-product-cli --offline --test reference_package_cli` → 8 passed (build_measure_ed50_package_is_complete_idempotent_and_input_safe pins the input-safety snapshot and idempotent rebuild; builds_into_different_dirs_are_byte_identical pins determinism); write_reference_artifact only touches out-dir paths (main.rs) |
| "Check re-derives and compares bytes, naming every drift row on stderr before it exits. The exit contract is closed: 0 ok, 2 argv, 3 unreadable inputs, 6 byte drift; 5 stays reserved and is not emitted" | feature | verified | live: flipped artifact byte → `drift: ...m217-reference-amend-provenance.json: byte drift` on stderr, exit 6; restored → exit 0; suite pins invalid_arguments_exit_2 / unreadable_inputs_exit_3 / zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3 / deleted_artifact_is_drift_exit_6; reference_layer.rs defines EXIT_ARGV/EXIT_INPUT/EXIT_DRIFT with no exit-5 emission |
| "The ed-50 measurements are compared only where the corpus carries edition 50; elsewhere they are explicitly marked not applicable, never written, and never counted as drift" | feature | verified | live no-ed50 build over the `basic` fixture → `measurement not applicable: corpus has no edition 50`, exactly the 4 core artifacts written, exit 0; suite measurement_scope_follows_edition_50_presence pins both scopes |
| implementation targets: `crates/ln-product-cli/src/main.rs#reference_package`, `crates/ln-consultant-parser/src/reference_layer.rs`, `crates/ln-product-cli/tests/reference_package_cli.rs` | structure | verified | all three exist (reference_package() at main.rs:625-741; dispatch arm at main.rs:773) |
| "Fixture-level proof only: the tracked measure-ed50 fixture (`crates/ln-consultant-parser/tests/fixtures/reference-layer/measure-ed50/`) with its recipe-built catalog (`scripts/test_m217_reference_parity.py`, `build_catalog` over `MEASURE_CATALOG_ROWS`)" | structure | verified | the fixture tree is tracked (edition-0050_rev-2017-01-01_from-unknown_deadbeef.xml); the recipe defines `build_catalog` and `MEASURE_CATALOG_ROWS`; the live probe built the catalog through exactly that recipe |
| "Recorded check result (T001 Log, 2026-10-31; authoritative orchestrator rerun `.git/gsd-path/dispatch/gsd-path-M011/T001/attempt-2/verify.json`): Verify exit 0 — ... 8/8 ok" | status | verified | the verify.json exists in the primary `.git/gsd-path/dispatch/gsd-path-M011/T001/attempt-2/` (exit_code 0, command pinned to the fmt+suite+health chain); independently reproduced in this audit: 8 passed, 0 failed |

## Doc: product-model/capabilities/reference-package/scenarios/build-check-ok.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Build writes the artifact set inside `--out-dir` — four core artifacts, plus the two ed-50 measurement artifacts where the corpus carries edition 50 — each announced with a `wrote` line, and exits 0; the corpus and the catalog stay byte-unchanged and a rebuild into the same directory is byte-identical. Check on the unmodified package exits 0 and reports `check=ok`" | feature | verified | live build → exactly 4+2 `wrote` lines (m217-reference-timeline.json, -digests.jsonl, -named-graphs.json, -amend-provenance.json, -references.json, -pageindex.json), exit 0; check → `check=ok artifacts byte-identical`, exit 0; pinned by the two named tests (8/8 suite run) |
| Edge cases: "A corpus without edition 50 builds with the four core artifacts only, the measurements explicitly marked `measurement not applicable: corpus has no edition 50`, exit 0"; "Unreadable or missing inputs — a missing catalog, an absent corpus directory, an empty corpus directory — exit 3"; "An unknown flag, a missing required flag, or a flag value that is not there exits 2" | feature | verified | live: no-ed50 corpus → the exact marking + 4 artifacts + exit 0; missing catalog → `unreadable inputs: unreadable catalog: ...nope.sqlite` (exit 3 pinned by unreadable_inputs_exit_3); empty corpus dir → `unreadable inputs: no edition files under corpus dir ...` (exit 3 pinned); unknown flag → `unexpected argument: --bogus` (exit 2 pinned by invalid_arguments_exit_2) |

## Doc: product-model/capabilities/reference-package/scenarios/check-detects-drift.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Every drift row is named on stderr before the command exits 6; a changed byte, a truncated (including zero-byte) artifact, and a deleted artifact are all drift. There is no warn-and-pass path" | feature | verified | live: flipped byte in an artifact → the drift row named on stderr, exit 6; suite pins zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3 and deleted_artifact_is_drift_exit_6 (8/8 run); run_check emits every drift row before exiting (reference_layer.rs) |
| "Restoring the artifact bytes makes the same package check ok again (exit 0)" | feature | verified | live: rebuilt the package and restored the bytes → `check=ok artifacts byte-identical`, exit 0 |

## Descriptive docs

<!-- Every inventoried doc with no testable claims, one path per line.
     The union of this list and the Doc section paths must equal the frozen
     inventory exactly. -->


- .agents/skills/law-nexus-rust/references/curated-rust-guidance.md
- .agents/skills/law-nexus-rust/references/project-policy.md
- .agents/skills/law-nexus-rust/workflows/implement-rust-slice.md
- .agents/skills/law-nexus-rust/workflows/migrate-python-parity.md
- .agents/skills/law-nexus-rust/workflows/optimize-proven-hot-path.md
- .agents/skills/law-nexus-rust/workflows/review-rust-change.md
- .agents/skills/law-nexus-rust/workflows/review-unsafe-code.md
- .agents/skills/law-nexus-subagent/workflows/parent-dispatch.md
- .ai/allspark/roles/owner.md
- .ai/allspark/roles/reviewer.md
- .ai/allspark/roles/worker.md
- WORKFLOW.md
- assessment/00-charter.md
- assessment/01-authority-map.md
- assessment/02-product-contract.md
- assessment/03-temporal-reconciliation.md
- assessment/04-adr-amendments.md
- assessment/05-roadmap-readiness.md
- assessment/06-derived-registry-quarantine.md
- assessment/07-adr-archive-governor-audit.md
- assessment/08-known-defects.md
- assessment/09-deterministic-paper-rehearsal.md
- assessment/10-semantic-review-rehearsal.md
- assessment/11-independent-external-assessment.md
- assessment/12-final-disposition.md
- assessment/13-current-head-gap-audit.md
- assessment/14-post-remediation-gap-disposition.md
- assessment/15-project-document-gap-disposition.md
- assessment/16-post-parser-protocol-gap-disposition.md
- assessment/17-glossary-and-semantic-control-gap-audit.md
- assessment/18-post-semantic-control-remediation.md
- assessment/19-temporal-model-and-cross-act-progress.md
- assessment/20-standing-execution-directive.md
- assessment/21-stub-fake-hardcode-census.md
- assessment/22-gsd-session-log-analysis.md
- assessment/23-dead-code-reuse-audit.md
- assessment/24-npa-engine-review.md
- assessment/25-npa-tokenizer-prior-art.md
- assessment/26-pullenti-semantic-morphology-synthesis.md
- assessment/27-recursive-document-analysis-patterns.md
- assessment/28-npa-process-fsm-meta-prompt-audit.md
- assessment/29-npa-bounds-hostile-plan.md
- assessment/30-npa-parsing-program-control-baseline.md
- assessment/31-npa-control-artifact-verification.md
- assessment/32-npa-governor-control-verification.md
- assessment/33-rc28-disposition-inventory.md
- assessment/34-rust-npa-foundation-readiness-audit.md
- doc/adr/0004-rust-migration-decision.md
- doc/adr/0005-rust-target-architecture.md
- doc/adr/0007-python-repository-harness.md
- doc/adr/0008-promotion-publication-authority.md
- doc/adr/0009-five-clock-temporal-model.md
- doc/adr/0010-evidence-kernel-gates.md
- doc/adr/0011-kof-da-ownership.md
- doc/adr/0012-consequential-evidence-protocol.md
- doc/adr/0013-universal-multi-source-parser.md
- doc/adr/0014-ruvector-primary-infrastructure.md
- doc/adr/0015-hexagonal-verification-architecture.md
- doc/adr/0016-frbr-structural-legal-identity.md
- doc/adr/0017-component-temporal-versioning.md
- doc/adr/0018-normative-state-resolver.md
- doc/adr/0019-normative-hierarchy-and-conflict.md
- doc/adr/0020-judicial-fas-practice-overlay.md
- doc/adr/0021-transitional-provisions-and-risk.md
- doc/adr/0022-industry-profiles-architecture.md
- doc/adr/0023-applicability-protocol-ownership.md
- doc/adr/0024-review-case-intake-and-disposition.md
- doc/adr/0025-consultant-parser-crate.md
- doc/adr/0026-ruvector-agent-memory.md
- doc/adr/0027-multi-layer-classifier.md
- doc/adr/0028-typed-lexer-legal-marker-lexicon.md
- doc/adr/0029-requisites-anchored-member-assembly-fsm.md
- doc/adr/0030-corpus-uri-anchor-knowledge-layers.md
- doc/adr/0031-reference-knowledge-layer-contract.md
- doc/gsd-headless-supervisor.md
- doc/litho-runbook.md
- doc/review/review-11-08-2026.md
- doc/review/review-12-08-2026.md
- doc/review/review-13-08-2026.md
- doc/review/review-14-08-2026.md
- doc/review/review-15-08-2026.md
- doc/review/review-16-08-2026.md
- doc/review/review-17-08-2026.md
- doc/review/review-20-08-2026.md
- doc/review/review-21-08-2026.md
- doc/review/review-22-08-2026.md
- doc/review/review-23-08-2026.md
- doc/review/review-24-08-2026.md
- doc/review/review-25-08-2026.md
- doc/review/review-26-23-08-2026.md
- doc/review/review-27-05-09-2026.md
- doc/review/review-28-10-09-2026.md
- doc/review/review-28.md
- doc/review/review-29-07-10-2026.md
- docs/agent-stack/AGENT_HANDOFF.md
- docs/agent-stack/ALLSPARK_NOTES.md
- docs/agent-stack/CUTOVER-READINESS-M001.md
- docs/agent-stack/INSTALL.md
- docs/agent-stack/MIGRATION-RECORD-2026-10-23.md
- docs/agent-stack/MIGRATION.md
- docs/agent-stack/PATH_SETUP.md
- docs/agent-stack/POST-SHIP-STATE-2026-10-27.md
- docs/agent-stack/SOURCES.md
- docs/agent-stack/TESTED.md
- docs/agent-stack/history/LEGACY_CROSSWALK.md
- law-source/consultant/okf/documents/byudzhetnyi-kodeks-rossiiskoi-federatsii-ot-31-07-1998-n-145-fz-red-ot-26-06-2026-s-izm-i-dop-vstup-v-silu-s-01-07-2026--124297b4.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-06-04-2011-n-63-fz-red-ot-31-07-2025-ob-elektronnoi-podpisi--6caf7614.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025-o-bukhgalterskom-uchete--fcc0b660.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-12-04-2010-n-61-fz-red-ot-29-12-2025-ob-obrashchenii-lekarstvennykh-sredstv-s-izm-i-dop-vstup-v-silu-s-01-03-2026--5af26e08.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-18-07-2011-n-223-fz-red-ot-08-08-2024-o-zakupkakh-tovarov-rabot-uslug-otdelnymi-vidami-yuridicheskikh-lits-s-izm-i--86e8fd8d.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.md
- law-source/consultant/okf/documents/federalnyi-zakon-ot-25-12-2008-n-273-fz-red-ot-28-12-2025-o-protivodeistvii-korruptsii--da724f03.md
- law-source/consultant/okf/documents/kodeks-rossiiskoi-federatsii-ob-administrativnykh-pravonarusheniyakh-ot-30-12-2001-n-195-fz-red-ot-04-07-2026-s-izm-i-dop-vstup-v-silu--b4fd4ec6.md
- law-source/consultant/okf/documents/obzor-izmenenii-federalnogo-zakona-ot-05-04-2013-n-44-fz-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--276d34f7.md
- law-source/consultant/okf/documents/obzor-narushenii-i-nedostatkov-vyyavlennykh-federalnym-kaznacheistvom-v-khode-osushchestvleniya-kontrolya-v-finansovo-byudzhetnoi-sfere--e41545c4.md
- law-source/consultant/okf/documents/obzor-nedostatkov-i-narushenii-vyyavlennykh-federalnym-kaznacheistvom-v-khode-osushchestvleniya-kontrolya-v-finansovo-byudzhetnoi-sfere--bef0d103.md
- law-source/consultant/okf/documents/obzor-rezultatov-osushchestvleniya-federalnym-kaznacheistvom-kontrolnoi-deyatelnosti-v-finansovo-byudzhetnoi-sfere-v-otnoshenii-glavnyk--49897501.md
- law-source/consultant/okf/documents/obzor-sudebnoi-praktiki-svyazannoi-s-privlecheniem-k-administrativnoi-otvetstvennosti-za-narusheniya-antimonopolnogo-zakonodatelstva-ut--4bb378ff.md
- law-source/consultant/okf/documents/obzor-sudebnoi-praktiki-verkhovnogo-suda-rossiiskoi-federatsii-n-1-2026-utv-postanovleniem-prezidiuma-verkhovnogo-suda-rf-ot-25-03-2026--353c3fc0.md
- law-source/consultant/okf/documents/obzor-sudebnoi-praktiki-verkhovnogo-suda-rossiiskoi-federatsii-n-2-2025-utv-prezidiumom-verkhovnogo-suda-rf-18-06-2025-red-ot-19-11-202--7ae2a955.md
- law-source/consultant/okf/documents/obzor-sudebnoi-praktiki-verkhovnogo-suda-rossiiskoi-federatsii-n-3-2022-utv-prezidiumom-verkhovnogo-suda-rf-21-12-2022-red-ot-25-03-202--e84b5bd5.md
- law-source/consultant/okf/documents/ok-029-2014-kdes-red-2-obshcherossiiskii-klassifikator-vidov-ekonomicheskoi-deyatelnosti-utv-prikazom-rosstandarta-ot-31-01-2014-n-14-s--ae072cec.md
- law-source/consultant/okf/documents/ok-034-2014-kpes-2008-obshcherossiiskii-klassifikator-produktsii-po-vidam-ekonomicheskoi-deyatelnosti-utv-prikazom-rosstandarta-ot-31-0--dc2109f9.md
- law-source/consultant/okf/documents/opredelenie-sedmogo-kassatsionnogo-suda-obshchei-yurisdiktsii-ot-10-06-2026-n-88-8444-2026-uid-66rs0044-01-2023-005497-11-kategoriya-sp--12ad6325.md
- law-source/consultant/okf/documents/opredelenie-verkhovnogo-suda-rf-ot-03-07-2026-n-310-es26-4320-po-delu-n-a48-2335-2025-trebovanie-o-peresmotre-v-kassatsionnom-poryadke--d3b817a9.md
- law-source/consultant/okf/documents/pismo-minstroya-rossii-ot-07-05-2026-n-27735-al-02-ob-ustanovlenii-trebovanii-o-chlenstve-v-samoreguliruemoi-organizatsii--06cf65ce.md
- law-source/consultant/okf/documents/pismo-minstroya-rossii-ot-13-03-2026-n-13623-av-09-o-perechne-dokumentov-aktov-o-priemke-rezultata-vypolnennykh-rabot-po-dogovoru-stroi--866d2575.md
- law-source/consultant/okf/documents/postanovlenie-arbitrazhnogo-suda-dalnevostochnogo-okruga-ot-03-07-2026-n-f03-913-2026-po-delu-n-a73-13075-2025-trebovanie-o-vzyskanii-d--d9e2d6ac.md
- law-source/consultant/okf/documents/postanovlenie-arbitrazhnogo-suda-volgo-vyatskogo-okruga-ot-06-07-2026-n-f01-7581-2026-po-delu-n-a39-5259-2025-trebovanie-o-priznanii-ne--c6b081b3.md
- law-source/consultant/okf/documents/postanovlenie-arbitrazhnogo-suda-vostochno-sibirskogo-okruga-ot-29-06-2026-n-f02-1611-2026-po-delu-n-a33-10080-2023-trebovanie-o-prizna--01819602.md
- law-source/consultant/okf/documents/postanovlenie-pervogo-arbitrazhnogo-apellyatsionnogo-suda-ot-02-07-2026-n-01ap-3115-2026-po-delu-n-a43-35691-2025-trebovanie-o-priznani--9cbeb8ca.md
- law-source/consultant/okf/documents/postanovlenie-plenuma-verkhovnogo-suda-rf-ot-24-03-2016-n-7-red-ot-22-06-2021-o-primenenii-sudami-nekotorykh-polozhenii-grazhdanskogo-k--15845971.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-moskvy-ot-25-12-2015-n-954-pp-red-ot-24-02-2026-ob-opredelenii-trebovanii-k-zakupaemym-organami-ispolnitelno--1de99445.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-02-09-2015-n-926-red-ot-12-06-2025-ob-utverzhdenii-obshchikh-pravil-opredeleniya-trebovanii-k-zakupaem--e6c4a931.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-06-10-2025-n-1546-o-tipovykh-usloviyakh-kontraktov-na-okazanie-uslug-po-provedeniyu-stroitelnogo-kontr--e269f805.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-08-02-2017-n-145-red-ot-23-12-2024-ob-utverzhdenii-pravil-formirovaniya-i-vedeniya-v-edinoi-informatsi--9299200a.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-08-07-2022-n-1224-ob-osobennostyakh-opisaniya-otdelnykh-vidov-tovarov-yavlyayushchikhsya-obektom-zakup--871d656f.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-08-11-2013-n-1005-red-ot-26-12-2024-o-nezavisimykh-garantiyakh-ispolzuemykh-dlya-tselei-federalnogo-za--f101c16f.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-10-07-2019-n-878-red-ot-13-04-2026-o-merakh-stimulirovaniya-proizvodstva-radioelektronnoi-produktsii-n--ed9a9370.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-12-06-2026-n-736-o-tsentralizatsii-zakupok-otdelnykh-vidov-lekarstvennykh-preparatov-dlya-meditsinskog--0ab4075b.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-12-06-2026-n-737-o-tsentralizatsii-zakupok-otdelnykh-vidov-meditsinskikh-izdelii-dlya-obespecheniya-go--7486d25f.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-15-04-2026-n-416-ob-izmenenii-sushchestvennykh-uslovii-kontraktov-zaklyuchennykh-dlya-obespecheniya-fe--42072b55.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-16-05-2011-n-373-red-ot-20-07-2021-o-razrabotke-i-utverzhdenii-administrativnykh-reglamentov-osushches--a07065f6.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-16-11-2015-n-1236-red-ot-09-12-2025-ob-utverzhdenii-pravil-formirovaniya-i-vedeniya-edinogo-reestra-ro--fca6af69.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-18-03-2026-n-287-o-federalnom-organe-ispolnitelnoi-vlasti-upolnomochennom-na-ustanovlenie-poryadka-opr--d45f3b8c.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-20-10-2014-n-1084-red-ot-31-10-2024-o-poryadke-opredeleniya-normativnykh-zatrat-na-obespechenie-funkts--71673343.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-21-06-2012-n-616-red-ot-30-12-2015-ob-utverzhdenii-perechnya-tovarov-rabot-i-uslug-zakupka-kotorykh-os--b479cc6c.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-23-05-2026-n-590-o-vnesenii-izmenenii-v-nekotorye-akty-pravitelstva-rossiiskoi-federatsii--eb8f2bad.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-23-12-2024-n-1875-red-ot-03-07-2026-o-merakh-po-predostavleniyu-natsionalnogo-rezhima-pri-osushchestvl--ac6afca0.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-24-12-2022-n-2411-red-ot-30-08-2025-ob-avansirovanii-dogovorov-gosudarstvennykh-kontraktov-o-postavke--a2c100f9.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-27-04-2026-n-476-o-federalnom-organe-ispolnitelnoi-vlasti-upolnomochennom-na-ustanovlenie-poryadka-opr--b74f7d99.md
- law-source/consultant/okf/documents/postanovlenie-pravitelstva-rf-ot-30-09-2019-n-1279-red-ot-02-09-2025-o-planakh-grafikakh-zakupok-i-o-priznanii-utrativshimi-silu-otdeln--0baaae5a.md
- law-source/consultant/okf/documents/prikaz-fas-rossii-ot-15-01-2026-n-16-26-ob-utverzhdenii-trebovanii-k-zakupaemym-federalnoi-antimonopolnoi-sluzhboi-ee-territorialnymi-o--0264c0ac.md
- law-source/consultant/okf/documents/prikaz-fas-rossii-ot-20-01-2026-n-32-26-ob-utverzhdenii-poryadka-deistvii-fas-rossii-i-ee-territorialnykh-organov-v-sluchae-vyyavleniya--10fb2bf1.md
- law-source/consultant/okf/documents/prikaz-fas-rossii-ot-25-05-2012-n-339-red-ot-16-02-2016-ob-utverzhdenii-administrativnogo-reglamenta-federalnoi-antimonopolnoi-sluzhby--26bd283c.md
- law-source/consultant/okf/documents/prikaz-fsb-rossii-ot-08-04-2026-n-136-ob-utverzhdenii-perechnya-dokumentov-predstavlyaemykh-v-federalnuyu-sluzhbu-bezopasnosti-rossiisk--9a634157.md
- law-source/consultant/okf/documents/prikaz-fstek-rossii-ot-24-04-2026-n-120-ob-utverzhdenii-trebovanii-k-zakupaemym-fstek-rossii-ee-territorialnymi-organami-i-podvedomstve--57826070.md
- law-source/consultant/okf/documents/prikaz-fts-rossii-ot-16-03-2026-n-204-ob-osushchestvlenii-federalnoi-tamozhennoi-sluzhboi-ee-territorialnymi-organami-i-uchrezhdeniyami--c8eace7c.md
- law-source/consultant/okf/documents/prikaz-minekonomrazvitiya-rossii-ot-04-06-2010-n-229-red-ot-09-06-2016-o-trebovaniyakh-energeticheskoi-effektivnosti-tovarov-ispolzuemy--f8324528.md
- law-source/consultant/okf/documents/prikaz-minekonomrazvitiya-rossii-ot-22-03-2021-n-131-red-ot-17-02-2023-o-trebovaniyakh-energeticheskoi-effektivnosti-v-otnoshenii-tovar--98a2b7b2.md
- law-source/consultant/okf/documents/prikaz-minfina-rossii-ot-08-10-2024-n-149n-o-priznanii-utrativshimi-silu-prikaza-ministerstva-finansov-rossiiskoi-federatsii-ot-4-iyuny--4949c2aa.md
- law-source/consultant/okf/documents/prikaz-minfina-rossii-ot-16-06-2025-n-74n-ob-utverzhdenii-poryadka-prisvoeniya-primeneniya-a-takzhe-izmeneniya-identifikatsionnykh-kodo--66248b2b.md
- law-source/consultant/okf/documents/prikaz-minfina-rossii-ot-25-03-2011-n-33n-red-ot-04-08-2025-ob-utverzhdenii-instruktsii-o-poryadke-sostavleniya-predstavleniya-godovoi--e80bb7fe.md
- law-source/consultant/okf/documents/prikaz-minfina-rossii-ot-31-12-2016-n-256n-red-ot-13-09-2023-ob-utverzhdenii-federalnogo-standarta-bukhgalterskogo-ucheta-dlya-organiza--4ee50d67.md
- law-source/consultant/okf/documents/prikaz-minpromtorga-rossii-ot-15-10-2025-n-5073-red-ot-04-03-2026-ob-utverzhdenii-metodicheskikh-rekomendatsii-po-provedeniyu-na-territ--d927bd51.md
- law-source/consultant/okf/documents/prikaz-minpromtorga-rossii-ot-28-02-2023-n-639-ob-utverzhdenii-poryadka-opredeleniya-nachalnoi-maksimalnoi-tseny-kontrakta-tseny-kontra--f068327b.md
- law-source/consultant/okf/documents/prikaz-rosfinmonitoringa-ot-13-05-2026-n-94-ob-utverzhdenii-trebovanii-k-zakupaemym-federalnoi-sluzhboi-po-finansovomu-monitoringu-i-ee--44d19fed.md
- law-source/consultant/okf/documents/prikaz-rosgvardii-ot-15-02-2021-n-45-ob-utverzhdenii-poryadka-opredeleniya-nachalnoi-maksimalnoi-tseny-kontrakta-tseny-kontrakta-zaklyu--f9493f06.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-08-12-2021-n-3500-r-red-ot-12-05-2023-ob-utverzhdenii-perechnei-tovarov-rabot-uslug-pri-osushchestvle--92d539ef.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-16-01-2018-n-21-r-red-ot-27-03-2020-ob-utverzhdenii-perechnya-tovarov-i-uslug-v-otnoshenii-kotorykh-p--0db4e799.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-16-08-2025-n-2227-r-ob-utverzhdenii-perechnya-istochnikov-informatsii-ispolzuemykh-dlya-tselei-oprede--b5a84d6d.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-18-12-2025-n-3867-r-ob-utverzhdenii-perechnya-zhiznenno-neobkhodimykh-i-vazhneishikh-lekarstvennykh-p--7259f6f6.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-21-03-2016-n-471-r-red-ot-31-10-2022-o-perechne-tovarov-rabot-uslug-v-sluchae-osushchestvleniya-zakup--e127e64d.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-28-04-2018-n-824-r-red-ot-16-01-2025-o-sozdanii-edinogo-agregatora-torgovli--a95736a6.md
- law-source/consultant/okf/documents/rasporyazhenie-pravitelstva-rf-ot-29-09-2025-n-2710-r-red-ot-13-03-2026-o-provedenii-na-territorii-rossiiskoi-federatsii-eksperimenta-p--790b9408.md
- law-source/consultant/okf/documents/reglament-funktsionirovaniya-edinogo-agregatora-torgovli-redaktsiya-n-20-utv-prikazom-ao-edinyi-agregator-torgovli-ot-28-01-2026-n-3-vm--334e8a67.md
- law-source/consultant/okf/documents/reshenie-fas-rossii-ot-16-06-2026-n-005-06-105-804-2026-obstoyatelstva-po-mneniyu-zayavitelya-obosnovanie-nachalnoi-maksimalnoi-tseny-k--2ca29d1d.md
- law-source/consultant/okf/documents/reshenie-fas-rossii-ot-16-06-2026-po-delu-n-050-06-105-20119-2026-obstoyatelstva-po-mneniyu-zayavitelya-ego-prava-i-zakonnye-interesy-n--c0114127.md
- law-source/consultant/okf/documents/reshenie-fas-rossii-ot-17-06-2026-n-048-06-105-547-2026-obstoyatelstva-v-antimonopolnyi-organ-postupilo-obrashchenie-s-zhaloboi-na-polo--8a9d6306.md
- law-source/consultant/okf/documents/reshenie-fas-rossii-ot-17-06-2026-po-delu-n-26-44-104-330-ob-otkaze-vo-vklyuchenii-svedenii-v-reestr-nedobrosovestnykh-postavshchikov-p--21c1baef.md
- law-source/consultant/okf/documents/reshenie-fas-rossii-ot-19-06-2026-po-delu-n-28-06-105-2268-2025-narushenie-p-3-ch-5-st-44-zakona-o-kontraktnoi-sisteme-reshenie-priznat--9f1b3f25.md
- law-source/consultant/okf/documents/reshenie-fas-rossii-ot-19-06-2026-po-zhalobe-n-011-06-105-542-2026-obstoyatelstva-v-antimonopolnyi-organ-postupilo-obrashchenie-s-zhalo--547d00b7.md
- law-source/consultant/okf/documents/reshenie-kemerovskogo-ufas-rossii-ot-07-05-2026-po-delu-n-042-06-105-760-2026-sut-zhaloby-1-tekhnicheskim-kharakteristikam-tovara-ne-so--413c2013.md
- law-source/consultant/okf/documents/reshenie-soveta-evraziiskoi-ekonomicheskoi-komissii-ot-14-09-2021-n-80-red-ot-01-07-2026-ob-utverzhdenii-edinoi-tovarnoi-nomenklatury-v--1e5dc26f.md
- law-source/consultant/okf/documents/zemelnyi-kodeks-rossiiskoi-federatsii-ot-25-10-2001-n-136-fz-red-ot-02-05-2026-s-izm-i-dop-vstup-v-silu-s-01-07-2026--77238147.md
- law-source/consultant/okf/log.md
- prd/annotation/m207-context-presentation-contract.md
- prd/annotation/m207-hybrid-eval-contract.md
- prd/annotation/m207-hybrid-records-contract.md
- prd/annotation/m207-s01-codebook.md
- prd/annotation/m207-s01-metaprompt.md
- prd/annotation/m207-s02-coder-protocol.md
- prd/annotation/m207-s03-eval-protocol.md
- prd/annotation/m207-s04-c4-protocol.md
- prd/annotation/m207-s07-c4-protocol.md
- prd/architecture/README.md
- prd/architecture/adr-governor-verification-design.md
- prd/architecture/architecture_health.md
- prd/architecture/architecture_report.md
- prd/architecture/assembly-pipeline-map.md
- prd/architecture/capability-promotion-board.md
- prd/architecture/claims_ledger.md
- prd/architecture/cleaned-projection-contract.md
- prd/architecture/closure_roadmap.md
- prd/architecture/documentation-semantic-control-plan.md
- prd/architecture/glossary-governance.md
- prd/architecture/intermediate-source-acceptance-contract.md
- prd/architecture/intermediate-source-clean-view-contract.md
- prd/architecture/intermediate-source-consumer-acceptance-contract.md
- prd/architecture/intermediate-source-navigation-contract.md
- prd/architecture/intermediate-source-reading-order-contract.md
- prd/architecture/kb-ontology-l1-l3-draft.md
- prd/architecture/kb-ontology-requirements.md
- prd/architecture/m111-final-architecture-baseline.md
- prd/architecture/m206-s01-adoption-state.md
- prd/architecture/m206-s02-adoption-state.md
- prd/architecture/m206-s03-adoption-state.md
- prd/architecture/m206-s04-adoption-state.md
- prd/architecture/m206-s05-runtime-admission.md
- prd/architecture/m206-s07-runtime-admission.md
- prd/architecture/m207-reassessment-2026-09-21.md
- prd/architecture/m207-unit-diagnosis.md
- prd/architecture/m208-s01-runtime-admission.md
- prd/architecture/m208-s02-nested-target-admission.md
- prd/architecture/m208-s03-admission-commencement.md
- prd/architecture/m208-s04-admission-bounded-replay.md
- prd/architecture/m209-s01-punkt-decision.md
- prd/architecture/m210-s01-decision-packet.md
- prd/architecture/m210-s01-ir-alternatives.md
- prd/architecture/m210-s01-normative-family-register.md
- prd/architecture/m210-s02-adoption-checkpoint-v2.md
- prd/architecture/m210-s02-adoption-checkpoint.md
- prd/architecture/m210-s02-external-analysis-brief.md
- prd/architecture/m210-s02-owner-decision-presentation-v2.md
- prd/architecture/m210-s02-owner-decision-presentation.md
- prd/architecture/m210-s02-packet-corrections-v2.md
- prd/architecture/m210-s03-bounded-semantics-contract.md
- prd/architecture/m210-s03-runtime-admission.md
- prd/architecture/m210-s04-rc28-final-check.md
- prd/architecture/m210-s04-rc28-review-presentation.md
- prd/architecture/m210-s04-runtime-admission.md
- prd/architecture/major_track_split.md
- prd/architecture/model-crystal.md
- prd/architecture/product_readiness_blockers.md
- prd/architecture/reader-fixture-manifest.md
- prd/architecture/reader-projection-contract.md
- prd/architecture/reader-transfer-gate.md
- prd/architecture/reader-view-contract.md
- prd/architecture/remediation_matrix.md
- prd/architecture/review-cases/README.md
- prd/architecture/review-cases/continuity-contract.md
- prd/architecture/review-cases/gsd-review-bridge.md
- prd/architecture/review-cases/path-review-bridge.md
- prd/architecture/review-cases/rc28-remediation-program.md
- prd/architecture/review-cases/review-11-12-delta-map.md
- prd/architecture/review-cases/session-triage-2026-08-12.md
- prd/architecture/source-jsonl-contract.md
- prd/architecture/temporal-ast-review-control.md
- prd/architecture/temporal-semantic-gap-register.md
- prd/archive/README.md
- prd/migration/acp-git-lex-decommission-roadmap.md
- prd/migration/decommission/acp-git-lex-manifest.md
- prd/migration/decommission/pre-commit-hook-transition.md
- prd/migration/external-architecture-assessment-roadmap.md
- prd/migration/forward-roadmap.md
- prd/migration/rust-evidence/m198-c2-delta.md
- prd/migration/rust-evidence/m198-c3-convergence.md
- prd/migration/rust-evidence/m199-s01-annotation-protocol.md
- prd/migration/rust-evidence/m199-s01-ds-noise.md
- prd/migration/rust-evidence/m199-s04-n2-acceptance.md
- prd/migration/rust-evidence/m203-s08-gold-codebook.md
- prd/migration/rust-evidence/m214-s04-horizon-reassessment.md
- prd/migration/rust-evidence/m221-s05-horizon-reassessment.md
- prd/migration/rust-evidence/probes/hc01-observe-source-runtime.md
- prd/migration/rust-evidence/probes/hc02-inventory-intake-runtime.md
- prd/migration/rust-evidence/probes/hc03-dispose-review-runtime.md
- prd/migration/rust-evidence/probes/hc04-commit-curated-promotion-runtime.md
- prd/migration/rust-evidence/probes/hc05-decode-anchor-runtime.md
- prd/migration/rust-evidence/probes/hc06-gate-lifecycle-runtime.md
- prd/migration/rust-evidence/probes/hc07-assert-identity-runtime.md
- prd/migration/rust-evidence/probes/hc08-validate-relation-runtime.md
- prd/migration/rust-evidence/probes/hc09-five-clock-runtime.md
- prd/migration/rust-evidence/probes/hc10-work-state-runtime.md
- prd/migration/rust-evidence/probes/hc11-dependency-closure-runtime.md
- prd/migration/rust-evidence/probes/hc12-disposable-projection-runtime.md
- prd/migration/rust-evidence/probes/hc13-decide-admission-runtime.md
- prd/migration/rust-evidence/probes/hc14-checkpoint-replay-runtime.md
- prd/migration/rust-evidence/probes/hc15-publish-h1-runtime.md
- prd/migration/rust-evidence/probes/hc16-provisional-acceleration-runtime.md
- prd/migration/rust-evidence/probes/hc17-evidence-bounded-query-runtime.md
- prd/migration/rust-evidence/probes/hc18-resolve-citation-runtime.md
- prd/migration/rust-evidence/probes/hc19-safe-diagnostics-runtime.md
- prd/migration/rust-evidence/probes/hc20-evaluate-conformance-runtime.md
- prd/migration/rust-evidence/probes/m132-consultant-real-tracer.md
- prd/migration/rust-evidence/probes/m133-garant-real-tracer.md
- prd/migration/rust-evidence/probes/m134-shared-extractors-real.md
- prd/migration/rust-evidence/probes/m135-golden-real-enrichment.md
- prd/migration/rust-evidence/probes/m139-end-to-end-acceptance.md
- prd/migration/rust-evidence/probes/m139-performance-baseline.md
- prd/migration/rust-evidence/probes/m143-release-baseline.md
- prd/migration/rust-evidence/probes/sqlite-turso-crash-recovery.md
- prd/migration/rust-migration-roadmap.md
- prd/parser/golden_test_contract.md
- prd/parser/odt_smoke_records.md
- prd/parser/parser_record_contract.md
- prd/parser/representative_golden_corpus_acceptance_protocol.md
- prd/retrieval/rust_offline_citation_retrieval_contract.md
- prd/retrieval/rust_real_artifact_retrieval_proof.md
- prd/retrieval/rust_retrieval_metrics_contract.md

## User rulings

<!-- Appended after the ruling walk (standalone runs). Verbatim, append-only.
     accept-drift rulings suppress the item in future audits.
     `planned: no` rows are the alignment queue: $gsd-path (Codex) or /gsd-path (Antigravity/Zed/Muse) and $gsd-path-plan (Codex) or /gsd-path-plan (Antigravity/Zed/Muse) offer
     to absorb them until drained. When a ruling becomes a task, set
     planned to the task id — never delete the row. -->

| Queue # | Ruling | User's words | Planned |
|---------|--------|--------------|---------|

| 1 | fix-doc | «продолжаем - двигай проект» (2026-10-26) — принять рекомендованные решения раунда define, включая п.8 (все fix-doc строки — в очередь выравнивания) | no |
| 2 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 3 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 4 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 5 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 6 | fix-code | «продолжаем - двигай проект» (2026-10-26), п.3 — создать минимальную PDD-модель в M001 | T005 |
| 7 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 8 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 9 | fix-code | «продолжаем - двигай проект» (2026-10-26), п.4 — ре-индекс GitNexus и регенерировать блок | T006 |
| 10 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 11 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 12 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 13 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 14 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 15 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 16 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.5 — поправить формулировку README | T010 |
| 17 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 18 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.8 | no |
| 19 | fix-code | «продолжаем - двигай проект» (2026-10-26), п.3 — закрыть вместе с #6 | T005 |
| 20 | fix-code | «да согласен, 3 корректируй согласно архитектурным требованиям репо - выполняй все оптимально и элегантно» (2026-10-30), define п.2а — README quick-start чинится `default-run = "law-nexus-inspect"` в ln-product-cli | T001 |
| 21 | fix-doc | «да согласен, 3 корректируй согласно архитектурным требованиям репо - выполняй все оптимально и элегантно» (2026-10-30), define п.2б — README статус-бенд: 47 участников, названы ln-consultant-parser и ln-kb-ontology | T002 |
| 22 | fix-doc | «да согласен, 3 корректируй согласно архитектурным требованиям репо - выполняй все оптимально и элегантно» (2026-10-30), define п.2в — AGENTS.md указывает на .agents/skills/law-nexus-rust/ вместо отсутствующего workflows/implement-rust-slice.md | T002 |
| 23 | fix-doc | «да согласен, 3 корректируй согласно архитектурным требованиям репо - выполняй все оптимально и элегантно» (2026-10-30), define п.2г — POST-SHIP-STATE-2026-10-28.md: главу M004 пометить superseded, red-CI секцию датировать как историю | T002 |
| 24 | fix-doc | «да согласен, 3 корректируй согласно архитектурным требованиям репо - выполняй все оптимально и элегантно» (2026-10-30), define п.3 — ARCHITECTURE.md строка ADR-0031: модульный код measurement-уровня есть (reference_layer), corpus-wide исполнение D5/D4 не доказано, ADR остаётся [proposed] | T002 |
| 25 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — ARCHITECTURE.md:133-135: обновить счётчики ln-consultant-parser (31 src + 14 bins, 358 int / 54 unit) или снять точные числа | no |
| 26 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — ARCHITECTURE.md:326: подрезать one-page oracle до бюджета ≤325 строк, бюджет не поднимать | no |
| 27 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — doc/adr/README.md:64-74: восстановить header/separator таблицы индекса ADR-0025..0031 | no |
| 28 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — doc/adr-architecture-cross-matrix.md: расширить inventory/matrix до ADR-0031 | no |
| 29 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — m221-s05 binding: перепин к sha256 текущего tracked файла (текущая ревизия канонична), батарея готовности должна проходить | no |
| 30 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — roadmap.md:43-44: строка M173 датируется как frozen legacy-ledger текст (живой фронт — roadmap.json) | no |
| 31 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — law-source/consultant/README.md:9: переформулировать — .deprecated gitignored и может отсутствовать в свежем checkout | no |
| 36 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — PHASE-ADAPTER.md:10-14: выровнять header со §9 (PARTIALLY, пилот 2026-10-25, записи потреблялись M001/M004) | no |
| 37 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — roadmap.md:9-16: переписать transition-preamble на пост-бутстрап реальность (native state есть, PR #1 merged) | no |
| 39 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — roadmap.md:50-56: ship-time projection refresh по SHIP-TIME-PROJECTION-REFRESH.md с записью M011 (ship 38abe687, integration ef17106b, archive 011) — упущенный шаг M011; pointer/freshness сьюиты снова зелёные | no |
| 40 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — POST-SHIP-STATE:54-58: зафиксировать текущее красное состояние (run 41198873586 @ ef17106b FAILURE, 2026-10-31), прежние runs — датированная история | no |
| 41 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — POST-SHIP-STATE:207-211: green-претензия датируется по cited runs до 3a39fd70 + назвать свежайший failure | no |
| 42 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — POST-SHIP-STATE:191-196: bootstrap step 4 снова ожидает all-pass после #39 (до тех пор — честно про 2 failed) | no |
| 43 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — POST-SHIP-STATE:5-7,97-100: дописать запись M011 (ship/integration/tag/archive) и переписать live-state повествование | no |
| 44 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — interface.md: пять подкоманд — добавить reference-package build|check (как в coverage.md) | no |
| 45 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — README.md:39: Current-status к tracked ledger (roadmap.json через M224) + отметка о M011 на Path-треке | no |
| 46 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — README.md:40: диапазон assessments 00–34, указатель на assessment/34 | no |
| 47 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — AGENTS.md:413,415: актуальный счётчик frozen-DB (3,074 of 8,355; запросы 2026-10-25/30/31) | no |
| 48 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — AGENTS.md:405: 82 tracked fixtures; 40 .deprecated — gitignored, в checkout отсутствуют | no |
| 49 | fix-doc | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — README.md:280: диапазон MADR ADR 0004–0031 | no |
| 50 | fix-code | «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» (2026-10-31), define — классы аудитора приняты — GitNexus block: перегенерировать через node .gitnexus/run.cjs analyze --force --name law-nexus; числа блока = свежий meta.json; пометку про local-exclusion сохранить | no |

## Remediation queue

<!-- Every non-verified claim, classified. The user rules on this queue;
     the auditor never fixes anything.
     Numbers are unique and strictly increasing, not necessarily contiguous.
     A persisting row keeps its number; a new row takes a number above every
     prior queue number and every User rulings Queue #. Never reuse a retired
     number: a ruling stays bound to the item it was made for. -->

| # | Doc | Claim | Verdict | Class | Suggested action |
|---|-----|-------|---------|-------|------------------|

| 25 | prd/ARCHITECTURE.md | "`ln-consultant-parser` has 10 source modules including `lib.rs`, 64 integration test functions and 4 source-unit tests" (prd/ARCHITECTURE.md:133-135) | stale | fix-doc | Refresh the counts (31 src modules + 14 bins, 358 integration `#[test]`, 54 unit `#[test]`) or drop exact numbers |
| 26 | prd/ARCHITECTURE.md | "One page. If it grows, split detail into tracked focused PRD sub-docs" (one-page living oracle) (prd/ARCHITECTURE.md:326) | stale | fix-doc | Trim the oracle to ≤325 lines per the M171 budget test (currently 327) or split detail into sub-docs; raising the tracked budget is an owner decision |
| 27 | doc/adr/README.md | ADR-0025..0031 index rows (table following the `fold_expression_presence`/`map_hierarchy_marker` comments) (doc/adr/README.md:64-74) | stale | fix-doc | Restore the missing table header/separator so the index renders as a table |
| 28 | doc/adr-architecture-cross-matrix.md | "## 1. Present ADR inventory" table enumerates 0004–0024 as the present ADR set (doc/adr-architecture-cross-matrix.md:7-24) | stale | fix-doc | Extend the inventory and cross-surface matrix to ADR-0031 |
| 29 | prd/architecture/npa-analysis-jsonl-contract.md | Tracked as an M221 authority-reconciliation source binding (hash-pinned companion) (`prd/architecture/m221-s05-docs-reconciliation.yaml` binds path+sha256) | stale | fix-doc | Re-pin the binding to the current file digest or revert the unpinned edit — the owner confirms which revision is canonical (the M221 s05 readiness battery fails with it) |
| 30 | prd/project-state/roadmap.md | "Latest completed product milestone: M173, inspect PP_60 class-matched punkt proof" (roadmap.md:43-44) | stale | fix-doc | Sync the front with roadmap.json/CHANGELOG (json groups through M224-M224, generated 2026-10-24), or date-bound the line as frozen legacy-ledger text like the marker rows below it |
| 31 | law-source/consultant/README.md | "Плюс подкаталог `.deprecated/` (40 файлов) — ... остаётся на диске только как история" (law-source/consultant/README.md:9) | stale | fix-doc | Reword: the set is gitignored and may be absent after a fresh checkout (it is absent in the current primary checkout) |
| 36 | docs/agent-stack/PHASE-ADAPTER.md | Header status: "The adapter is verified against deterministic stub children only. No real Allspark/model pilot has been run, no native phase gate has consumed its records, and the acceptance table in §8 below is **not yet satisfied**" (docs/agent-stack/PHASE-ADAPTER.md:10-14) | stale | fix-doc | Align the header with §9 (PARTIALLY satisfied; real-model pilot 2026-10-25 in §9.1; dispatch records consumed by the M001/M004 native phases) |
| 37 | prd/project-state/roadmap.md | "Until native Path state exists and the bootstrap PR is accepted on the default branch, this projection keeps describing the **frozen legacy GSD-Pi milestone ledger**" (roadmap.md:9-16) | stale | fix-doc | Rewrite the transition preamble for the post-bootstrap reality (native state exists, PR #1 merged at `54a495cd`, native markers recorded below it) |
| 39 | prd/project-state/roadmap.md | "Local GSD workflow marker: doc-consistency is the current milestone — shipped/archived/integrated (2026-10-29) on branch `gsd-path/M010` ... Current-state document: `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`" (roadmap.md:50-56) | stale | fix-doc | Refresh the projection per `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`: a `docs:` commit naming the shipped `reference-front-door` milestone (ship `38abe687`, integration `ef17106b`, archive `011-reference-front-door`) before the ship commit — this is what M011 skipped; it turns `test_project_state_roadmap_freshness.py` (2 failed) and `test_post_ship_pointers.py` (1 failed) green again |
| 40 | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md | CI-section intro: "The live state is green: see \"M005–M009: red CI cleared\" below — run 40805352394 at `319a7b1a` success, re-confirmed by the newest main run 40822037565 at `3a39fd70` success (recorded by the 2026-10-30 docs audit)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:54-58) | stale | fix-doc | Record the current red state: main run 41198873586 at `ef17106b` (M011 integration, 2026-10-31) concluded failure on "Product and architecture harness tests" (the projection suites); keep 40805352394/40822037565 as dated history |
| 41 | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md | Non-claims: "Integrated `main` is green on `repository-quality` since the M009 integration (run 40805352394 at `319a7b1a`; re-confirmed by main run 40822037565 at `3a39fd70`, recorded 2026-10-30) — the pre-M005 red rows in the CI section above stay as dated history" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:207-211) | stale | fix-doc | Date-bound the green claim to the cited runs through `3a39fd70` and name the newest failure (run 41198873586 at `ef17106b`) so the non-claims list stops asserting a live green state |
| 42 | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md | Fresh-session bootstrap step 4: "Run the roadmap freshness guard — expect all tests to pass" (`uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:191-196) | stale | fix-doc | The expectation holds again once #39 lands; until then the bootstrap section must tell the reader to expect (and record) the observed 2 failures instead of all-pass |
| 43 | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md | "Role: current-state document for the `law-nexus` repository" with the delivered record ending at M010 and "M011 inspect active" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:5-7,97-100) | stale | fix-doc | Append the M011 record (ship `38abe687`, integration `ef17106b`, tag `milestone/011-reference-front-door`, archive `.project/archive/011-reference-front-door`, STATE.md shipped/done reference-front-door) and re-point the live-state narrative; AGENTS.md:224 names this file the current-state document |
| 44 | product-model/interfaces/terminal/interface.md | "one binary, four subcommands": health, `inspect <path>`, `replay <seed-edition> <target-edition>`, `subordinates <resolution\|order> <path>` (interfaces/terminal/interface.md:1-10) | stale | fix-doc | Add `reference-package <build\|check> --corpus-dir <dir> --catalog <path> --out-dir <dir>` to the entryPoints/inventory (five subcommands, as coverage.md already records) |
| 45 | README.md | "Latest tracked product/design band: **M165**" (README.md:39) | stale | fix-doc | Refresh the Current-status paragraph to the tracked ledger (roadmap.json groups through M224, generated 2026-10-24) or point at roadmap.json as the live front; note M011 shipped on the Path track 2026-10-31 while roadmap.json still fronts doc-consistency (see #39) |
| 46 | README.md | "The current documentation/control baseline includes post-D150 assessments 13–18" (README.md:40) | stale | fix-doc | Update the assessment range (tracked set is 00–34) and move the "latest remediation assessment" pointer to assessment/34 |
| 47 | AGENTS.md | "Known issue: 2,478 artifact rows in the DB contain `../`-style paths" (AGENTS.md:413,415) | stale | fix-doc | Update to the current frozen-DB count (3,074 of 8,355; queried read-only 2026-10-25, 2026-10-30 and 2026-10-31) or date-bound the figure to its 2026-08-31 assessment |
| 48 | AGENTS.md | Data Sources Map: "law-source/consultant/ — Fragment of the corpus (122 XML files)" (AGENTS.md:405) | stale | fix-doc | State 82 tracked fixtures and note the 40 `.deprecated/` files are gitignored and absent from current checkouts |
| 49 | README.md | "MADR ADRs 0004–0023 (0001/0002/0003/0006 retired, not present)" — the `doc/adr/` Active-tree row (README.md:280) | stale | fix-doc | Update the range to 0004–0031 to match doc/adr/ and the README's own ADR-0024..0031 mentions (README.md:292-295) |
| 50 | AGENTS.md | GitNexus block: "This project is indexed by GitNexus as **law-nexus** (43047 symbols, 102234 relationships, 584 execution flows)" and "`node .gitnexus/run.cjs analyze --force --name law-nexus`" (AGENTS.md:355-398) | stale | fix-code | Re-run `node .gitnexus/run.cjs analyze --force --name law-nexus` on the primary checkout and regenerate the tool block so its numbers match the recorded index (meta.json: nodes=43059, edges=102250, processes=584, pinned at 2026-10-26/M001 — the index now predates M002–M011); note the index stays local-excluded, so clean checkouts cannot verify it |
