# M051 S11 Git Lex Expanded Corpus

## Status

In progress for `M051-q6ctvc / S11`.

This artifact inventories additional git-lex-related repositories for later clone/pin/index/classification. It is a corpus-discovery artifact, not an ACP adoption decision and not runtime proof.

## Source input for T01

User-provided research report:

```text
tmp/deep-research-report.md
```

Evidence boundary:

- The report is a discovery lead and external research input.
- Repository existence is not proof.
- Descriptions, star counts, language, and issue counts from the report remain unverified until S11 T02/T03 clone/pin/index checks or direct upstream inspection.
- No repository listed here validates ACP adoption, git-lex production fitness, main-repo `.lex` mutation, JSON-LD/SHACL/SPARQL-star support, or R035/R037/R038.

## Claude-oriented repository interpretation

The git-lex ecosystem is currently oriented around Claude Code as a concrete agent CLI/harness. For ACP/GSD analysis, treat `Claude`, `Claude Code`, Claude plugins, and Claude session-export references as an implementation target analogous to GSD/pi rather than as narrow vendor-only noise.

Implications for S11/S12:

- `subtext-mcp`, `git-lex-plugins`, `git-lex-kit-claude-code`, and `git-lex-kit-claude-export` are relevant agent-CLI integration evidence.
- Their Claude-specific names should be mapped to generic concerns: agent session capture, CLI plugin distribution, MCP/tool bridge, local binary discovery, daemon/process management, UX, and privacy boundaries.
- This does not upgrade them to ACP proof. They remain process/UX/runtime-integration evidence until source/runtime proof demonstrates portable behavior and ACP authority boundaries are preserved.

## Candidate repositories

| Priority | Owner/name | URL | Suspected role | Discovery source | Description from report | Clone later | Initial GitNexus action | Initial ACP claim impact |
|---|---|---|---|---|---|---|---|---|
| high | `repolex-ai/git-lex` | `https://github.com/repolex-ai/git-lex` | core runtime | `tmp/deep-research-report.md` | Rust CLI/server, knowledge graph store, sync/query/list/history-verify. Already studied but remains baseline corpus anchor. | already present | already indexed as `git-lex-reference`; recheck if S11 needs fresh index | confirms KD01/KD02/KD03 boundaries; may refine production-cycle gates |
| high | `repolex-ai/git-lex-kit-base` | `https://github.com/repolex-ai/git-lex-kit-base` | kit | `tmp/deep-research-report.md` | Base scaffold, ontology, harness and `www` assets installed into repos. Already studied. | already present | ontology/content; index only if code generator analysis needed | confirms semantic prior-art layer |
| high | `repolex-ai/git-lex-kit-squad` | `https://github.com/repolex-ai/git-lex-kit-squad` | kit | `tmp/deep-research-report.md` | Multi-agent collaboration kit. Already studied enough for S10 runtime smoke. | already present | defer unless deeper kit internals needed | confirms kit/domain prior art; should not leak into ACP core |
| high | `repolex-ai/git-lex-kit-soul` | `https://github.com/repolex-ai/git-lex-kit-soul` | kit | `tmp/deep-research-report.md` | Personal agent memory kit. Already cloned and smoke-tested. | already present | defer unless Python/harness internals matter | confirms KD05; may refine agent-memory boundaries |
| high | `repolex-ai/git-lex-kit-autoknow` | `https://github.com/repolex-ai/git-lex-kit-autoknow` | kit / extraction pipeline | `tmp/deep-research-report.md` | Automated knowledge organization from unstructured sources; adaptive shapes. Already cloned and smoke-tested. | already present | defer or index if adaptive generator code matters | confirms KD05; may refine ingestion/adapter-later scope |
| high | `repolex-ai/subtext-mcp` | `https://github.com/repolex-ai/subtext-mcp` | MCP/plugin | `tmp/deep-research-report.md` | MCP/plugin runtime for Claude Code. Already studied and indexed. | already present | already indexed as `subtext-mcp-reference`; recheck if UX path matters | confirms KD07; may refine MCP/UX production-cycle risk |
| high | `repolex-ai/squad-explorer` | `https://github.com/repolex-ai/squad-explorer` | MCP/UX / web visualization | `tmp/deep-research-report.md` | Web visualization for squad repos: SPARQL + chat + live push. | clone later | index if code contains server/UI query flows | may refine visualization/UX, SPARQL operational risks, and non-authoritative UI boundary |
| high | `repolex-ai/git-lex-plugins` | `https://github.com/repolex-ai/git-lex-plugins` | plugin marketplace | `tmp/deep-research-report.md` | Marketplace of Claude Code plugins for git-lex. | clone later | inspect/index if code/config, defer if metadata-only | may refine plugin distribution/supply-chain policy |
| high | `repolex-ai/code-ontology-spec` | `https://github.com/repolex-ai/code-ontology-spec` | ontology/spec / code KG direction | `tmp/deep-research-report.md` | RDF ontology specification for code knowledge graphs; uses git-lex as storage layer per report. | clone later | likely no index if spec-only; inspect ontology/docs | may refine ACP code-graph roadmap and architecture-correction candidates |
| high | `repolex-ai/lex-o-seed` | `https://github.com/repolex-ai/lex-o-seed` | ontology evolution / workflow-tooling | `tmp/deep-research-report.md` | Seed ontology for git-lex agents with merge-base bridging. | clone later | inspect docs/content; index only if code exists | may refine ontology versioning and branch-native evolution model |
| medium | `repolex-ai/git-lex-kit-familiar` | `https://github.com/repolex-ai/git-lex-kit-familiar` | kit | `tmp/deep-research-report.md` | Soul-extension for observations, co-reasoning, relationship tracking. | clone later | defer/index only if code exists | may refine agent-memory/privacy boundaries |
| medium | `repolex-ai/git-lex-kit-lab` | `https://github.com/repolex-ai/git-lex-kit-lab` | kit | `tmp/deep-research-report.md` | Collaborative research kit. | clone later | defer unless code/generators exist | may refine research/experiment artifact modeling |
| medium | `repolex-ai/git-lex-kit-collab` | `https://github.com/repolex-ai/git-lex-kit-collab` | kit | `tmp/deep-research-report.md` | Lightweight ideation/collaboration kit. | clone later | defer unless code/generators exist | may refine ACP planning/collaboration vocabulary |
| medium | `repolex-ai/git-lex-kit-claude-code` | `https://github.com/repolex-ai/git-lex-kit-claude-code` | kit / agent-session ingestion | `tmp/deep-research-report.md` | Kit for indexing Claude Code sessions. | clone later | inspect/index if extraction/session code exists | may refine agent-session provenance and privacy boundary |
| medium | `repolex-ai/git-lex-kit-claude-export` | `https://github.com/repolex-ai/git-lex-kit-claude-export` | kit / export adapter | `tmp/deep-research-report.md` | Name suggests Claude export kit; public description unclear. | clone later | inspect; index if Python code matters | may refine Claude/export ingestion path or be noise |
| medium | `repolex-ai/forx` | `https://github.com/repolex-ai/forx` | extraction pipeline / adjacent code analysis | `tmp/deep-research-report.md` | Forx tool; public description unclear in report. | clone later | index if code is substantive | may refine code-analysis/extraction roadmap |
| medium | `repolex-ai/forxq` | `https://github.com/repolex-ai/forxq` | query tool / adjacent code analysis | `tmp/deep-research-report.md` | Query tool for Forx. | clone later | inspect/index if code is substantive | may refine query/tooling landscape |
| medium | `repolex-ai/repolex-forx-tools` | `https://github.com/repolex-ai/repolex-forx-tools` | workflow/tooling / parsing workflows | `tmp/deep-research-report.md` | Orchestration tools for parsing workflows. | clone later | index if code affects extraction/pipeline | may refine production ingestion/tooling risks |
| medium | `repolex-ai/semanticstate` | `https://github.com/repolex-ai/semanticstate` | adapter / adjacent ontology-code bridge | `tmp/deep-research-report.md` | Decorator library linking code with FBP/SYSML ontology. | clone later | index if code is substantive | may refine code-to-ontology integration ideas |
| medium | `repolex-ai/stack-graphs` | `https://github.com/repolex-ai/stack-graphs` | adjacent code graph runtime | `tmp/deep-research-report.md` | Rust implementation of stack graphs. | clone later | index only if fork changes matter; otherwise treat as upstream/fork reference | may refine code graph strategy; avoid overclaiming fork relevance |
| medium | `repolex-ai/multilspy` | `https://github.com/repolex-ai/multilspy` | adjacent code analysis / LSP library | `tmp/deep-research-report.md` | Python LSP client library. | clone later | index only if fork changes matter; otherwise treat as dependency/fork reference | may refine source-code indexing options, not git-lex proof |
| low | `repolex-ai/current-projects` | `https://github.com/repolex-ai/current-projects` | docs/demo / roadmap | `tmp/deep-research-report.md` | Overview of current directions: Repolex, Octobody, AutoOntology, SemanticState, SlopNet. | clone later or inspect remotely | no index unless code exists | may refine S12 roadmap context; docs-only |
| low | `repolex-ai/awesome-papers` | `https://github.com/repolex-ai/awesome-papers` | docs/demo / research bibliography | `tmp/deep-research-report.md` | Papers influencing Repolex thinking. | defer | no index | research context only, not ACP proof |
| low | `repolex-ai/git-lex-www` | `https://github.com/repolex-ai/git-lex-www` | docs/demo / website | `tmp/deep-research-report.md` | Site `git-lex.com`. | defer | no index unless site content critical | marketing/docs context only |
| low | `repolex-ai/repolex-www` | `https://github.com/repolex-ai/repolex-www` | docs/demo / website | `tmp/deep-research-report.md` | Repolex website. | defer | no index | marketing/docs context only |
| low | `repolex-ai/repolex-marketplace` | `https://github.com/repolex-ai/repolex-marketplace` | marketplace / unknown | `tmp/deep-research-report.md` | Public description not specified. | clone later if marketplace metadata affects plugins | inspect first, index only if code exists | may refine plugin distribution or be noise |
| low | `repolex-ai/git-lex-kit-canon` | `https://github.com/repolex-ai/git-lex-kit-canon` | kit / currently empty | `tmp/deep-research-report.md` | Canon kit reported as currently empty. | reject-before-clone unless changed | no index | likely noise until content exists |
| low | `repolex-ai/git-lex-kit-obsidian` | `https://github.com/repolex-ai/git-lex-kit-obsidian` | kit / currently empty | `tmp/deep-research-report.md` | Obsidian ingestion kit reported as currently empty. | reject-before-clone unless changed | no index | likely noise until content exists |
| low | `repolex-ai/octologies` | `https://github.com/repolex-ai/octologies` | unknown | `tmp/deep-research-report.md` | Public description not specified. | defer | inspect before index | unknown relevance |
| low | `repolex-ai/repolex-alto` | `https://github.com/repolex-ai/repolex-alto` | docs/theme / noise | `tmp/deep-research-report.md` | Ghost theme adapted for Repolex. | reject-before-clone unless web/publishing path matters | no index | likely unrelated to ACP/git-lex core |

## Priority rationale

### High priority

High-priority candidates either are already part of the studied core or could materially affect ACP production-cycle decisions:

- runtime/store/query behavior: `git-lex`;
- semantic substrate and kits: base/squad/soul/autoknow;
- plugin and MCP operational surface: `subtext-mcp`, `git-lex-plugins`, `squad-explorer`;
- code graph / ontology direction: `code-ontology-spec`;
- branch-native ontology evolution: `lex-o-seed`.

### Medium priority

Medium-priority candidates may refine integration architecture, agent-memory modeling, ingestion, code analysis, or production-cycle tooling, but are less likely to change the immediate ACP authority boundary without deeper proof.

### Low priority

Low-priority candidates are docs, websites, empty kits, unknown repositories, themes, or likely noise. They should not consume clone/index time unless S11 discovery finds new evidence that they affect ACP integration.

## Initial clone-later queue for S11 T02

Recommended first clone batch:

1. `repolex-ai/squad-explorer`
2. `repolex-ai/git-lex-plugins`
3. `repolex-ai/code-ontology-spec`
4. `repolex-ai/lex-o-seed`
5. `repolex-ai/git-lex-kit-familiar`
6. `repolex-ai/git-lex-kit-lab`
7. `repolex-ai/git-lex-kit-collab`
8. `repolex-ai/git-lex-kit-claude-code`
9. `repolex-ai/git-lex-kit-claude-export`
10. `repolex-ai/forx`
11. `repolex-ai/forxq`
12. `repolex-ai/repolex-forx-tools`
13. `repolex-ai/semanticstate`

Deferred unless needed:

- `stack-graphs`, `multilspy` — likely fork/reference repos; clone only if fork deltas matter.
- `current-projects`, `awesome-papers`, websites — docs context only.
- `git-lex-kit-canon`, `git-lex-kit-obsidian` — reported empty.
- `repolex-alto` — likely web/theme noise.
- `octologies`, `repolex-marketplace` — inspect metadata first.

## S11 handoff to S12

S11 expanded the repository corpus, cloned and pinned selected repositories, indexed selected code repositories, and classified corpus relevance. This is still not an ACP adoption decision.

### Final S11 checks

Command output anchor:

```text
.gsd/exec/0476fff0-df14-4499-8f33-e10f772cfc6a.stdout
```

Observed results:

```text
no-main-repo .lex: pass
git diff --check: pass
S11 core corpus/source inventory checks: pass
```

GitNexus change detection for law-nexus:

```text
gitnexus_detect_changes({repo:"law-nexus", scope:"all"})
changed_files: 1
risk_level: low
changed_symbols: []
affected_processes: []
```

### Vendor-source changes produced by S11

S11 created or confirmed these external reference checkouts under `/root/vendor-source`:

- `/root/vendor-source/squad-explorer`
- `/root/vendor-source/git-lex-plugins`
- `/root/vendor-source/code-ontology-spec`
- `/root/vendor-source/lex-o-seed`
- `/root/vendor-source/git-lex-kit-familiar`
- `/root/vendor-source/git-lex-kit-lab`
- `/root/vendor-source/git-lex-kit-collab`
- `/root/vendor-source/git-lex-kit-claude-code`
- `/root/vendor-source/git-lex-kit-claude-export`
- `/root/vendor-source/forx`
- `/root/vendor-source/forxq`
- `/root/vendor-source/repolex-forx-tools`
- `/root/vendor-source/semanticstate`

These are external reference checkouts, not law-nexus source files.

### Source inventory update

Updated compact source inventory:

```text
.agents/skills/git-lex/references/source-inventory.md
```

The source inventory now points to this S11 report for detailed corpus evidence and records key cloned repo anchors and GitNexus index names.

### Open questions for GPT Pro and S12 reconciliation

1. Do GPT Pro findings identify additional repositories not in the 30-repo corpus from `tmp/deep-research-report.md`?
2. Do GPT Pro findings contradict S10 runtime semantics: `list --json` class discovery, expected-empty `owl:Class` / `sh:targetClass` queries, or bounded `history-verify`?
3. Do any newly cloned repos provide stronger evidence for JSON-LD, negative SHACL validation, SPARQL-star, production build fitness, or binary provenance?
4. Do `squad-explorer`, `git-lex-plugins`, or subtext-related repos change the agent CLI/GSD-like harness integration model?
5. Do `code-ontology-spec`, `forx`, `repolex-forx-tools`, or `semanticstate` imply architecture correction candidates for ACP code graph or production ingestion?
6. Which repo families should be `adopt now`, `ACP-native absorb`, `adapter-later`, `research-only`, `blocked`, or `reject` in S12?
7. Does any evidence remain profile-specific enough to affect R035/R037/R038, or do those requirements remain unvalidated by git-lex corpus evidence?

### S11 final boundary

S11 proves expanded corpus acquisition, pinning, selected indexing, and relevance triage. It does not prove ACP adoption, production-cycle fitness, runtime portability, legal/profile correctness, or R035/R037/R038 validation.

## T04 relevance classification and claim impact

S11/T04 classifies the expanded corpus for ACP relevance. This is a triage matrix for S12, not a final ACP decision.

| Repository / family | Relevance classification | Risk / evidence class | Current M051 claim impact | S12 implication |
|---|---|---|---|---|
| `git-lex` | runtime implementation | runtime/source/supply-chain | confirms and refines KD01/KD02/KD03; still leaves production fitness blocked | Keep as core runtime reference; do not adopt without production gates. |
| `git-lex-kit-base` | semantic vocabulary / kit | source-only + runtime-smoke through S10 | confirms base semantic substrate and shape-driven class discovery | Preserve as baseline ontology prior art. |
| `git-lex-kit-squad` | kit / MCP coordination domain | source-only + runtime-smoke | confirms collaboration/task/decision vocabulary but unchanged ACP-core boundary | Treat as prior art, not ACP core dependency. |
| `git-lex-kit-soul` | kit / agent memory | source-only + runtime-smoke | refines KD05 around agent memory and personal knowledge contexts | Consider privacy and agent-memory boundaries in S12. |
| `git-lex-kit-autoknow` | extraction pipeline / adaptive kit | source-only + runtime-smoke | refines KD05; confirms adaptive shape smoke but not authority | Candidate adapter-later ingestion idea; block authority claims. |
| `subtext-mcp` | MCP/UX / plugin runtime | source/supply-chain/UX evidence | confirms KD07; wrapper remains interaction model, not proof | S12 should classify as agent CLI bridge candidate with trust policy requirements. |
| `squad-explorer` | MCP/UX / web visualization | GitNexus-indexed source-navigation evidence | refines UX/SPARQL visualization surface; may confirm non-authoritative UI boundary | Inspect as visualization/query UI candidate; not source truth. |
| `git-lex-plugins` | plugin marketplace / agent CLI distribution | metadata/docs pending | refines Claude-as-agent-CLI distribution concern; no code proof yet | Inspect plugin manifests before any workflow claims. |
| `code-ontology-spec` | semantic vocabulary / code KG spec | documentation/ontology spec | expands ACP code-graph roadmap questions; does not change runtime proof | Candidate architecture input for code ontology, not implementation proof. |
| `lex-o-seed` | ontology evolution / workflow-tooling | kit/ontology source evidence | refines ontology versioning and branch-native evolution questions | S12 should decide if ACP needs branch-native ontology governance. |
| `git-lex-kit-familiar` | kit / agent memory and relationships | kit/ontology source evidence | refines soul/privacy/co-reasoning boundaries | Candidate prior art for agent memory profile, not ACP core. |
| `git-lex-kit-lab` | kit / research workflow | kit/ontology source evidence | refines research/experiment lifecycle vocabulary | Candidate for ACP research artifact model. |
| `git-lex-kit-collab` | kit / collaboration workflow | kit/ontology source evidence | refines collaboration/ideation vocabulary | Candidate prior art for planning artifacts. |
| `git-lex-kit-claude-code` | kit / agent session ingestion | kit/ontology source evidence | refines Claude-as-agent-CLI session capture concern | Treat as GSD/pi-like harness prior art; inspect privacy/provenance before adoption. |
| `git-lex-kit-claude-export` | kit / agent export adapter | kit/ontology source evidence | refines export/import concern but remains unverified | Candidate for S12 ingestion/export questions; not proof. |
| `forx` | extraction pipeline / code-analysis workflow | GitNexus-indexed source-navigation evidence | expands code parsing/extraction direction beyond current git-lex core | Candidate future code-KG ingestion path; requires separate proof. |
| `forxq` | stale/noise | empty repo at clone time | unchanged; no evidence content | Exclude unless upstream changes. |
| `repolex-forx-tools` | production operations / parsing workflow tooling | GitNexus-indexed source-navigation evidence | expands production-cycle workflow/orchestration questions | Candidate operational tooling reference; not ACP proof. |
| `semanticstate` | adapter / code-to-ontology bridge | GitNexus-indexed source-navigation evidence | expands architecture-correction candidates around semantic code state | Candidate later architecture input; requires source/runtime review. |
| `stack-graphs`, `multilspy` | adjacent code-analysis dependencies/forks | deferred | unchanged until fork deltas are inspected | Clone only if S12 needs code graph implementation alternatives. |
| `current-projects`, `awesome-papers`, websites | docs/demo context | documentation-only | expands strategic context, not proof | Use only for roadmap/context, not adoption claims. |
| `git-lex-kit-canon`, `git-lex-kit-obsidian` | empty/stale kit candidates | reported empty/deferred | unchanged | Exclude until content exists. |
| `repolex-alto` | web/theme noise | likely unrelated | unchanged | Reject for ACP/git-lex integration unless publishing UX becomes relevant. |
| `octologies`, `repolex-marketplace` | unknown | deferred metadata inspection | new question only | Inspect only if S12 needs marketplace/ontology context. |

### Repo-to-claim impact summary

| Current M051 conclusion | S11 impact |
|---|---|
| ACP authority remains ACP-native | unchanged; no expanded repo currently proves replacement source authority. |
| git-lex runtime smoke is useful but not production fitness | unchanged; expanded repos add UX/tooling/code-analysis context, not production proof. |
| Claude references are agent CLI/GSD-like harness evidence | refined; Claude-oriented kits/plugins should remain in corpus. |
| subtext/plugin path is UX/process evidence | confirmed/refined by `git-lex-plugins` and `squad-explorer` candidates. |
| code graph direction may matter to ACP architecture | expanded by `code-ontology-spec`, `forx`, `repolex-forx-tools`, `semanticstate`, and possibly `stack-graphs`/`multilspy`. |
| JSON-LD, negative validation, SPARQL-star, production binary trust remain blocked | unchanged; no S11 T01-T04 evidence upgrades these. |
| R035/R037/R038 are not validated by git-lex evidence | unchanged; expanded corpus provides no profile-specific proof. |

### T04 conclusion

The expanded corpus confirms that git-lex is more than one CLI: it is an ecosystem around semantic kits, agent CLI integration, visualization, code ontology, extraction workflows, and ontology evolution. That broadens S12's production-cycle review scope, but it does not upgrade current adoption claims. S12 should treat the added repositories as architecture-input and proof-target sources, not as final evidence of ACP fitness.

## T03 GitNexus indexing ledger

S11/T03 indexed selected code repositories and ran sanity queries. This establishes query-addressability for later classification; it does not prove ACP integration fitness.

Index command output anchor:

```text
.gsd/exec/fc8b0da0-62c4-4e3f-a54a-8534731b6a40.stdout
```

Pre-index code scan anchor:

```text
.gsd/exec/e71efb60-4b67-4c23-bb6f-fbfbabccc84a.stdout
```

| Repository | GitNexus repo name | Index status | Reason indexed | Sanity query result |
|---|---|---|---|---|
| `squad-explorer` | `git-lex-squad-explorer-reference` | indexed | `dev-server.py` plus web UI assets indicate executable UX/SPARQL surface. | Query `server SPARQL visualization` returned `www/js/main.js:sparql`, `dev-server.py:main`, `DevHandler`, and UI files. |
| `forx` | `repolex-forx-reference` | indexed | Python package candidate for extraction/code-analysis pipeline. | Query `forx parse graph workflow` returned `src/forx/cli.py:parse`, `index_cmd`, `dispatch_workflow`, `check_running`, and spider/orchestration flows. |
| `repolex-forx-tools` | `repolex-forx-tools-reference` | indexed | Python workflow tooling around parsing queues/manifests. | Query `queue manifest workflow` returned `scripts/queue_manager.py`, `find_next_work.py`, `discover_versions.py`, and queue/manifest flows. |
| `semanticstate` | `repolex-semanticstate-reference` | indexed | Python decorator/state-store code linking code with semantic state. | Query `semantic state decorator store` returned `semanticstate/core.py:_semantic_decorator`, `StateStore`, `SSBoundProperty`, examples, and tests. |

### Deferred indexing decisions

| Repository family | Decision | Reason |
|---|---|---|
| `git-lex-plugins` | deferred | Initial scan found no top-level code files; inspect as plugin metadata/docs first. |
| `code-ontology-spec` | deferred | Appears documentation/ontology-spec first; inspect content before indexing. |
| `lex-o-seed` | deferred | Kit/ontology prior art; index only if executable code is discovered. |
| `git-lex-kit-familiar`, `git-lex-kit-lab`, `git-lex-kit-collab`, `git-lex-kit-claude-code`, `git-lex-kit-claude-export` | deferred | Kit/ontology content; inspect as source evidence first unless generator/adapter code is found. |
| `forxq` | deferred | Empty repository at clone time; classify as stale/noise unless upstream changes. |

### T03 indexing caveats

- GitNexus queryability is source-navigation evidence only.
- Indexing does not approve runtime execution, install scripts, ACP adoption, or production-cycle use.
- The indexed repositories may refine S12 architecture decisions, but they do not validate R035/R037/R038.
- Direct `gitnexus analyze --force --name <repo>` was used from each vendor checkout.

## T02 clone and pin ledger

S11/T02 cloned the selected high-priority queue into `/root/vendor-source` and recorded commit, remote, default branch, README/license presence, and top-level type hints. No install scripts, hooks, daemons, plugin activation, or runtime tests were run. The main repository `.lex` guard remained clean.

Command output anchor:

```text
.gsd/exec/53cf846e-8629-423c-aff4-9af3fb0d0227.stdout
```

| Repository | Local path | Clone status | Remote | Default branch | Commit | README | License | Type after clone | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `squad-explorer` | `/root/vendor-source/squad-explorer` | cloned | `https://github.com/repolex-ai/squad-explorer.git` | `main` | `0dba67f2ee400b8e3ca87c601e0f48c0ef077328` | README.md | missing | documentation/demo or web/plugin surface pending inspection | Candidate UX/SPARQL/live-push surface; not proof. |
| `git-lex-plugins` | `/root/vendor-source/git-lex-plugins` | cloned | `https://github.com/repolex-ai/git-lex-plugins.git` | `main` | `0af28825698211b2d1f44a9a8743b348fce04875` | README.md | missing | documentation/plugin metadata pending inspection | Candidate agent CLI/plugin distribution surface; not proof. |
| `code-ontology-spec` | `/root/vendor-source/code-ontology-spec` | cloned | `https://github.com/repolex-ai/code-ontology-spec.git` | `main` | `6b0494a820171e750632acd94ff1de7fc0d61506` | README.lex.md README.md | missing | documentation/ontology spec | Candidate code-KG ontology direction; not runtime proof. |
| `lex-o-seed` | `/root/vendor-source/lex-o-seed` | cloned | `https://github.com/repolex-ai/lex-o-seed.git` | `main` | `851891d107ea9ef698400444b12b88ac3dac1d34` | README.md | missing | kit/ontology | Candidate branch-native ontology evolution prior art. |
| `git-lex-kit-familiar` | `/root/vendor-source/git-lex-kit-familiar` | cloned | `https://github.com/repolex-ai/git-lex-kit-familiar.git` | `main` | `8043ce75ef281776ee3677a7656fdbd00f16510a` | README.md | missing | kit/ontology | Candidate soul-extension/privacy/relationship-tracking prior art. |
| `git-lex-kit-lab` | `/root/vendor-source/git-lex-kit-lab` | cloned | `https://github.com/repolex-ai/git-lex-kit-lab.git` | `main` | `2ba6e747a53c5cc100eeff5b31c9fe7192924bf2` | README.md | missing | kit/ontology | Candidate research/experiment kit prior art. |
| `git-lex-kit-collab` | `/root/vendor-source/git-lex-kit-collab` | cloned | `https://github.com/repolex-ai/git-lex-kit-collab.git` | `main` | `8769580c93c2114fe781228a9caaae5940170080` | README.md | missing | kit/ontology | Candidate collaboration kit prior art. |
| `git-lex-kit-claude-code` | `/root/vendor-source/git-lex-kit-claude-code` | cloned | `https://github.com/repolex-ai/git-lex-kit-claude-code.git` | `main` | `95f5f515977869029650e229550a2d6034e32dc2` | README.md | missing | kit/ontology | Treat Claude Code as concrete agent CLI/GSD-like harness target; candidate session-ingestion prior art. |
| `git-lex-kit-claude-export` | `/root/vendor-source/git-lex-kit-claude-export` | cloned | `https://github.com/repolex-ai/git-lex-kit-claude-export.git` | `main` | `fc201b4f90b1c21ee846239a8b4f756bdeab59b9` | README.md | missing | kit/ontology | Treat Claude export as agent CLI export prior art; inspect before claims. |
| `forx` | `/root/vendor-source/forx` | cloned | `https://github.com/repolex-ai/forx.git` | `main` | `60fc55aa459ed556930ed3a99ae2d143dc9a5ab8` | README.md | missing | code | Candidate extraction/code-analysis pipeline. |
| `forxq` | `/root/vendor-source/forxq` | cloned empty repository | `https://github.com/repolex-ai/forxq.git` | `main` | unavailable | missing | missing | stale/noise | Empty repository at clone time; defer indexing and claims. |
| `repolex-forx-tools` | `/root/vendor-source/repolex-forx-tools` | cloned | `https://github.com/repolex-ai/repolex-forx-tools.git` | `main` | `cddc651c5231a926e4d621a2e925dc1f6a89d7d0` | README.md | missing | code | Candidate parsing workflow tooling. |
| `semanticstate` | `/root/vendor-source/semanticstate` | cloned | `https://github.com/repolex-ai/semanticstate.git` | `main` | `4110c9f787af12a94e2eeda6c731baedde30f8f0` | README.md | LICENSE | code | Candidate code/ontology bridge. |

### T02 interpretation

- `code` candidates for possible S11/T03 GitNexus indexing: `forx`, `repolex-forx-tools`, `semanticstate`, and maybe `squad-explorer`/`git-lex-plugins` if inspection shows executable code rather than metadata/docs only.
- `kit/ontology` candidates should usually be inspected as source/content evidence first; GitNexus indexing can be deferred unless they contain non-trivial generator or adapter code.
- `forxq` is empty and should be classified as stale/noise unless upstream changes before final S12 reconciliation.
- Missing LICENSE is common across cloned candidates and remains a supply-chain/redistribution caveat.
- Claude-oriented repositories remain relevant as agent CLI/GSD-like harness evidence, not vendor-only noise and not proof by themselves.

### T02 safety result

```text
no-main-repo .lex: pass
```

## S11 T01 non-proof conclusion

T01 discovers and prioritizes a 30-repository Repolex/git-lex candidate corpus. T02 cloned and pinned the selected high-priority queue, but did not execute repo setup or runtime actions. All candidate roles and descriptions remain provisional until S11 T03/T04 provide indexing and classification evidence.
