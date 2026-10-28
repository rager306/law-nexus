# Docs Audit

<!-- Written by the docs auditor ($gsd-path-docs-audit (Codex) or /gsd-path-docs-audit (Antigravity/Zed/Muse) or $gsd-path-inspect (Codex) or /gsd-path-inspect (Antigravity/Zed/Muse)).
     Every verdict carries evidence; a verdict without evidence is a defect. -->

Repo root: /root/law-nexus
Audited: 2026-10-25
Audited HEAD: 2c7f5b13c60b4f4ef24e14c9a80ad95460bd2ad4
Alignment mode: no

## Summary

| Verdict | Count |
|---------|-------|
| verified | 55 |
| stale | 15 |
| aspirational | 3 |
| unverifiable | 1 |
| descriptive docs (no testable claims) | 308 |

Worst drift: the README quick-start command `cargo run -q -p ln-product-cli -- health` fails as written ("could not determine which binary to run" — the package gained a second binary and no `default-run`), and the front page's status paragraph is bands behind the tracked ledger (45/44-member claims vs 47 workspace members; "M165 latest band" vs tracked M174–M211 evidence).

Verification runs executed in the pre-created sidecar at the recorded clean HEAD: `cargo test -p ln-hc01-runner --offline` (1 passed), `cargo test -p ln-query --offline --test retrieval_metrics` (7 passed), `cargo run -p ln-product-cli --bin law-nexus-inspect -- health` (status ok), `cargo fmt --all -- --check` (pass, via preflight), `python -m law_nexus_harness governor` (71 pass / 1 error — the error is this sidecar's workflow-state branch conflict, not tracked content), `python -m law_nexus_harness preflight` (5 pass / 1 warn / 2 errors — same workflow-state cause; the warn is "GitNexus metadata is missing"), `scripts/verify-adr-conformance.py` (ok, 29 files), `pytest -q` (29 failed, 881 passed, 12 skipped, 7 errors — 2 failures are real tracked-contract drift recorded below; the rest are environmental: the sidecar branch conflict cascading into live-governor tests, the unbuilt `ln-status` binary, and gitignored local PI-skill tooling). Git history and file checks ran against the sidecar; gitignored vault paths were read only on the primary checkout.

## Doc: README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "The workspace has 45 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed `ln-applicability`" (README.md:12-16) | structure | stale | Cargo.toml members list has 47 entries; `crates/` has 47 dirs; Cargo.toml:7 comment says "47 workspace crates"; `ln-kb-ontology` and `ln-consultant-parser` are workspace members missing from the README enumeration |
| "the executable 44-member inventory" (README.md:301) | structure | stale | same evidence — 47 members; also contradicts README.md:13's own "45" |
| "Latest tracked product/design band: **M165**" (README.md:23) | status | stale | CHANGELOG.md records M211-hkknug S01 (2026-09-19) with landed artifacts (verified in the CHANGELOG section); prd/project-state/data/roadmap.json has sync events through `roadmap-sync-20261005-m214-complete-horizon-held`; prd/ARCHITECTURE.md records the M174 band as completed |
| "The current documentation/control baseline includes post-D150 assessments 13–18" (README.md:25-27) | status | stale | assessment/ holds 00–34; `assessment/34-rust-npa-foundation-readiness-audit.md` (reviewed base `24b8872`, commit exists) is a post-M221 remediation audit |
| "Retired ADR IDs **0001/0002/0003/0006** have no files under `doc/adr/`" | structure | verified | `ls doc/adr` → 27 ADR files 0004–0031, none for the retired IDs |
| "Governor ADR/lifecycle probes ... include: adr-truth-oracle-sync, adr-index-completeness, adr-doc-matrix-coverage, adr-structure-hygiene, adr-cross-surface-matrix, adr-retired-id-ban, active-surface-era-noise, archive-path-policy" | feature | verified | all 8 names present in src/law_nexus_harness/governor.py (2–5 occurrences each); all passed in the live governor run |
| "`cargo run -q -p ln-product-cli -- health` # release health smoke" | command | stale | ran in sidecar → "error: `cargo run` could not determine which binary to run" (binaries: hierarchy-registry-generator, law-nexus-inspect; no `default-run` key in either Cargo.toml); corrected `--bin law-nexus-inspect -- health` → `{"phase":"Health","status":"ok"}`, exit 0 |
| "uv run python -m law_nexus_harness governor / preflight; uv run pytest -q; uv run python scripts/verify-adr-conformance.py" | command | verified | all four executed in the sidecar at HEAD: governor 71 pass/1 error (sidecar workflow-state only), preflight 5 pass/1 warn/2 errors (same cause), conformance ok (29 files), pytest 29F/881P/12S/7E (2 real drifts → own rows below; remainder environmental) |
| "M205/S04 ... `prd/architecture/m205-s04-docs-reconciliation.yaml`" | structure | verified | file exists; companion verifier scripts exist (scripts/m205_s04_reconciliation.py, scripts/test_m205_s04_reconciliation.py) |
| "A Rust workspace of twenty exclusive `ln-*` capability crates (ADR-0011)" | structure | verified | the 20 owner crates named in the map table are all workspace members in Cargo.toml |

## Doc: AGENTS.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Product behavior: PDD Kit in `product-model/`, orchestration off" (AGENTS.md:262) | structure | aspirational | no `product-model/` in the tracked tree, the primary checkout, or git history (`git log -- product-model` empty) |
| Data Sources Map: "consru_export/consru_export/exports/ ... 43,785 files, 3.7 GB" | structure | verified | 43,785 XML files by count, 3.7G by size (primary checkout; gitignored) |
| "Known issue: 2,478 artifact rows in the DB contain `../`-style paths" | status | stale | read-only query on the frozen DB /root/.gsd/projects/3495c0714df3/gsd.db → 3,074 of 8,355 artifact rows have `../` in `path` (all `../`-prefixed; the DB grew after assessment/24 recorded 2,478 on 2026-08-31) |
| Data Sources Map: "law-source/consultant/ — Fragment of the corpus (122 XML files)" | structure | stale | 82 tracked XML fixtures; the other 40 were the gitignored `.deprecated/` set, which is no longer on disk in the primary checkout |
| "`scripts/ai/allspark`", "`scripts/ai/phase-dispatch.py`", "`.gsd-path/runtime.json`" | structure | verified | all three exist |
| GitNexus block: "This project is indexed by GitNexus as **law-nexus** (23577 symbols ...)" and "`node .gitnexus/run.cjs analyze ...`" | integration | stale | `.gitnexus/` absent in the sidecar and the primary checkout; preflight independently warns "GitNexus metadata is missing" with remediation "Run `gitnexus analyze --force --name law-nexus`" |
| "`src/law_nexus_harness/workflow_state.py` is the only sanctioned adapter" | structure | verified | file exists |

## Doc: prd/ARCHITECTURE.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Foundation/ontology ADR lifecycle map (ADR-0004..0031 with `[bounded]`/`[proposed]`/`[validated]` tags) | status | verified | every ADR's frontmatter Status and D098 tags cross-checked (0007 validated; 0014/0016–0024/0026/0028–0031 proposed; the rest bounded); governor `adr-truth-oracle-sync` passed over 27 ADRs |
| "20/20 hostile contracts have `[bounded]` synthetic Rust runtime PASS" | status | verified | 20 `ln-hcNN-runner` crates tracked with tests; governor `hostile-baseline-aggregate`: "PASS 20/20; FAIL 0/20"; sampled re-run `cargo test -p ln-hc01-runner --offline` → 1 passed, exit 0 (full 20-suite re-run not performed) |
| "`ln-consultant-parser` has 10 source modules including `lib.rs`, 64 integration test functions and 4 source-unit tests" | structure | stale | actual: 31 top-level src modules (incl. lib.rs) plus 14 `src/bin/` binaries; 358 `#[test]` functions under tests/; 54 `#[test]` functions in src/*.rs |
| "One page. If it grows, split detail into tracked focused PRD sub-docs" (one-page living oracle) | structure | stale | `wc -l prd/ARCHITECTURE.md` → 327 lines vs tracked budget 325 (tests/test_architecture_m171_alignment.py:28); its own test fails: "living oracle grew to 327 lines (budget 325)" |
| "G1 ... anchor is 119 structural hierarchy markers on the tracked 435-ФЗ fixture (`EXPECTED_HIERARCHY_COUNT` in `crates/ln-decode/tests/consultant_real_tracer.rs`)" | feature | verified | constant = 119 at consultant_real_tracer.rs:17; the 435-ФЗ fixture `law-source/consultant/...-d71bf702.xml` is tracked |
| "a bounded Rust reference-capture runtime landed under M211 (npa_anchor/npa_typed/npa_link/npa_classify/npa_continuation, npa-integration-runner)" | structure | verified | all five modules exist in crates/ln-decode/src/; runner at crates/ln-decode/src/bin/npa-integration-runner.rs (plus its CLI contract test) |
| "`python_archive/product/`", "`python_archive/acp_git_lex/`" | structure | verified | gitignored (.gitignore:27); both exist in the primary checkout; governor `archive-path-policy` confirms ignored+untracked |
| "Values 3772/3641/2619/502 ... come from gitignored `consru_export`; ... skip-capable when the export is absent" | config | verified | .gitignore:152 `consru_export/`; export present on primary (3.7G), absent in sidecar; governor `corpus-grounding` correctly reports "corpus absent; skipped" |
| "the observable product CLI `law-nexus-inspect`" | structure | verified | crates/ln-product-cli/Cargo.toml `[[bin]] name = "law-nexus-inspect"`; `health`/`inspect` subcommands at src/main.rs:622-623; health run → status ok |
| KB ontology inventory (`ln-kb-ontology` write-set crate; `fold_membership_at`, `mint_work`/`compare_work_identities`, `try_push_node`/`try_push_edge`, `map_hierarchy_marker`, `fold_expression_presence`, `join_force_with_membership`, `DecodePrefixCatalog`, `legal_act_effect_day_to_ordinal`, product-cli `lift_extracted_hierarchy`) | feature | verified | all names found in crates/ln-kb-ontology/src/, crates/ln-product-cli/src/main.rs, crates/ln-temporal/src/ |
| "no live RuVector/TEI product path", "Historical FalkorDB is not active infrastructure" | status | verified | Cargo.lock has no ruvector/falkordb entries; no PyO3 in any crate manifest; governor `live-adapter-readiness`: "ruvector=proposed, overclaim_count=0" |

## Doc: doc/adr/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Current ADRs" index 0004–0031 with per-ADR statuses/lifecycles | status | verified | 27 ADR files on disk; every listed status matches the file frontmatter (0028–0031 Proposed; rest Accepted) and D098 tags |
| ADR-0025..0031 index rows (table following the `fold_expression_presence`/`map_hierarchy_marker` comments) | structure | stale | the 7 table rows have no header/separator row — they directly follow two HTML comments after "## Retired Python-era records", so the index renders as plain pipe text, not a table |
| "active ADR frontmatter uses canonical `supersedes` and `superseded_by` keys. The legacy misspelling `superseds` ... is rejected on active ADRs by Governor" | config | verified | frontmatter scan: only canonical keys (0005 `superseded_by: [ADR-0011#crate-map-only]`; 0011/0017/0023 supersedes chained); `superseds` appears 3× in src/law_nexus_harness/governor.py (rejection logic) |
| "ADR-0001, ADR-0002 and ADR-0003 ... ADR-0006 ... local vault is gitignored, untracked" | structure | verified | no 0001/0002/0003/0006 files under doc/adr/; vault roots (.lex/, archive/, python_archive/) gitignored and present only on the primary checkout |

## Doc: doc/adr-architecture-cross-matrix.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "## 1. Present ADR inventory" table enumerates 0004–0024 as the present ADR set | structure | stale | doc/adr/ contains 0025–0031 (7 further active ADRs); 0025/0026/0027/0030/0031 are not mentioned anywhere in the matrix (0028/0029 only in passing) — the matrix predates ADR-0025+ and was never extended |

## Doc: CHANGELOG.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| M211-hkknug S01 entry: `ln-decode/src/npa_anchor.rs`; `tests/npa_members_gold_parity.rs` + TSV fixture `anchor-parity-fixture.tsv`; CI job `offline-contract-verifiers` | structure | verified | npa_anchor.rs exists; crates/ln-decode/tests/npa_members_gold_parity.rs exists; crates/ln-decode/tests/fixtures/npa-members/anchor-parity-fixture.tsv exists; `.github/workflows/` defines job `offline-contract-verifiers` (yml:251) |
| Self-description (via README map): "Human-readable delivery history; not architecture authority" | status | verified | content is dated, revision-bound milestone records; the head entries' file claims all resolve (checked above) |

## Doc: prd/PRODUCT.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Planning baseline: `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)" | status | verified | commit exists, dated 2026-08-11 |
| "EA-02 tested revision: `37f82c4245642f7c1e9104f288db43df762178fe` (`assessment/02-product-contract.md`)" | status | verified | commit exists: "docs: establish product contract assessment package" |
| "`[proposed]` Product Contract; document state `ready-for-assessment`" (not validated by EA-10 D150) | status | verified | matches README/ARCHITECTURE/roadmap framing ("EA-10 D150 accepted the assessment packet, not these documents") |

## Doc: prd/REQUIREMENTS.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Planning baseline: `60fd8245...` (2026-08-11)" | status | verified | same commit as the PRODUCT.md row |
| "EA-02 tested revision: `37f82c42...`" | status | verified | same commit as the PRODUCT.md row |
| "document state `ready-for-assessment`"; "`prd/ARCHITECTURE.md` currently labels the same design sequence L1–L7" | status | verified | ARCHITECTURE.md uses L1–L7 for ADR-0016..0022; both documents claim `[proposed]` |

## Doc: prd/temporal-legal-model.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "TL-G01–12 gates" | structure | verified | TL-G01..TL-G12 all present (78 TL-G mentions; sorted unique = exactly G01–G12) |
| "explicit 14-area completeness matrix" (README's description; §14) | structure | verified | "## 14. Primary-critique contract completeness matrix" at line 384 |
| "EA-03 tested revision: `e1ac83a714e20a6b551d5305fc4fca9f29d91aa7`" | status | verified | commit exists |

## Doc: prd/parser/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Canonical artifacts: `prd/parser/schemas/*.json` (5), `profiles/{consultant_wordml,garant_odt}.yaml`, `examples/*.jsonl` (3), `odt_smoke_records.{json,md}` | structure | verified | all listed files exist with the stated counts |
| "the PP filename mismatch (`PP_60_27-02-2022.odt` stated vs `PP_60_27-01-2022.odt` observed) must remain visible" | structure | verified | law-source/garant/PP_60_27-01-2022.odt is the tracked file; no 27-02 variant tracked |
| "Large Python-era dumps ... relocated to `prd/archive/parser-dumps-era/` (gitignored archaeology)" | structure | verified | .gitignore:135 `prd/archive/parser-dumps-era/`; dir exists on the primary checkout only |

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
| "Latest completed product milestone: M173, inspect PP_60 class-matched punkt proof" (roadmap.md:43) | status | stale | the doc's own data source prd/project-state/data/roadmap.json records later events (`roadmap-sync-20261005-m214-complete-horizon-held`; M211/M213/M214/M225 ids present); CHANGELOG.md records M211 S01 (2026-09-19); ARCHITECTURE.md shows the M174 band completed |
| "Initial front synchronization was frozen in EA-05 at `94d58ea`"; packet `120d44b` | status | verified | both commits exist |
| Active Direction Contract block (runtime=rust-only; python=repository-control-only; graph_vector=ruvector; ...) | config | verified | identical block in prd/ARCHITECTURE.md; governor `architecture-direction-contract` pass |

## Doc: law-source/consultant/README.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "82 XML-документа КонсультантПлюс" (tracked fixtures) | structure | verified | `git ls-files 'law-source/consultant/*.xml'` → 82 |
| "Плюс подкаталог `.deprecated/` (40 файлов) — ... остаётся на диске только как история" | status | stale | `.deprecated/` does not exist on the primary checkout (a gitignored path lost on re-checkout); only the gitignore entry remains (.gitignore:62) |
| Corpus counts: "43 785 файлов, включая `npa/` 916, `fas/` 30 399, `courts/` 5 667, `xml/` 6 803" | structure | verified | primary-checkout find counts: 43,785 / 916 / 30,399 / 5,667 / 6,803 — exact |
| "Проверено по sha256: пересечение = 0 файлов" (fixture set disjoint from corpus) | feature | unverifiable | would need sha256 of all 82 tracked fixtures against the full 3.7 GB corpus tree; not re-run in this audit |
| Canonical fixtures: `...-44-fz-...-f9c8ca4c.xml`, `Список документов (5).xml` | structure | verified | both files tracked under law-source/consultant/ |
| "Governor-проверка `law-source-corpus-glob-guard` это отмечает" | feature | aspirational | no `law-source-corpus-glob-guard` anywhere in src/, scripts/, tests/, .github/ — the named governor check was never built (the existing `law-source-fixture-guard` checks only the README marker) |

## Doc: law-source/consultant/okf/index.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Portable Open Knowledge Format (OKF) catalogue of the XML legal-document sources in this directory" (81 linked documents) | structure | verified | 81 links, all resolve to existing documents/*.md; 81 files on disk; zero orphans in either direction |

## Doc: docs/agent-stack/WORKFLOW.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Описание product behavior — PDD, `product-model/`" (ownership table, line 14) | structure | aspirational | `product-model/` does not exist in the tracked tree, primary checkout, or git history |
| "`.ai/path-run.json` — **настройка нашей обёртки**"; "`.gsd-path/runtime.json`" | config | verified | both files exist |

## Doc: docs/agent-stack/PHASE-ADAPTER.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "`scripts/ai/phase-dispatch.py` is the repo-owned glue" | structure | verified | file exists |
| "verified against deterministic stub children only. No real Allspark/model pilot has been run, no native phase gate has consumed its records ... acceptance table in §8 ... **not yet satisfied**" | status | verified | primary .project/ contains only STATE.md — no phase-dispatch records; the doc's non-executed framing is consistent with the tree |

## Doc: .agents/skills/law-nexus-rust/SKILL.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Python product code is archived prior art under `python_archive/product/`" | structure | verified | gitignored (.gitignore:27); exists in the primary checkout |
| References: `references/verification-matrix.md`, `doc/adr/0015-...`, `prd/temporal-legal-model.md` §3, `prd/architecture/temporal-vocabulary-contract.json` | structure | verified | all referenced paths exist |

## Doc: .agents/skills/law-nexus-rust/references/verification-matrix.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Default command set (`cargo fmt --all --check`, `cargo check/test/clippy --workspace --offline`, `uv run law-nexus-harness governor/preflight`, `uv run python scripts/verify-adr-conformance.py`) | command | verified | `law-nexus-harness` console script declared (pyproject.toml:13); governor/preflight/conformance/fmt all executed in this audit (results in the README section); the full `cargo check/test/clippy --workspace` was not re-run (bounded-sample policy) |
| Contract suites `npa_corpus_sweep_contract`, `morphology_contract` | structure | verified | crates/ln-decode/tests/npa_corpus_sweep_contract.rs and morphology_contract.rs exist |
| "`scripts/m205_s04_reconciliation.py check` plus its subprocess adversarial suite (`scripts/test_m205_s04_reconciliation.py`)" | command | verified | both scripts exist |

## Doc: .agents/skills/law-nexus-rust/UPSTREAM.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Upstream `SKILL.md` SHA-256: `5a74070e...`" at pinned commit `fd2a861` | status | verified | fetched raw.githubusercontent.com at that commit → sha256 exact match |
| "Upstream `LICENSE` SHA-256: `663ce6f8...`" | status | verified | same fetch → sha256 exact match |
| "identifies itself as current for Rust 1.96 and edition 2024 ... 265 rules"; "Upstream version in frontmatter: 1.5.1" | status | verified | fetched upstream SKILL.md frontmatter: version 1.5.1, "265 rules across 26 categories" |

## Doc: .agents/skills/law-nexus-subagent/SKILL.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| "Live discovery path is `~/.gsd/agent/agents/`, not project `.pi/agents` or `.gsd/agents`" | structure | verified | /root/.gsd/agent/agents/ exists with _CONTRACT.md and role files incl. scout/reviewer/worker/researcher/tester/planner; /root/law-nexus/.pi absent |

## Doc: prd/architecture/npa-analysis-jsonl-contract.md

| Claim | Type | Verdict | Evidence |
|-------|------|---------|----------|
| Tracked as an M221 authority-reconciliation source binding (hash-pinned companion) | status | stale | `pytest tests/test_m221_authority_reconciliation.py::test_source_bindings_resolve_and_match_disk` fails: "sha256 drift for source binding: prd/architecture/npa-analysis-jsonl-contract.md" — the file no longer matches its pinned digest at this HEAD |

## Descriptive docs

<!-- The remaining inventoried docs carry no testable product claims; they are dated evidence/decision/assessment records, design contracts, protocols, process instructions, or corpus data. Scope notes: -->

<!-- - Root `WORKFLOW.md` describes only the installed GSD Path pipeline (router, phases, gates, dispatch contract). Per the audit scope, GSD Path source/pipeline internals are installed-dependency claims, not law-nexus product claims; the file contains no law-nexus product statements to test (zero product-technology lines), so it is listed as descriptive. -->
<!-- - `doc/adr/0004..0031` (26 files) are decision records: their testable surface (Status, lifecycle tags, supersession keys, index coverage, retired IDs) is verified in aggregate in the `doc/adr/README.md` section above; the remaining body text is normative design substance, which reality cannot contradict. -->
<!-- - `assessment/*` (35), `doc/review/*` (18), `prd/migration/rust-evidence/*` (36), `prd/migration/decommission/*` (2), the four frozen migration roadmaps, `prd/annotation/*` (9), the `prd/architecture/m1../m2../` admission/adoption/decision/checkpoint records, `prd/architecture/*` governance contracts and D7-quarantined derived views, and the `docs/agent-stack` plans/records dated 2026-10-23 (`AGENT_HANDOFF`, `ALLSPARK_NOTES`, `INSTALL`, `MIGRATION`, `MIGRATION-RECORD`, `PATH_SETUP`, `SOURCES`, `TESTED`, `history/LEGACY_CROSSWALK`) are explicitly dated, revision-pinned records of past decisions, runs, or plans (most carry their own "not yet executed / non-authoritative" markers). Their recorded values were treated as historical evidence, not current-state claims; cheap spot checks all resolved (pinned commits `50173de`, `9d72884`, `24b8872`, `bfe2ee6` exist; the m207 frozen inputs exist and the model-crystal L0 digest `c438ddfb...` matches sha256 of `doc/review/review-25-08-2026.md`; `scripts/ai/path-run.py`, `.ai/versions.json`, `docs/agent-stack/history/LEGACY_CROSSWALK.md` exist). External stack pins (Allspark fork.009, GSD Path 1.6.2, PDD 0.37.1) are installed-dependency claims outside this repository's product scope. -->
<!-- - `law-source/consultant/okf/documents/*` (81) are corpus source documents (provider-derived legal text), not product documentation. -->
<!-- - `.ai/allspark/roles/{owner,reviewer,worker}.md`, `.agents/skills/law-nexus-subagent/workflows/parent-dispatch.md`, and the five `law-nexus-rust/workflows/*.md` are process instructions (directives), not claims; their referenced files exist (checked via the skill sections above). -->
<!-- - `prd/archive/README.md` documents nine gitignored vault subtrees; all nine ignore entries and primary-checkout directories were confirmed during the vault checks (`litho.toml`, `.litho/`, `litho.docs/` gitignored at .gitignore:80-82 per `doc/litho-runbook.md`). -->
<!-- - `doc/gsd-headless-supervisor.md` is the tracked operator contract for the retired GSD-Pi supervisor; AGENTS.md itself scopes it as historical process archaeology, so its "keep `gsd headless auto` alive" instruction is a dated record, not operative drift. -->
<!-- - `prd/architecture/README.md` (registry contract; generator `scripts/generate-architecture-views.py` exists; baseline `bfe2ee6` exists), `prd/architecture/model-crystal.md` (L0 digest verified above), `prd/architecture/glossary-governance.md`, `prd/architecture/capability-promotion-board.md`, and the remaining `prd/architecture` contracts and reader/intermediate-source projections were sampled; their owning modules exist (e.g. `ln_decode::source_package`, `reader_contract`, `cleaned_wire`, `cleaned_projection_wire` tests), and their own headers mark them non-authoritative. -->

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
- docs/agent-stack/INSTALL.md
- docs/agent-stack/MIGRATION-RECORD-2026-10-23.md
- docs/agent-stack/MIGRATION.md
- docs/agent-stack/PATH_SETUP.md
- docs/agent-stack/SOURCES.md
- docs/agent-stack/TESTED.md
- docs/agent-stack/history/LEGACY_CROSSWALK.md
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

## Remediation queue

<!-- Every non-verified claim, classified. The user rules on this queue;
     the auditor never fixes anything.
     Numbers are unique and strictly increasing. -->

| # | Doc | Claim | Verdict | Class | Suggested action |
|---|-----|-------|---------|-------|------------------|
| 1 | README.md | "The workspace has 45 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed `ln-applicability`" (README.md:12-16) | stale | fix-doc | Recount from Cargo.toml: 47 members; add `ln-kb-ontology` and `ln-consultant-parser` to the map table |
| 2 | README.md | "the executable 44-member inventory" (README.md:301) | stale | fix-doc | Same recount as #1 (README.md:301); make the two numbers consistent |
| 3 | README.md | "Latest tracked product/design band: **M165**" (README.md:23) | stale | fix-doc | Refresh the Current-status paragraph to the tracked ledger (M174–M211 bands; roadmap.json events through 2026-10-05) or point at roadmap.json as the live front |
| 4 | README.md | "The current documentation/control baseline includes post-D150 assessments 13–18" (README.md:25-27) | stale | fix-doc | Update the assessment range (tracked set is 00–34) and move the "latest remediation assessment" pointer to assessment/34 |
| 5 | README.md | "`cargo run -q -p ln-product-cli -- health` # release health smoke" | stale | fix-doc | Document `--bin law-nexus-inspect` (verified working), or add `default-run = "law-nexus-inspect"` to crates/ln-product-cli/Cargo.toml (owner decision) |
| 6 | AGENTS.md | "Product behavior: PDD Kit in `product-model/`, orchestration off" (AGENTS.md:262) | aspirational | NEEDS-USER | Either create product-model/ per the migration plan or reword AGENTS.md to mark PDD adoption as pending |
| 7 | AGENTS.md | "Known issue: 2,478 artifact rows in the DB contain `../`-style paths" | stale | fix-doc | Update to the current frozen-DB count (3,074 of 8,355; queried read-only 2026-10-25) or date-bound the figure to its 2026-08-31 assessment |
| 8 | AGENTS.md | Data Sources Map: "law-source/consultant/ — Fragment of the corpus (122 XML files)" | stale | fix-doc | State 82 tracked fixtures and note the 40 `.deprecated/` files are gitignored and absent from current checkouts |
| 9 | AGENTS.md | GitNexus block: "This project is indexed by GitNexus as **law-nexus** (23577 symbols ...)" and "`node .gitnexus/run.cjs analyze ...`" | stale | NEEDS-USER | Re-index to regenerate the tool block (`gitnexus analyze --force --name law-nexus`; preflight already warns the metadata is missing) or remove the block until the index is maintained |
| 10 | prd/ARCHITECTURE.md | "`ln-consultant-parser` has 10 source modules including `lib.rs`, 64 integration test functions and 4 source-unit tests" | stale | fix-doc | Refresh the counts (31 src modules + 14 bins, 358 integration `#[test]`, 54 unit `#[test]`) or drop exact numbers |
| 11 | prd/ARCHITECTURE.md | "One page. If it grows, split detail into tracked focused PRD sub-docs" (one-page living oracle) | stale | fix-doc | Trim the oracle to ≤325 lines per the M171 budget test (currently 327) or split detail into sub-docs; raising the tracked budget is an owner decision |
| 12 | doc/adr/README.md | ADR-0025..0031 index rows (table following the `fold_expression_presence`/`map_hierarchy_marker` comments) | stale | fix-doc | Restore the missing table header/separator so the index renders as a table |
| 13 | doc/adr-architecture-cross-matrix.md | "## 1. Present ADR inventory" table enumerates 0004–0024 as the present ADR set | stale | fix-doc | Extend the inventory and cross-surface matrix to ADR-0031 |
| 14 | prd/architecture/npa-analysis-jsonl-contract.md | Tracked as an M221 authority-reconciliation source binding (hash-pinned companion) | stale | fix-doc | Re-pin the binding to the current file digest or revert the unpinned edit — the owner confirms which revision is canonical |
| 15 | prd/project-state/roadmap.md | "Latest completed product milestone: M173, inspect PP_60 class-matched punkt proof" (roadmap.md:43) | stale | fix-doc | Sync the front with roadmap.json/CHANGELOG (M211 recorded 2026-09-19; json events through 2026-10-05), or accelerate the planned post-Path rebuild |
| 16 | law-source/consultant/README.md | "Governor-проверка `law-source-corpus-glob-guard` это отмечает" | aspirational | NEEDS-USER | Implement the named governor probe (a small harness check) or remove the claim; the existing `law-source-fixture-guard` covers only the README marker |
| 17 | law-source/consultant/README.md | "Плюс подкаталог `.deprecated/` (40 файлов) — ... остаётся на диске только как история" | stale | fix-doc | Reword: the set is gitignored and may be absent after a fresh checkout (it is absent in the current primary checkout) |
| 18 | law-source/consultant/README.md | "Проверено по sha256: пересечение = 0 файлов" (fixture set disjoint from corpus) | unverifiable | fix-doc | Date-bound the recorded 2026-09-26 check (or commit a fixture-hash manifest so it can be re-verified cheaply) |
| 19 | docs/agent-stack/WORKFLOW.md | "Описание product behavior — PDD, `product-model/`" (ownership table, line 14) | aspirational | NEEDS-USER | Same ruling as #6: create the directory per plan or mark PDD adoption pending |
