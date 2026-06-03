# git-lex ontology map for ACP

## Core mapping

| git-lex surface | Evidence type | ACP interpretation | Cannot prove |
|---|---|---|---|
| `lex:Thing`, `lex:Information`, `lex:Document`, `lex:Decision`, `lex:Process`, `lex:Concept` | Semantic ontology evidence | Candidate upper ontology for reusable ACP classes. ACP classes can subclass these for cross-kit discoverability. | ACP source truth, runtime extraction, or requirement validation. |
| `lex:relatedTo`, `lex:supports`, `lex:opposes`, `lex:replaces`, `lex:partOf`, `lex:requires` | Semantic relation vocabulary | Candidate superproperties for ACP relations such as depends-on, supersedes, supports-claim, blocks, requires-proof. | Correctness of any particular ACP edge. |
| `lex:mentions`, `lex:linksTo`, `lex:externalLink`, `lex:hasUnresolvedLink` | Extraction vocabulary evidence | Useful model for link/recovery diagnostics across ACP/GSD documents. | That extractors run or resolve links correctly. |
| `lex:sourceDocument`, `lex:mentionedInPath`, `lex:mentionedInBlob`, `lex:filePath`, `lex:blobHash` | Provenance vocabulary evidence | Good fit for ACP evidence anchors, staleness checks, and tracked path/blob grounding. | That current tracked artifacts satisfy proof gates. |
| `lex:observedBy`, `lex:observedAt`, `lex:observedInCommit`, `lex:confidence`, `lex:extractor`, `lex:retracted` | Quoted-triple provenance vocabulary | Attractive pattern for ACP claim provenance and multi-agent observations. | RDF 1.2/SPARQL-star runtime support or legal/product authority. |
| `git:Commit`, `git:Blob`, `git:File`, `git:Changeset`, `git:Reference` | Git semantic vocabulary | Useful projection of git provenance for ACP history, freshness, and recovery views. | Actual git extraction behavior. |
| `fm:path`, `fm:title`, `fm:status`, `fm:tags`, dynamic `fm:*` comments | Frontmatter semantic vocabulary | Candidate mapping for GSD/ACP frontmatter and metadata projections. | Actual dynamic extraction until runtime proof. |
| `www/js/main.js` SPARQL endpoint and WebSocket contracts | UI/API contract evidence | Reveals expected query/display/recovery surfaces. | Backend/API existence or correctness. |
| JSON-LD claim | Marketing/architecture claim unless context/exporter exists | Possible future interchange format for ACP records. | Any current base-kit JSON-LD behavior; none was found in inspected files. |

## Recommended ACP layering

```text
lex:   universal git-lex upper ontology and generic relations
git:   git object/provenance vocabulary
fm:    frontmatter vocabulary
acp:   reusable Architecture Control Plane ontology
lgn:   law-nexus profile ontology for Russian legal/FalkorDB/parser constraints
```

Keep `acp:` reusable. Keep `lgn:` profile-specific. Do not put law-nexus legal/runtime assumptions into `lex:` or generic ACP core.

## High-value ACP use cases

- Query accepted decisions without proof gates.
- Find requirements validated only by projection evidence.
- Trace records to tracked paths and blob hashes.
- Detect stale evidence anchors after file changes.
- Preserve multi-agent claim provenance without making LLM output authoritative.
- Build recovery dashboards and inspection UIs over non-authoritative projections.


## M051 S08 prototype mapping

S08 created `prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl` as a proposed, non-authoritative static scaffold.

| ACP prototype surface | git-lex mapping | Boundary |
|---|---|---|
| `acp:SourceRecord` | `rdfs:subClassOf lex:Document` | Source authority still requires lifecycle + evidence anchor + proof gate. |
| `acp:Decision` | `rdfs:subClassOf lex:Decision` | Decision authority comes from accepted ACP decision evidence, not RDF shape. |
| `acp:EvidenceAnchor` | `rdfs:subClassOf lex:Reference`; source path resembles `fm:path` usage | Must remain tracked repository-relative; no `.gsd/exec`, absolute paths, secrets, raw legal text, provider payloads, or vectors. |
| `acp:ProofGate` | `rdfs:subClassOf lex:Process` | Gate definition is not gate satisfaction. |
| `acp:Projection` | `rdfs:subClassOf lex:Information` | Derived/non-authoritative unless explicitly tied back to source/proof. |
| `acp:RuntimeAdapter` | `rdfs:subClassOf lex:Process` | git-lex adapter remains deferred until explicit adoption proof. |

S08 also created JSON-LD and SHACL files, but only as static-check scaffolds. JSON-LD expansion/roundtrip, RDF/SPARQL engine execution, SHACL engine validation, and OWL entailment remain unproven.

## M051 S10 query semantics

- Use `git-lex list --json` for runtime class discovery.
- Use SPARQL `GRAPH ?g { ?s ?p ?o }` for named graph inventory after committed `sync` in an isolated repo.
- Use `query --json` for SELECT/ASK machine parsing only; do not rely on CONSTRUCT/DESCRIBE JSON.
- Treat `owl:Class` and `sh:targetClass` graph queries as expected-empty unless ontology/shape triples are explicitly loaded.

## M052 S02 JSON-LD runtime boundary

M052/S02 rechecked the JSON-LD claim and found no git-lex runtime RDF import/export surface.

Safe ACP wording:

```text
ACP may maintain JSON-LD static interchange/prototype artifacts independently of git-lex, but current git-lex runtime JSON-LD RDF import/export is unsupported/not observed.
```

Unsafe ACP wording:

```text
git-lex supports JSON-LD import/export or roundtrip for ACP records.
```

Boundary:

- A `.jsonld` file can be recorded as a file with language metadata.
- That does not mean git-lex parses JSON-LD into RDF graph facts or exports graph facts as JSON-LD.
- Transitive JSON-LD-related crates are not proof unless a source call path and runtime behavior are demonstrated.

## M052 S03 SPARQL-star query boundary

M052/S03 upgraded one narrow SPARQL-star capability from unproven to runtime-backed:

```sparql
SELECT ?ann ?s ?p ?o WHERE {
  ?ann <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> <<( ?s ?p ?o )>> .
}
LIMIT 10
```

In an isolated synced repo with history annotations, `git-lex query` accepted explicit `<<( ?s ?p ?o )>>` syntax; SELECT returned rows and ASK returned `true`. `query --json` also returned `Term::Triple` bindings as a non-standard `{ "type": "triple" }` shape.

Safe ACP wording:

```text
git-lex user-facing SPARQL-star support is runtime-backed for history-graph
`rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns in the observed build.
```

Unsafe ACP wording:

```text
git-lex has full RDF-star/SPARQL-star feature parity.
```

Still not proven:

- broad RDF-star/SPARQL-star parity;
- quoted-triple subject storage semantics;
- production compatibility guarantees beyond the observed source-built debug binary;
- SPARQL-star support outside git-lex history graph annotations.
