# M049 S03 Registry Source Mapping

## Status

Verified for `M049 / S03 / T05`.

This artifact maps law-nexus architecture binding claims to ACP source-record categories, lifecycle/status defaults, evidence anchor kinds, proof gates, derived-view boundaries, S04 verifier inputs, and S05 synthesis handoff. It defines a source-mapping contract only; it does not claim generated architecture JSONL/report freshness.

## Purpose

S03 converts the verified S01/S02 boundaries into a source-mapping contract for ACP-native registry binding. The mapping must preserve this rule:

```text
Source evidence and accepted proof gates are authoritative; JSONL registry rows, graph reports, RDF/SHACL/SPARQL/JSON-LD projections, git-lex diagnostics, browser summaries, and polished prose remain derived or diagnostic unless traced back to accepted source/proof machinery.
```

S03 does not hand-edit generated architecture JSONL or claim that the current generated registry is fresh. It defines the mapping that S04 can verify and S05 can synthesize.

## Source inputs consumed by T01

| Input | Use in S03 | Boundary implication |
|---|---|---|
| `prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md` | Source-boundary input map. | Supplies accepted/rejected anchors, requirement implications, and git-lex/ACP evidence boundaries. |
| `prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md` | Profile/core boundary contract. | Supplies reusable ACP core responsibilities, law-nexus profile-owned proof paths, and S03/S04 handoff rules. |
| `prd/architecture/README.md` | Architecture registry contract. | Defines source-of-truth hierarchy, derived-view boundaries, verifier workflow, lifecycle statuses, and remediation classes. |
| `prd/architecture/architecture.schema.json` | Registry schema contract. | Defines record shape, item types, statuses, proof levels, lifecycle states, and source-anchor kinds used by this mapping. |

## Registry contract inventory

### Source-of-truth hierarchy

| Layer | S03 interpretation | Authority boundary |
|---|---|---|
| PRD/GSD/ADR/source/runtime/real-document evidence | Authoritative when tracked, repository-relative, and scoped to the claim. | May define source records and proof gates. |
| Accepted requirements and decisions | Authoritative governance inputs within their recorded scope. | May constrain lifecycle/status and proof requirements. |
| Architecture registry JSONL | Derived projection from curated mappings and source anchors. | Must not create authority by itself or be hand-edited into truth. |
| Graph reports and generated views | Derived diagnostics for health, blockers, and claim safety. | Must not prove product readiness, runtime behavior, parser completeness, retrieval quality, legal correctness, generated-Cypher safety, FalkorDB production scale, or LLM authority. |
| git-lex diagnostics | M055-bounded L1 shadow diagnostic/projection support. | Must not validate profile claims or migrate source truth. |

### Schema enums relevant to S03

| Schema field | Allowed values S03 may use | S03 mapping note |
|---|---|---|
| `item_type` | `requirement`, `decision`, `assumption`, `risk`, `proof_gate`, `component`, `interface`, `data_entity`, `quality_scenario`, `viewpoint`, `evidence`, `workflow_check`, `prompt_record`, `proposal`, `decision_candidate`, `health_finding` | Use `requirement`, `decision`, `proof_gate`, `evidence`, `workflow_check`, and `health_finding` for M049 binding surfaces; reserve component/interface/data_entity for later implementation claims with proof. |
| `item_status` | `proposed`, `active`, `hypothesis`, `bounded-evidence`, `validated`, `deferred`, `blocked`, `rejected`, `superseded`, `out-of-scope` | Default profile claims to `active`, `blocked`, `deferred`, or `bounded-evidence`; use `validated` only when matching proof exists. |
| `proof_level` | `none`, `source-anchor`, `static-check`, `unit-test`, `integration-test`, `runtime-smoke`, `real-document-proof`, `production-observation` | Use the lowest accurate proof level. S03 mapping itself is at most `source-anchor`/`static-check` unless independent profile proof exists. |
| `lifecycle_state` | `initiating`, `researching`, `evaluating`, `implementing`, `maintaining`, `sunsetting` | Use lifecycle state to locate claim maturity, not to validate the claim. |
| `source_anchor.kind` | `prd`, `gsd-requirement`, `gsd-decision`, `gsd-summary`, `source-code`, `runtime-artifact`, `test-artifact`, `external-reference`, `manual-note` | Use tracked repository-relative paths; do not use resolved symlink targets, GSD execution-output storage, absolute local paths, or ignored/local-only bundles. |

## Source anchor rules for S03

Accepted anchor classes:

- `prd`: tracked PRD, architecture, ACP, or research artifacts under `prd/`.
- `gsd-requirement`: lexical `.gsd/REQUIREMENTS.md` requirement entries.
- `gsd-decision`: lexical `.gsd/DECISIONS.md` decision entries.
- `gsd-summary`: lexical `.gsd/milestones/...` summaries, plans, validation, or UAT artifacts outside GSD execution-output storage.
- `source-code`: tracked source files when implementation evidence is relevant.
- `test-artifact`: tracked tests or test fixtures when proof depends on test behavior.
- `runtime-artifact`: tracked runtime proof artifacts only when safe and non-secret.
- `external-reference`: external source references only when explicitly recorded and scoped.
- `manual-note`: bounded manual notes only when they do not replace required proof gates.

Rejected anchors:

- GSD execution-output storage;
- absolute local paths such as resolved symlink targets outside the repository;
- ignored or local-only `.artifacts/browser/**` bundles;
- raw provider payloads, raw legal text where not necessary, raw vectors, secrets, session logs, or untracked workspaces.

## Derived-view boundary for S03

S03 may mention these derived views only as diagnostics or mapping outputs:

| Derived surface | Allowed use | Forbidden use |
|---|---|---|
| `prd/architecture/architecture_items.jsonl` | Derived item projection from curated mappings and anchors. | Creating or upgrading source authority without source evidence. |
| `prd/architecture/architecture_edges.jsonl` | Derived relationship projection for graph analysis and verifier checks. | Treating an edge as proof when its source/proof gate is missing. |
| `prd/architecture/architecture_graph_report.json` and `prd/architecture/architecture_report.md` | Health and graph diagnostics after regeneration/checks. | Proving product readiness, runtime, parser, retrieval, legal, generated-Cypher, or LLM-authority claims. |
| RDF/OWL/SHACL/SPARQL/JSON-LD outputs | Interoperability, audit, recovery, and queryability support if traced back to source/proof. | Source truth, requirement-validation proof, or profile proof. |
| git-lex diagnostics | Non-authoritative L1 diagnostic/projection support under M055. | ACP core authority, profile validation, main `.lex` approval, production readiness, or source-truth migration. |

## ACP core source-record mapping

| ACP core mapping subject | Registry item type | Default item status | Default proof level | Accepted anchor kinds | Required proof gate or edge expectation | Forbidden promotion | S04 diagnostic seed |
|---|---|---|---|---|---|---|---|
| Requirement source record | `requirement` | `active` or current GSD status mapping | `source-anchor` until stronger proof exists | `gsd-requirement`; supporting `prd` or `gsd-summary` when scoped | Edges to proof gates only when validation evidence exists; otherwise active/pending ownership remains visible. | Do not mark requirement validated from projection shape, summary prose, or diagnostic output. | `missing_requirement_proof_gate` |
| Decision source record | `decision` | `active`, `superseded`, or `rejected` based on accepted decision history | `source-anchor` or `static-check` when verifier checks decision fitness | `gsd-decision`; supporting `prd` or `gsd-summary` | Active high-risk decisions should have consequences and proof/validation coverage where required. | Do not treat a decision as runtime/product/legal proof outside its accepted scope. | `decision_fitness_gap` |
| Architecture claim record | `assumption`, `proposal`, `component`, `interface`, `quality_scenario`, or `viewpoint` depending on claim kind | `proposed`, `active`, `bounded-evidence`, `blocked`, or `deferred` | Lowest accurate level: `none`, `source-anchor`, or stronger only with evidence | `prd`, `gsd-summary`, `source-code`, `test-artifact`, `runtime-artifact` as applicable | Claim must link to evidence/proof gate before promotion to validated architecture. | Do not encode profile legal/runtime/parser/retrieval facts as generic ACP-core validated claims. | `profile_core_drift` |
| Evidence record | `evidence` | `bounded-evidence`, `active`, or `out-of-scope` | Matching evidence class: `source-anchor`, `static-check`, `unit-test`, `integration-test`, `runtime-smoke`, `real-document-proof`, or `production-observation` | `prd`, `source-code`, `test-artifact`, `runtime-artifact`, `gsd-summary`, `external-reference` | Evidence must state checked claim, scope, and remaining boundary. | Do not use unsafe/local/raw anchors or evidence outside its scope. | `unsafe_anchor` or `evidence_scope_gap` |
| Proof gate record | `proof_gate` or `workflow_check` | `active`, `blocked`, `deferred`, or `validated` only when gate has passed | `none` for pending gates; proof level of the gate when passed | `prd`, `gsd-summary`, `source-code`, `test-artifact`, `runtime-artifact` | Gate should name claim, required evidence, owner, acceptance rule, and failure mode. | Do not treat a proof-gate placeholder as proof. | `missing_profile_proof_gate` |
| Health finding record | `health_finding` | `active`, `blocked`, `deferred`, `rejected`, or `superseded` | `static-check` when derived from verifier; otherwise `source-anchor` or `none` | `prd`, `gsd-summary`, verifier outputs when tracked, source/proof anchors | Finding should name failure class, affected claim, remediation class, and source/proof anchor. | Do not let health findings mutate source truth automatically. | `health_finding_without_remediation` |
| Derived projection link | `evidence` or edge metadata, not source authority | `bounded-evidence` or `out-of-scope` | `static-check` only for projection freshness/shape, not profile proof | `prd` projection artifacts plus source anchors behind them | Projection must trace back to source records and proof gates. | Do not use JSONL/RDF/SHACL/SPARQL/JSON-LD output as source truth by itself. | `authority_inversion` |
| git-lex diagnostic record | `evidence` or `health_finding` | `bounded-evidence` or `active` diagnostic only | `static-check` or bounded diagnostic proof only | M055 PRD artifacts, adapter source/tests, tracked diagnostics when safe | Must be marked L1 shadow diagnostic/projection support and non-authoritative. | Do not promote git-lex to source truth, L2 operational backend, main `.lex`, or profile validator. | `forbidden_git_lex_promotion` |

## law-nexus profile claim gate mapping

| Profile claim class | Registry item type | Default item status | Required proof level for validation | Evidence anchor class | Profile-owned proof gate | Forbidden positive claim | S04 diagnostic seed |
|---|---|---|---|---|---|---|---|
| Russian legal correctness | `proof_gate`, `evidence`, or `quality_scenario` | `active`, `blocked`, or `deferred` | `real-document-proof` plus review evidence when legal correctness is asserted | `prd`, `gsd-summary`, future safe `runtime-artifact` or `test-artifact`; real legal source anchors when tracked and bounded | `GATE-RUSSIAN-LEGAL-EVIDENCE-CORRECTNESS` | Do not claim legal correctness or legal authority from ACP registry shape, generated prose, or git-lex diagnostics. | `profile_core_drift` / `missing_profile_proof_gate` |
| Legal-source authority and temporal provenance | `proof_gate` or `evidence` | `active` or `blocked` | `real-document-proof` or `static-check` for bounded source-authority mapping only | `prd`, `gsd-summary`, source/evidence artifacts when future proof exists | `GATE-LEGAL-SOURCE-AUTHORITY-PROVENANCE` | Do not infer authority hierarchy, temporal validity, or citation support from source-record category alone. | `authority_inversion` |
| Garant ODT parser completeness | `proof_gate`, `evidence`, or `workflow_check` | `active`, `blocked`, or `bounded-evidence` if scoped proof exists | `real-document-proof` for parser completeness; `runtime-smoke` only for bounded parser smoke | `source-code`, `test-artifact`, `runtime-artifact`, `gsd-summary`, `prd` | `GATE-GARANT-ODT-PARSER-COMPLETENESS` | Do not claim parser completeness from S03 mapping, prior non-ODT assumptions, or git-lex diagnostics. | `missing_profile_proof_gate` |
| FalkorDB ingest path | `proof_gate`, `workflow_check`, or `evidence` | `active`, `blocked`, or `bounded-evidence` for small scoped proof | `integration-test` or `runtime-smoke` depending on ingest scope | `source-code`, `test-artifact`, `runtime-artifact`, `gsd-summary`, `prd` | `GATE-FALKORDB-INGEST-R037` | Do not close R037 or claim production data loading, larger corpus ingest, skipped/failed row accounting, resource profile, or recovery without matching proof. | `forbidden_profile_validation` |
| FalkorDB runtime behavior | `proof_gate`, `workflow_check`, or `evidence` | `active`, `blocked`, or `bounded-evidence` | `runtime-smoke` for bounded runtime behavior; `production-observation` for production claims | `source-code`, `test-artifact`, `runtime-artifact`, `prd` | `GATE-FALKORDB-RUNTIME-BEHAVIOR` | Do not claim FalkorDB production readiness, vector/full-text/UDF behavior, graph-scale behavior, or operational behavior from generic ACP mapping. | `missing_profile_proof_gate` |
| Retrieval quality and graph-vector behavior | `proof_gate`, `quality_scenario`, or `evidence` | `active`, `blocked`, or `deferred` | `integration-test` or stronger; independent review if proof-heavy | `test-artifact`, `runtime-artifact`, `gsd-summary`, `prd` | `GATE-RETRIEVAL-QUALITY-R035` | Do not close R035 or claim retrieval quality, graph-vector behavior, standards adoption, or pilot scale from projections or profile-boundary prose. | `forbidden_profile_validation` |
| Citation safety and legal-answer non-authority | `proof_gate`, `quality_scenario`, or `evidence` | `active`, `blocked`, or `deferred` | `integration-test`, `real-document-proof`, or bounded static proof depending on claim | `prd`, `test-artifact`, `runtime-artifact`, `gsd-summary` | `GATE-CITATION-SAFE-RETRIEVAL` | Do not claim citation-safe legal answering from generated summaries, generic evidence anchors, or LLM output. | `missing_profile_proof_gate` |
| Generated-Cypher / Legal KnowQL safety | `proof_gate`, `workflow_check`, or `quality_scenario` | `active`, `blocked`, or `deferred` | `unit-test`, `integration-test`, or static deterministic safety check as claim requires | `source-code`, `test-artifact`, `prd`, `gsd-summary` | `GATE-GENERATED-CYPHER-SAFETY` | Do not infer generated-Cypher safety from registry source mapping, graph projection, or git-lex diagnostics. | `missing_profile_proof_gate` |
| R035 ontology/product architecture promotion | `requirement`, `proof_gate`, or `health_finding` | `active` with profile-owned pending/blocked gates | `static-check`, `integration-test`, or `runtime-smoke` according to the specific trigger; never lower than source-mapped proof gate requirements | `gsd-requirement`, `prd`, `gsd-summary`, future proof artifacts | `GATE-R035-ONTOLOGY-PROMOTION` plus trigger-specific gates from architecture README where applicable | Do not validate R035, ontology standards, graph-vector, retrieval-quality, or pilot-scale claims from ACP/git-lex/projection evidence alone. | `forbidden_profile_validation` |
| R037 FalkorDB ingest validation | `requirement`, `proof_gate`, or `health_finding` | `active` with bounded evidence only where scoped proof exists | `integration-test` or `runtime-smoke` for ingest; stronger proof for production loading | `gsd-requirement`, `source-code`, `test-artifact`, `runtime-artifact`, `gsd-summary` | `GATE-R037-FALKORDB-INGEST` | Do not validate R037 or production ingest from generic integration proof-gate structure. | `forbidden_profile_validation` |
| R038 independent review gate | `requirement`, `workflow_check`, or `proof_gate` | `active` standing gate | `static-check` for review-gate presence; stronger if reviewing runtime/legal/retrieval proof | `gsd-requirement`, `gsd-summary`, `prd` | `GATE-R038-INDEPENDENT-PROOF-REVIEW` | Do not retire R038 because S03 mapping or self-authored verification exists. | `missing_profile_proof_gate` |
| git-lex diagnostic consumption by profile | `evidence` or `health_finding` | `bounded-evidence` or `active` diagnostic only | `static-check` or bounded diagnostic proof only | M055 artifacts, adapter source/tests, tracked safe diagnostics | `GATE-GIT-LEX-L1-DIAGNOSTIC-BOUNDARY` | Do not use git-lex diagnostics to validate legal, parser, FalkorDB, retrieval, citation, generated-Cypher, or R035/R037/R038 claims. | `forbidden_git_lex_promotion` |

## Profile mapping defaults

- Use `active`, `blocked`, `deferred`, or `bounded-evidence` for profile claims unless independent profile proof justifies a stronger state.
- Use `validated` only when the required proof level and accepted evidence anchors exist for the exact claim scope.
- Use `source-anchor` for mapped proof obligations and `none` for placeholder gates that have not yet earned evidence.
- Use `health_finding` records to preserve missing proof, unsafe anchor, profile/core drift, forbidden git-lex promotion, and R035/R037/R038 overclaim diagnostics without changing source truth automatically.

## S04 verifier input matrix

| Verifier concern | Source fields or surfaces to inspect | Example unsafe pattern | Expected diagnostic | Remediation class |
|---|---|---|---|---|
| Authority inversion | `item_type`, `item_status`, `proof_level`, source anchors, derived projection references, prose around JSONL/RDF/SHACL/SPARQL/JSON-LD/git-lex/browser outputs | A generated projection, graph report, LLM summary, browser summary, or git-lex diagnostic is treated as source truth or validation proof. | `authority_inversion` | `downgrade-claim` or `add-source-anchor` plus `add-proof-gate` |
| Unsafe anchor | `source_anchors[].path`, `source_anchors[].kind`, evidence/proof references in binding artifacts | GSD execution-output storage, absolute local path, ignored `.artifacts/browser/**`, raw payload/vector/secret/session log, or untracked workspace appears as accepted anchor. | `unsafe_anchor` | `add-source-anchor` or `downgrade-claim` |
| Missing proof gate | `item_status`, `proof_level`, outgoing proof/validation/check edges, proof-gate records | A claim is `validated` or production-ready but lacks proof gate, accepted evidence anchor, checked claim, or owner. | `missing_profile_proof_gate` or `missing_requirement_proof_gate` | `add-proof-gate` and `add-evidence-class` |
| Profile/core drift | ACP core mapping records versus law-nexus profile claim classes | Russian legal correctness, parser completeness, FalkorDB runtime, retrieval quality, citation safety, generated-Cypher safety, or R035/R037/R038 validation is represented as generic ACP-core authority. | `profile_core_drift` | `downgrade-claim` and move to profile-owned proof gate |
| Forbidden git-lex promotion | git-lex references, M055 anchors, diagnostic evidence records, adoption/provenance wording | git-lex is promoted to source truth, L2 operational backend, main `.lex`, production backend, ACP authority, or profile validator without future proof/adoption decision. | `forbidden_git_lex_promotion` | `downgrade-claim` or `defer-to-backlog` |
| R035/R037/R038 overclaim | Requirement mappings, proof gates, profile claim table, synthesis prose | R035/R037/R038 are closed, retired, or substantively validated from ACP/git-lex/projection/profile-boundary evidence alone. | `forbidden_profile_validation` | `downgrade-claim`, `add-proof-gate`, or `defer-to-backlog` |
| Main-state residue | Repository root state and binding artifacts | Main checkout contains `.lex`, `Squad`, `Raw`, or `.artifacts` residue, or artifact text approves blind `git lex init`. | `main_state_residue` | remove residue; `downgrade-claim`; require explicit future adoption decision |
| Derived-registry currency overclaim | Claims about `architecture_items.jsonl`, `architecture_edges.jsonl`, graph reports, or verifier/router currency | S03 claims generated registry is current without running canonical architecture verifier on default paths. | `registry_currency_overclaim` | run canonical verifier before currency claim or downgrade wording |
| Placeholder proof misuse | `proof_gate` or `workflow_check` records with `proof_level=none`, missing evidence, or pending status | A placeholder gate is cited as proof that profile behavior exists. | `proof_gate_placeholder_used_as_proof` | `add-evidence-class` or `downgrade-claim` |

## S05 synthesis handoff

S05 may claim from S03 only that M049 has a source-mapping contract for ACP-native binding. S05 must not claim:

- current generated architecture JSONL/report freshness unless the canonical architecture verifier was run and passed on default paths;
- law-nexus legal correctness, Garant parser completeness, FalkorDB runtime/ingest validation, retrieval quality, citation safety, generated-Cypher safety, or R035/R037/R038 validation;
- git-lex adoption beyond M055 L1 shadow diagnostic/projection support;
- production readiness or main `.lex` readiness.

S05 should synthesize these positive bounded claims:

- reusable ACP core mechanics are mapped to registry item/status/proof/anchor defaults;
- law-nexus profile claims are mapped to profile-owned proof gates and non-validated defaults;
- derived views and git-lex diagnostics are explicitly non-authoritative unless traced to source/proof;
- S04 has concrete verifier inputs for authority inversion, unsafe anchors, missing proof gates, profile/core drift, forbidden git-lex promotion, R035/R037/R038 overclaim, main-state residue, and registry-currency overclaim.

## Verification expectations for T05

T05 should run focused verification for:

- required S03 sections and mapping tables;
- unsafe anchors and accepted-anchor misuse;
- forbidden R035/R037/R038 positive validation/closure wording;
- no `.lex`, `Squad`, `Raw`, or `.artifacts` residue;
- `git diff --check`;
- `gitnexus_detect_changes(repo="law-nexus", scope="all")`.
