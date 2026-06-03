# M051 S07 Git Lex Interim Synthesis

## Status

Interim checkpoint for `M051-q6ctvc / S07`.

This is **not final** ACP integration or git-lex adoption decision. It summarizes the current evidence from S05, S06, S08, S09, and S10 and prepares the handoff to S11/S12.

R059 changes the milestone boundary: final conclusions about what can be integrated into ACP and the full production cycle must wait until additional git-lex-related repositories are inventoried in S11 and the user's external GPT Pro research is reconciled in S12.

## Executive interim conclusion

Current M051 evidence supports this bounded position:

```text
ACP source authority stays ACP-native.
git-lex is strong semantic and runtime-smoke prior art.
git-lex is not approved as ACP core runtime.
S07 is an interim synthesis, not a final adoption decision.
S11 and S12 are required before final ACP production-cycle disposition.
```

The most important change since S05 is not that S05 was wrong; it is that S05 is now an **interim disposition**. S05 remains the best current ACP integration decision for the already-studied corpus, but it is no longer sufficient to close M051 because the git-lex ecosystem includes additional repositories and the upcoming GPT Pro research may refine or challenge current assumptions.

## Evidence scope consumed

| Slice | Artifact | Current role in S07 |
|---|---|---|
| S05 | `prd/architecture/acp/M051-S05-GIT-LEX-ACP-INTEGRATION-DECISION.md` | Current ACP-native-first integration decision for the studied subset. Now treated as interim, not final milestone closure. |
| S06 | `prd/architecture/acp/M051-S06-GIT-LEX-SKILL-VALIDATION.md` | Validated project-local skill update and R058 knowledge-delta ledger KD01-KD08. |
| S08 | `prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md` | Proposed non-authoritative ACP ontology/static-check scaffold, sample records, SPARQL audit pack, JSON-LD sample, and SHACL layer. |
| S09 | `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` | Supply-chain, binary trust, subtext-mcp interaction model, license/provenance/runtime-surface boundaries. |
| S10 | `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md` | Authoritative current runtime gate evidence: source build, isolated matrix, query semantics, bounded runtime-smoke outcomes. |

## What git-lex currently is for ACP

For ACP, git-lex is currently best classified as:

1. **Semantic prior art**: `lex:`, `git:`, `fm:`, and selected kit vocabularies provide useful vocabulary and modeling patterns.
2. **Runtime-smoke candidate**: source-built debug binaries work on this host and pass bounded isolated matrix checks.
3. **Optional future adapter candidate**: an adapter may become useful after stronger reproducibility, corpus, safety, and production-cycle checks.
4. **Not source authority**: `.lex`, Oxigraph stores, Turtle/SHACL/SPARQL/JSON-LD projections, subtext views, and git-lex runtime output are not ACP source truth by themselves.
5. **Not current production dependency**: M051 has not approved git-lex as core ACP runtime.

## Current evidence classes

| Claim area | Current classification | Evidence | Boundary |
|---|---|---|---|
| ACP-native authority | accepted interim decision | S05 | Final production-cycle disposition waits for S12. |
| `lex:`, `git:`, `fm:` vocabulary | source-reviewed prior art | S03/S05/S08 | Vocabulary shape is not authority. |
| base kit | runtime-smoke + source prior art | S10 | Useful for minimal init/sync/query smoke; not production proof. |
| squad kit | runtime-smoke + domain prior art | S10 | Useful class/shape prior art; should not leak into ACP core by default. |
| soul kit | runtime-smoke + process prior art | S10/S06 | Prompt-handled init and larger class inventory are useful; harness claims remain process evidence. |
| autoknow kit | runtime-smoke + adaptive prior art | S10/S06 | Adaptive shape generation ran in isolation; `_ontology` mutation must not become ACP authority. |
| subtext-mcp | interaction-model evidence | S09 | Not binary provenance, semantic correctness, or ACP integration proof. |
| source-built debug binaries | runtime-smoke-backed | S10 | Production/distribution fitness unproven. |
| prebuilt plugin binaries | hash-identified research-only files | S09 | No machine-verifiable provenance manifest; not adoption proof. |
| S08 ontology prototype | static-check/proposed | S08 | Non-authoritative; no RDF/SPARQL/JSON-LD/SHACL engine proof. |
| SPARQL graph inventory | runtime-smoke-backed after committed sync | S10 | Only in isolated repos and only for proven query shapes. |
| `git-lex list --json` class discovery | runtime-smoke-backed | S10 | Shape-driven discovery, not `owl:Class` graph query. |
| `owl:Class` / `sh:targetClass` graph inventory | expected-empty by default | S10 | Do not use as class inventory unless ontology/shape triples are explicitly loaded. |
| `history-verify` | bounded runtime-smoke-backed | S10/S06 | Isolated proof only; not production or ACP authority. |
| negative validation | unproven | S10/S06 | Malformed fixture did not fail; needs stronger shape-specific invalid fixture. |
| JSON-LD runtime support | unproven | S08/S10 | S08 JSON-LD sample is ACP-native static interchange, not git-lex support proof. |
| SPARQL-star user-facing compatibility | source-bounded but runtime-unproven | S10 | Needs explicit query fixture before claim. |
| R035/R037/R038 validation | not validated | S05/S08/S10/S06 | Requires independent law-nexus profile-specific proof. |

## S05 decision status after R059

S05 remains valid as the current bounded integration decision:

```text
Keep ACP source authority ACP-native.
Use git-lex as source-reviewed semantic prior art and future optional adapter candidate.
Do not adopt git-lex as ACP core runtime.
Do not mutate main-repo .lex.
Do not validate R035/R037/R038 from git-lex evidence.
```

R059 changes S05's finality:

- **Retained**: ACP-native authority, no-main-repo `.lex`, no requirement validation from derived projections, and adapter-later posture.
- **Refined**: runtime availability is no longer blocked in the old M048/S04 sense; S10 opened a bounded source-built debug runtime-smoke gate.
- **Deferred for finality**: production-cycle integration, broader ecosystem fit, and final ACP architecture corrections wait for S11/S12.

## S08 prototype status

S08 created a useful proposed scaffold:

- `prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl`
- `prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.ttl`
- `prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld`
- `prd/architecture/acp/shacl/m051/acp-prototype.shacl.ttl`
- `prd/architecture/acp/sparql/m051/*.rq`
- `scripts/verify-m051-s08-acp-ontology-prototype.py`

Interim meaning:

- The prototype proves that ACP concepts can be represented as a static RDF/OWL/SHACL/SPARQL/JSON-LD-compatible scaffold.
- It proves deterministic static checks over the scaffold are possible.
- It does not prove runtime RDF/SPARQL engine execution, JSON-LD semantic expansion/roundtrip, SHACL engine behavior, OWL entailment, or git-lex adapter fitness.
- It does not validate R035/R037/R038.

## S09 supply-chain and subtext status

S09 established these interim constraints:

- `git-lex` source uses locked Rust dependencies and native surfaces including `oxrocksdb-sys`, RocksDB, libgit2/OpenSSL, Oxigraph, SHACL/RDF crates, Axum/Tokio server dependencies, and tree-sitter parsing.
- `subtext-mcp` is a Bun/TypeScript MCP/plugin wrapper with host-binary symlinks, broker daemon, Bun SQLite database, peer messaging, `start_viz`, and possible browser-open behavior.
- Prebuilt `subtext-mcp` platform binaries are hash-identified but not provenance-proven.
- `subtext-mcp` has no explicit top-level license in the reviewed snapshot.
- Wrapper behavior is useful UX/process evidence, not semantic correctness or ACP proof.

Production-cycle implication: any future integration must explicitly address binary provenance, license/trust policy, daemon/process behavior, local database state, host binary setup, failure modes, and consent boundaries.

## S10 runtime gate status

S10 is the current runtime-status authority for studied git-lex runtime behavior.

Runtime-smoke-backed after S10:

- source-built debug `git-lex` and `git-lex-serve` are available on this host after `clang`/`cmake` remediation;
- `init` works for base, squad, soul, and autoknow in isolated repos;
- committed isolated repos can `sync` into Oxigraph stores;
- named graph inventory works after committed sync;
- `query --json` works for SELECT/ASK;
- `list --json` is the class-discovery surface;
- `.spo` sidecars are emitted;
- `history-verify` passed in corrected committed/synced isolated repos;
- autoknow adaptive shape generation can run in isolation.

Still blocked or unproven after S10:

- production/distribution fitness;
- negative validation behavior;
- JSON-LD import/export;
- explicit user-facing SPARQL-star query compatibility;
- `owl:Class` / `sh:targetClass` graph inventory as default class discovery;
- ACP backend/runtime adoption;
- LegalGraph requirement validation for R035/R037/R038.

## R058 interim knowledge-delta ledger

These entries are carried forward from S06. They are valid for the studied corpus and remain interim until S11/S12 reconciliation.

| ID | Type | Prior assumption or open question | Evidence anchor | Proof class | Updated conclusion | Remaining boundary | Downstream implication |
|---|---|---|---|---|---|---|---|
| KD01 | newly verified | Local git-lex runtime was blocked by missing runnable binary. | `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md#T11` | runtime-smoke | Source-built debug binaries are available on this host after clang/cmake remediation. | Production/distribution fitness unproven. | S11/S12 should separate local source-build smoke from production build policy. |
| KD02 | refined | `git-lex list` and `owl:Class` SPARQL were conflated as class inventory mechanisms. | `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md#T08` | source + runtime-smoke | `list --json` is shape-driven class discovery; `owl:Class`/`sh:targetClass` graph queries are expected-empty by default. | Ontology/shape graph loading unproven unless explicit. | S11/S12 must reject repo claims that rely on `owl:Class` inventory without loading proof. |
| KD03 | newly verified | History equivalence was unproven after initial smoke. | `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md#T09` | runtime-smoke | `history-verify` passed in corrected committed/synced isolated base/squad/soul/autoknow repos. | Isolated smoke only. | S12 may consider history verification as adapter-later proof target, not ACP authority. |
| KD04 | refined | Negative validation was open. | `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md#T09` | runtime negative attempt | Malformed negative fixture did not fail validation; negative validation remains unproven. | Needs shape-specific invalid fixture and non-zero validate result. | Negative validation must be a S11/S12 blocker for any validation claim. |
| KD05 | newly verified | Soul/autoknow kit scope was absent from the skill references. | `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md#T07` | source inventory + runtime-smoke | soul/autoknow are local vendor sources and initialized in isolated runtime matrix; autoknow built adaptive shapes. | Harness/subagent and adaptive mutation claims are not ACP authority. | S11 should search for more kit repos and classify each kit's ACP relevance. |
| KD06 | newly verified | ACP ontology prototype did not exist before S08. | `prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md` | static-check | S08 created proposed ontology, samples, JSON-LD sample, SPARQL audit pack, SHACL layer, and verifier. | Non-authoritative; no RDF/SPARQL/JSON-LD/SHACL engine proof. | S12 should decide whether this becomes implementation seed or remains research scaffold. |
| KD07 | rechecked | Supply-chain trust of subtext bundled binaries needed explicit policy. | `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` | source/supply-chain review | subtext-mcp is interaction-model evidence; bundled binaries are not adoption proof. | Missing subtext license and machine-verifiable binary provenance. | S11/S12 must include plugin/wrapper repos in corpus and trust review where relevant. |
| KD08 | rechecked | R035/R037/R038 might be accidentally upgraded by semantic artifacts. | `prd/architecture/acp/M051-S05-GIT-LEX-ACP-INTEGRATION-DECISION.md`; `prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md`; `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md` | decision + static-check + runtime-smoke boundary | M051 evidence does not validate R035/R037/R038. | Profile-specific proof remains required. | S12 must preserve non-validation unless independent proof exists. |

## Current blocked claims

Do not claim these at S07:

- git-lex is adopted as ACP core runtime;
- `.lex` may be created or mutated in `/root/law-nexus`;
- subtext-mcp proves git-lex semantic correctness or binary provenance;
- prebuilt plugin binaries are suitable adoption proof;
- S08 JSON-LD sample proves git-lex JSON-LD support;
- S08 SHACL file proves SHACL engine validation;
- SPARQL-star compatibility is proven;
- negative validation is proven;
- additional git-lex repositories are irrelevant before S11 triage;
- GPT Pro research confirms anything before S12 reconciliation;
- R035, R037, or R038 are validated by ACP/git-lex/projection evidence.

## R059 impact on roadmap

R059 requires M051 to continue past this interim checkpoint:

1. S07 records the current state and open research plan.
2. S11 discovers, clones, pins, indexes, and classifies additional git-lex-related repositories.
3. S12 reconciles S11 with the user's GPT Pro research and produces the final M051 production-cycle decision.

This means the old S07 “final synthesis” expectation is superseded. The new S07 output is deliberately an interim artifact.

## Handoff to S11

S11 should start from these questions:

1. Which additional git-lex-related repositories exist beyond the already-studied `git-lex`, `git-lex-kit-base`, `git-lex-kit-squad`, `git-lex-kit-soul`, `git-lex-kit-autoknow`, and `subtext-mcp`?
2. Which are core runtime, kits, MCP/plugin surfaces, demos/docs, adapters, or noise?
3. Which need local cloning and commit pins under `/root/vendor-source`?
4. Which code repositories need GitNexus indexing?
5. Which current KD entries do they confirm, refine, contradict, or leave unchanged?
6. Do any repos change production-cycle risk around runtime operations, repository state, supply chain, provenance, proof gates, or developer workflow?

Safety rules for S11:

- Do not mutate `/root/law-nexus/.lex`.
- Clone into `/root/vendor-source` only.
- Pin commits and record remotes.
- Treat repo existence as source/corpus evidence, not proof of ACP fitness.
- Use GitNexus for code repos selected for deeper analysis.

## Handoff to S12

S12 should reconcile three evidence streams:

1. current M051 evidence and KD01-KD08;
2. expanded S11 repository corpus;
3. user-provided GPT Pro research.

For each material claim, S12 should classify it as:

- confirmed;
- refined;
- contradicted;
- superseded;
- still blocked;
- out-of-scope.

Then S12 should produce the actual production-cycle disposition:

- adopt now;
- ACP-native absorb;
- adapter-later;
- research-only;
- blocked;
- reject.

## GPT Pro external research intake contract for S12

The user's GPT Pro research package is expected to be valuable, but it is research input, not proof by itself. S12 must reconcile it against tracked repository/source/runtime evidence and ACP authority rules before changing any conclusion.

### Expected input format

When the GPT Pro research arrives, S12 should ask for or normalize it into this structure:

| Field | Meaning |
|---|---|
| Claim ID | Stable row identifier assigned by S12 if the research does not provide one. |
| Claim text | The concrete statement being made. |
| Source/citation | URL, repo, file path, snippet, or other citation supplied by the research. |
| Evidence type | source, runtime, docs, issue, release, benchmark, inference, opinion, unknown. |
| Relevance | ACP architecture, runtime adapter, production cycle, supply chain, UX/MCP, ontology/semantic kit, or out-of-scope. |
| Relationship to M051 | confirms, contradicts, refines, expands, duplicates, or unrelated. |
| Required verification | What S12/S11 would need to inspect or run before accepting it. |
| Provisional confidence | high/medium/low based on citation quality, not model confidence. |

If the package is prose-only, S12 should extract atomic claims before evaluating them. If it lacks citations or source anchors, mark claims as `research input without proof anchor` and do not upgrade ACP conclusions from them.

### Citation and evidence handling

S12 should prefer this evidence order:

1. Tracked law-nexus source/PRD/GSD/ADR/test/runtime evidence.
2. Local pinned vendor repositories under `/root/vendor-source` with commit anchors.
3. GitNexus-indexed source/code analysis.
4. Reproducible isolated runtime proof with command outputs.
5. Upstream release/issues/docs with URLs and dates.
6. GPT Pro analysis as a guide to what to inspect, not as authority.

External research can propose a conclusion, but acceptance requires at least one concrete evidence anchor from levels 1-5 or an explicit decision to keep the conclusion as unverified/open.

### Conflict-resolution rules

For each GPT Pro claim, S12 should classify the result as:

| Classification | Meaning | Action |
|---|---|---|
| confirmed | The claim matches tracked source/runtime evidence. | May update final synthesis with anchor. |
| contradicted | The claim conflicts with tracked evidence. | Preserve tracked evidence, record contradiction, inspect if material. |
| refined | The claim improves wording/scope without changing the boundary. | Update wording and knowledge-delta ledger. |
| new-question | The claim identifies a plausible but unverified area. | Add S11/S12 proof task or future backlog item. |
| out-of-scope | The claim is unrelated to ACP/git-lex production decision. | Record and exclude. |
| insufficient-anchor | The claim has no usable citation/evidence. | Treat as research lead only. |

Tracked source/runtime evidence wins over model prose. If GPT Pro contradicts S10 runtime smoke or S09 supply-chain boundaries, S12 should inspect the cited source or add a targeted proof task rather than silently accepting either side.

### Authority boundary

GPT Pro research must not directly:

- approve git-lex as ACP core runtime;
- validate R035/R037/R038;
- approve main-repo `.lex` mutation;
- prove binary provenance;
- prove JSON-LD, SHACL engine, SPARQL-star, or production fitness;
- override ACP source authority or proof-gate requirements.

It may:

- identify missing repositories for S11;
- point to upstream docs/issues/releases;
- suggest architecture risks or integration paths;
- propose production-cycle questions;
- refine the final disposition taxonomy for S12.

### Required S12 output

S12 should include a GPT Pro reconciliation table with:

1. claim ID;
2. source/citation or missing-anchor marker;
3. classification: confirmed, contradicted, refined, new-question, out-of-scope, or insufficient-anchor;
4. evidence anchor used for verification;
5. impact on R058/R059 knowledge delta;
6. impact on final disposition: adopt now, ACP-native absorb, adapter-later, research-only, blocked, or reject.

## Expanded repository intake plan for S11

S11 should treat repository discovery as corpus construction, not proof. A repository appearing in search results or in the `repolex-ai` ecosystem is only a candidate evidence source until it is cloned, commit-pinned, classified, and reconciled with source/runtime evidence.

### Discovery sources

S11 should discover additional git-lex-related repositories from these sources, in order:

1. Upstream organization/user pages for `repolex-ai` and repositories linked from current READMEs.
2. Existing local checkouts in `/root/vendor-source`, including README links, workflow references, package/plugin metadata, and kit manifests.
3. `git-lex` and kit documentation references to companion repos, adapters, examples, or plugins.
4. `subtext-mcp` package/plugin metadata and workflow references.
5. Web search only where upstream/local references are insufficient.
6. User-provided GPT Pro research pointers, but only as candidate leads until S12 reconciliation.

### Candidate metadata schema

For every candidate repository, S11 should record:

| Field | Required meaning |
|---|---|
| URL | Canonical remote URL. |
| Owner/name | Repository owner and short name. |
| Discovery source | README, workflow, package metadata, org listing, web search, GPT Pro lead, or user-provided. |
| Suspected role | core runtime, kit, MCP/plugin, docs/demo, adapter, workflow/tooling, abandoned/noise. |
| Priority | high, medium, low, or reject-before-clone. |
| Reason for priority | Why this repo might affect ACP or why it likely does not. |
| Clone decision | clone now, defer, reject, already present. |
| Local path | `/root/vendor-source/<repo-name>` if cloned. |
| Commit | Full commit SHA after clone. |
| Default branch | Branch observed at clone time. |
| License/README status | Present/missing/unclear. |
| GitNexus action | index, defer indexing, non-code/no index, already indexed. |
| Evidence class | source-only, runtime candidate, supply-chain evidence, UX/process evidence, documentation-only, noise. |
| ACP claim impact | confirm, refine, contradict, unchanged, new question, or out-of-scope. |

### Clone and pin rules

- Clone selected repositories only under `/root/vendor-source`.
- Record full commit hashes, remotes, and default branch names immediately after clone.
- Do not run install scripts, hooks, daemons, plugin activation, or repo-specific setup during clone/pin unless a later task explicitly justifies it.
- Do not create or mutate `/root/law-nexus/.lex`.
- Treat `/root/vendor-source` checkouts as external reference sources, not law-nexus source truth.
- Prefer read-only inspection first; runtime checks must happen only in isolated `/tmp` workspaces.

### GitNexus indexing rules

S11 should index a repository with GitNexus when it contains code whose control flow or implementation semantics could affect ACP decisions:

- core Rust/TypeScript/Python runtime code;
- MCP/plugin wrapper code;
- extractor or adapter code;
- operational tooling likely to run in workflows;
- non-trivial kit generators or adaptive ontology code.

S11 may defer GitNexus indexing when the repository is:

- ontology-only with small Turtle/YAML/Markdown content;
- documentation/demo-only;
- abandoned/noise after README inspection;
- too large or unsuitable, with explicit reason recorded.

For each indexed repo, S11 should record the GitNexus repo name, indexing command used, node/edge summary when available, and at least one query/context sanity check. In this repository, prefer direct `gitnexus analyze` where applicable; do not assume `npx gitnexus analyze` works without a `package.json`.

### Relevance classification taxonomy

| Classification | Meaning | Default ACP implication |
|---|---|---|
| core runtime | Implements git-lex CLI/server/store/sync/query behavior. | May refine runtime/adoption gates. |
| kit | Provides semantic kit ontology, shapes, prompts, content, or generated structures. | May refine vocabulary/prior-art and class-discovery assumptions. |
| MCP/plugin | Wraps git-lex for agents, UI, local services, hooks, binaries, or UX. | May refine operational/supply-chain/UX boundaries. |
| docs/demo | Shows expected workflows without authoritative implementation. | Documentation-only unless corroborated. |
| adapter | Bridges git-lex to another tool or workflow. | Candidate for adapter-later design, not proof. |
| workflow/tooling | Builds, syncs, packages, or deploys git-lex artifacts. | May affect reproducibility/supply-chain policy. |
| abandoned/noise | Irrelevant, stale, duplicate, or unrelated. | Record and exclude from final ACP decision. |

### S11 non-proof rules

- Repo existence is not proof.
- README claims are not proof without source/runtime corroboration.
- A kit ontology is vocabulary evidence, not ACP authority.
- A plugin is UX/process evidence, not semantic correctness proof.
- A binary artifact is not provenance proof without a manifest binding it to source commit, workflow, build environment, and digest.
- A successful isolated runtime smoke is not production fitness.
- No S11 repository can validate R035/R037/R038 without independent law-nexus profile-specific proof.

### Output expected from S11

S11 should produce `prd/architecture/acp/M051-S11-GIT-LEX-EXPANDED-CORPUS.md` with:

1. candidate repository list;
2. cloned repository ledger;
3. GitNexus indexing ledger;
4. relevance classification matrix;
5. repo-to-current-claim impact matrix;
6. open questions for S12 and GPT Pro reconciliation;
7. no-main-repo `.lex` safety result.

## Interim safety checks and handoff status

S07/T04 ran fresh checks after T02/T03 edits and before closing S07.

### Verification evidence

Command anchor:

```text
.gsd/exec/d1079bfd-ebb3-4de4-a636-9356a2ddbb8b.stdout
```

Observed results:

```text
no-main-repo .lex: pass (`no .lex in main repo`)
git diff --check: pass
S08 verifier: status=ok failure_count=0
architecture verifier: status=ok failure_count=0
R059 and S11/S12 roadmap: present
S07 artifact contracts: present
```

GitNexus change detection:

```text
gitnexus_detect_changes({repo:"law-nexus", scope:"all"})
risk_level: none
message: No changes detected.
changed_symbols: []
affected_processes: []
```

### Caveats preserved for S11/S12

- This S07 artifact is not final and must not be used as an adoption decision.
- S11 still needs to discover and triage additional git-lex-related repositories.
- S12 still needs to reconcile S11 with the user's GPT Pro research.
- No final production-cycle architecture correction is approved by S07.
- No R035/R037/R038 validation is produced by S07.
- No main-repo `.lex` mutation is allowed before a future explicit adoption decision.
- GitNexus reindexing in this repository should use direct `gitnexus analyze`; do not assume `npx gitnexus analyze` works without `package.json`.

### Next-step handoff

S11 should begin with the `Expanded repository intake plan for S11` section above and produce `prd/architecture/acp/M051-S11-GIT-LEX-EXPANDED-CORPUS.md`. S12 should begin with the `GPT Pro external research intake contract for S12` section above and produce `prd/architecture/acp/M051-S12-GIT-LEX-FINAL-RECONCILIATION.md` after S11 and the external research package are available.

## T01 conclusion

S07/T01 establishes the interim synthesis required by R059. Current evidence strongly supports ACP-native authority with git-lex as semantic prior art and bounded runtime-smoke adapter candidate, but it does not close final ACP integration or production-cycle decisions. The next required work is S11 expanded repository corpus triage followed by S12 external research reconciliation and final production-cycle decision.
