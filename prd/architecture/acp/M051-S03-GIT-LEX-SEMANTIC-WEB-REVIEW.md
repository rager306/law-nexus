# M051 S03 Git Lex Semantic Web Review

Date: 2026-05-27

## Scope

This review covers three local vendor checkouts:

- `/root/vendor-source/git-lex-kit-base`
- `/root/vendor-source/git-lex-kit-squad`
- `/root/vendor-source/git-lex`

The goal is to separate reusable semantic-kit assets from domain-specific or runtime-dependent claims before ACP adoption work. Evidence here is source/file review only; command-level runtime behavior remains unproven unless explicitly called out as a file-backed implementation claim.

## Evidence levels used

| Level | Meaning |
|---|---|
| File-proven | A file, ontology, dependency, or source implementation exists in the reviewed checkout. |
| Code-backed, runtime-unverified | Source code appears to implement the feature, but no command was executed in this task to prove it works in this environment. |
| Runtime proof required | A claim depends on executing git-lex, building stores, validating data, or querying generated graph state. |
| UI-only | Capability appears in the visualization layer and should not be treated as core semantic correctness. |

## T01: Base and squad kit ontology review

### Kit layout classification

| Asset | Evidence | Classification | ACP relevance | Notes |
|---|---|---|---|---|
| `git-lex-kit-base/kit.yml` | `name: base`, `install folders: false` | Base reusable | High | Base kit ships system ontologies and no content folders, suitable as common substrate if runtime init supports it. |
| `git-lex-kit-base/ontology/lex/lex.ttl` | `lex:` OWL ontology with 12 classes, 15 object properties, 17 datatype properties | Base reusable | High | Upper ontology for generic information, decisions, references, links, mention provenance, unresolved links, and extraction metadata. |
| `git-lex-kit-base/ontology/git/git.ttl` | `git:` OWL ontology with commit/actor/blob/ref/change/file model | Base reusable | High | Git provenance model is directly relevant to ACP repository evidence and traceability. |
| `git-lex-kit-base/ontology/fm/fm.ttl` | `fm:` frontmatter datatype properties | Base reusable with runtime proof | Medium | Useful for ACP document metadata if extraction maps actual markdown frontmatter into graph data as documented. |
| `git-lex-kit-squad/kit.yml` | `name: squad`, `install folders: true`, `folder base: Squad`, `folder ontology: squad.ttl` | Domain-specific kit | Medium | Demonstrates non-base kit structure and typed document folders; ACP may reuse the pattern rather than the exact domain. |
| `git-lex-kit-squad/ontology/squad/squad.ttl` | `squad:` OWL ontology with collaboration/work/knowledge classes | Domain-specific, ACP-relevant subset | Medium | Task, project, decision, brief, discovery, situation, and blocker concepts overlap ACP planning/review workflows. |
| `git-lex-kit-squad/content/AGENTS.md` and `.claude` harness files | agent instruction scaffolds | UI/harness/process-only | Low to Medium | Useful as kit packaging example; not semantic proof. |

### `lex:` upper ontology classification

| Group | Terms | Classification | ACP use |
|---|---|---|---|
| Foundational classes | `lex:Thing`, `lex:Concrete`, `lex:Physical`, `lex:Event`, `lex:Process`, `lex:Abstract`, `lex:Concept`, `lex:Quality`, `lex:Information` | Base reusable | Generic ACP concepts can fit without importing squad-specific semantics. |
| Document and decision classes | `lex:Document`, `lex:Decision`, `lex:Reference` | Base reusable and ACP-relevant | Directly maps to ACP architecture docs, decisions, references, and evidence records. |
| Semantic relation properties | `lex:relatedTo`, `lex:supports`, `lex:opposes`, `lex:replaces`, `lex:partOf`, `lex:causes`, `lex:requires`, `lex:broader`, `lex:narrower` | Base reusable | Useful for expressing dependency and argument structure, but ACP should define stricter domain predicates where needed. |
| Link and mention properties | `lex:mentions`, `lex:linksTo`, `lex:hasUnresolvedLink`, `lex:unresolvedPredicate` | Base reusable, runtime proof required for extraction behavior | File-proven ontology terms exist; actual extraction quality must be tested against ACP docs. |
| Git/observation provenance | `lex:mentionedInBlob`, `lex:observedInCommit`, `lex:observedBy`, `lex:observedAt`, `lex:confidence`, `lex:extractor`, `lex:filePath`, `lex:blobHash`, `lex:retracted` | ACP-relevant, runtime proof required | Strong fit for evidence provenance; must prove generated triples are stable and queryable. |
| Human-readable metadata | `lex:name`, `lex:description`, `lex:alias`, `lex:externalLink`, `lex:mentionedInPath`, `lex:sourceDocument`, `lex:unresolvedSlug` | Base reusable | Safe vocabulary for ACP metadata and cross-document references. |

### `git:` provenance ontology classification

| Group | Terms | Classification | ACP use |
|---|---|---|---|
| Git object classes | `git:Commit`, `git:Actor`, `git:Blob`, `git:Reference`, `git:Branch`, `git:Tag`, `git:Changeset`, `git:File` | Base reusable | Directly relevant to ACP claims about source provenance and repo history. |
| Commit identity and message | `git:hexsha`, `git:message`, `git:authoredDate`, `git:committedDate` | Base reusable | Good ACP provenance primitives if generated from actual git history. |
| Actor model | `git:author`, `git:committer`, `git:actorName`, `git:email`, plus transitional `git:authorName`, `git:authorEmail`, `git:committerName`, `git:committerEmail` | Base reusable with migration caveat | ACP should prefer actor object properties while tolerating transitional literal fields in existing output. |
| History topology | `git:parent`, `git:changed`, `git:commit` | Base reusable, runtime proof required | Ontology supports history traversal; sync/history graph execution must prove completeness. |
| File/blob/change details | `git:path`, `git:blobHash`, `git:blob`, `git:size`, `git:type`, `git:language`, `git:changeType`, `git:renamedTo`, `git:shortName`, `git:blamedAuthor`, `git:blamedEmail` | ACP-relevant, runtime proof required | Valuable for ACP traceability and blame/evidence views, but file-level coverage needs execution proof. |

### `fm:` frontmatter ontology classification

| Group | Terms | Classification | ACP use |
|---|---|---|---|
| Document location and title | `fm:path`, `fm:title` | Base reusable | Useful for ACP document indexing. |
| Taxonomy/status | `fm:tags`, `fm:status`, `fm:project`, `fm:technologies` | Base reusable but schema-light | ACP likely needs stricter controlled vocabularies or SHACL constraints for production use. |
| Authorship/date | `fm:author`, `fm:date` | ACP-relevant, runtime proof required | Useful if frontmatter extraction preserves exact values and date normalization expectations. |

### `squad:` ontology classification

| Group | Terms | Classification | ACP use |
|---|---|---|---|
| Identity and communication | `squad:Squaddie`, `squad:Message`, `squad:Pod`, `squad:Proclamation`, `squad:worksOn`, `squad:from`, `squad:to`, `squad:inReplyTo`, `squad:squadMembers`, `squad:podMembers` | Domain-specific | Mostly not ACP-core; could inform multi-agent collaboration modeling. |
| Work model | `squad:Project`, `squad:Task`, `squad:taskId`, `squad:taskStatus`, `squad:assignedTo`, `squad:blocks`, `squad:blockedBy`, `squad:projectStatus`, `squad:priority` | ACP-relevant subset | Useful prior art for ACP tasks/dependencies if not already covered by GSD artifacts. |
| Decision/knowledge model | `squad:Decision`, `squad:Discovery`, `squad:Brief`, `squad:Situation`, `squad:Freeform`, `squad:Bug`, plus `squad:rationale`, `squad:outcome`, `squad:sources`, `squad:takeaways`, `squad:confidence`, `squad:blockers`, `squad:bugSeverity` | ACP-relevant subset | Decision, evidence brief, discovery, situation, and bug vocabulary overlap ACP review workflows. |
| Harness/status properties | `squad:soulId`, `squad:substrate`, `squad:role`, `squad:expertise`, `squad:messageStatus`, `squad:podStatus`, `squad:repo`, `squad:type` | Domain-specific or UI/process-only | Reuse only if ACP explicitly models agents/pods; otherwise avoid coupling ACP to squad identity terms. |
| Cross-reference properties | `squad:relatedDecision`, `squad:relatedTo`, `squad:mentions`, `squad:regarding`, `squad:project`, `squad:pod`, `squad:affectsProject` | ACP-relevant but domain-namespaced | Consider replacing with ACP-native predicates or base `lex:` predicates to avoid squad namespace leakage. |

## T02: Main git-lex semantic web claim review

### File/code-proven semantic web capabilities

| Claim area | File-backed evidence | Evidence level | ACP interpretation |
|---|---|---|---|
| RDF/OWL ontologies | `ontology/git-lex/{lex,git,fm}/`, kit ontology TTL files, `owl:Ontology`, `owl:Class`, `owl:ObjectProperty`, `owl:DatatypeProperty` | File-proven | git-lex ships OWL/Turtle vocabularies for base and kit semantics. |
| Oxigraph RDF store | `Cargo.toml` depends on `oxigraph = { version = "0.5.6", features = ["rdf-12"] }`; `src/lib.rs` and `src/main.rs` reference `.git/lex/oxigraph` | Code-backed, runtime-unverified | Store implementation is present; ACP still needs local build/sync/query proof. |
| SPARQL query surface | `README.md` documents `git lex query "SELECT ..."`; `src/main.rs` parses/evaluates queries; `src/bin/git-lex-serve.rs` exposes `/api/query`; `viz/js/main.js` issues SPARQL | Code-backed, runtime-unverified | Strong source evidence for SPARQL support; must run representative SELECT/CONSTRUCT queries before relying on it. |
| SHACL generation | `src/shacl.rs` generates SHACL shapes from OWL ontology via SPARQL; `README.md` describes SHACL-validated graph; `src/main.rs` builds shapes on init/update | Code-backed, runtime-unverified | SHACL generation is implemented in source; generated shape quality and validation semantics require execution tests. |
| SHACL validation | `src/main.rs` uses `rudof_rdf`, `shacl_rdf`, `shacl_ir`, and `shacl_validation` around lines reported by source scan | Code-backed, runtime-unverified | Validation path exists but is dependency-sensitive; README warns source installs require `--locked` because rudof family versions are coupled. |
| N-Quads generation/loading | `src/nquad.rs` generates virtual N-Quads; `src/main.rs` loads `RdfFormat::NQuads` into oxigraph; `git lex sync` docs rebuild store from `.spo` sidecars | Code-backed, runtime-unverified | Core graph materialization path appears N-Quads-based; ACP needs runtime proof for expected graph partitioning. |
| Named graphs | `src/main.rs` has command help noting union of all named graphs by default; source clears/loads graphs via `GraphName`; `viz/js/main.js` scopes queries to frontmatter named graph | Code-backed, runtime-unverified | Named graph support is implemented against Oxigraph; exact graph URIs and lifecycle need testing. |
| RDF 1.2 quoted/triple terms | `Cargo.toml` enables `rdf-12`; `src/spo_events.rs` wraps events with `rdf:reifies <<( s p o )>>`; `src/main.rs` emits and queries triple terms in history verification | Code-backed, runtime-unverified | Promising for history graph annotations; not proven until sync/history verify succeeds locally. |
| History graph | `src/spo_events.rs` documents history graph ingest; `src/main.rs` has history graph incremental update and `history-verify` reconstruction comments | Code-backed, runtime-unverified | ACP should treat history graph as candidate capability pending execution evidence. |
| Visualization of semantic graph | `viz/README.md`, `viz/index.html`, `viz/js/main.js` | UI-only | Useful for demos/inspection; not evidence of semantic correctness. |

### Claims not proven by this review

| Claim | Why runtime proof is still required |
|---|---|
| `git lex init --kit ...` creates the expected `.lex/` layout for base/squad kits | Reviewed kit files and source only; did not execute init. |
| `git lex sync` produces complete SPARQL-queryable data from sidecars | Source code exists, but no store was built in this task. |
| SHACL validation correctly accepts/rejects ACP documents | Validation code exists, but no ACP fixture was validated. |
| RDF 1.2 quoted triple / `rdf:reifies <<( ... )>>` queries work in the installed runtime | Code and dependency flags exist, but Oxigraph parser/evaluator behavior must be tested. |
| Named graph contents are stable and isolated as expected | Source references named graphs; graph URI inventory requires runtime query. |
| JSON-LD support | This review found RDF/Turtle, N-Quads, SHACL, SPARQL, and JSON query-result surfaces, but no file-backed JSON-LD import/export implementation in the scanned evidence. |
| SPARQL-star syntax compatibility | Source uses RDF 1.2 triple-term syntax; this does not by itself prove SPARQL-star compatibility claims. |

### Runtime proof checklist for follow-up

1. Build or run `git lex --help` from `/root/vendor-source/git-lex` with locked dependencies.
2. Initialize a scratch repo with `git lex init --kit base` and/or `git lex init --kit squad`.
3. Create representative documents with frontmatter and ontology-backed classes.
4. Run `git lex sync`, then query:
   - class inventory (`SELECT ?class WHERE { ?class a owl:Class }`),
   - git provenance (`git:Commit`, `git:Blob`, `git:Changeset`),
   - frontmatter named graph contents,
   - history graph annotation triples using `rdf:reifies <<( ?s ?p ?o )>>`.
5. Run SHACL validation on both valid and intentionally invalid fixtures.
6. Record exact graph URIs, N-Quads samples, and query outputs before promoting any claim to ACP architecture fact.

## T03: ACP semantic web claim matrix

Status vocabulary for ACP follow-up:

- **supported**: sufficient source/file evidence exists for the narrow statement, and ACP may reference it as source-reviewed fact.
- **partially supported**: source evidence exists, but the ACP claim must include a runtime-proof qualifier.
- **unproven**: no source/runtime evidence in this review is sufficient for ACP adoption claims.
- **blocked**: cannot be upgraded without a missing dependency, failing command, or explicit runtime gap being resolved.
- **not applicable**: the capability is demonstrational, UI-only, or outside ACP's current semantic evidence needs.

### Claim matrix

| Claim | Status | Evidence class | What ACP may say now | Forbidden inference | Exact S04 runtime checks needed to upgrade |
|---|---|---|---|---|---|
| Base `lex:` OWL/Turtle ontology exists and defines generic document, decision, reference, relation, mention, and provenance terms. | supported | File-proven ontology files in base kit and main git-lex ontology tree. | ACP may cite `lex:` as a reviewed reusable vocabulary candidate. | Do not infer extraction accuracy, SHACL enforcement, or queryability from ontology files alone. | Run `git lex init --kit base`; verify copied ontology paths; query `SELECT ?c WHERE { ?c a owl:Class }`; preserve output showing `lex:Document`, `lex:Decision`, and `lex:Reference`. |
| Base `git:` OWL/Turtle ontology exists for commits, actors, blobs, refs, changesets, and files. | supported | File-proven ontology files. | ACP may cite `git:` as source-reviewed git provenance vocabulary. | Do not infer complete repository history ingestion, blame correctness, or rename handling. | Run `git lex sync` in a scratch git repo; query `git:Commit`, `git:Blob`, `git:Changeset`, `git:File`; compare counts with `git log` and tracked files. |
| Base `fm:` ontology exists for frontmatter-like metadata. | supported | File-proven ontology files. | ACP may cite `fm:` as a lightweight metadata vocabulary candidate. | Do not infer ACP frontmatter values are parsed, typed, normalized, or validated. | Add fixture markdown with title/date/tags/status; run sync; query frontmatter named graph for `fm:title`, `fm:date`, `fm:tags`, `fm:status`; record literal values and datatypes. |
| Squad kit ontology and content harness exist. | supported | File-proven squad `kit.yml`, ontology, and harness files. | ACP may treat squad kit as domain prior art and packaging example. | Do not infer squad concepts are ACP-native, production-safe, or required for ACP. | Run `git lex init --kit squad` in a scratch repo; verify folder layout and ontology loading; query `squad:Task`, `squad:Decision`, and `squad:Brief` only as migration candidates. |
| Oxigraph-backed RDF store is used by git-lex. | partially supported | Code-backed dependency and source references. | ACP may say source code is written around Oxigraph and `.git/lex/oxigraph`. | Do not claim local build success, store durability, query performance, or deployed compatibility. | Build with locked dependencies; run `git lex --help`; run init/sync/query; capture `.git/lex/oxigraph` creation and successful query output. |
| SPARQL SELECT query surface exists in CLI/server/UI code. | partially supported | Code-backed CLI/API/UI references. | ACP may say SPARQL query paths are implemented in source. | Do not claim arbitrary SPARQL coverage, API stability, auth behavior, or result correctness. | Execute CLI `git lex query 'SELECT ...'`; if server is in scope, run local server and POST `/api/query`; compare result rows against fixture triples. |
| SHACL shape generation from ontology exists. | partially supported | Code-backed `src/shacl.rs` and init/update references. | ACP may say shape-generation code exists. | Do not claim generated shapes are complete, strict enough, or ACP-validating. | Run init/update on fixture ontologies; inspect generated SHACL output; verify required classes/properties appear; save exact generated shape snippets. |
| SHACL validation path exists. | partially supported | Code-backed validation imports and main execution path. | ACP may say validation code path exists but is runtime-sensitive. | Do not claim invalid ACP documents are rejected or valid documents accepted. | Create one valid and one intentionally invalid fixture; run validation path; record pass/fail output and the failing constraint ID. |
| N-Quads generation/loading path exists. | partially supported | Code-backed `src/nquad.rs`, `RdfFormat::NQuads`, and sync docs. | ACP may say graph materialization appears N-Quads-based. | Do not infer graph partitioning, stable serialization, or complete sidecar ingestion. | Run sync; export or inspect generated N-Quads; verify named graph column is present; compare sample triples with source sidecars/documents. |
| Named graph support exists in source and visualization queries. | partially supported | Code-backed `GraphName` handling and UI query scoping. | ACP may say named graphs are implemented as a candidate isolation mechanism. | Do not claim graph URI names, lifecycle, isolation, or union semantics are stable. | Query graph inventory with `SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }`; query default union and specific graphs; record URI inventory and row counts. |
| RDF 1.2 quoted/triple-term history annotations appear in source. | partially supported | Code-backed `rdf-12` feature and `rdf:reifies <<( s p o )>>` construction. | ACP may say quoted-triple support is a candidate history-annotation mechanism. | Do not claim SPARQL-star compatibility or Oxigraph runtime acceptance until executed. | Run history fixture; query `rdf:reifies <<( ?s ?p ?o )>>`; run `history-verify`; capture parser/evaluator success or exact error. |
| History graph incremental reconstruction exists in source comments/code paths. | partially supported | Code-backed history ingest/verify source. | ACP may say history graph support is implemented in source but unproven. | Do not claim complete temporal provenance, merge handling, or deterministic replay. | Create multiple commits changing sidecars/docs; run sync and history verification; query before/after events; compare event count to commit diff expectations. |
| Visualization shows semantic graph data. | not applicable | UI-only files and JavaScript queries. | ACP may use it for inspection/demo if runtime data exists. | Do not treat visual rendering as semantic correctness, validation, provenance, or completeness evidence. | Optional S04 demo check only: run UI against a proven store and verify it does not contradict CLI query results. |
| JSON query-result surfaces exist. | partially supported | Code/UI surfaces returning JSON results, not JSON-LD. | ACP may say some query APIs return JSON-shaped results if runtime proves it. | Do not infer JSON-LD import/export, JSON-LD context handling, framing, compaction, or expansion. | Run CLI/API query and inspect JSON response if supported; separately search/execute JSON-LD import/export commands before making any JSON-LD claim. |
| JSON-LD import/export support exists. | unproven | No file-backed implementation found in this review. | ACP should say JSON-LD support is not established. | Do not infer JSON-LD from JSON API responses, RDF support, Turtle files, or web UI serialization. | S04 may upgrade only after finding an explicit JSON-LD parser/serializer dependency/path and executing import/export round trip with a JSON-LD fixture. |
| SPARQL-star compatibility exists. | unproven | Source uses RDF 1.2 triple terms, not a proven SPARQL-star compatibility contract. | ACP should say SPARQL-star support is not established. | Do not equate RDF 1.2 quoted triples, Oxigraph `rdf-12`, or `rdf:reifies` syntax with general SPARQL-star support. | Execute a SPARQL-star-specific fixture/query if ACP needs this; otherwise keep out of ACP claims. |
| ACP production readiness of git-lex semantic stack. | blocked | Runtime proof absent for build, init, sync, validation, query, history, and graph inventory. | ACP may only describe git-lex as a source-reviewed candidate. | Do not state ACP can rely on it operationally, at scale, or with legal evidence until S04 passes. | Complete S04 smoke suite: locked build, scratch init, sync, graph inventory, positive/negative SHACL, quoted triple query, named graph isolation, history verification, and captured outputs. |

### Forbidden inference checklist

- Ontology files prove vocabulary existence, not extraction behavior, validation behavior, or graph completeness.
- Cargo dependencies and source references prove implementation intent, not a working local runtime.
- JSON response bodies do not prove JSON-LD support.
- RDF 1.2 quoted triple code does not prove broad SPARQL-star compatibility.
- Visualization assets do not prove semantic correctness.
- Squad kit prior art does not make `squad:` an ACP domain model.
- Source-reviewed git provenance terms do not prove complete, deterministic, or legally sufficient evidence lineage.

### S04 upgrade checks

S04 should only upgrade a claim after recording command output, fixture inputs, and exact query results for the relevant row in the matrix. Minimum shared checks:

1. Build/run check: `cargo run --locked -- --help` or the project-supported equivalent from the git-lex checkout.
2. Kit install check: scratch repository `git lex init --kit base` and `git lex init --kit squad` where applicable.
3. Sync check: create fixture markdown/sidecar/git history, run `git lex sync`, and prove store creation.
4. Query check: run class inventory, git provenance, frontmatter, named graph inventory, and history annotation queries.
5. Validation check: run SHACL against one valid fixture and one intentionally invalid fixture.
6. Serialization check: capture N-Quads samples and any JSON response surfaces separately; require explicit parser/serializer proof for JSON-LD.
7. Regression check: keep negative fixtures for unsupported JSON-LD/SPARQL-star in S04 so unsupported claims fail closed rather than silently becoming marketing claims.

### Failure Modes

| Dependency | Failure path | Handling/expected evidence |
|---|---|---|
| Local filesystem artifact `prd/architecture/acp/M051-S03-GIT-LEX-SEMANTIC-WEB-REVIEW.md` | Missing or unreadable file prevents updating the matrix. | This task verified the file existed and extended it in place; verification grep fails loudly if the file is absent. |
| Source-review evidence from prior T01/T02 summaries and existing document sections | Malformed or incomplete prior evidence could overstate support. | Matrix keeps runtime-sensitive claims at `partially supported`, `unproven`, or `blocked` unless previous sections give file/source evidence. |
| Shell/grep verification | Bad pattern, missing file, or malformed content returns non-zero. | Planned grep command is the close-gate check and bubbles failure directly. |

### Load Profile

This task has no runtime load dimension. The generated matrix is static documentation; S04 runtime work must establish load or scale limits separately if ACP intends to operationalize git-lex.

### Negative Tests

| Negative surface | Guard in this artifact |
|---|---|
| Marketing drift from file evidence to runtime support | Claim matrix separates `supported`, `partially supported`, `unproven`, `blocked`, and `not applicable`. |
| JSON API response misread as JSON-LD | JSON-LD row is `unproven`, with an explicit forbidden inference and required round-trip check. |
| RDF 1.2 triple-term code misread as SPARQL-star support | SPARQL-star row is `unproven`, with a specific compatibility check required only if ACP needs the claim. |
| UI visualization misread as semantic correctness | Visualization row is `not applicable` for core ACP capability proof. |
| Squad kit prior art imported as ACP-native model | Squad row restricts current use to source-reviewed prior art and packaging evidence. |

## Preliminary ACP recommendation

- Treat `lex:`, `git:`, and selected `fm:` terms as the most reusable base substrate for ACP semantic evidence.
- Treat `squad:` as domain prior art: useful for task/decision/brief vocabulary review, but do not import it wholesale into ACP unless ACP intentionally models multi-agent squads.
- Treat SPARQL, SHACL, N-Quads, named graphs, RDF 1.2 quoted triples, and history graphs as source-backed candidate capabilities that still require runtime proof.
- Treat JSON-LD and SPARQL-star as unproven for ACP based on this source review; do not claim support without additional evidence.
