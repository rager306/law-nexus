# M049 S01 Binding Input Audit

## Status

Verified for `M049 / S01 / T05`.

This artifact is the input map for binding the current law-nexus architecture into ACP. It classifies what M049 may consume, what remains diagnostic or derived, and what must stay blocked or out of scope. It also records requirement implications, evidence boundaries, durable-anchor policy, and the handoff to S02/S03.

## Purpose

M049 should bind law-nexus architecture through ACP-native source records, lifecycle states, evidence anchors, and proof gates without turning git-lex, RDF/SHACL/SPARQL/JSONL, browser debug bundles, or polished prose into source truth by shape alone.

The central rule for this milestone:

```text
ACP source truth remains ACP-native; git-lex is L1 shadow diagnostic/projection support only.
```

## Input classification legend

| Class | Meaning for M049 |
|---|---|
| Authoritative source input | May define or constrain M049 binding if anchored to tracked PRD/GSD/ADR/source/tests/runtime/real-document evidence. |
| Bounded foundation input | May be consumed as prior validated or accepted project planning evidence, but only within its stated scope. |
| Diagnostic support input | May inform checks, health findings, or implementation-readiness, but cannot validate requirements or transfer authority. |
| Derived projection input | May support inspection or recovery, but cannot become source truth by itself. |
| Blocked promotion | Must not be claimed in M049 unless a new accepted proof gate explicitly changes it. |
| Out-of-scope input | Relevant to future work but not owned by M049. |

## Candidate inputs for M049

| Input | Class | Accepted use in M049 | Must not be used for |
|---|---|---|---|
| `.gsd/milestones/M049/M049-ROADMAP.md` | Authoritative source input | Defines M049 vision, success criteria, slice order, boundary map, and verification contract. | Expanding scope beyond planned binding/proof-boundary work. |
| `.gsd/REQUIREMENTS.md` | Authoritative source input | Defines active requirement contract and status for R035/R037/R038/R041/R042/R046/R047/R048/R055/R056/R057. | Silently changing requirement status without GSD requirement update and proof. |
| `.gsd/DECISIONS.md` | Authoritative source input | Provides accepted decision history, especially D074-D078 around ACP closure and git-lex staged adoption. | Treating decisions as runtime/product proof where verification is still required. |
| `.gsd/milestones/M048-q4x62e/M048-q4x62e-SUMMARY.md` | Bounded foundation input | Supplies ACP/git-lex foundation, source-record/lifecycle/projection boundary, and deferred adoption decision. | Runtime git-lex adoption, R035/R037/R038 validation, or final law-nexus binding proof. |
| `.gsd/milestones/M051-q6ctvc/M051-q6ctvc-SUMMARY.md` | Bounded foundation input | Supplies git-lex research dispositions: ACP-native authority, absorb selected vocabulary/proof-boundary ideas, runtime adapter-later. | Production adoption, main `.lex`, JSON-LD runtime support, broad SPARQL-star, or product/legal validation. |
| `.gsd/milestones/M052-idogd6/M052-idogd6-SUMMARY.md` | Bounded foundation input | Supplies hardened capability classifications and production/provenance gates. | Treating local serve/viz/listen or SHACL smoke as production readiness or source truth. |
| `.gsd/milestones/M053-2jp3nm/M053-2jp3nm-SUMMARY.md` | Bounded foundation input | Supplies adapter-readiness boundaries and Claude/session logs ACP-nonfit decision. | Using raw/session logs, `save`, broad mutating commands, or plugin binaries as ACP-safe primitives. |
| `.gsd/milestones/M054-63ujns/M054-63ujns-SUMMARY.md` | Diagnostic support input | Supports proof-only wrapper feasibility and safe diagnostic tooling design. | ACP adoption, production readiness, main `.lex`, source-truth transfer, or LegalGraph requirement validation. |
| `.gsd/milestones/M055-dbt65v/M055-dbt65v-SUMMARY.md` | Diagnostic support input | Supports continued L1 shadow diagnostic/projection backend use and L2 follow-up route. | L2 immediate promotion, main `.lex` approval, source-truth migration, production/provenance, legal/FalkorDB/parser validation. |
| `prd/architecture/acp/M055-S05-GIT-LEX-BACKEND-NEXT-DECISION.md` | Diagnostic support input | Provides final M055 decision ledger: selected O1 continue L1, rejected O2-O5 as current actions, blocked claims preserved. | Any stronger git-lex promotion not selected by M055. |
| `prd/architecture/acp/M055-S04-GIT-LEX-REMAINING-ADOPTION-GATES.md` | Diagnostic support input | Provides remaining adoption gates, proof classes, and blocked/rejected/out-of-scope surfaces for later routing. | Claiming gates are already met. |
| `scripts/git_lex_diagnostic_adapter.py` and `tests/test_git_lex_diagnostic_adapter.py` | Diagnostic support input | Show M054 wrapper contract and tests for isolated proof-only diagnostics. | Treating the wrapper as production backend or ACP authority. |
| `scripts/acp_git_lex_backend.py` and `tests/test_acp_git_lex_backend.py` | Diagnostic support input | Show M055 ACP-facing L1 diagnostic normalization and tests. | Requirement validation, source-truth mutation, main checkout mutation. |
| `prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl` | Diagnostic support input | Supports proof-only wrapper runtime matrix classification. | Durable source truth, legal/product proof, raw payload evidence. |
| `prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl` | Diagnostic support input | Supports ACP-shaped synthetic L1 diagnostic classification counts and safety fields. | Requirement validation or source-truth migration. |
| `.agents/skills/git-lex/references/acp-boundaries.md` | Derived guidance input | Helps future agents preserve safe wording and ACP authority boundaries. | Overriding tracked PRD/GSD/decision/source evidence. |
| `.agents/skills/git-lex/references/runtime-adoption-gates.md` | Derived guidance input | Captures runtime/adoption gates and safe follow-up route. | Treating guidance text as proof that a gate has passed. |
| `prd/architecture/architecture_items.jsonl`, `prd/architecture/architecture_edges.jsonl`, and generated graph reports | Derived projection input | May support inspection if regenerated and verified through canonical architecture workflow. | Creating authority without source anchors or proof gates. |

## Requirement implication table

| Requirement | Current status | Allowed M049 binding implication | Forbidden promotion in M049 | Next owner or follow-up |
|---|---|---|---|---|
| R035 | Active; not validated by prior bounded descriptor/retrieval evidence. | M049 may map ontology architecture research to ACP source categories, proof gates, and registry-source expectations. | Do not validate ontology/product architecture, graph-vector, pilot-scale, retrieval-quality, or standards-adoption claims from ACP/git-lex diagnostics or projection shape. | Future retrieval-quality / production-readiness and registry-source mapping proof with independent accepted evidence. |
| R037 | Active; partially evidenced for small ingest fixtures only. | M049 may keep FalkorDB ingest as law-nexus profile-owned proof path and require explicit source shape, counts, error handling, and cleanup gates. | Do not validate larger corpus ingest, production data loading, skipped/failed row accounting, operational recovery, or FalkorDB runtime behavior from git-lex/ACP binding. | Future ingest-scale or production data-loading milestone. |
| R038 | Active standing proof-heavy milestone review gate; advanced by prior independent review but not retired. | M049 should treat the S01/S04/S05 review and verification surfaces as required proof discipline for binding claims. | Do not treat passing self-authored scripts or polished artifacts as sufficient if independent proof/inspection is required for proof-heavy claims. | Future proof-heavy milestones and M049 verifier/final synthesis checks. |
| R041 | Active; mapped by M048 source-record model work. | M049 may refine and consume ACP source-record categories for requirements, decisions, project-state docs, architecture registry, milestone evidence, proof gates, and health findings. | Do not mark fully validated unless S03/S04/S05 produce accepted source-record mapping and verification for current law-nexus binding. | M049/S03 registry source mapping and M049/S05 outcomes. |
| R042 | Active; mapped by M048 lifecycle/health model work. | M049 may bind lifecycle states, transition rules, health categories, allowed/blocked actions, and reusable/profile boundary into law-nexus architecture mapping. | Do not imply lifecycle/health runtime automation or full operationalization; M050 remains the operationalization horizon. | M049/S02 profile boundary, M049/S03 mapping, M050 CI/operationalization. |
| R046 | Active constraint; mapped by M048 and reinforced by M051-M055. | M049 must enforce the source-truth vs derived-projection boundary in every binding artifact and verifier check. | Do not treat ACP, git-lex, RDF, SHACL, SPARQL, JSONL projections, dashboards, recovery views, or L1 diagnostics as source truth or requirement-validation proof by themselves. | M049/S04 binding verifier checks and M049/S05 final synthesis. |
| R047 | Active constraint; mapped by M048 and preserved through M055. | M049 must preserve no-main-repo git-lex mutation and no blind `git lex init`; any future `.lex` path needs explicit decision and isolated rehearsal. | Do not approve main `.lex`, `Squad`, `Raw`, broad `save`, raw payload mirroring, or direct main checkout mutation. | Optional future disposable-clone `.lex` rehearsal; not S01. |
| R048 | Active; mapped by M048 reusable/profile boundary. | M049 should define law-nexus profile constraints separately from reusable ACP core and keep legal/FalkorDB/parser/retrieval constraints profile-owned. | Do not move R035/R037/R038 or Russian legal/FalkorDB/parser constraints into generic ACP core. | M049/S02 profile adapter boundary and M049/S05 final synthesis. |
| R055 | Active; pending validation by executable/document assertions. | M049 may advance anti-imitation controls by requiring source category, lifecycle state, evidence anchors, and proof gate or accepted decision before authority. | Do not let polished LLM/analysis/projection artifacts become authoritative by format, prose quality, or generated shape alone. | M049/S04 verifier checks should include authority-inversion and missing-proof-gate cases. |
| R056 | Active; pending final capability-matrix disposition and implementation delta. | M049 may consume M048-M055 as a proof-backed git-lex capability decision sequence: selected mechanics absorbed ACP-natively, M055 L1 diagnostics allowed, stronger roles blocked. | Do not state that every ACP capability is satisfied by git-lex runtime; do not promote adapter-later/blocked capabilities without new proof. | M049/S03 mapping and S05 final synthesis should record remaining ACP-native implementation delta and optional L2 follow-up. |
| R057 | Active; pending closure condition for safe law-nexus binding. | M049 is the binding milestone allowed after M051-M055 produced a proof-backed git-lex disposition and checkpoint; it must explicitly record adapter boundaries and missing/absorbed capability deltas. | Do not treat M049 as proof that downstream product/legal/runtime claims are validated; do not bypass remaining blocked git-lex gates. | M049/S05 final binding synthesis and later M050/L2 diagnostic integration planning. |

## Evidence boundary table

| Surface | Authority level in M049 | Accepted anchors | Safe wording | Unsafe wording |
|---|---|---|---|---|
| ACP source records | Authoritative only when source category, lifecycle state, evidence anchor, and proof gate or accepted decision are present. | `.gsd/REQUIREMENTS.md`; `.gsd/DECISIONS.md`; future M049 S03/S04 source mapping and checks. | `ACP-native records and accepted proof gates define the binding authority.` | `Any ACP-shaped record is authoritative because it has the right structure.` |
| GSD requirements and decisions | Authoritative planning and governance inputs within recorded scope. | `.gsd/REQUIREMENTS.md`; `.gsd/DECISIONS.md`; M048-M055 summaries. | `Requirements and accepted decisions constrain M049 binding.` | `A decision or summary proves runtime/product/legal behavior without matching verification.` |
| M048 ACP foundation | Bounded foundation input. | `.gsd/milestones/M048-q4x62e/M048-q4x62e-SUMMARY.md`; `prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md`; `prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md`. | `M048 provides bounded ACP/git-lex foundation and preserves deferred runtime adoption.` | `M048 validated full law-nexus binding or runtime git-lex adoption.` |
| M051 git-lex research | Bounded foundation input and research disposition. | `.gsd/milestones/M051-q6ctvc/M051-q6ctvc-SUMMARY.md`; `prd/architecture/acp/M051-S12-GIT-LEX-FINAL-RECONCILIATION.md`. | `M051 keeps ACP authority ACP-native and routes git-lex runtime to adapter-later paths.` | `M051 proves git-lex is ready as ACP core backend or closes R035/R037/R038.` |
| M052 capability hardening | Bounded capability evidence and gate inventory. | `.gsd/milestones/M052-idogd6/M052-idogd6-SUMMARY.md`; `prd/architecture/acp/M052-S07-GIT-LEX-CAPABILITY-HARDENING-SYNTHESIS.md`. | `M052 hardens weak surfaces and keeps production/main .lex blocked.` | `M052 local smoke proves production/browser/server readiness.` |
| M053 adapter boundary | Adapter-readiness boundary only. | `.gsd/milestones/M053-2jp3nm/M053-2jp3nm-SUMMARY.md`; `prd/architecture/acp/M053-S06-MINIMAL-ACP-ADAPTER-BOUNDARY.md`; `prd/architecture/acp/M053-S08-GIT-LEX-ADAPTER-ADVANCEMENT-SYNTHESIS.md`. | `M053 narrows future adapter work to proof-only isolated source-built diagnostics.` | `M053 approves production, release/plugin binaries, raw/session logs, or main .lex.` |
| M054 proof-only wrapper | Diagnostic support input. | `.gsd/milestones/M054-63ujns/M054-63ujns-SUMMARY.md`; `prd/architecture/acp/M054-S04-PROOF-ONLY-ADAPTER-SPIKE-SYNTHESIS.md`; `prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl`; `scripts/git_lex_diagnostic_adapter.py`; `tests/test_git_lex_diagnostic_adapter.py`. | `A pinned source-built proof-only wrapper can emit bounded non-authoritative diagnostics in isolation.` | `The wrapper is ACP authority, production backend, or product/legal proof.` |
| M055 L1 shadow backend | Diagnostic support input; current allowed git-lex use. | `.gsd/milestones/M055-dbt65v/M055-dbt65v-SUMMARY.md`; `prd/architecture/acp/M055-S05-GIT-LEX-BACKEND-NEXT-DECISION.md`; `prd/architecture/acp/M055-S04-GIT-LEX-REMAINING-ADOPTION-GATES.md`; `prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl`; `scripts/acp_git_lex_backend.py`; `tests/test_acp_git_lex_backend.py`. | `ACP can continue using git-lex as an isolated, non-authoritative L1 shadow diagnostic/projection backend over ACP-shaped synthetic records.` | `M055 promotes git-lex to L2, approves main .lex, migrates source truth, proves production, or validates legal/FalkorDB/parser/R035/R037/R038 claims.` |
| RDF/OWL/SHACL/SPARQL/JSONL/JSON-LD projections | Derived projection input. | Tracked projection contracts and regenerated/verified architecture outputs when present, plus source anchors behind them. | `Derived projections support audit, recovery, interoperability, and queryability when tied back to source/proof.` | `Projection shape or query result is source truth or requirement validation by itself.` |
| Architecture registry generated views | Derived projection input unless traced to source anchors and verifier gates. | `prd/architecture/architecture_items.jsonl`; `prd/architecture/architecture_edges.jsonl`; `prd/architecture/architecture_graph_report.json`; canonical verifier outputs after regeneration. | `Generated registry views diagnose and inspect source-backed architecture claims.` | `Generated JSONL/report output creates or upgrades authority without source evidence.` |
| Browser validation summaries | Bounded validation summary only. | Tracked assertion-summary prose in `prd/architecture/acp/M052-S04-SERVE-VIZ-LISTEN-RUNTIME-PROOF.md` and GSD validation summaries. | `Browser assertions supported a local git-lex viz smoke with a known /api/store-info gap.` | `Local browser debug bundles are durable proof anchors or prove production UI readiness.` |
| Raw/session/provider payloads | Rejected durable proof anchors by default. | None for M049 binding. | `Raw/session/provider payloads remain excluded unless a future explicit redaction/proof policy accepts them.` | `Raw logs or provider payloads are ACP proof evidence by default.` |
| law-nexus legal/FalkorDB/parser/retrieval claims | Out-of-scope/profile-owned for S01 binding inputs. | Future real-document, parser, FalkorDB runtime, retrieval-quality, and citation-safe proof artifacts. | `These claims stay law-nexus profile-owned and need independent proof paths.` | `git-lex or ACP projection diagnostics prove Russian legal correctness, Garant parser completeness, FalkorDB behavior, retrieval quality, or citation safety.` |

## Blocked promotions carried into M049

M049 must not claim these from M048-M055 inputs:

- git-lex L2 operational backend readiness.
- main repository `.lex` approval.
- ACP source-truth migration into git-lex.
- production runtime readiness.
- release or plugin-bundled binary trust.
- JSON-LD runtime import/export support.
- broad SPARQL-star/RDF-star parity.
- raw/session/provider payload safety.
- Russian legal evidence correctness.
- Garant ODT parser completeness.
- FalkorDB runtime behavior.
- R035, R037, or R038 validation from ACP/git-lex/projection diagnostics.

## Out-of-scope surfaces for S01

These may become future milestones or later M049 slices, but T01 does not prove them:

- L2 operational diagnostic integration for git-lex.
- Disposable-clone rehearsal for main `.lex` state.
- Production/provenance/security hardening for git-lex binaries or server surfaces.
- Legal evidence, parser, retrieval-quality, and FalkorDB runtime proof paths.
- Architecture registry regeneration or verifier changes; S01 only maps inputs for later S03/S04 work.

## Durable anchor policy for M049

Accepted durable anchors:

- tracked repository-relative PRD, architecture, source, test, and runtime artifact paths;
- GSD milestone/requirement/decision artifacts when referenced lexically as `.gsd/...` and outside GSD execution-output storage;
- accepted GSD decisions and summaries as planning/source-boundary evidence.

Rejected durable anchors:

- `.gsd/exec` outputs;
- absolute local paths such as `/root/...`;
- ignored or local-only `.artifacts/browser/**` bundles;
- raw provider payloads, raw legal text where not necessary, raw vectors, secrets, or session logs;
- untracked files or temporary workspaces.

## S02 and S03 handoff

S02 should consume this audit to define the law-nexus profile adapter boundary. It should preserve these handoff rules:

- ACP core owns reusable source-record, lifecycle, evidence-anchor, proof-gate, projection, and health-finding mechanics.
- law-nexus profile owns Russian legal evidence, Garant parser, FalkorDB, retrieval quality, citation safety, and substantive R035/R037/R038 proof paths.
- git-lex remains L1 shadow diagnostic/projection support only; it cannot migrate authority or validate profile claims.

S03 should consume this audit to map law-nexus architecture claims into ACP source records, lifecycle states, evidence anchors, and proof gates. It should use the accepted-anchor policy above and reject generated projections or diagnostics that lack source/proof backing.

## Verification commands for T05

T05 should run these checks before completing S01:

```bash
rg -n '/root/|\.gsd/exec|\.artifacts/browser/[0-9]|validates? R0?(35|37|38)|R0?(35|37|38) validated' prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md
```

The `rg` command may find rejected-anchor examples such as `.gsd/exec` or `/root/...`; those hits are acceptable only when they appear in the rejected durable-anchor policy or unsafe wording examples, not as accepted anchors.

```bash
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
git diff --check
```

Also run GitNexus change detection for the repository:

```text
gitnexus_detect_changes(repo="law-nexus", scope="all")
```

Expected result: no high-risk changed symbols/processes for this markdown-only audit work. Because newly created markdown artifacts may be untracked until commit, direct artifact inspection remains required.
