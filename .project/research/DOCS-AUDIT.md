# Docs Audit

<!-- Written by the docs auditor ($gsd-path-docs-audit (Codex) or /gsd-path-docs-audit (Antigravity/Zed/Muse) or $gsd-path-inspect (Codex) or /gsd-path-inspect (Antigravity/Zed/Muse)).
     Every verdict carries evidence; a verdict without evidence is a defect. -->

Repo root: /root/law-nexus
Audited: 2026-10-30
Audited HEAD: 3a39fd70294c34d072b2aaa448ee226691dbaeae
Alignment mode: no

## Summary

| Verdict | Count |
|---------|-------|
| verified | 116 |
| stale | 20 |
| aspirational | 0 |
| unverifiable | 1 |
| descriptive docs (no testable claims) | 310 |

Worst drift: the current-state document `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` still carries the Non-claims bullet "Integrated `main` is red on `repository-quality`" and the "## M004 continuation (current)" header — both contradicted by the same document's own M005–M009 section and by live CI (runs 40805352394 and 40822037565 green on `main`), and `docs/agent-stack/PHASE-ADAPTER.md`'s header still says "No real Allspark/model pilot has been run" above a §9 that records one. The worst persistent drift is unchanged: the README quick-start command `cargo run -q -p ln-product-cli -- health` still fails as written (two binaries, no `default-run`).

Verification runs executed in the pre-created sidecar at the recorded clean HEAD (branch `gsd-path-verify/inspect-docs`): `cargo run -q -p ln-product-cli -- health` (exact README command → "could not determine which binary to run"), `cargo run -q -p ln-product-cli --bin law-nexus-inspect -- health` (status ok, exit 0), `--bin law-nexus-inspect -- inspect` on a tracked Consultant XML (status ok, blocks=586), on an empty `.xml` (status ok, `blocks: 0`), on a `.txt` (typed failure Parse/UnsupportedFamily, exit 1), on a missing path (Io/ReadFailure, exit 1); `replay <f> <f>` same-file (diff 0/0, drafts 0, status ok); `replay` without arguments (usage line, exit 2); `subordinates resolution` on the tracked Garant PP_60 ODT (status ok, group `government_resolution`, 246 punkt units) and on a dateless copy (`skip_reason: no_document_date`); `cargo test -p ln-query --offline --test retrieval_metrics` (7 passed); `cargo test -p ln-hc01-runner --offline` (1 passed); `uv run --frozen python -m law_nexus_harness.governor` (72 pass / 0 error / 0 warn, exit 0, `kind=shipped-integrated`); `uv run --frozen python -m law_nexus_harness preflight` (7 pass / 1 warn / 0 error, exit 0; the warn is this sidecar's absent local `.gitnexus/` metadata); `uv run --frozen python scripts/verify-adr-conformance.py` (ok, 29 files); `uv run --frozen pytest tests/test_architecture_m171_alignment.py -q` (1 failed — the 325-line budget), `tests/test_project_state_roadmap_freshness.py -q` (6 passed, 5 skipped), `tests/test_m221_authority_reconciliation.py::test_source_bindings_resolve_and_match_disk` (failed — sha256 drift), `ruff check`/`ruff format --check` on the phase-dispatch adapter (clean); `python3 scripts/ai/path-run.py status` (exit 0); full `uv run --frozen pytest -q` (31 failed, 973 passed, 12 skipped, 7 errors — decomposition in the README section below). GitHub CI facts re-checked live via `gh run view` (conclusions and head SHAs as cited). Git history/tag checks, the frozen GSD-Pi DB query, the `consru_export` counts and the `.deprecated`/vault/`.gitnexus` filesystem checks ran read-only (sidecar `git`, primary for gitignored local state). Upstream SHA-256 pins re-fetched from raw.githubusercontent.com at commit `fd2a861`. The full `cargo check/test/clippy --workspace` was not re-run (bounded-sample policy; sampled suites above).

## Doc: README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The workspace has 45 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed `ln-applicability`" (README.md:12-16) | structure | stale | Cargo.toml members list has 47 entries and `crates/` has 47 dirs; `ln-kb-ontology` and `ln-consultant-parser` are members missing from the README enumeration |
| "Latest tracked product/design band: **M165**" (README.md:38) | status | stale | prd/project-state/data/roadmap.json (`generated_at` 2026-10-24) records `completed_milestone_groups` through "M224-M224" status complete and notes through 2026-10-16 (ADR-0031 schema); `current_milestone` = doc-consistency |
| "The current documentation/control baseline includes post-D150 assessments 13–18" (README.md:39) | status | stale | assessment/ holds 00–34 (35 files); `assessment/34-rust-npa-foundation-readiness-audit.md` is a post-M221 remediation audit |
| "Retired ADR IDs **0001/0002/0003/0006** have no files under `doc/adr/`" (README.md:460) | structure | verified | doc/adr/ holds 27 ADR files 0004–0031, none for the retired IDs; governor `adr-retired-id-ban` pass in the live run |
| "Governor ADR/lifecycle probes ... include: adr-truth-oracle-sync, adr-index-completeness, adr-doc-matrix-coverage, adr-structure-hygiene, adr-cross-surface-matrix, adr-retired-id-ban, active-surface-era-noise, archive-path-policy" (README.md:417-424) | feature | verified | all 8 named `check_id`s appear in the live governor run (72 pass, exit 0), each with status pass |
| "`cargo run -q -p ln-product-cli -- health` # release health smoke" (README.md:413) | command | stale | ran in sidecar → "error: `cargo run` could not determine which binary to run" (binaries: hierarchy-registry-generator, law-nexus-inspect; no `default-run` key in crates/ln-product-cli/Cargo.toml); corrected `--bin law-nexus-inspect -- health` → `{"phase":"Health","status":"ok"}`, exit 0 |
| "`cargo run -q -p ln-product-cli -- inspect <path>` # structural + retrieval inspect" (README.md:414) | command | verified | ran on the tracked 63-ФЗ XML → `{"phase":"Inspect","status":"ok",...,"blocks":586,"hierarchy_markers":345,...}`, exit 0 |
| "`uv run python -m law_nexus_harness governor` # process + ADR/lifecycle/retired-era probes" (README.md:392) | command | verified | sidecar run → `"error_count":0,"pass_count":72,...,"status":"ok"` and exit 0 |
| "`uv run python -m law_nexus_harness preflight`" (README.md:393) | command | verified | sidecar run → `"error_count":0,"pass_count":7,...,"warn_count":1`, exit 0; the warn is `gitnexus-index-freshness` ("GitNexus metadata is missing" — `.gitnexus/` is local-excluded and absent in a fresh worktree) |
| "`uv run pytest -q` # full suite; CI process suite is a subset" (README.md:394) | command | verified | sidecar run → `31 failed, 973 passed, 12 skipped, 7 errors` in 315s; the failures decompose into the two real tracked-contract drifts recorded as queue rows #11 and #14 (the architecture one-page budget test, and the M221 hash-pinned source binding with its readiness battery) plus sidecar-environmental classes (the live governor/preflight scenario tests against this worktree's branch-conflicted workflow state, the unbuilt `ln-status` binary, and gitignored local PI-skill tooling) |
| "`uv run python scripts/verify-adr-conformance.py`" (README.md:395) | command | verified | sidecar run → `{"files_scanned": 29, "finding_count": 0, "status": "ok"}`, exit 0 |
| "M205/S04 ... `prd/architecture/m205-s04-docs-reconciliation.yaml`" (README.md:259-268) | structure | verified | the YAML exists; companion verifier `scripts/m205_s04_reconciliation.py` and its adversarial suite exist |
| "A Rust workspace of twenty exclusive `ln-*` capability crates (ADR-0011)" (README.md:58) | structure | verified | the 20 owner crates named in the map table are all workspace members in Cargo.toml; governor `hostile-baseline-aggregate`: "PASS 20/20; FAIL 0/20"; sampled `cargo test -p ln-hc01-runner --offline` → 1 passed |
| "Requires Python 3.13+ and [uv]" (README.md:378-380) | config | verified | pyproject.toml `requires-python = ">=3.13"`; `uv --version` → 0.12.13 available |
| "MADR ADRs 0004–0023 (0001/0002/0003/0006 retired, not present)" — the `doc/adr/` Active-tree row (README.md:277) | structure | stale | doc/adr/ holds 27 ADRs 0004–0031; the README itself names ADR-0024..0031 further down (README.md:289-292) |
| "the executable 44-member inventory" (README.md:301) | structure | stale | same 47-member evidence as row 1; also contradicts README.md:12 and README.md:216 ("### Rust workspace: 45 members") |
| "`CHANGELOG.md` — Human-readable delivery history; not architecture authority" (README map row, README.md:251) | status | verified | head entry M211-hkknug S01 is a dated revision-bound record whose named artifacts all resolve (see CHANGELOG section) |


## Doc: AGENTS.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Current delivery state: `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` is the current-state document" superseding `POST-SHIP-STATE-2026-10-27.md` and `CUTOVER-READINESS-M001.md` (AGENTS.md:224-227) | status | verified | all three files exist; the supersession chain is recorded in each snapshot header (POST-SHIP-STATE-2026-10-28.md:5-8, POST-SHIP-STATE-2026-10-27.md:5-8, CUTOVER-READINESS-M001.md title block) |
| "Product behavior: PDD Kit in `product-model/`, orchestration off" (AGENTS.md:275) | structure | verified | product-model/ is tracked (`git ls-files product-model` → 28 files, 25 Markdown) and models the shipped CLI behavior (see product-model sections) |
| Data Sources Map: "`consru_export/consru_export/exports/` ... 43,785 files, 3.7 GB" (AGENTS.md:403) | structure | verified | primary-checkout `find ... -name '*.xml' \| wc -l` → 43,785; `du -sh consru_export/consru_export/exports` → 3.7G (gitignored, .gitignore:153) |
| Data Sources Map: "law-source/consultant/ — Fragment of the corpus (122 XML files)" (AGENTS.md:404) | structure | stale | `git ls-files 'law-source/consultant/*.xml'` → 82 tracked XML (81 document fixtures + `Список документов (5).xml` list file) |
| "Known issue: 2,478 artifact rows in the DB contain `../`-style paths" (AGENTS.md:412,414) | status | stale | read-only query on the frozen DB /root/.gsd/projects/3495c0714df3/gsd.db → 3,074 of 8,355 artifact rows have `../` in `path` (unchanged since the 2026-10-25 audit; the figure is still the 2026-08-31 assessment value) |
| GitNexus block: "This project is indexed by GitNexus as **law-nexus** (43047 symbols, 102234 relationships, 584 execution flows)" and "`node .gitnexus/run.cjs analyze --force --name law-nexus`" (AGENTS.md:342-359) | integration | stale | the local `.gitnexus/` exists on the primary checkout (local-excluded via `.git/info/exclude`, absent in clean checkouts and in this sidecar; preflight warns "GitNexus metadata is missing"), but its recorded stats (`meta.json`/`gitnexus.json`: nodes=43059, edges=102250, processes=584, indexedAt 2026-10-26, branch gsd-path/M001, lastCommit 2a0ead24) do not match the block's numbers, and the index predates M002–M010 |
| "`src/law_nexus_harness/workflow_state.py` is the only sanctioned adapter" (AGENTS.md:306) | structure | verified | file exists |
| "`scripts/ai/allspark`", "`scripts/ai/phase-dispatch.py`", "`.gsd-path/runtime.json`" (AGENTS.md:279,295,268) | structure | verified | all three exist (the launcher on the primary root; the script and runtime.json tracked) |
| "`/root/law-nexus/.gsd` is a symlink to `/root/.gsd/projects/3495c0714df3`" (AGENTS.md:316-317,410) | structure | verified | `os.readlink('/root/law-nexus/.gsd')` → `/root/.gsd/projects/3495c0714df3` |
| "the live successor is `scripts/verify-source-snapshot-v2.py`" (AGENTS.md:324) | structure | verified | file exists |
| "the pointer suites in CI fail on the shipped tree when it is skipped" (AGENTS.md:273) | feature | verified | `tests/test_post_ship_pointers.py` and `tests/test_project_state_roadmap_freshness.py` are referenced in `.github/workflows/repository-quality.yml`; M010 demonstrates the rule (`e8b5696f` "docs: refresh the roadmap projection to the shipping milestone" immediately before ship commit `fd60893f`); the freshness suite passed in the sidecar (6 passed, 5 skipped) |

## Doc: prd/ARCHITECTURE.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Foundation/ontology ADR lifecycle map (ADR-0004..0031 with `[bounded]`/`[proposed]`/`[validated]` tags) (prd/ARCHITECTURE.md:46-68) | status | verified | all 27 rows' lifecycle tags match the ADR frontmatter (0007 validated; 0014/0016–0024/0026/0028–0031 proposed; the rest bounded); governor `adr-truth-oracle-sync` pass over 27 ADRs |
| "20/20 hostile contracts have `[bounded]` synthetic Rust runtime PASS" (prd/ARCHITECTURE.md:25) | status | verified | 20 `ln-hcNN-runner` crates tracked; governor `hostile-baseline-aggregate`: "PASS 20/20; FAIL 0/20"; sampled re-run `cargo test -p ln-hc01-runner --offline` → 1 passed, exit 0 (full 20-suite re-run not performed) |
| "`ln-consultant-parser` has 10 source modules including `lib.rs`, 64 integration test functions and 4 source-unit tests" (prd/ARCHITECTURE.md:133-135) | structure | stale | actual: 31 top-level src modules (incl. lib.rs) plus 14 `src/bin/` binaries; 358 `#[test]` functions under tests/; 54 `#[test]` functions in src/*.rs |
| "One page. If it grows, split detail into tracked focused PRD sub-docs" (one-page living oracle) (prd/ARCHITECTURE.md:326) | structure | stale | the file is 327 lines vs tracked budget 325 (tests/test_architecture_m171_alignment.py:28); its own test fails: "living oracle grew to 327 lines (budget 325)" (reproduced in the sidecar) |
| "G1 ... anchor is 119 structural hierarchy markers on the tracked 435-ФЗ fixture (`EXPECTED_HIERARCHY_COUNT` in `crates/ln-decode/tests/consultant_real_tracer.rs`)" (prd/ARCHITECTURE.md:136-137) | feature | verified | constant = 119 at consultant_real_tracer.rs:17; the 435-ФЗ fixture `law-source/consultant/...-d71bf702.xml` is tracked |
| "a bounded Rust reference-capture runtime landed under M211 (npa_anchor/npa_typed/npa_link/npa_classify/npa_continuation, npa-integration-runner)" (prd/ARCHITECTURE.md:66) | structure | verified | all five modules exist in crates/ln-decode/src/; runner at crates/ln-decode/src/bin/npa-integration-runner.rs |
| "`python_archive/product/`", "`python_archive/acp_git_lex/`" (prd/ARCHITECTURE.md:275) | structure | verified | gitignored (.gitignore:27); both exist in the primary checkout; governor `archive-path-policy` confirms ignored+untracked |
| "Values 3772/3641/2619/502 ... come from gitignored `consru_export`; ... skip-capable when the export is absent" (prd/ARCHITECTURE.md:147) | config | verified | .gitignore:153 `consru_export/`; export present on primary (43,785 files), absent in sidecar; governor `corpus-grounding` correctly reports "corpus absent; skipped" in the sidecar run |
| "the observable product CLI `law-nexus-inspect`" (prd/ARCHITECTURE.md:128,255) | structure | verified | crates/ln-product-cli/Cargo.toml `[[bin]] name = "law-nexus-inspect"`; `health`/`inspect`/`replay`/`subordinates` in src/main.rs; health run → status ok, exit 0 |
| KB ontology inventory (`ln-kb-ontology` write-set crate; `fold_membership_at`, `mint_work`/`compare_work_identities`, `try_push_node`/`try_push_edge`, `map_hierarchy_marker`, `fold_expression_presence`, `join_force_with_membership`, `DecodePrefixCatalog`, `legal_act_effect_day_to_ordinal`, product-cli `lift_extracted_hierarchy`) (prd/ARCHITECTURE.md:74-91) | feature | verified | all names found: fold_membership_at/try_push_*/fold_expression_presence/map_hierarchy_marker/legal_act_effect_day_to_ordinal in crates/ln-kb-ontology/src/, mint_work/compare_work_identities in crates/ln-identity/src/, join_force_with_membership in crates/ln-temporal/src/, DecodePrefixCatalog in crates/ln-decode/src/, lift_extracted_hierarchy in crates/ln-product-cli/src/main.rs |
| "no live RuVector/TEI product path", "Historical FalkorDB is not active infrastructure" (prd/ARCHITECTURE.md:32-42,160) | status | verified | Cargo.lock has no ruvector/falkordb/pyo3 entries; governor `live-adapter-readiness`: "ruvector=proposed, overclaim_count=0" |
| "**Consultant XML parser hardening** — `[bounded]` through M086–M105: 81 XML source files" (prd/ARCHITECTURE.md:282) | structure | verified | 82 tracked .xml under law-source/consultant/ = 81 document fixtures + the `Список документов (5).xml` list file; matches the 81-document OKF catalogue |


## Doc: doc/adr/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Current ADRs" index 0004–0031 with per-ADR statuses/lifecycles | status | verified | 27 ADR files on disk; every listed status matches the file frontmatter (0025/0026/0027 Accepted; 0028–0031 Proposed) and D098 tags; governor `adr-index-completeness` pass |
| ADR-0025..0031 index rows (table following the `fold_expression_presence`/`map_hierarchy_marker` comments) (doc/adr/README.md:64-74) | structure | stale | the 7 table rows still have no header/separator row — they directly follow two HTML comments after "## Retired Python-era records", so the index renders as plain pipe text, not a table |
| "active ADR frontmatter uses canonical `supersedes` and `superseded_by` keys. The legacy misspelling `superseds` ... is rejected on active ADRs by Governor" (doc/adr/README.md:17-20) | config | verified | frontmatter scan: only canonical keys (0005 `superseded_by: [ADR-0011#crate-map-only]`; 0011/0017 supersedes chained); governor `adr-supersession-graph` pass: "adr_nodes=27, supersession_edges=2, cycles=0" |
| "ADR-0001, ADR-0002 and ADR-0003 ... ADR-0006 ... local vault is gitignored, untracked" (doc/adr/README.md:57-63) | structure | verified | no 0001/0002/0003/0006 files under doc/adr/; vault roots (.lex/, archive/, python_archive/) gitignored and present only on the primary checkout (governor `archive-path-policy` pass) |

## Doc: doc/adr-architecture-cross-matrix.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "## 1. Present ADR inventory" table enumerates 0004–0024 as the present ADR set (doc/adr-architecture-cross-matrix.md:7-24) | structure | stale | doc/adr/ contains 0025–0031 (7 further active ADRs); 0025/0026/0027/0030/0031 are not mentioned anywhere in the matrix (0028/0029 only in passing) — the matrix predates ADR-0025+ and was never extended |

## Doc: CHANGELOG.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| M211-hkknug S01 entry: `ln-decode/src/npa_anchor.rs`; `tests/npa_members_gold_parity.rs` + TSV fixture `anchor-parity-fixture.tsv`; CI job `offline-contract-verifiers` (CHANGELOG.md:5-23) | structure | verified | npa_anchor.rs exists; crates/ln-decode/tests/npa_members_gold_parity.rs exists; crates/ln-decode/tests/fixtures/npa-members/anchor-parity-fixture.tsv exists; `.github/workflows/` defines job `offline-contract-verifiers` |
| Self-description (via README map): "Human-readable delivery history; not architecture authority" | status | verified | content is dated, revision-bound milestone records; the head entries' file claims all resolve (checked above) |

## Doc: prd/PRODUCT.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Planning baseline: `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)" (prd/PRODUCT.md:4) | status | verified | commit exists, dated 2026-08-11 ("chore: keep .agents/skills local-only (gitignored)") |
| "EA-02 tested revision: `37f82c4245642f7c1e9104f288db43df762178fe` (`assessment/02-product-contract.md`)" (prd/PRODUCT.md:5) | status | verified | commit exists: "docs: establish product contract assessment package" |
| "`[proposed]` Product Contract; document state `ready-for-assessment`" (prd/PRODUCT.md:3) | status | verified | matches README/ARCHITECTURE/roadmap framing ("EA-10 D150 accepted the assessment packet, not these documents") |

## Doc: prd/REQUIREMENTS.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Planning baseline: `60fd8245...` (2026-08-11)" (prd/REQUIREMENTS.md:5) | status | verified | same commit as the PRODUCT.md row |
| "EA-02 tested revision: `37f82c42...`" (prd/REQUIREMENTS.md:6) | status | verified | same commit as the PRODUCT.md row |
| "document state `ready-for-assessment`"; "`prd/ARCHITECTURE.md` currently labels the same design sequence L1–L7" (prd/REQUIREMENTS.md:4,10) | status | verified | ARCHITECTURE.md uses L1–L7 for ADR-0016..0022; both documents claim `[proposed]` |

## Doc: prd/temporal-legal-model.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "TL-G01–12 gates" | structure | verified | TL-G01..TL-G12 all present; sorted unique = exactly G01–G12 |
| "explicit 14-area completeness matrix" (§14) | structure | verified | "## 14. Primary-critique contract completeness matrix" at prd/temporal-legal-model.md:384 |
| "EA-03 tested revision: `e1ac83a714e20a6b551d5305fc4fca9f29d91aa7`" (prd/temporal-legal-model.md:4) | status | verified | commit exists: "docs: add temporal legal model crosswalk" |

## Doc: prd/parser/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Canonical artifacts: `prd/parser/schemas/*.json` (5), `profiles/{consultant_wordml,garant_odt}.yaml`, `examples/*.jsonl` (3), `odt_smoke_records.{json,md}` (prd/parser/README.md:13-20) | structure | verified | all listed files exist with the stated counts (5 schemas, 2 profiles, 3 jsonl examples, both smoke records) |
| "the PP filename mismatch (`PP_60_27-02-2022.odt` stated vs `PP_60_27-01-2022.odt` observed) must remain visible" (prd/parser/README.md:35,136) | structure | verified | law-source/garant/PP_60_27-01-2022.odt is the tracked file; no 27-02 variant tracked |
| "Large Python-era dumps ... relocated to `prd/archive/parser-dumps-era/` (gitignored archaeology)" (prd/parser/README.md:9,19) | structure | verified | .gitignore:136 `prd/archive/parser-dumps-era/`; governor `archive-path-policy` lists the vault as ignored+untracked |


## Doc: prd/retrieval/rust_retrieval_output_validator_contract.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Contract version string `retrieval-output-validator/rust-v1`, exported as `ln_query::retrieval_output::VALIDATOR_CONTRACT_VERSION`" | feature | verified | crates/ln-query/src/retrieval_output.rs:22 → `pub const VALIDATOR_CONTRACT_VERSION: &str = "retrieval-output-validator/rust-v1";` |

## Doc: prd/retrieval/rust_retrieval_metrics_proof.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Computation surface: `crates/ln-query/src/retrieval_metrics.rs`"; "Consuming test: `crates/ln-query/tests/retrieval_metrics.rs`" | structure | verified | both files exist |
| "proof_command: `cargo test -p ln-query --offline --test retrieval_metrics`" | command | verified | re-ran in sidecar: "test result: ok. 7 passed; 0 failed" — the deterministic proof reproduces at HEAD |

## Doc: prd/project-state/roadmap.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Latest completed product milestone: M173, inspect PP_60 class-matched punkt proof" (roadmap.md:43-44) | status | stale | the doc's own data source prd/project-state/data/roadmap.json records `completed_milestone_groups` through "M224-M224" complete (generated_at 2026-10-24); the freshness framing below does not cover this line |
| "Until native Path state exists and the bootstrap PR is accepted on the default branch, this projection keeps describing the **frozen legacy GSD-Pi milestone ledger**" (roadmap.md:9-16) | status | stale | the condition has lapsed: native Path state exists and bootstrap PR #1 merged (`54a495cd`, 2026-10-25); the projection now carries native shipped markers for M007 and M010 (roadmap.md:50-60) |
| "Initial front synchronization was frozen in EA-05 at `94d58ea`"; EA-09 packet `120d44b` (roadmap.md:7) | status | verified | both commits exist ("docs: synchronize roadmap and readiness front"; "docs: record EA-09 independent desk assessment") |
| Active Direction Contract block (runtime=rust-only; python=repository-control-only; graph_vector=ruvector; ...) (roadmap.md:25-33) | config | verified | identical block in prd/ARCHITECTURE.md:35-42; governor `architecture-direction-contract` pass |
| "Local GSD workflow marker: doc-consistency — shipped/archived/integrated (2026-10-29) on branch `gsd-path/M010` ... through the green run 40805352394. Current-state document: `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`" (roadmap.md:50-56) | status | verified | ship `fd60893f` (2026-10-29), integration `3a39fd70` into main, tag `milestone/010-doc-consistency` (annotated); run 40805352394 at `319a7b1a` conclusion success (live `gh run view`); the named current-state document exists |
| "Local GSD workflow marker (superseded 2026-10-28): ci-proof-inputs — ship commit `e311f0ed`, integration merge `50386e26` into `main`, tag `milestone/007-ci-proof-inputs`, archive `.project/archive/007-ci-proof-inputs`" (roadmap.md:57-60) | status | verified | commit subjects/dates match ("ship: M007 — ci-proof-inputs"; "integrate: M007 — merge gsd-path/M007 into main"); tag exists; archive directory exists |

## Doc: law-source/consultant/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "82 XML-документа КонсультантПлюс" (tracked fixtures) (law-source/consultant/README.md:7) | structure | verified | `git ls-files 'law-source/consultant/*.xml'` → 82 |
| "Плюс подкаталог `.deprecated/` (40 файлов) — ... остаётся на диске только как история" (law-source/consultant/README.md:9) | status | stale | `.deprecated/` does not exist on the primary checkout (a gitignored path lost on re-checkout); only the gitignore entry remains, and the governor's `law-source-fixture-guard` observes "`.deprecated` ignored and untracked", not present-on-disk |
| Corpus counts: "43 785 файлов, включая `npa/` 916, `fas/` 30 399, `courts/` 5 667, `xml/` 6 803" (law-source/consultant/README.md:15) | structure | verified | primary-checkout find counts: 43,785 / 916 / 30,399 / 5,667 / 6,803 — exact |
| "Проверено по sha256: пересечение = 0 файлов" (fixture set disjoint from corpus) (law-source/consultant/README.md:16) | feature | unverifiable | would need sha256 of all 82 tracked fixtures against the full 3.7 GB corpus tree; not re-run in this audit |
| "В корпусе — 118 редакций: `consru_export/.../npa/law_2013-04-05_44-fz/edition-NNNN_*.xml`" (law-source/consultant/README.md:19) | structure | verified | `ls consru_export/consru_export/exports/npa/law_2013-04-05_44-fz \| wc -l` → 118 on the primary checkout |
| Canonical fixtures: `...-44-fz-...-f9c8ca4c.xml`, `Список документов (5).xml` (law-source/consultant/README.md:31-32) | structure | verified | both files tracked under law-source/consultant/ |
| "Governor-проверка `law-source-fixture-guard` покрывает только маркер fixture vault в этом README (плюс состояние `.deprecated/` в `.gitignore`) — глоббинг каталога как корпуса она не замечает" (law-source/consultant/README.md:35) | feature | verified | the live governor run shows `law-source-fixture-guard`: "README marker present, .deprecated ignored and untracked" — no corpus-globbing probe exists (grep over src/, scripts/, tests/ finds none), exactly as the README now states |
| "См. также: ... `prd/architecture/npa-skeleton-fsm.yaml`" (law-source/consultant/README.md:48) | structure | verified | file exists |

## Doc: law-source/consultant/okf/index.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Portable Open Knowledge Format (OKF) catalogue of the XML legal-document sources in this directory" (81 linked documents) | structure | verified | 81 links, all resolve to existing documents/*.md; 81 files on disk; zero orphans in either direction |

## Doc: docs/agent-stack/WORKFLOW.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Описание product behavior — PDD, `product-model/`" (ownership table, docs/agent-stack/WORKFLOW.md:14) | structure | verified | product-model/ is tracked (28 files) and populated with the PDD capability model |
| "`.ai/path-run.json` — **настройка нашей обёртки**" with the profile block (schema 1, projectDir .project, worker scripts/ai/allspark-worker -p, capacity 1, childTimeoutSeconds 900, pollSeconds 5, maxAttempts 1) (docs/agent-stack/WORKFLOW.md:26-44) | config | verified | the tracked-side `.ai/path-run.json` on the primary checkout matches the documented profile field-for-field; `scripts/ai/allspark-worker` exists |
| "`.gsd-path/runtime.json`" (docs/agent-stack/WORKFLOW.md:13) | config | verified | file exists: `{"schema": "gsd-path/runtime/v1", "version": "1.6.2", "digest": "6f95a31e..."}` |

## Doc: docs/agent-stack/PHASE-ADAPTER.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "`scripts/ai/phase-dispatch.py` is the repo-owned glue" (docs/agent-stack/PHASE-ADAPTER.md:3) | structure | verified | file exists (608 lines) with its stub-child test suite `tests/test_phase_dispatch_adapter.py` |
| Header status: "The adapter is verified against deterministic stub children only. No real Allspark/model pilot has been run, no native phase gate has consumed its records, and the acceptance table in §8 below is **not yet satisfied**" (docs/agent-stack/PHASE-ADAPTER.md:10-14) | status | stale | contradicted by the same document: §9 (line 247) says "PARTIALLY satisfied — Three rows were proven by a real-model pilot on 2026-10-25 (see §9.1)", §9.1 records the pilot, and `.project/archive/001-001-native-workflow-acceptance/research/` and `.project/archive/004-pointer-refresh-m003/research/` hold `dispatch-record-*.json` files (2026-10-26/28) produced through the adapter during native phases |
| "## 9. Acceptance status — PARTIALLY satisfied. Three rows were proven by a real-model pilot on 2026-10-25" + §9.1 pilot record (docs/agent-stack/PHASE-ADAPTER.md:247-296) | status | verified | consistent with the archived dispatch records and with the doc's explicit non-proof list; the "What this pilot does NOT prove" boundaries are preserved |
| "uv run ruff check scripts/ai/phase-dispatch.py tests/test_phase_dispatch_adapter.py; uv run ruff format --check ..." (docs/agent-stack/PHASE-ADAPTER.md:304-305) | command | verified | both ran in the sidecar → "All checks passed!" / "2 files already formatted" |


## Doc: docs/agent-stack/POST-SHIP-STATE-2026-10-28.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Shipped-milestones table M001–M003 (ship `886a36a8`/`ba31ffb8`/`7786d5d3`, integration `4e0cd4db`/`f9061889`/`7e200294`, tags, archives) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:18-23) | structure | verified | all six commits exist with the exact subjects/dates; the three annotated tags resolve to the integration merges; the three `.project/archive/` directories exist |
| "bootstrap PR merge (`54a495cd`)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:15-16) | status | verified | commit exists: "Merge pull request #1 from rager306/chore/allspark-path-pdd-bootstrap" (2026-10-25) |
| CI red table: runs 40446077586 @`4e0cd4db`, 40533158703 @`f9061889`, 40632991938 @`7e200294` concluded failure (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:59-64) | status | verified | live `gh run view` → failure/failure/failure at exactly those head SHAs |
| "The last green `repository-quality` run on `main` is run 40203533977 (2026-10-25, on the bootstrap merge `54a495cd`)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:55-56) | status | verified | live `gh run view 40203533977` → success at `54a495cd` |
| M001 delivered: M225 rerun `prd/migration/rust-evidence/m225-validation-rerun-m001.json` verdict `hermetic-pass-parity-unproven`; minimal PDD model in `product-model/`; GitNexus re-indexed (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:29-34) | status | verified | the JSON exists; product-model/ tracked; `.gitnexus/` regenerated on the primary (indexedAt 2026-10-26) |
| "vendored at `.ai/vendor/gsd-path-1.6.2.tgz`, digest-verified against `.gsd-path/runtime.json` (`1.6.2@6f95a31e…`)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:36-37,152-153) | config | verified | the tgz exists and contains `gsd-path/scripts/install.py`; `.gsd-path/runtime.json` records version 1.6.2, digest `6f95a31e4b8a...d9f6f` |
| M005–M009 table (ship/integration per milestone) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:125-131) | structure | verified | all ten commits exist with matching subjects/dates (e890831e/121a2006, 7d1c62c2/3e047fe8, e311f0ed/50386e26, 63c7d07d/4dd35d25, 5e5fdaee/319a7b1a) |
| "40805352394 — `319a7b1a` (M009) — success — all four jobs" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:119-121) | status | verified | live `gh run view` → success at `319a7b1a` |
| "`prd/project-state/workflow-backend.json` `cutover` stays `false`" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:133-135) | status | verified | file content: `{"schema": 1, "backend": "gsd-path", "cutover": false}` |
| "## M004 continuation (current)" — "Milestone `pointer-refresh-m003` ... branch `gsd-path/M004` ... is active" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:95-99) | status | stale | M004 shipped and integrated (tag `milestone/004-pointer-refresh-m003` → `57bb2282` "integrate: M004", 2026-10-28); M005–M009 are recorded as shipped in this same document and M010 shipped 2026-10-29; at the audited HEAD the workflow state is shipped/done M010 and M011 inspect is active — the "(current)" framing is two milestones behind |
| Non-claims: "Integrated `main` is red on `repository-quality` (see the CI section)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:196-197) | status | stale | contradicted by the document's own M005–M009 section ("the integrated `main` is green", run 40805352394 success) and by live CI: the newest main run 40822037565 at `3a39fd70` (the audited HEAD) concluded success |
| Fresh-session bootstrap commands (`tar -xzf .ai/vendor/gsd-path-1.6.2.tgz` + `install.py --runtime-restore`; `python3 scripts/ai/path-run.py status`; `uv run --frozen python -m law_nexus_harness.governor` expecting exit 0; `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`) (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:147-181) | command | verified | path-run.py status ran in the sidecar (exit 0, honest state JSON); governor ran exit 0 with 72 pass in the shipped-integrated context; the freshness suite passed (6 passed, 5 skipped); the vendored archive contains `gsd-path/scripts/install.py` (tar listing); the restore itself was not executed (it writes a runtime store — outside read-only scope) |

## Doc: docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The pointer suites (`tests/test_post_ship_pointers.py`, `tests/test_project_state_roadmap_freshness.py`) run in CI and fail on the shipped tree when this is skipped" (docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:19-20) | feature | verified | both test files exist and are referenced in `.github/workflows/repository-quality.yml`; M010 history shows the `docs:` refresh commit `e8b5696f` immediately before ship `fd60893f` |
| "the ship commit may only change `.project/`" (docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:17-18) | structure | verified | `git show --name-only fd60893f` → only `.project/...` paths |

## Doc: .agents/skills/law-nexus-rust/SKILL.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Python product code is archived prior art under `python_archive/product/`" (SKILL.md:12) | structure | verified | gitignored (.gitignore:27); exists in the primary checkout |
| References: `references/verification-matrix.md`, `doc/adr/0015-...`, `prd/temporal-legal-model.md` §3, `prd/architecture/temporal-vocabulary-contract.json` (SKILL.md:17,20,43,49) | structure | verified | all referenced paths exist |
| "follow project GitNexus impact-analysis requirements" (SKILL.md:29) | structure | verified | the AGENTS.md GitNexus contract exists and the local `.gitnexus/` index is present on the primary checkout (see the AGENTS.md row for its staleness nuance) |

## Doc: .agents/skills/law-nexus-rust/references/verification-matrix.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Default command set (`cargo fmt --all --check`, `cargo check/test/clippy --workspace --offline`, `uv run law-nexus-harness governor/preflight`, `uv run python scripts/verify-adr-conformance.py`) (verification-matrix.md:26-66) | command | verified | `law-nexus-harness` console script declared (pyproject.toml); fmt ran clean inside preflight; governor/preflight/conformance all executed in this audit (results in the README section); the full `cargo check/test/clippy --workspace` was not re-run (bounded-sample policy) |
| Contract suites `npa_corpus_sweep_contract`, `morphology_contract` (verification-matrix.md:31) | structure | verified | crates/ln-decode/tests/npa_corpus_sweep_contract.rs and morphology_contract.rs exist |
| "`scripts/m205_s04_reconciliation.py check` plus its subprocess adversarial suite (`scripts/test_m205_s04_reconciliation.py`)" (verification-matrix.md:101-102) | command | verified | both scripts exist |

## Doc: .agents/skills/law-nexus-rust/UPSTREAM.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Upstream `SKILL.md` SHA-256: `5a74070e...`" at pinned commit `fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9` (UPSTREAM.md:6,9) | status | verified | fetched raw.githubusercontent.com at that commit → sha256 exact match `5a74070e740c8aacec1264adfc537daeab14c0f629bb604943295c08fd9252e6` |
| "Upstream `LICENSE` SHA-256: `663ce6f8...`" (UPSTREAM.md:10) | status | verified | same fetch → sha256 exact match `663ce6f8f087dc366602ac34eefd4cf71a5d8db411359422298a1399a014a9d5` |
| "identifies itself as ... 265 rules"; "Upstream version in frontmatter: 1.5.1" (UPSTREAM.md:8,15) | status | verified | fetched upstream SKILL.md frontmatter: version "1.5.1", "265 rules across 26 categories" |

## Doc: .agents/skills/law-nexus-subagent/SKILL.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Live discovery path is `~/.gsd/agent/agents/`, not project `.pi/agents` or `.gsd/agents`" (SKILL.md:10,13,51) | structure | verified | /root/.gsd/agent/agents/ exists with `_CONTRACT.md` and role files incl. scout/reviewer/worker/researcher/tester/planner; no `.pi/` in the repository |

## Doc: prd/architecture/npa-analysis-jsonl-contract.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Tracked as an M221 authority-reconciliation source binding (hash-pinned companion) (`prd/architecture/m221-s05-docs-reconciliation.yaml` binds path+sha256) | status | stale | `pytest tests/test_m221_authority_reconciliation.py::test_source_bindings_resolve_and_match_disk` fails: "sha256 drift for source binding: prd/architecture/npa-analysis-jsonl-contract.md" — the file no longer matches its pinned digest at this HEAD (the M221 s05 readiness battery fails with it) |


## Doc: product-model/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "This directory is the **Product Model** of this repository ... plain Markdown tracked in Git" (product-model/README.md:1-6) | structure | verified | `git ls-files product-model` → 28 tracked files (25 Markdown) |
| "use the `pdd-verify` skill ... `pdd-ideate` ... `pdd-map`" (product-model/README.md:14-22) | integration | verified | the three PDD skills are installed at `.agents/skills/pdd-{verify,ideate,map}/` on the primary checkout (local skill tree; the `npx pdd-toolkit install` fallback is an installed-dependency command and was not run) |

## Doc: product-model/product.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "One binary, `law-nexus-inspect`, decodes a document file (Consultant WordML or Garant ODT) ... compares two editions ... or resolves the punkt structure of a subordinate act" (product-model/product.md:21-24) | feature | verified | main.rs dispatches exactly health/inspect/replay/subordinates (main.rs:619-653); live inspect on a Consultant XML and subordinates on a Garant ODT both returned status ok |
| "Only Consultant WordML (.xml) and Garant ODT (.odt) inputs are accepted" (product-model/product.md:32) | feature | verified | live probe: `inspect /tmp/probe-unsupported.txt` → `{"phase":"Parse","status":"failed","kind":"UnsupportedFamily",...}`, exit 1; main.rs:130 |
| "Retrieval ... exercised through `StubEmbedding`, the fail-closed stub of the embedding port" (product-model/product.md:31,14) | feature | verified | `struct StubEmbedding; impl EmbeddingPort for StubEmbedding` at main.rs:58-59; used at main.rs:222,1380 |

## Doc: product-model/business-rules/failures-are-typed-and-atomic.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "A command that cannot complete prints exactly one failure record naming its phase and kind and exits nonzero ... usage errors print the usage line and exit 2 before any input is read" (failures-are-typed-and-atomic.md:11-20) | feature | verified | live probes: missing path → `{"phase":"Io","kind":"ReadFailure","fingerprint":"fnv1a64:...","duration_ms":...}`, exit 1; `.txt` path → Parse/UnsupportedFamily, exit 1; `replay` without arguments → usage line on stderr, exit 2 (main.rs:101-106,626-653) |

## Doc: product-model/business-rules/reports-carry-explicit-non-claims.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The inspect, replay, and subordinates reports each end with a `non_claims` list" (reports-carry-explicit-non-claims.md:13) | feature | verified | `non_claims` emitted in the inspect (main.rs:547), replay and subordinates (main.rs:1166,1470) reports; present in every live probe output |

## Doc: product-model/business-rules/retrieval-is-deterministic-non-semantic.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The retrieval count ... comes from hash-derived vectors over the in-memory store, ranked by cosine similarity; ... a construction failure is a typed storage error, never a silent all-zero vector" (retrieval-is-deterministic-non-semantic.md:11-18) | feature | verified | StubEmbedding hash-derived vectors (main.rs:58-59,222,1380); inspect report carries the retrieval count with status ok/unavailable/unexpected_result semantics; no semantic embedding dependency in Cargo.lock |

## Doc: product-model/business-rules/runs-keep-nothing-between-runs.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Every command builds its stores in memory, prints its report, and exits; no document, count, vector, or graph node survives the process" (runs-keep-nothing-between-runs.md:11-20) | feature | verified | main.rs builds per-run in-memory stores (InMemoryVectorStore/InMemoryGraphStore via ln-storage) and writes no files; no persistence paths in the CLI (static read of main.rs) |

## Doc: product-model/capabilities/check-health/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The health subcommand reads no input, prints one JSON status line, and exits 0" (check-health/capability.md:6-8) | feature | verified | live run → `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust",...}`, exit 0 |

## Doc: product-model/capabilities/check-health/scenarios/health-ok.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The status line prints with `status: ok`, naming `law-nexus-inspect` and the Rust runtime, and the command exits 0" (health-ok.md:37-38) | feature | verified | live probe output names binary law-nexus-inspect and runtime rust, exit 0 |

## Doc: product-model/capabilities/inspect-document/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Decode one act file and print a bounded JSON report ... blocks, hierarchy markers and their registry lifts, membership proposals, admits, and commits, the structural AST assembly with its oracle drift counters, text-CTV resolutions, the detected document group, reference, temporal, and deontic counts, one retrieval hit count, and the presence report ... in-memory adapters ... StubEmbedding ... every report ends with an explicit non-claims list" (inspect-document/capability.md:9-24) | feature | verified | live inspect on the tracked 63-ФЗ XML printed exactly these sections (blocks/hierarchy_markers/lifts/membership_*/... counters and `non_claims`); store wiring at main.rs:222 |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-consultant-document.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints with status ok: counted blocks, markers, lifts, membership, assembly, retrieval, ... and the non-claims list" for a Consultant WordML path (inspect-consultant-document.md:37-59) | feature | verified | live run on the tracked 63-ФЗ XML: `{"phase":"Inspect","status":"ok",...,"source":{path,bytes,fingerprint},"family":"family:consultant-wordml","result":{"blocks":586,...}}` with non_claims, exit 0 |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-empty-input-is-explicit-zero.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints with status ok and `blocks: 0`; the empty result is visible" (inspect-empty-input-is-explicit-zero.md:30) | feature | verified | live probe on a 0-byte `.xml` → `{"phase":"Inspect","status":"ok",...,"result":{"blocks":0,"hierarchy_markers":0,...}}` |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-refuses-unreadable-path.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "One typed failure record (phase Io, kind ReadFailure, message fingerprint, duration) prints and the command exits 1; no report follows" (inspect-refuses-unreadable-path.md:30-31) | feature | verified | live probe on a nonexistent path → `{"phase":"Io","status":"failed","kind":"ReadFailure",...,"fingerprint":"fnv1a64:2bfc07...","duration_ms":1}`, exit 1 (main.rs:120,106) |

## Doc: product-model/capabilities/inspect-document/scenarios/inspect-refuses-unsupported-family.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "One typed failure record (phase Parse, kind UnsupportedFamily) prints and the command exits 1; no decoding starts" (inspect-refuses-unsupported-family.md:30-31) | feature | verified | live probe on an existing `.txt` file → `{"phase":"Parse","status":"failed","kind":"UnsupportedFamily",...}`, exit 1 (main.rs:130) |

## Doc: product-model/capabilities/replay-edition/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "read the hierarchy markers of the seed and target files, diff the marker sets, turn the diff into attach and detach drafts ... verify by drift, missing, and phantom counters ... Missing arguments are a usage error before any file is read" (replay-edition/capability.md:9-19) | feature | verified | live same-file replay printed seed/target source blocks, `diff added:0 removed:0`, drafts 0 and verify counters, status ok; `replay` with no arguments → usage line, exit 2 (main.rs:635-636) |

## Doc: product-model/capabilities/replay-edition/scenarios/replay-refuses-missing-arguments.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The usage line prints on stderr and the command exits 2; nothing is read or processed" (replay-refuses-missing-arguments.md:13,30) | feature | verified | live probe → `usage: law-nexus-inspect replay <seed-edition> <target-edition>`, exit 2 |

## Doc: product-model/capabilities/replay-edition/scenarios/replay-same-edition-zero-drift.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "when the seed equals the target, the diff, the drafts, and the verify counters are all zero" (replay-same-edition-zero-drift.md:53-54) | feature | verified | live same-file replay on the tracked 402-ФЗ XML: `"diff":{"added":0,"removed":0},"drafts":{"total":0,...}` status ok, exit 0 |

## Doc: product-model/capabilities/resolve-subordinates/capability.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "bind its document group from the kind the operator names ... collect its punkt units, mint fixture component identities ... A missing effect day is fail-closed: the report keeps the key and states the skip reason" (resolve-subordinates/capability.md:9-20) | feature | verified | live run on the tracked Garant PP_60 ODT: group `government_resolution`, `punkt_units:246`, fixture expression id, effect_day, non_claims; the no-date skip path returns `skip_reason: no_document_date` (main.rs:1112) |

## Doc: product-model/capabilities/resolve-subordinates/scenarios/subordinates-bound-group-report.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints bounded JSON with the bound group ..., punkt unit and fixture identity counts, resolved and conflicting text versions, the effect day, and the non-claims list" (subordinates-bound-group-report.md:33,53) | feature | verified | live probe output carried document_group, punkt_units/cc_punkts 246, ctv_resolved/conflict, effect_day and non_claims, status ok |

## Doc: product-model/capabilities/resolve-subordinates/scenarios/subordinates-missing-date-fails-closed.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The report prints with status ok, `skip_reason: no_document_date`, and zero text-version counts" (subordinates-missing-date-fails-closed.md:13,33) | feature | verified | live probe on a dateless copy of a tracked ODT → `"skip_reason":"no_document_date"` in the output |

## Doc: product-model/coverage.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The law-nexus-inspect binary, its four subcommands, reports, and failure records" covered under crates/ln-product-cli/; storage/embedding ports and in-memory adapters under crates/ln-storage/; exclusions/unmapped paths listed (coverage.md:4-16) | structure | verified | all named paths exist; four subcommands confirmed in main.rs; the "registry-backed inspect and replay paths depend on registry data absent in this environment" limitation matches the observed inspect run (hierarchy_lifts_unknown=345, no registry binding) |

## Doc: product-model/entities/document.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Information kept: Path, Byte size, Content fingerprint, Source family (entities/document.md:8-12) | feature | verified | every live report's `source` block printed path, bytes, `fingerprint: fnv1a64:...` and `family` (e.g. family:consultant-wordml / family:garant-odt); fingerprint via `fingerprint_bytes` (main.rs:123) |

## Doc: product-model/entities/operator.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The product keeps no facts about the operator: there is no sign-in, no profile, and no session" (entities/operator.md:9) | structure | verified | no auth/session/profile code or operator fields anywhere in crates/ln-product-cli/src/ (static read); reports carry only document facts |

## Doc: product-model/interfaces/terminal/interface.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "one binary, four subcommands": health, `inspect <path>`, `replay <seed-edition> <target-edition>`, `subordinates <resolution or order> <path>` (interfaces/terminal/interface.md:6-14) | command | verified | exact usage strings at main.rs:626,635,644,651; all four exercised live in this audit |

## Doc: product-model/interfaces/terminal/screens/document-report.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "the source block (path, bytes, fingerprint), the decoded family, the result counters, and the explicit non-claims list" (screens/document-report.md:13) | feature | verified | matches the live inspect and subordinates outputs field-for-field |

## Doc: product-model/interfaces/terminal/screens/replay-report.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "the seed and target source blocks, the marker diff, the drafted changes, and the replay verify counters with their status" (screens/replay-report.md) | feature | verified | matches the live replay output (`seed`/`target` blocks, `diff`, `drafts`, verify counters, status ok) |


## Descriptive docs

<!-- The remaining inventoried docs carry no testable product claims; they are dated evidence/decision/assessment records, design contracts, protocols, process instructions, or corpus data. Scope notes: -->

<!-- - Root `WORKFLOW.md` describes only the installed GSD Path pipeline (router, phases, gates, dispatch contract). Per the audit scope, GSD Path source/pipeline internals are installed-dependency claims, not law-nexus product claims; the file contains no law-nexus product statements to test, so it is listed as descriptive. -->
<!-- - `doc/adr/0004..0031` (27 files) are decision records: their testable surface (Status, lifecycle tags, supersession keys, index coverage, retired IDs, link integrity) is verified in aggregate in the `doc/adr/README.md` section above and by the passing governor probes (`adr-truth-oracle-sync`, `adr-structure-hygiene`, `adr-link-integrity`, `adr-supersession-graph`); the remaining body text is normative design substance, which reality cannot contradict. -->
<!-- - `assessment/*` (35), `doc/review/*` (18), `prd/migration/rust-evidence/*` (36, incl. probes), `prd/migration/decommission/*` (2), the four frozen migration roadmaps, `prd/annotation/*` (9), the `prd/architecture/m1../m2../` admission/adoption/decision/checkpoint records, and the `prd/architecture/*` governance contracts and D7-quarantined derived views are explicitly dated, revision-pinned records of past decisions, runs, or plans (most carry their own "not yet executed / non-authoritative" markers). Their recorded values were treated as historical evidence, not current-state claims; spot checks all resolved (pinned commits `50173de`, `9d72884`, `24b8872`, `bfe2ee6`, `430ebfd`, `962a4e7`, `f09416f` exist), and their mechanically checkable surfaces are enforced by passing governor probes (hostile-proof-hc01..hc20 aggregate PASS 20/20, companion-manifest, golden-corpus-catalog, npa-control-artifacts, kb-ontology-draft, temporal-vocabulary checks, model-crystal-anchors with L0 digest ok, capability-promotion-board, review-case-integrity). External stack pins (Allspark fork, GSD Path 1.6.2, PDD) are installed-dependency claims outside this repository's product scope. -->
<!-- - `docs/agent-stack/AGENT_HANDOFF`, `ALLSPARK_NOTES`, `CUTOVER-READINESS-M001`, `INSTALL`, `MIGRATION`, `MIGRATION-RECORD-2026-10-23`, `PATH_SETUP`, `POST-SHIP-STATE-2026-10-27`, `SOURCES`, `TESTED`, and `history/LEGACY_CROSSWALK` are dated records/snapshots (each superseded snapshot says so in its own header); their recorded values were spot-checked where cheap (ship/integration commits and tags resolve, the vendored `gsd-path-1.6.2.tgz` and `runtime.json` digest agree, `tests/test_m001_cutover_readiness.py` exists) and treated as historical evidence, not current-state claims. The one current-state document (`POST-SHIP-STATE-2026-10-28.md`) is audited above. -->
<!-- - `law-source/consultant/okf/documents/*` (81) are corpus source documents (provider-derived legal text), not product documentation. -->
<!-- - `.ai/allspark/roles/{owner,reviewer,worker}.md`, `.agents/skills/law-nexus-subagent/workflows/parent-dispatch.md`, and the `.agents/skills/law-nexus-rust` references (`curated-rust-guidance`, `project-policy`) and five workflows are process instructions (directives), not claims; their referenced files exist (checked via the skill sections above). Note: `.agents/skills/` is intentionally gitignored local tooling (kept out of the index per commit `60fd8245`), present on both the primary checkout and this sidecar. -->
<!-- - `prd/archive/README.md` documents nine gitignored vault subtrees; the governor `archive-path-policy` probe lists all nine `prd/archive/*` vaults ignored+untracked in the live run. -->
<!-- - `doc/gsd-headless-supervisor.md` is the tracked operator contract for the retired GSD-Pi supervisor; AGENTS.md itself scopes it as historical process archaeology, so its instructions are a dated record, not operative drift. `doc/litho-runbook.md` documents a gitignored local derived-wiki tool (non-authoritative). -->
<!-- - The remaining `prd/architecture/*` contracts and projections were sampled; their owning modules/tests exist (e.g. `ln_decode::source_package`, reader/cleaned-projection tests) and their headers mark them non-authoritative. -->


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

## Remediation queue

<!-- Every non-verified claim, classified. The user rules on this queue;
     the auditor never fixes anything.
     Numbers are unique and strictly increasing, not necessarily contiguous.
     A persisting row keeps its number; a new row takes a number above every
     prior queue number and every User rulings Queue #. Never reuse a retired
     number: a ruling stays bound to the item it was made for. -->

| # | Doc | Claim | Verdict | Class | Suggested action |
|---|-----|-------|---------|-------|------------------|
| 1 | README.md | "The workspace has 45 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed `ln-applicability`" (README.md:12-16) | stale | fix-doc | Recount from Cargo.toml: 47 members; add `ln-kb-ontology` and `ln-consultant-parser` to the map table |
| 2 | README.md | "the executable 44-member inventory" (README.md:301) | stale | fix-doc | Same recount as #1 (README.md:301); make the three numbers (12/216/301) consistent |
| 20 | README.md | "Latest tracked product/design band: **M165**" (README.md:38) | stale | fix-doc | Refresh the Current-status paragraph to the tracked ledger (roadmap.json groups through M224, notes through 2026-10-16; M010 shipped on the Path track) or point at roadmap.json as the live front |
| 21 | README.md | "The current documentation/control baseline includes post-D150 assessments 13–18" (README.md:39) | stale | fix-doc | Update the assessment range (tracked set is 00–34) and move the "latest remediation assessment" pointer to assessment/34 |
| 22 | README.md | "`cargo run -q -p ln-product-cli -- health` # release health smoke" (README.md:413) | stale | fix-doc | Document `--bin law-nexus-inspect` (verified working), or add `default-run = "law-nexus-inspect"` to crates/ln-product-cli/Cargo.toml (owner decision) |
| 23 | AGENTS.md | "Known issue: 2,478 artifact rows in the DB contain `../`-style paths" (AGENTS.md:412,414) | stale | fix-doc | Update to the current frozen-DB count (3,074 of 8,355; queried read-only 2026-10-25 and 2026-10-30) or date-bound the figure to its 2026-08-31 assessment |
| 24 | AGENTS.md | Data Sources Map: "law-source/consultant/ — Fragment of the corpus (122 XML files)" (AGENTS.md:404) | stale | fix-doc | State 82 tracked fixtures and note the 40 `.deprecated/` files are gitignored and absent from current checkouts |
| 25 | prd/ARCHITECTURE.md | "`ln-consultant-parser` has 10 source modules including `lib.rs`, 64 integration test functions and 4 source-unit tests" (prd/ARCHITECTURE.md:133-135) | stale | fix-doc | Refresh the counts (31 src modules + 14 bins, 358 integration `#[test]`, 54 unit `#[test]`) or drop exact numbers |
| 26 | prd/ARCHITECTURE.md | "One page. If it grows, split detail into tracked focused PRD sub-docs" (one-page living oracle) (prd/ARCHITECTURE.md:326) | stale | fix-doc | Trim the oracle to ≤325 lines per the M171 budget test (currently 327) or split detail into sub-docs; raising the tracked budget is an owner decision |
| 27 | doc/adr/README.md | ADR-0025..0031 index rows (table following the `fold_expression_presence`/`map_hierarchy_marker` comments) (doc/adr/README.md:64-74) | stale | fix-doc | Restore the missing table header/separator so the index renders as a table |
| 28 | doc/adr-architecture-cross-matrix.md | "## 1. Present ADR inventory" table enumerates 0004–0024 as the present ADR set (doc/adr-architecture-cross-matrix.md:7-24) | stale | fix-doc | Extend the inventory and cross-surface matrix to ADR-0031 |
| 29 | prd/architecture/npa-analysis-jsonl-contract.md | Tracked as an M221 authority-reconciliation source binding (hash-pinned companion) (`prd/architecture/m221-s05-docs-reconciliation.yaml` binds path+sha256) | stale | fix-doc | Re-pin the binding to the current file digest or revert the unpinned edit — the owner confirms which revision is canonical (the M221 s05 readiness battery fails with it) |
| 30 | prd/project-state/roadmap.md | "Latest completed product milestone: M173, inspect PP_60 class-matched punkt proof" (roadmap.md:43-44) | stale | fix-doc | Sync the front with roadmap.json/CHANGELOG (json groups through M224-M224, generated 2026-10-24), or date-bound the line as frozen legacy-ledger text like the marker rows below it |
| 31 | law-source/consultant/README.md | "Плюс подкаталог `.deprecated/` (40 файлов) — ... остаётся на диске только как история" (law-source/consultant/README.md:9) | stale | fix-doc | Reword: the set is gitignored and may be absent after a fresh checkout (it is absent in the current primary checkout) |
| 32 | law-source/consultant/README.md | "Проверено по sha256: пересечение = 0 файлов" (fixture set disjoint from corpus) (law-source/consultant/README.md:16) | unverifiable | fix-doc | Date-bound the recorded 2026-09-26 check (or commit a fixture-hash manifest so it can be re-verified cheaply) |
| 33 | README.md | "MADR ADRs 0004–0023 (0001/0002/0003/0006 retired, not present)" — the `doc/adr/` Active-tree row (README.md:277) | stale | fix-doc | Update the range to 0004–0031 to match doc/adr/ and the README's own ADR-0024..0031 mentions (README.md:289-292) |
| 34 | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md | Non-claims: "Integrated `main` is red on `repository-quality` (see the CI section)" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:196-197) | stale | fix-doc | Rewrite the bullet to the green state the document itself records (M005–M009 section: run 40805352394 success; live: run 40822037565 at `3a39fd70` success) |
| 35 | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md | "## M004 continuation (current)" — "Milestone `pointer-refresh-m003` ... branch `gsd-path/M004` ... is active" (docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:95-99) | stale | fix-doc | Reframe the M004 section as dated history (M004–M010 shipped/integrated; at the audited HEAD M011 inspect is active) |
| 36 | docs/agent-stack/PHASE-ADAPTER.md | Header status: "The adapter is verified against deterministic stub children only. No real Allspark/model pilot has been run, no native phase gate has consumed its records, and the acceptance table in §8 below is **not yet satisfied**" (docs/agent-stack/PHASE-ADAPTER.md:10-14) | stale | fix-doc | Align the header with §9 (PARTIALLY satisfied; real-model pilot 2026-10-25 in §9.1; dispatch records consumed by the M001/M004 native phases) |
| 37 | prd/project-state/roadmap.md | "Until native Path state exists and the bootstrap PR is accepted on the default branch, this projection keeps describing the **frozen legacy GSD-Pi milestone ledger**" (roadmap.md:9-16) | stale | fix-doc | Rewrite the transition preamble for the post-bootstrap reality (native state exists, PR #1 merged at `54a495cd`, native markers recorded below it) |
| 38 | AGENTS.md | GitNexus block: "This project is indexed by GitNexus as **law-nexus** (43047 symbols, 102234 relationships, 584 execution flows)" and "`node .gitnexus/run.cjs analyze --force --name law-nexus`" (AGENTS.md:342-359) | stale | fix-code | Re-run `node .gitnexus/run.cjs analyze --force --name law-nexus` on the primary checkout and regenerate the tool block so its numbers match the recorded index (meta.json: nodes=43059, edges=102250, processes=584, pinned at 2026-10-26/M001 — the block disagrees and the index predates M002–M010); note the index stays local-excluded, so clean checkouts cannot verify it |
