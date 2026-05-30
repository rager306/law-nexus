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
