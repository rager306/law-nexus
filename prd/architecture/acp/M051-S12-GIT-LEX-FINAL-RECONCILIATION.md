# M051 S12 Git Lex Final Reconciliation

## Status

In progress for `M051-q6ctvc / S12`.

This artifact reconciles the expanded git-lex repository corpus, the user-provided GPT Pro/deep research report, and current M051 evidence into final M051 ACP production-cycle decisions. It is still task-scoped until all S12 tasks complete.

## T05: Final M051 safety and validation checks

### Final M051 safety results

Command output anchor:

```text
.gsd/exec/2a0e8080-f3cf-4cfb-9774-be59463e0bc5.stdout
```

Observed results:

```text
no-main-repo .lex: pass
git diff --check: pass
S08 verifier: status=ok failure_count=0
architecture verifier: status=ok failure_count=0
S12 artifact contracts: present
R058/R059 present in requirements
```

GitNexus change detection:

```text
gitnexus_detect_changes({repo:"law-nexus", scope:"all"})
changed_files: 1
risk_level: low
changed_symbols: []
affected_processes: []
```

### Tracked artifacts checked or produced by M051

Key final artifacts:

- `prd/architecture/acp/M051-S05-GIT-LEX-ACP-INTEGRATION-DECISION.md`
- `prd/architecture/acp/M051-S06-GIT-LEX-SKILL-VALIDATION.md`
- `prd/architecture/acp/M051-S07-GIT-LEX-INTERIM-SYNTHESIS.md`
- `prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md`
- `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md`
- `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md`
- `prd/architecture/acp/M051-S11-GIT-LEX-EXPANDED-CORPUS.md`
- `prd/architecture/acp/M051-S12-GIT-LEX-FINAL-RECONCILIATION.md`
- `.agents/skills/git-lex/SKILL.md`
- `.agents/skills/git-lex/references/source-inventory.md`
- `.agents/skills/git-lex/references/ontology-map.md`
- `.agents/skills/git-lex/references/runtime-adoption-gates.md`
- `scripts/verify-m051-s08-acp-ontology-prototype.py`
- `prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl`
- `prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.ttl`
- `prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld`
- `prd/architecture/acp/shacl/m051/acp-prototype.shacl.ttl`
- `prd/architecture/acp/sparql/m051/*.rq`
- `tmp/deep-research-report.md`

External vendor-source anchors are recorded in S11 and source inventory; they are external reference checkouts, not law-nexus source truth.

### Final M051 completion recommendation

```text
recommendation: pass
```

Reason: M051 met the revised R059 scope. It did not approve git-lex runtime adoption, but it did complete the required research, runtime gate, ontology prototype, skill update, expanded repo corpus, external research reconciliation, and production-cycle disposition.

### Preserved caveats

- No main-repo `.lex` mutation occurred or is approved.
- ACP source authority remains ACP-native.
- git-lex runtime remains adapter-later, not core backend.
- `subtext-mcp`, plugin repos, and Claude/GSD-like agent CLI artifacts remain process/UX/runtime-integration evidence, not ACP proof.
- JSON-LD runtime support remains blocked.
- Negative SHACL validation remains blocked.
- SPARQL-star user-facing compatibility remains blocked.
- Prebuilt binary provenance remains blocked/rejected as adoption proof.
- R035, R037, and R038 remain not validated by git-lex corpus evidence.

### T05 conclusion

S12 passes final safety checks. The final M051 outcome is a bounded research/decision closure: adopt ACP-native authority and selected semantic patterns, use S08/S12 as implementation planning seeds, and keep git-lex runtime/plugin/code-graph paths behind future proof gates.

## T04: M048 and S07 interim re-evaluation

### M048 re-evaluation

| Prior M048 conclusion | S12 status | Reason | Requirement/decision impact |
|---|---|---|---|
| Runtime git-lex adoption should be deferred/blocked because executable acquisition was not proven. | upgraded but still blocked for production | S10 built and smoke-tested debug binaries, but production fitness, provenance, and adapter safety remain unproven. | Keep ACP-native-first decision; future adapter spike allowed only behind gates. |
| ACP-native deterministic mechanics should remain primary. | retained | S11/S12 add corpus breadth but no replacement source-authority proof. | No decision update required except wording: ACP-native authority is final M051 disposition. |
| Main repo `.lex` must remain absent. | retained | All M051 slices preserved no-main `.lex`; S12 still blocks mutation. | No requirement update; keep as hard guardrail. |
| Semantic kit evidence can inform ACP but not validate requirements. | retained/refined | Expanded kits confirm richer prior art, but still source/ontology evidence only. | Keep R035/R037/R038 active/unvalidated. |
| subtext/Claude plugin path was absent or not enough for adoption. | corrected/refined | S09/S11 show subtext/plugin/Claude-agent CLI path exists and is relevant, but only as UX/process evidence. | Update synthesis only: agent CLI surfaces are adapter-later, not ignored. |
| Runtime availability was blocked. | superseded for local smoke, still blocked for production | S10 local source-build debug runtime passed bounded isolated smoke. | M048 blocked acquisition statement should be read as historically true, not current runtime-smoke status. |
| JSON-LD/SPARQL-star/negative validation remained unproven. | retained | S08/S10/S11/S12 did not upgrade these. | Keep blocked. |
| Prebuilt binaries are not adoption proof. | retained | S09 provenance gaps remain; S11 added no stronger manifest. | Keep rejected as proof. |

### S07 interim conclusion re-evaluation

| S07 interim conclusion | S12 status | Reason |
|---|---|---|
| S07 is not final; S11/S12 required. | superseded by completion | S11 corpus and S12 reconciliation now exist. |
| ACP-native authority remains current safest posture. | retained as final M051 disposition | No expanded evidence replaces ACP source/proof authority. |
| Expanded repos may change production-cycle scope. | confirmed/refined | S11 shows code graph, plugin/UX, ontology evolution, and agent CLI integration scope. |
| GPT Pro/deep research must be normalized and reconciled. | completed | S12 T01 normalized GP01-GP15 and T02 reconciled them. |
| R059 pending S11/S12. | validated in M051 | S11 and S12 now provide expanded repo corpus and external research reconciliation. |

### Requirements and decisions outcome

| ID / decision | Outcome | Notes |
|---|---|---|
| R058 | validated for M051 knowledge-delta requirement | S06 recorded KD01-KD08; S12 added KD09-KD14 with evidence anchors, proof class, remaining boundary, and downstream implication. |
| R059 | validated | M051 now treats S07 as interim, completes S11 expanded corpus triage, and completes S12 external research / production-cycle reconciliation. |
| R035 | still not validated | No git-lex evidence provides independent law-nexus profile-specific proof. |
| R037 | still not validated | No git-lex evidence proves FalkorDB ingest/runtime proof. |
| R038 | still not validated | No git-lex evidence proves independent LegalGraph proof review. |
| S05 ACP-native decision | retained/refined | Retained as final M051 posture after S12; refined to acknowledge adapter-later scope and ecosystem breadth. |
| M048 adoption decision | retained with corrections | ACP-native-first retained; runtime-smoke status corrected by S10; final production adoption still blocked. |

### Decision update recommendation

No existing decision needs to be overwritten. The S12 final reconciliation should be treated as the current superseding synthesis for M051. Future work should create a new implementation/adoption decision only if it actually builds an ACP-native projection implementation or an isolated git-lex adapter proof.

### T04 conclusion

M048's conservative architecture boundary was mostly correct. M051/S10 corrected the runtime availability status from unavailable to bounded local runtime-smoke-backed, and S11/S12 expanded the production-cycle scope. The final M051 decision remains conservative: ACP-native authority is retained, selected semantic patterns are absorbed, git-lex runtime/plugin/code-graph paths are adapter-later or research-only, and unsafe claims remain blocked.

## T03: ACP production-cycle dispositions

### Final disposition summary

| Disposition | Meaning in M051 | Capability / repo family |
|---|---|---|
| adopt now | Safe to use immediately as current ACP planning/source guidance, not runtime backend. | S12 final reconciliation artifact; updated git-lex skill guidance; R058/R059 knowledge-delta method. |
| ACP-native absorb | Incorporate the concept into ACP-owned implementation/proof surfaces. | Source records, lifecycle states, proof gates, evidence anchors, health findings, derived projection boundary, selected `lex:`/`git:`/`fm:` vocabulary patterns, S08 audit concepts, no-main-repo guard. |
| adapter-later | Potentially useful behind an isolated adapter after proof gates. | git-lex runtime, Oxigraph sync/query, history graphs, `history-verify`, `squad-explorer`, `subtext-mcp`, `git-lex-plugins`, Claude/GSD-like agent CLI session/export kits, autoknow ingestion, selected kit mappings. |
| research-only | Keep as architecture context or future design input. | `code-ontology-spec`, `lex-o-seed`, `forx`, `repolex-forx-tools`, `semanticstate`, lab/collab/familiar kits until deeper proof. |
| blocked | Not allowed until specific missing proof is produced. | production git-lex runtime adoption, main-repo `.lex`, JSON-LD runtime support, negative validation, SPARQL-star user-facing compatibility, binary provenance, wrapper default workflow adoption, R035/R037/R038 validation. |
| reject | Do not use as proof or current architecture input. | Prebuilt subtext binaries as adoption proof; projection-as-source-truth; UI/plugin visualization as authority; empty/noise repos such as `forxq` until content exists. |

### Detailed production-cycle dispositions

| Area | Final M051 disposition | Production-cycle implication | Required proof gate before promotion |
|---|---|---|---|
| ACP source authority | ACP-native absorb | ACP owns source records, lifecycle, proof gates, evidence anchors, and requirement validation. | Existing ACP verifier/tests; future implementation milestone should harden these. |
| Semantic vocabulary | ACP-native absorb | Borrow selected `lex:`, `git:`, `fm:` concepts into ACP projection vocabulary while preserving ACP authority. | Mapping review and verifier checks ensuring projections remain derived. |
| S08 ontology/static projection scaffold | adopt now as planning artifact; ACP-native absorb selectively | Use as seed for next ACP ontology/projection implementation, not source truth. | RDF/SPARQL/JSON-LD/SHACL engine proof before stronger semantic-web claims. |
| git-lex runtime core | adapter-later | Build optional isolated adapter spike only after reproducible source-build and repository-state gates. | pinned source build manifest, binary identity, isolated init/sync/query/validate, cleanup/rollback, no-main `.lex`. |
| `.lex` repository state | blocked for main repo | Main law-nexus checkout must stay `.lex`-free. | explicit future adoption decision, isolated proof, rollback plan, ownership contract. |
| base/squad/soul/autoknow kits | adapter-later / research-only by kit | Use as vocabulary/domain prior art; possibly adapter fixtures. | Per-kit source review and isolated runtime proof before mapping into ACP workflows. |
| familiar/lab/collab/claude-code/claude-export kits | research-only | Useful for agent memory, research, collaboration, and agent CLI/GSD-like session modeling. | Inspect ontology/content and privacy/provenance implications before adoption. |
| subtext-mcp | adapter-later | Candidate agent CLI/MCP bridge; informs plugin/daemon/process/privacy concerns. | license resolution, binary provenance, broker/SQLite/process failure tests, no-main `.lex`, portable GSD/pi mapping. |
| squad-explorer | adapter-later / research-only | Candidate visualization/SPARQL UX; must remain non-authoritative. | source review, auth/local exposure policy, query provenance, UI non-authority markers. |
| git-lex-plugins | research-only / adapter-later | Candidate plugin distribution surface for agent CLI workflows. | manifest/source review, supply-chain policy, install/permission boundaries. |
| code-ontology-spec | research-only | Candidate architecture input for future ACP/code graph ontology. | spec review and mapping to ACP source/proof model. |
| forx / repolex-forx-tools | research-only | Candidate code/extraction workflow inputs for future code graph or ingestion pipeline work. | deep source review, isolated execution, data/output contracts. |
| semanticstate | research-only | Candidate code-to-ontology design idea. | source review, runtime examples, compatibility with ACP authority model. |
| lex-o-seed | research-only | Candidate branch-native ontology governance model. | source/content review and ACP governance design comparison. |
| JSON-LD | blocked for git-lex runtime support; allowed as ACP-native proposed static interchange | Do not claim git-lex JSON-LD support. | JSON-LD import/export/expansion/compaction roundtrip proof. |
| SHACL negative validation | blocked | Do not rely on git-lex validation for proof gates yet. | shape-specific invalid fixture causing expected non-zero failure. |
| SPARQL-star | blocked | Do not advertise user-facing SPARQL-star compatibility. | explicit user-facing query fixture in isolated runtime. |
| Binary/provenance | blocked for adoption | Do not use prebuilt plugin binaries as ACP proof. | manifest linking binary hash to full source commit, workflow, environment, Cargo.lock, artifact digest, signer/attestation. |
| R035/R037/R038 | still blocked / not validated | No requirement status promotion from git-lex corpus. | independent law-nexus profile-specific proof for each requirement. |

### Production-cycle architecture implications

#### Source ingestion

ACP should keep source ingestion ACP-native. git-lex can inform document typing, frontmatter extraction, provenance vocabulary, and graph projection, but ACP ingestion must remain deterministic and testable without git-lex runtime.

#### Proof gates

Proof gates must remain ACP-owned records. git-lex validation, SHACL, history graphs, or SPARQL queries may become adapter-later diagnostic inputs only after positive and negative proof fixtures exist.

#### Registry/verifier integration

Next implementation work should extend ACP verifier checks for:

- non-authoritative projection markers;
- forbidden evidence anchors;
- blocked runtime-adoption states;
- R035/R037/R038 non-validation boundaries;
- git-lex adapter outputs marked as derived diagnostics;
- stale projection detection.

#### Runtime operations

Any git-lex adapter must be isolated, explicit, and observable:

- no main-repo `.lex` by default;
- scratch workspace or dedicated worktree only;
- command logs and binary identity recorded;
- cleanup/rollback verified;
- failed sync/query/validate becomes a health finding, not silent fallback.

#### Rollback

Because git-lex can create repository-local state and graph stores, rollback policy must be designed before adoption:

- isolate generated `.lex` state;
- keep ACP source records readable without git-lex;
- ensure removing adapter artifacts does not remove source truth;
- never make Oxigraph store the only copy of ACP facts.

#### Supply-chain policy

Production-cycle use requires:

- license review for cloned repos with missing LICENSE;
- no prebuilt binaries as proof without provenance manifest;
- direct source builds with locked dependencies;
- CI checks for build, tests, formatting/linting where applicable;
- explicit policy for plugin installs, local daemons, SQLite state, browser-open behavior, and network exposure.

#### Developer workflow

The safest workflow starts as docs-as-code / research / decision / coordination support:

1. ACP-native source record remains primary.
2. Projection/artifact generation is deterministic.
3. git-lex adapter runs only as optional research diagnostic.
4. UI/plugin/agent CLI surfaces are opt-in and non-authoritative.
5. S12 final artifact seeds a future implementation milestone rather than merging runtime adoption now.

#### Architecture correction candidates

S12 identifies these candidates for later milestones:

- ACP ontology/projection implementation from S08 scaffold.
- Optional git-lex isolated adapter spike.
- Agent CLI/GSD-like session capture/export proof inspired by Claude-oriented kits.
- Code graph/source-analysis research track using `code-ontology-spec`, `forx`, `repolex-forx-tools`, and `semanticstate` as prior art.
- Branch-native ontology governance comparison using `lex-o-seed`.
- Production supply-chain/trust policy for git-lex plugins and binaries.

### T03 conclusion

The final M051 production-cycle disposition is conservative: **adopt ACP-native concepts now, absorb selected semantic vocabulary and proof-boundary patterns, keep git-lex runtime and agent CLI integration adapter-later, keep code graph and ontology evolution research-only, and keep production adoption / main `.lex` / JSON-LD runtime / negative validation / SPARQL-star / binary provenance / R035-R037-R038 validation blocked.**

## T02: Reconcile corpus and external claims

### Conflict matrix

| Claim / theme | External research signal | S11 corpus evidence | Prior M051 evidence | Reconciliation | Result |
|---|---|---|---|---|---|
| ACP authority | Git-lex is powerful semantic substrate. | Expanded corpus still contains no ACP source-authority implementation for law-nexus. | S05/S07 require ACP-native authority. | Semantic substrate can inform ACP, but does not replace ACP source records/proof gates. | retained |
| Runtime availability | Git-lex core is real Rust CLI/server platform. | `git-lex` already pinned/indexed; S10 built debug binaries. | S10 runtime-smoke gate passed. | Runtime is no longer blocked for local smoke, but remains blocked for production adoption. | upgraded but still blocked for production |
| Ecosystem breadth | 30 public repos, many kits and adjacent tools. | S11 cloned/pinned selected repos and indexed selected code repos. | S06/S10 only covered base/squad/soul/autoknow/subtext. | Corpus scope expanded; final decisions must consider kits, UX/plugin, code graph, extraction tooling, ontology evolution. | refined |
| Agent CLI/Claude framing | Claude Code is prominent integration target. | Claude-oriented repos cloned: `git-lex-kit-claude-code`, `git-lex-kit-claude-export`; subtext/plugins remain relevant. | User clarified Claude means agent CLI/harness analogous to GSD/pi. | Treat Claude-specific artifacts as concrete agent-CLI evidence, not vendor-only noise. | refined |
| UX/plugin surfaces | `subtext-mcp`, `squad-explorer`, `git-lex-plugins` matter. | `squad-explorer` indexed; `git-lex-plugins` cloned but code not yet found; `subtext-mcp` already indexed. | S09 classified subtext as interaction model. | UX/plugin path is relevant for adapter-later workflow, but not semantic correctness or proof. | confirmed/refined |
| Code graph direction | `code-ontology-spec`, `forx`, `repolex-forx-tools`, `semanticstate`, `stack-graphs`, `multilspy` point to code KG. | `forx`, `repolex-forx-tools`, `semanticstate` indexed; spec cloned; stack-graphs/multilspy deferred. | Earlier M051 did not deeply cover code-KG side. | This is a real architecture-correction candidate for future ACP/code graph work, but not current git-lex adoption proof. | new-question/refined |
| Ontology evolution | `lex-o-seed` branch/merge-base model may matter. | `lex-o-seed` cloned/pinned. | S08 prototype has static ontology scaffold only. | Branch-native ontology governance is candidate future design input; needs source review. | new-question |
| Semantic discipline vs DevSecOps maturity | Report says semantics are stronger than engineering guardrails. | S11 found many missing LICENSE files and early-stage repos. | S09 supply-chain/binary trust concerns. | Production-cycle adoption must be gated by CI/security/license/provenance policies. | refined/confirmed |
| Empty/noise repos | Some repos are empty or irrelevant. | `forxq` cloned empty; canon/obsidian deferred as reported empty. | N/A | Keep stale/noise classification; do not overfit architecture to empty concepts. | confirmed |
| JSON-LD support | Report mentions semantic web stack broadly. | No S11 repo upgraded JSON-LD runtime proof. | S08 sample static only; S10 JSON-LD unproven. | JSON-LD remains blocked for runtime/git-lex support; ACP-native static context remains allowed as proposed. | still blocked |
| Negative validation | Report praises SHACL/semantic discipline. | No S11 repo proves negative validation. | S10 malformed fixture did not fail. | Negative validation remains blocked pending shape-specific invalid fixture. | still blocked |
| SPARQL-star / RDF-star | Report discusses triple-term provenance/history. | No new explicit user-facing SPARQL-star proof. | S10 source-bounded but runtime-unproven. | SPARQL-star user-facing compatibility remains blocked. | still blocked |
| Binary provenance | Report notes build/binary sync. | S11 did not add provenance manifest. | S09 found missing binary provenance manifest. | Prebuilt binary adoption proof remains rejected/blocked. | still blocked |
| R035/R037/R038 | Report is generic git-lex ecosystem research. | No law-nexus profile-specific legal/FalkorDB/parser proof. | S05/S06/S08/S10 non-validation boundary. | Requirements remain unvalidated by git-lex corpus evidence. | still blocked |

### Knowledge delta ledger beyond KD01-KD08

| ID | Type | Prior assumption or open question | Evidence anchor | Proof class | Updated conclusion | Remaining boundary | Downstream implication |
|---|---|---|---|---|---|---|---|
| KD09 | newly verified | The additional git-lex ecosystem repo scope was unknown after S07. | `tmp/deep-research-report.md`; `prd/architecture/acp/M051-S11-GIT-LEX-EXPANDED-CORPUS.md` | external research + local clone/pin | The ecosystem corpus includes 30 candidate repos; selected high-priority repos were cloned/pinned. | Descriptions remain provisional until source review per repo. | S12 final disposition must consider kits, UX/plugin, code graph, extraction, and ontology evolution, not only `git-lex` core. |
| KD10 | refined | Claude-oriented repos might be vendor-specific noise. | user instruction; `prd/architecture/acp/M051-S11-GIT-LEX-EXPANDED-CORPUS.md` | human decision + corpus evidence | Claude/Claude Code repos are concrete agent CLI/harness evidence analogous to GSD/pi. | Portability still requires source/runtime proof. | Treat `subtext-mcp`, plugins, and Claude kits as adapter/UX candidates. |
| KD11 | newly verified | Code graph side of Repolex was only a research hint. | `code-ontology-spec`, `forx`, `repolex-forx-tools`, `semanticstate` clone/index anchors in S11 | local source + GitNexus source-navigation evidence | Code ontology/extraction/semanticstate repos exist and are query-addressable where code is present. | No ACP code-graph implementation proof. | Add future architecture-correction candidate for code graph/source analysis integration. |
| KD12 | refined | Production-cycle risks were mostly binary/supply-chain focused. | `tmp/deep-research-report.md`; S09; S11 missing LICENSE and plugin/UX corpus | external research + supply-chain/source inventory | Production-cycle review must include CI/security policy, license gaps, plugin distribution, daemon/process UX, ontology governance, and rollback, not only binaries. | Specific guardrails still need implementation tasks. | S12 dispositions must include operational guardrails. |
| KD13 | rechecked | Repo existence might justify integration direction. | S11 clone/pin and classification matrix | local corpus evidence | Repository existence is corpus evidence only; several repos are docs/ontology-only, empty, or noise. | Deep source review still needed before architecture changes. | Keep final dispositions conservative and evidence-class-specific. |
| KD14 | rechecked | JSON-LD, negative validation, SPARQL-star, binary provenance might be upgraded by expanded corpus. | S11 corpus; S10/S09/S08 boundaries | reconciliation | No S11/GPT Pro claim upgrades these proof gaps. | Need dedicated runtime/source proofs. | Keep these as blocked in final dispositions. |

### T02 conclusion

The expanded corpus and GPT Pro research refine the shape of the production-cycle review but do not contradict the core M051 safety boundary. The final disposition should be broader than S05 because it must include agent CLI integration, code graph direction, ontology governance, and DevSecOps guardrails; however, the disposition remains conservative because no new evidence validates production adoption, `.lex` mutation, JSON-LD runtime support, negative validation, SPARQL-star compatibility, binary provenance, or R035/R037/R038.

## T01: GPT Pro / external research ingest

### Input package

User-provided research package:

```text
tmp/deep-research-report.md
```

S11 expanded corpus package:

```text
prd/architecture/acp/M051-S11-GIT-LEX-EXPANDED-CORPUS.md
```

Current M051 evidence baseline:

```text
prd/architecture/acp/M051-S05-GIT-LEX-ACP-INTEGRATION-DECISION.md
prd/architecture/acp/M051-S06-GIT-LEX-SKILL-VALIDATION.md
prd/architecture/acp/M051-S07-GIT-LEX-INTERIM-SYNTHESIS.md
prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md
prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md
prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md
```

### Authority rule for external research

The GPT Pro/deep research report is useful research input and citation guidance, but it is **not proof by itself**.

A claim can change ACP conclusions only when it is reconciled with at least one of:

1. tracked law-nexus source/PRD/GSD/ADR/test/runtime evidence;
2. local pinned vendor repository evidence under `/root/vendor-source`;
3. GitNexus-indexed source/code analysis;
4. reproducible isolated runtime proof;
5. upstream source/docs/issues/releases with stable URLs and dates.

External model prose, repo popularity, README summaries, stars, issue counts, and diagrams are not enough to approve git-lex adoption, production-cycle fitness, `.lex` mutation, or LegalGraph requirement validation.

## Normalized external research claims

| Claim ID | Claim | Source/citation | Evidence type | Relation to M051 evidence | Confidence | Conflict status | Required verification before acceptance |
|---|---|---|---|---|---|---|---|
| GP01 | Repolex AI has about 30 public repositories and is a young ecosystem around `git-lex`. | `tmp/deep-research-report.md`, portfolio table | external research + repo list | confirms S11 corpus expansion need | medium | confirmed by S11 candidate corpus | S11 clone/pin already sampled high-priority repos; S12 can use this as corpus-scope context, not proof. |
| GP02 | `git-lex` is a git-native knowledge graph substrate over Markdown/frontmatter, Oxigraph, provenance, named graphs, and typed semantic kits. | `tmp/deep-research-report.md`, git-lex product/code sections | external research + prior source/runtime evidence | confirms S05/S10 framing | high | confirmed/refined | Already supported by S02/S03/S05/S10; keep ACP-native authority boundary. |
| GP03 | The ecosystem's semantic discipline is stronger than its engineering/DevSecOps maturity. | `tmp/deep-research-report.md`, CI/security sections | external research | refines S09 supply-chain concern | medium | refined | Verify against upstream workflows/security docs if used as final operational claim. |
| GP04 | Public `git-lex` CI focuses on build/artifacts and binary sync to `subtext-mcp`, while tests/clippy/fmt/SAST/CODEOWNERS/security policy are not evident in the public view. | `tmp/deep-research-report.md`, CI/security discussion | external research | refines S09 production-fitness boundary | medium | new-question/refined | Inspect upstream `.github`, security policy, and current branch before finalizing production-cycle policy. |
| GP05 | The strongest current use case is semantic layer for requirements, decisions, research, onboarding, and multi-agent coordination rather than critical production code governance. | `tmp/deep-research-report.md`, executive/practical conclusion | external research + synthesis | aligns with S05/S07 interim posture | medium | confirmed/refined | S12 can classify as ACP-native absorb/research-only unless source/runtime evidence suggests stronger adoption. |
| GP06 | The ecosystem includes important kits beyond base/squad/soul/autoknow: familiar, lab, collab, claude-code, claude-export, and others. | `tmp/deep-research-report.md`, portfolio table | external research + S11 clone/pin | expands S06/S10 KD05 | high | confirmed by S11 clone/pin | Inspect each kit's ontology/content before using specific vocabulary claims. |
| GP07 | Claude Code oriented repositories should be treated as an agent CLI/harness integration direction. | user instruction + `tmp/deep-research-report.md` repo list | user interpretation + external research | refines S11/S07 framing | high | confirmed/refined | Map to generic agent CLI/GSD-like concerns; do not treat as vendor-only or proof. |
| GP08 | `squad-explorer`, `git-lex-plugins`, and `subtext-mcp` represent UX/plugin/MCP surfaces around git-lex. | `tmp/deep-research-report.md`; S11 clone/index | external research + GitNexus source-navigation evidence | refines S09/S11 UX/process surface | medium | confirmed/refined | Deep source review before any integration; preserve non-authoritative UI boundary. |
| GP09 | `code-ontology-spec`, `forx`, `forxq`, `repolex-forx-tools`, `semanticstate`, `stack-graphs`, and `multilspy` point toward code knowledge graph and code-analysis directions. | `tmp/deep-research-report.md`; S11 clone/index for subset | external research + GitNexus source-navigation evidence | expands ACP architecture-correction candidates | medium | refined/new-question | Inspect code/spec scope before architecture corrections; `forxq` is empty in S11 clone. |
| GP10 | `lex-o-seed` suggests branch-native ontology evolution via shared genesis and merge-base bridging. | `tmp/deep-research-report.md`; S11 clone/pin | external research + local source anchor | expands ontology governance questions | medium | new-question/refined | Inspect repo content before adopting governance pattern. |
| GP11 | Some repos are empty, documentation-only, websites, themes, or likely noise. | `tmp/deep-research-report.md`; S11 T02 clone `forxq` empty | external research + clone evidence | confirms S11 triage need | high for `forxq`; medium generally | confirmed/refined | Keep low-priority/noise classification until direct inspection changes it. |
| GP12 | A practical pilot should start with docs-as-code / requirements / research / coordination, not full replacement of SDLC tooling. | `tmp/deep-research-report.md`, SDLC and integration sections | external research recommendation | aligns with ACP-native-first posture | medium | confirmed/refined | Translate into S12 production-cycle disposition and next milestone backlog. |
| GP13 | Production adoption needs additional guardrails: privacy boundaries, ontology governance, CI checks, history verification, markdown/frontmatter linting, rollback, external exposure/auth controls. | `tmp/deep-research-report.md`, migration checklist | external research recommendation | expands S09/S10 gates | medium | refined/new-question | Convert into production-cycle implications; do not claim implementation exists. |
| GP14 | The ecosystem has low public OSS traction and looks like internal incubation rather than mature OSS product. | `tmp/deep-research-report.md`, executive/portfolio metrics | external research + repo metrics | refines supply-chain/adoption risk | medium | refined | Treat as adoption-risk context, not technical disproof. |
| GP15 | `git-lex` should remain promising but operationally early. | `tmp/deep-research-report.md`, engineering assessment | external research synthesis | aligns with S05/S07/S10 | medium | confirmed/refined | Use as S12 final risk posture unless contradicted by source/runtime evidence. |

## T01 conflict and confidence notes

- No external claim currently contradicts the core M051 boundary that ACP authority remains ACP-native.
- No external claim validates R035, R037, or R038.
- No external claim proves JSON-LD runtime support, negative SHACL validation, SPARQL-star user-facing compatibility, binary provenance, production fitness, or safe main-repo `.lex` mutation.
- The report expands the scope of S12 production-cycle review toward agent CLI integration, code graph architecture, ontology governance, CI/DevSecOps guardrails, and pilot strategy.
- Some claims are citation-rich inside the report, but the local artifact preserves only report-level anchors; S12 should use local clone/GitNexus evidence when making final dispositions.

## T01 conclusion

The GPT Pro/deep research package is available and ingested. It confirms the need for S11/S12, broadens the production-cycle review, and provides candidate claims, but it does not by itself change ACP adoption status. Final reconciliation continues in T02.
