# M051 S05 Git Lex ACP Integration Decision

## Status

Accepted as the M051 S05 source-anchor decision for ACP integration architecture and per-capability git-lex disposition.

This is an architecture and backlog decision, not runtime adoption approval.

## Decision

Keep ACP source authority ACP-native. Use git-lex as source-reviewed semantic prior art and a future optional adapter candidate, not as the ACP core runtime backend.

The M051 evidence strengthens the previous conservative M048 decision:

- `lex:`, `git:`, and selected `fm:` ontology terms are useful source-reviewed vocabulary candidates.
- `squad:` is useful domain prior art for work, decision, brief, blocker, and collaboration vocabulary, but must not leak into ACP core by default.
- SPARQL, SHACL, N-Quads, named graphs, RDF 1.2 quoted triples, history graph behavior, JSON-LD, and SPARQL-star remain unproven or runtime-blocked for ACP adoption.
- `subtext-mcp` is an interaction model for surfacing git-lex tools to agents, not binary provenance proof, semantic correctness proof, or ACP integration proof.
- No `.lex` state may be created or mutated in `/root/law-nexus` main checkout without a later explicit adoption decision and isolated proof.

ACP should therefore implement the architecture as:

```text
ACP-native source records
  -> ACP-native lifecycle, proof gates, health findings, source anchors, and verifier checks
  -> derived RDF/SHACL/SPARQL/JSON-LD-compatible projection surfaces where useful
  -> optional git-lex adapter later, only after reproducible runtime and repository-state gates pass
```

## Evidence consumed

- `prd/architecture/acp/M045-RDF-PROJECTION-CONTRACT.md` — derived non-authoritative projection contract and R035/R037/R038 non-claim boundaries.
- `prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md` — prior ACP-native-first git-lex disposition.
- `prd/architecture/acp/M051-S02-GIT-LEX-CODE-ANALYSIS.md` — command surfaces, subtext-mcp wrapper seams, and runtime-proof checklist.
- `prd/architecture/acp/M051-S03-GIT-LEX-SEMANTIC-WEB-REVIEW.md` — file-proven ontology facts and runtime-sensitive semantic-web claim matrix.
- `prd/architecture/acp/M051-S04-GIT-LEX-RUNTIME-PROOF.md` — blocked runtime proof, no-main-repo `.lex` guard, and missing executable diagnostics.
- `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` — license, dependency, binary hash, wrapper, and acquisition policy evidence.

## Authority boundary

No artifact is authoritative by shape alone.

Authority requires:

```text
source category + lifecycle state + evidence anchor + proof gate or accepted decision
```

RDF, OWL, SHACL, SPARQL, JSON-LD, JSONL, dashboards, recovery views, git-lex output, subtext-mcp views, and GSD summaries are derived or diagnostic surfaces unless tied back to ACP source records and accepted proof or decisions.

This decision does not validate R035, R037, or R038.

- R035 remains outside git-lex/RDF projection proof because ontology/product architecture claims still need independent bounded architecture and runtime evidence.
- R037 remains outside git-lex/RDF projection proof because FalkorDB ingest/runtime proof is separate from ACP semantic projection or git-lex source review.
- R038 remains outside git-lex/RDF projection proof because independent proof review must evaluate the relevant LegalGraph claim, not derived projection shape alone.

## Per-capability ACP disposition table

| Capability | M051 evidence | Disposition | Rationale | Proof gate before promotion | Blocked or allowed next action |
|---|---|---|---|---|---|
| ACP source records | M048 proves ACP-native fixtures; M051 adds no runtime git-lex proof. | `implement ACP-native` | Source records are the authority root and must work without git-lex runtime. | Schema tests, source-anchor checks, lifecycle/proof-gate verifier checks. | Allowed: implement and harden ACP-native records. |
| Lifecycle states and transitions | M048 lifecycle mechanics remain valid; M051 runtime proof is blocked. | `implement ACP-native` | Candidate, accepted, blocked, deferred, rejected, stale, and derived states drive allowed actions independently of backend. | Transition-history tests and verifier checks for illegal state promotion. | Allowed: ACP-native transition history and blocked-action rules. |
| Proof gates | S03/S04 show semantic claims cannot be upgraded without runtime evidence. | `implement ACP-native` | Gate definitions must stay separate from gate satisfaction. Blocked diagnostics are valid evidence of non-satisfaction, not pass evidence. | Tests proving definitions, executed evidence, accepted decisions, blocked diagnostics, and requirement validation are distinct. | Allowed: ACP-native proof-gate records and health findings. |
| Evidence anchors | M045 and M048 require repo-relative anchors; M051 S04 uses `.gsd/exec` only as transient diagnostics, not durable registry anchors. | `implement ACP-native` | Durable proof must remain portable and repository-relative. | Static checks rejecting absolute paths, ignored paths, raw provider payloads, secrets, raw vectors, and `.gsd/exec` as durable anchors. | Allowed: harden anchor validation. |
| Health findings and blocked diagnostics | S04 records missing executable and `oxrocksdb-sys`/`stdbool.h` blocker; S09 records supply-chain gaps. | `implement ACP-native` | ACP needs first-class blocked/unsafe/insufficient-evidence records so future agents do not confuse diagnostics with proof. | Tests for fail-closed health categories and recovery reports. | Allowed: model `BlockedCapability`, `InsufficientEvidence`, `UnsafeMutation`, and `UntrustedBinary` findings. |
| Derived projection boundary | M045 contract requires derived non-authoritative projection; S03 keeps semantic web claims bounded. | `implement ACP-native` | Projection provenance and freshness must be ACP-controlled even if vocabulary borrows from git-lex. | Projection generator write/check tests and stale-output detection. | Allowed: keep derived projection under approved paths. |
| `lex:` vocabulary | S03 file-proves `lex:` classes/properties for documents, decisions, references, relations, mentions, and provenance. | `absorb approach` | ACP can reuse the conceptual shape while preserving ACP-native authority and stricter predicates where needed. | Prototype mapping and audit query proving each borrowed term remains non-authoritative until linked to ACP source records. | Allowed: map selected `lex:` terms into ACP ontology prototype. |
| `git:` vocabulary | S03 file-proves commit, actor, blob, ref, changeset, and file vocabulary. | `absorb approach` | Useful for repository provenance, but runtime ingestion/history completeness is not proven. | Runtime or deterministic ACP-native fixture checks comparing git evidence to expected commits/files. | Allowed: use `git:` as vocabulary prior art; keep ordinary git as baseline. |
| `fm:` vocabulary | S03 file-proves lightweight frontmatter metadata vocabulary. | `absorb approach` | Useful for document metadata, but ACP needs stricter lifecycle/status/proof semantics than generic frontmatter. | Prototype fixture proving status/date/tag mapping does not bypass ACP schema validation. | Allowed: borrow terms only for projection metadata. |
| `squad:` vocabulary | S03 file-proves task/project/decision/brief/discovery/blocker prior art. | `adapter later` | Some terms overlap ACP planning, but importing the namespace would couple ACP core to a domain kit. | S08 prototype must either isolate `squad:` as prior art or map only a narrow subset through ACP-native predicates. | Allowed: review as prior art; do not make ACP core depend on `squad:`. |
| SHACL generation and validation | S03 source-backed but runtime-unverified; S04 runtime proof blocked. | `implement ACP-native` for current validation; `adapter later` for git-lex SHACL runtime | ACP validation must not wait for git-lex runtime. SHACL may remain a derived smoke layer or adapter proof target. | Positive/negative ACP-native tests now; later executable git-lex SHACL proof before adapter use. | Allowed: ACP-native validation and optional SHACL projection smoke. |
| SPARQL query and audit surfaces | S03 source-backed but runtime-unverified; M045 allows derived SPARQL handoff; S04 blocked. | `implement ACP-native` for current audits; `adapter later` for git-lex SPARQL runtime | ACP audits should be deterministic and available without git-lex. SPARQL files may describe future engine queries but are not product proof alone. | Structural audit tests now; later engine-executed queries against proven store before runtime adoption. | Allowed: add SPARQL audit pack as derived, non-authoritative artifact. |
| UI/recovery and diagnostic views | M045/M048 treat dashboards and recovery views as derived unless tied to ACP source records; S09 visualization is wrapper/UI interaction evidence only. | `implement ACP-native` for recovery; `adapter later` for git-lex/subtext UI | Cold-reader recovery must work from ACP-native records without git-lex runtime. Visualization does not prove semantic correctness, source authority, or requirement validation. | Deterministic recovery report tests, source-anchor checks, non-authoritative markers, blocked-action diagnostics, and projection freshness checks. | Allowed: ACP-native recovery/audit views; blocked: treating git-lex/subtext visualization as authority or proof. |
| N-Quads and named graphs | S03 source-backed but runtime-unverified; S04 blocked. | `adapter later` | Candidate graph partitioning mechanism, but no local store was generated. | Isolated runtime proof with graph inventory and sample triples. | Blocked for adoption; allowed in prototype as non-authoritative design target. |
| RDF 1.2 quoted triples and history graph | S03 source-backed but runtime-unverified; S04 blocked. | `adapter later` | Promising provenance concept, but parser/evaluator/history behavior is not proven. | Multi-commit fixture, sync, history verification, and query output. | Blocked for ACP proof; allowed as future proof backlog. |
| JSON-LD interchange | S03 found no file-backed JSON-LD import/export implementation. | `blocked` | JSON-shaped query results are not JSON-LD. ACP must not claim JSON-LD support from current evidence. | Explicit JSON-LD parser/serializer path plus import/export round trip. | Blocked except for future ACP-native context prototype if clearly marked non-authoritative. |
| SPARQL-star compatibility | S03 distinguishes RDF 1.2 triple terms from broad SPARQL-star support. | `blocked` | Current evidence is not enough to claim SPARQL-star compatibility. | SPARQL-star-specific fixture/query in a proven runtime. | Blocked; do not mention as ACP capability. |
| git-lex runtime backend | S04 no runnable binary from source build; S09 prebuilt binaries are research-only. | `blocked` | Runtime adoption lacks reproducible source build, executable proof, and repository-state policy. | Source-build manifest, help/version or manifest identity, init/sync/query/validate proof, cleanup and rollback. | Blocked; do not use git-lex runtime in ACP core. |
| `.lex` repository state | S04 confirms no main repo `.lex`; S09 requires no-main-repo guard. | `reject` for main checkout; `adapter later` for isolated fixture | Main repository `.lex` state would create unsafe hidden authority and rollback risk. | Explicit adoption decision, isolated workspace, rollback/cleanup proof, and state ownership contract. | Reject main-repo mutation now. |
| subtext-mcp MCP wrapper | S09 proves wrapper behavior and trust gaps; missing explicit license. | `adapter later` | Useful interaction model, but not ACP proof and not production-ready. | License resolution, wrapper behavior manifest, broker/SQLite/failure tests, binary provenance, no-main-repo guard. | Allowed only as research reference; blocked for default workflow. |
| Prebuilt subtext-mcp binaries | S09 records hashes but no provenance manifest and no version output. | `reject` for adoption proof; `adapter later` for research-only help checks | Hashes identify local files but do not prove source, build, signer, or suitability. | Machine-verifiable provenance manifest and source-build comparison. | Do not use as ACP adapter/runtime evidence. |
| law-nexus profile constraints | Project rules keep Russian legal, FalkorDB, parser, citation, and R035/R037/R038 proof outside ACP core. | `implement ACP-native` profile seam; `adapter later` for git-lex binding | ACP must stay reusable and law-nexus proof must remain independent. | Profile-specific proof gates and verifier checks. | Allowed: define profile seam; do not validate law-nexus claims from projections. |

## Final disposition summary

| Disposition | Capabilities |
|---|---|
| `use git-lex runtime` | None from M051 evidence. |
| `absorb approach` | Selected `lex:`, `git:`, and `fm:` vocabulary patterns; isolation/no-main-repo discipline; source-reviewed semantic-web claim classification. |
| `implement ACP-native` | Source records; lifecycle; proof gates; evidence anchors; health findings; derived projection boundary; deterministic audit/recovery; current validation; profile seam. |
| `adapter later` | `squad:` prior-art mapping; git-lex SHACL/SPARQL/N-Quads/named graph/history runtime; subtext-mcp wrapper; optional git-lex backend. |
| `reject` | Main-checkout `.lex` mutation; prebuilt binaries as adoption proof; projection-as-source-truth; wrapper behavior as semantic correctness proof. |
| `blocked` | git-lex runtime backend; JSON-LD support claim; SPARQL-star compatibility claim; any R035/R037/R038 validation from ACP/git-lex/projection evidence alone. |

## ACP semantic integration architecture

### Layering

The ACP ontology/projection architecture should use explicit layers:

```text
lex:     source-reviewed generic document, decision, reference, relation, mention, and provenance vocabulary candidate
          imported conceptually or mapped selectively, not treated as authority by itself

git:     source-reviewed commit, actor, blob, ref, changeset, and file vocabulary candidate
          used for repository provenance projection where ACP source anchors already exist

fm:      source-reviewed frontmatter metadata vocabulary candidate
          used only for non-authoritative document metadata projection

squad:   domain-kit prior art for tasks, decisions, briefs, blockers, and collaboration
          kept outside ACP core unless mapped through ACP-native predicates

acp:     authoritative project-local governance vocabulary for source records, lifecycle states,
          proof gates, evidence anchors, health findings, profile seams, allowed/blocked actions,
          non-claims, and projection provenance

profile: law-nexus-specific proof gates for Russian legal evidence, FalkorDB runtime, parser completeness,
          citation-safe retrieval, R035, R037, and R038
```

### Projection flow

The preferred flow is:

```text
Tracked ACP source evidence
  -> architecture/source-record extractor
  -> ACP-native JSONL registry and decision/proof records
  -> verifier and deterministic audit checks
  -> derived projection generator
  -> Turtle / SHACL-shaped / SPARQL audit / optional JSON-LD context artifacts
```

Rules:

1. Source truth remains PRD/GSD/ADR/source/test/runtime/real-document evidence and accepted decisions.
2. Generated projection artifacts are derived diagnostics and recovery/interoperability surfaces.
3. Projection files must carry non-authoritative markers and source-anchor provenance.
4. Projection checks may detect drift, missing anchors, blocked gates, unsafe actions, and non-claims.
5. Projection checks must not validate product runtime, parser completeness, legal answer correctness, FalkorDB ingestion, retrieval quality, or independent review.

### Adapter boundary

A future git-lex adapter may exist only behind a narrow boundary:

```text
ACP source record API
  -> adapter input manifest
  -> isolated git-lex workspace
  -> git-lex init/sync/query/validate proof
  -> adapter output comparison against ACP-native expected records
  -> cleanup and no-main-repo-.lex guard
```

The adapter must not:

- mutate `/root/law-nexus/.lex`;
- replace ACP source records;
- treat `.lex/oxigraph` as authority;
- use prebuilt binaries as proof without provenance;
- hide `subtext-mcp` broker, SQLite, hook, symlink, browser-open, or detached process behavior;
- validate R035, R037, or R038.

## Proof gates for future promotion

A later milestone may reconsider `adapter later` or `blocked` rows only after these gates pass:

1. Reproducible source build from full pinned `git-lex` commit with `Cargo.lock` hash, Rust toolchain, target triple, build command, binary `sha256`, size, mode, and builder identity.
2. Explicit license resolution for `subtext-mcp` before redistribution or workflow adoption.
3. Isolated runtime proof for help, identity/version or manifest, init, kit install, sync, query, validation, RDF/N-Quads, named graphs, frontmatter, and cleanup.
4. Positive and negative fixtures for SHACL/proof-gate behavior.
5. JSON-LD import/export round trip before any JSON-LD support claim.
6. SPARQL-star-specific fixture before any SPARQL-star support claim.
7. No-main-repo `.lex` guard before and after every runtime run.
8. Wrapper operational tests for missing binaries, unsupported platform, broker failure, SQLite failure, subprocess timeout, detached process cleanup, and browser-open failure.
9. ACP verifier integration proving projection outputs remain derived and source records remain authoritative.
10. Profile-specific proof before any law-nexus requirement status change.

## Implementation backlog

### B01: ACP ontology prototype

- Create minimal tracked ACP ontology/projection files under approved ACP paths.
- Include `acp:` classes for source records, lifecycle states, proof gates, evidence anchors, health findings, derived projections, profile bindings, and non-claims.
- Map selected `lex:`, `git:`, and `fm:` vocabulary as borrowed/prior-art terms, not authority.
- Keep `squad:` out of ACP core except as commented prior-art mapping or optional profile/adapter example.
- Acceptance criteria: ACP ontology artifact parses structurally; it contains `lex:`, `git:`, `fm:`, `acp:`, and `profile` boundaries; it states projection non-authority and R035/R037/R038 non-validation.

### B02: JSON-LD context decision

- Decide whether ACP needs a JSON-LD context now or should defer it until runtime JSON-LD proof exists.
- If included, make it ACP-native and non-authoritative; do not claim git-lex JSON-LD support.
- Acceptance criteria: artifact explicitly distinguishes JSON-LD context convenience from git-lex JSON-LD import/export support and keeps JSON-LD support claim `blocked` unless a round trip exists.

### B03: SPARQL audit pack

- Add derived SPARQL audit queries for source record counts, unresolved proof gates, blocked capabilities, unsafe anchors, non-claims for R035/R037/R038, and high/critical risk records.
- Treat the pack as a handoff artifact unless an engine executes it.
- Acceptance criteria: SPARQL audit file includes queries and non-authoritative caveat; deterministic structural checks cover equivalent questions when no SPARQL engine is available.

### B04: SHACL-shaped smoke checks

- Add minimal shapes for ACP source records, proof gates, anchors, projection records, and decision candidates.
- Keep shapes as smoke checks, not ontology correctness or product proof.
- Acceptance criteria: positive and negative fixtures demonstrate missing authority markers, unsafe anchors, and projection-as-source-truth attempts fail closed.

### B05: Optional git-lex adapter spike

- Only after source-build and license gates, create an isolated adapter spike that maps ACP fixtures into a scratch git-lex workspace and compares runtime output to ACP-native expectations.
- Acceptance criteria: source-build manifest exists; no-main-repo `.lex` guard passes before/after; init/sync/query/validate outputs are captured; cleanup succeeds; discrepancies produce health findings instead of adoption claims.

### B06: subtext-mcp wrapper safety review

- If the wrapper is still desired, write tests/checklists for host-binary setup, broker startup, SQLite path, peer cleanup, `start_viz`, subprocess timeout, and detached process cleanup.
- Acceptance criteria: missing binary, unsupported platform, broker failure, sync failure, serve failure, and browser-open failure are handled explicitly; license gap is resolved before workflow adoption.

### B07: ACP verifier integration

- Extend the architecture/source verifier to check ACP ontology/projection source anchors, non-authoritative markers, blocked claims, and R035/R037/R038 non-validation boundaries.
- Acceptance criteria: `uv run python scripts/verify-architecture-graph.py` remains green, and focused tests fail if projection artifacts are treated as source truth.

### B08: Profile-specific proof gates

- Define law-nexus profile gates for Russian legal source evidence, FalkorDB runtime/ingest, parser completeness, temporal/citation safety, and independent review.
- Acceptance criteria: profile gates are represented as ACP records but cannot be satisfied by git-lex/RDF/projection shape alone.

## Non-claims

This decision does not prove runtime git-lex works in the local environment.

This decision does not approve `subtext-mcp` for default LegalGraph workflows.

This decision does not approve prebuilt binaries as adoption proof.

This decision does not prove JSON-LD support, SPARQL-star compatibility, SHACL correctness, SPARQL engine correctness, RDF completeness, ontology correctness, product runtime behavior, FalkorDB ingestion/runtime loading, parser completeness, citation-safe retrieval, legal answer correctness, or independent external review.

This decision does not validate R035.

This decision does not validate R037.

This decision does not validate R038.

## Closeout verdict

`ACP-native authority remains mandatory; selected git-lex ontology patterns may be absorbed into a derived ACP semantic prototype; runtime git-lex and subtext-mcp remain adapter-later or blocked until reproducible source-build, runtime, wrapper, cleanup, and profile proof gates pass.`
