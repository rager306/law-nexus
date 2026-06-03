# M049 S02 Profile Adapter Boundary

## Status

Verified for `M049 / S02 / T05`.

This artifact defines the profile adapter boundary for separating reusable ACP core mechanics from law-nexus profile-owned constraints. It records the input-derived inventory, ACP core responsibilities, law-nexus profile responsibilities, S03 registry mapping handoff, S04 verifier handoff, and T05 verification expectations.

## Purpose

S02 must keep ACP reusable while allowing law-nexus to bind into ACP without weakening law-nexus-specific proof requirements. The core rule is:

```text
Reusable ACP core defines record, lifecycle, evidence, proof-gate, projection, and health mechanics; law-nexus profile owns Russian legal evidence, Garant parser, FalkorDB, retrieval, citation safety, and substantive R035/R037/R038 proof paths.
```

S02 consumes the verified S01 input audit and must not promote git-lex, ACP projections, registry views, browser summaries, or polished analysis into profile authority by shape alone.

## Source inputs consumed by T01

| Input | Use in S02 | Boundary implication |
|---|---|---|
| `prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md` | Primary S02 source-boundary map. | Supplies accepted/rejected anchors, requirement implications, and S02/S03 handoff rules. |
| `.gsd/milestones/M049/M049-ROADMAP.md` | Milestone contract. | Requires reusable ACP core to remain separate from law-nexus profile constraints and forbids git-lex/source-truth overpromotion. |
| `.gsd/REQUIREMENTS.md` | Active capability/constraint contract. | Defines current statuses and ownership boundaries for R035/R037/R038/R041/R042/R046/R047/R048/R055/R056/R057. |
| `.agents/skills/legalgraph-architecture-verification/SKILL.md` | Derived routing guidance. | Reinforces source-truth hierarchy and keeps generated registry JSONL/report/verifier outputs diagnostic unless tied to source anchors and proof gates. |

## Input-derived boundary inventory

| Boundary concern | Reusable ACP core responsibility | law-nexus profile responsibility | Forbidden promotion |
|---|---|---|---|
| Source records | Define generic record categories for requirements, decisions, project-state docs, architecture registry claims, milestone evidence, proof gates, and health findings. | Bind law-nexus claims to the correct source categories and supply profile-specific evidence anchors where needed. | Do not treat a record-shaped artifact as authoritative without lifecycle state, evidence anchor, and proof gate or accepted decision. |
| Lifecycle and health | Define generic lifecycle states, transition rules, health categories, allowed/blocked actions, and authority-inversion/missing-proof signals. | Interpret those lifecycle/health states for law-nexus legal, parser, FalkorDB, retrieval, and citation-safety proof paths. | Do not claim lifecycle automation or operationalization from S02; M050 remains the operationalization horizon. |
| Evidence anchors | Define portable anchor rules: tracked repo-relative PRD, architecture, source, test, runtime, and lexical `.gsd/...` planning artifacts outside GSD execution-output storage. | Provide law-nexus-specific anchors for real-document evidence, parser proof, FalkorDB runtime/ingest proof, retrieval metrics, and citation-safety evidence when future proof exists. | Do not use `.gsd/exec`, absolute local paths, `.artifacts/browser/**`, raw payloads, secrets, raw vectors, or untracked workspaces as durable anchors. |
| Proof gates | Define generic proof-gate fields and decision acceptance requirements. | Own substantive proof gates for R035, R037, R038, Russian legal correctness, Garant parser completeness, FalkorDB behavior, retrieval quality, and citation safety. | Do not validate R035/R037/R038 from ACP/git-lex/projection diagnostics or from S02 profile-boundary prose. |
| Derived projections | Define derived projection boundaries for JSONL, RDF, OWL, SHACL, SPARQL, JSON-LD, graph reports, dashboards, and recovery views. | Consume projections only as inspection/recovery aids after tracing back to law-nexus source anchors and proof gates. | Do not let projection shape or query results become source truth or requirement-validation proof by themselves. |
| git-lex diagnostics | Allow only the M055-bounded L1 shadow diagnostic/projection role as non-authoritative support. | Treat any future law-nexus use of git-lex diagnostics as diagnostic only unless a later explicit proof gate and adoption decision changes scope. | Do not approve L2 operational backend readiness, main `.lex`, `Squad`, `Raw`, source-truth migration, production readiness, or R035/R037/R038 validation. |
| Russian legal evidence | Provide generic slots for source records, evidence anchors, lifecycle state, and proof gates. | Own legal-source authority boundaries, temporal-first evidence, citation-safe claims, and non-authoritative LLM answer boundaries. | Do not move Russian legal correctness into generic ACP core or validate it from registry/projection shape. |
| Garant parser and real-document proof | Provide generic parser-proof record and evidence-gate structure. | Own real Garant ODT parser completeness, extraction shape, parser diagnostics, and real-document evidence anchors. | Do not infer parser completeness from ACP binding, git-lex diagnostics, or prior non-ODT assumptions. |
| FalkorDB ingest/runtime | Provide generic runtime/ingest proof gate structure and health categories. | Own FalkorDB CSV ingest, idempotency, counts, error handling, cleanup, resource profile, runtime behavior, and future production-loading policy. | Do not validate FalkorDB behavior, larger corpus ingest, or production runtime from ACP/profile mapping alone. |
| Retrieval and citation safety | Provide generic retrieval-quality and citation-safety proof slots. | Own retrieval metrics, graph-vector claims, source provenance, citation formatting, and legal-answer non-authority boundaries. | Do not validate retrieval quality, graph-vector behavior, pilot scale, or citation safety from M049 binding artifacts alone. |

## ACP core responsibility table

| ACP core surface | Allowed core responsibility | Forbidden core responsibility | Accepted anchors | S03 mapping implication |
|---|---|---|---|---|
| Source-record categories | Define reusable categories for requirements, decisions, project-state docs, architecture registry claims, milestone evidence, proof gates, and health findings. | Owning law-nexus legal correctness, parser completeness, FalkorDB behavior, retrieval quality, or citation safety as generic core facts. | `.gsd/REQUIREMENTS.md`; `.gsd/DECISIONS.md`; tracked PRD/architecture artifacts; tracked source/test/runtime artifacts when proof exists. | S03 may map law-nexus claims into generic source-record categories, but must attach profile-owned evidence/proof gates for profile claims. |
| Lifecycle states | Define generic lifecycle states such as active, mapped, bounded, validated, deferred, blocked, superseded, and rejected where supported by source evidence. | Advancing profile claims to validated/production-ready states without profile proof. | GSD requirement status; accepted decisions; tracked verifier or proof artifacts. | S03 should assign lifecycle state based on current source/proof evidence, not on projection shape or prose completeness. |
| Evidence anchors | Define portable anchor policy and anchor validation expectations. | Accepting `.gsd/exec`, absolute local paths, `.artifacts/browser/**`, raw payloads, raw vectors, secrets, session logs, or untracked workspaces as durable anchors. | Repository-relative tracked files; lexical `.gsd/...` planning artifacts outside execution-output storage; accepted decision and requirement artifacts. | S03 should reject or downgrade claims with unsafe, missing, or local-only anchors. |
| Proof gates | Define generic proof-gate structure: proof class, evidence anchor, checked claim, acceptance decision, and remaining boundary. | Treating generic proof-gate shape as proof that law-nexus runtime/legal/parser/retrieval behavior exists. | Tracked tests, verifier output, runtime observations, real-document evidence, and accepted decisions when present. | S03 should create proof-gate slots for profile claims but leave them pending/blocked unless profile evidence exists. |
| Derived projections | Define projection boundaries for JSONL, RDF, OWL, SHACL, SPARQL, JSON-LD, dashboards, graph reports, and recovery views. | Making projections source truth or requirement-validation proof by themselves. | Projection files only when traced back to source records, evidence anchors, and verifier checks. | S03 may list projections as derived views but must point back to source records and proof gates. |
| Health findings | Define generic health categories for authority inversion, missing proof gate, unsafe anchor, stale projection, contradictory state, and forbidden promotion. | Resolving profile-specific legal/runtime/parser/retrieval findings without profile evidence or owner. | Verifier outputs, tracked audit artifacts, requirements, decisions, and source/proof anchors. | S03 should emit health findings when claims lack profile evidence or use unsafe anchors. |
| Authority-inversion checks | Define checks that prevent analysis, summaries, generated reports, projections, or diagnostics from becoming authority by shape alone. | Allowing polished LLM/projection artifacts to bypass record category, lifecycle state, evidence anchor, and proof gate requirements. | R055, S01 audit, accepted decisions, verifier rules, and tracked source evidence. | S03 should mark shape-only claims as diagnostic/derived until source/proof backing exists. |
| git-lex integration boundary | Represent git-lex only as optional L1 shadow diagnostic/projection support under M055 boundaries. | Promoting git-lex to source truth, L2 operational backend, main `.lex`, production backend, or profile validator. | M055 decision artifacts, bounded diagnostics, adapter source/tests, and S01/S02 boundary artifacts. | S03 may reference git-lex diagnostics only as non-authoritative support and must not use them to validate profile claims. |

## law-nexus profile responsibility table

| Profile concern | Profile-owned proof path | Forbidden ACP-core promotion | Downstream owner |
|---|---|---|---|
| Russian legal evidence | Real legal-source anchors, temporal-first evidence, legal authority boundaries, jurisdiction/source provenance, and explicit non-authoritative LLM answer wording. | Generic ACP core must not claim Russian legal correctness, legal authority, or source hierarchy truth beyond typed record/proof-gate mechanics. | Future Russian legal evidence and citation-safe retrieval proof milestones; S03 maps source/proof slots only. |
| Legal-source authority boundaries | Profile defines which legal sources, citations, temporal states, and evidence spans can support claims. | ACP core must not infer legal authority from source-record shape, projection output, or generated prose. | S03 for mapping slots; later legal evidence verifier or retrieval milestone for substantive proof. |
| Garant ODT parser proof | Real `law-source/garant/44-fz.odt` and future real-document parser evidence, extraction diagnostics, completeness criteria, and parser error handling. | ACP core must not validate parser completeness or extraction quality from binding artifacts, git-lex diagnostics, or non-ODT prior assumptions. | Future parser/ETL proof milestone; S03 records pending proof gates. |
| FalkorDB ingest proof | Verified CSV/source shape, idempotency, counts, skipped/failed row accounting, Docker/file access or client-loader constraints, error handling, cleanup, and larger-corpus readiness when proven. | ACP core must not validate R037, production data loading, resource profile, operational recovery, or FalkorDB runtime behavior from generic integration gates. | Future ingest-scale / production-data-loading milestone; S03 records gate structure. |
| FalkorDB runtime behavior | Runtime smoke, source-backed FalkorDB capability evidence, graph query behavior, operational diagnostics, and production-readiness proof when separately produced. | ACP core must not claim FalkorDB runtime correctness, production readiness, vector/full-text/UDF behavior, or graph-scale behavior from profile boundary prose. | Future FalkorDB runtime/prod proof milestones; S04 can check missing proof gates. |
| Retrieval quality | Representative corpus, metrics, source provenance, bounded retrieval claims, graph-vector proof gates, and independent review where proof-heavy. | ACP core must not validate R035, retrieval quality, graph-vector behavior, standards adoption, or pilot scale from source-record/projection shape. | Future retrieval-quality / production-readiness horizon; S03 maps pending gates. |
| Citation safety | Citation formatting, evidence-span traceability, legal answer non-authority, source provenance, and failure-mode handling for missing/ambiguous evidence. | ACP core must not claim citation-safe legal answering from generic evidence anchors or generated summaries. | Future citation-safe retrieval proof; S04 should check missing citation proof gates. |
| Generated-Cypher safety | Profile owns generated-Cypher safety requirements where legal retrieval/query generation relies on graph queries, including deterministic constraints and failure modes. | ACP core must not infer generated-Cypher safety from architecture registry mapping or projection diagnostics. | Future Legal KnowQL / generated-Cypher safety proof; S03/S04 can reserve/check gates. |
| R035 substantive validation | Profile owns conversion of ontology architecture research into bounded evidence, registry source mappings, proof gates, retrieval-quality/product proof, and accepted promotion decisions. | ACP core must not close R035 or promote ontology/standards/graph-vector/pilot-scale claims. | Future retrieval-quality and production-readiness milestones; S03 maps pending source/proof gates. |
| R037 substantive validation | Profile owns larger ingest/data-loading proof, skipped/failed row accounting, operational recovery, and production loading constraints. | ACP core must not close R037 or treat generic ingest proof-gate structure as FalkorDB ingest validation. | Future ingest-scale / production-data-loading milestone; S03 maps pending source/proof gates. |
| R038 standing review gate | Profile and ACP milestone owners must preserve independent proof-review expectations for proof-heavy profile claims. | ACP core must not retire R038 because S02 has a boundary contract or because self-authored checks pass. | Future proof-heavy milestones; S04/S05 should preserve review-gate wording. |
| git-lex diagnostic consumption | Profile may consume M055-bounded git-lex outputs only as non-authoritative diagnostics for ACP-shaped synthetic records. | Profile must not use git-lex diagnostics to validate legal, parser, FalkorDB, retrieval, citation, generated-Cypher, or R035/R037/R038 claims. | Optional future L2 diagnostic integration after separate proof; not S02/S03 authority. |

## Requirement ownership implications from inputs

| Requirement | S02 boundary implication | Current non-claim |
|---|---|---|
| R035 | Profile owns ontology/product architecture, graph-vector, standards-adoption, retrieval-quality, and pilot-scale proof paths; ACP core may model the proof-gate machinery. | S02 does not validate R035 or any product/retrieval/standards claim. |
| R037 | Profile owns FalkorDB ingest/runtime proof details; ACP core may define generic integration proof gates and health findings. | S02 does not validate larger corpus ingest, production data loading, or FalkorDB runtime behavior. |
| R038 | Profile and ACP binding work should preserve independent proof-review expectations for proof-heavy claims. | S02 does not retire the standing independent-review gate. |
| R041 | ACP core owns typed source-record categories; profile supplies law-nexus-specific source/evidence instances. | S02 does not fully validate current law-nexus registry source mapping; S03 owns that mapping. |
| R042 | ACP core owns lifecycle/health model; profile interprets it for law-nexus proof paths. | S02 does not implement lifecycle automation. |
| R046 | ACP core must preserve source-truth versus derived-projection boundary. | S02 does not promote projections or diagnostics to authority. |
| R047 | ACP/profile contract must preserve no-main-repo git-lex mutation. | S02 does not approve `.lex`, `Squad`, `Raw`, or blind `git lex init`. |
| R048 | S02 is the primary boundary slice: keep law-nexus constraints in profile/adapter layer. | S02 must not move R035/R037/R038 or legal/FalkorDB/parser constraints into generic ACP core. |
| R055 | ACP core should encode anti-imitation controls requiring record category, lifecycle state, evidence anchor, and proof gate or accepted decision. | S02 prose does not make polished artifacts authoritative. |
| R056 | Profile boundary should preserve M055 L1 diagnostics as bounded and leave missing/absorbed capability deltas explicit. | S02 does not state git-lex satisfies every ACP capability. |
| R057 | S02 advances safe law-nexus binding after M055 disposition by defining adapter boundaries. | S02 does not prove final binding or downstream legal/runtime/product claims. |

## Forbidden promotions carried forward

S02 must preserve these blocked claims:

- reusable ACP core owns law-nexus legal correctness, parser completeness, FalkorDB behavior, retrieval quality, citation safety, or R035/R037/R038 substantive validation;
- git-lex L1 diagnostics become ACP or profile authority;
- main `.lex`, `Squad`, or `Raw` is approved;
- generated projections, registry views, browser summaries, or polished prose become source truth by shape alone;
- rejected anchors such as GSD execution-output storage, absolute local paths, `.artifacts/browser/**`, raw payloads, raw vectors, secrets, session logs, or untracked workspaces become durable proof anchors.

## S03 registry source mapping handoff

S03 may map these as reusable ACP source-record/proof-gate mechanics:

- requirement, decision, project-state, architecture-claim, milestone-evidence, proof-gate, and health-finding record categories;
- lifecycle states and transition rules when backed by `.gsd/REQUIREMENTS.md`, `.gsd/DECISIONS.md`, tracked PRD/architecture source, or accepted proof evidence;
- evidence-anchor fields and durable-anchor validation rules;
- derived projection links when they point back to source records and proof gates;
- health findings for authority inversion, missing proof gate, unsafe anchor, stale projection, profile/core drift, and forbidden git-lex promotion.

S03 must keep these as law-nexus profile-owned proof gates, not ACP-core facts:

- Russian legal correctness, legal-source authority, temporal/source provenance, and citation-safe answer behavior;
- Garant ODT parser completeness, extraction quality, parser diagnostics, and parser error handling;
- FalkorDB ingest/runtime behavior, production data loading, resource profile, and operational recovery;
- retrieval quality, graph-vector behavior, standards/pilot-scale architecture claims, and representative metrics;
- generated-Cypher/Legal KnowQL safety where graph query generation is involved;
- substantive R035/R037/R038 validation or review-gate retirement.

S03 must use these state defaults unless new independent proof exists:

| Claim type | Default S03 mapping state | Required reason |
|---|---|---|
| Generic ACP mechanics | `mapped` or `active` | Source-record/lifecycle/evidence/proof-gate structure is the reusable ACP subject of M049. |
| law-nexus profile proof gates | `active`, `pending`, `blocked`, or `deferred` | S02 defines ownership only; substantive proof belongs to future profile-owned milestones. |
| git-lex diagnostics | `diagnostic` or derived support only | M055 permits L1 shadow diagnostic/projection support, not authority or profile validation. |
| generated projections/views | `derived` | Projection output remains non-authoritative unless traced back to source/proof. |

## S04 verifier handoff

S04 should add or specify checks that fail on these cases:

| Verifier concern | Failure condition | Expected diagnostic |
|---|---|---|
| Profile/core drift | A profile-owned claim is mapped as generic ACP-core authority. | `profile_core_drift` or equivalent health finding. |
| Missing proof gate | A profile-owned claim has validated/production-ready wording without a proof gate and accepted evidence anchor. | `missing_profile_proof_gate`. |
| Unsafe anchor | A durable proof anchor uses GSD execution-output storage, absolute local paths, `.artifacts/browser/**`, raw payloads, raw vectors, secrets, session logs, or untracked workspaces. | `unsafe_anchor`. |
| Authority inversion | Projection/report/LLM prose/browser summary/git-lex diagnostic output is treated as source truth. | `authority_inversion`. |
| Forbidden git-lex promotion | git-lex is promoted beyond M055 L1 shadow diagnostic/projection support without a future explicit proof gate and adoption decision. | `forbidden_git_lex_promotion`. |
| R035/R037/R038 overclaim | ACP/git-lex/projection/profile-boundary prose closes or substantively validates R035/R037/R038 without independent profile proof. | `forbidden_profile_validation`. |
| Main-state residue | Main checkout contains `.lex`, `Squad`, `Raw`, or `.artifacts` residue. | `main_state_residue`. |

## Verification expectations for T05

T05 should run focused verification for:

- required S02 sections and tables;
- unsafe anchors and accepted-anchor misuse;
- forbidden R035/R037/R038 positive validation/closure wording;
- no `.lex`, `Squad`, `Raw`, or `.artifacts` residue;
- `git diff --check`;
- `gitnexus_detect_changes(repo="law-nexus", scope="all")`.
