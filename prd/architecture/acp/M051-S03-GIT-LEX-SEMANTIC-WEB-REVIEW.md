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

## Preliminary ACP recommendation

- Treat `lex:`, `git:`, and selected `fm:` terms as the most reusable base substrate for ACP semantic evidence.
- Treat `squad:` as domain prior art: useful for task/decision/brief vocabulary review, but do not import it wholesale into ACP unless ACP intentionally models multi-agent squads.
- Treat SPARQL, SHACL, N-Quads, named graphs, RDF 1.2 quoted triples, and history graphs as source-backed candidate capabilities that still require runtime proof.
- Treat JSON-LD and SPARQL-star as unproven for ACP based on this source review; do not claim support without additional evidence.
