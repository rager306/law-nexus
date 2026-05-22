# M045 RDF Projection Design Check

## Status

Design checked for S02 implementation. This artifact is a pre-implementation structure check, not generated projection output.

## Input snapshot

The projection design targets the current default architecture registry shape:

- input items: 63
- input edges: 98
- ACP governance items: 5
- ACP governance edges: 7

Inputs remain:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

Those JSONL files are generated registry projections, not architecture source truth. PRD/GSD/ADR/source/runtime evidence remains authoritative.

## Design conclusion

Use a deterministic stdlib-first Turtle/SHACL/SPARQL output design for S02.

Do not add an RDF dependency for the first proof. The first proof can safely validate structural projection invariants with deterministic Python checks and produce SPARQL as a handoff artifact. A later milestone may add `rdflib`, `pyshacl`, or git-lex runtime integration if the custom projection proof shows the shape is useful.

## Turtle structure

### Prefixes

The Turtle output should start with stable prefixes:

```turtle
@prefix lgarch: <urn:law-nexus:vocab:architecture:> .
@prefix acp: <urn:law-nexus:vocab:acp:> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

SHACL prefixes belong in the SHACL artifact, not necessarily the main Turtle artifact:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
```

### Subject identity

Each registry item and edge should use a stable repository-local IRI:

```text
urn:law-nexus:architecture:<record-id>
```

Examples:

```turtle
<urn:law-nexus:architecture:ACP-DC-0001> a lgarch:DecisionCandidate, lgarch:ArchitectureItem .
<urn:law-nexus:architecture:ACP-EDGE-DC-0001-requiresProof-PG-0001> a lgarch:ArchitectureEdge .
```

Do not use branch URLs, forge UI URLs, absolute local paths, or `.gsd/exec` paths as identity.

### Minimal item triples

Every item resource should emit these predicates when present:

```turtle
<urn:law-nexus:architecture:ACP-DC-0001>
  a lgarch:ArchitectureItem, lgarch:DecisionCandidate ;
  lgarch:recordId "ACP-DC-0001" ;
  lgarch:recordKind "item" ;
  lgarch:itemType "decision_candidate" ;
  lgarch:status "active" ;
  lgarch:layer "architecture-governance" ;
  lgarch:proofLevel "source-anchor" ;
  lgarch:riskLevel "medium" ;
  lgarch:generatedDraft false ;
  rdfs:label "..." .
```

Optional fields should be projected only when present. Lists should emit repeated predicates rather than serialized JSON strings when the values are simple strings:

```turtle
<urn:law-nexus:architecture:ACP-DC-0001>
  lgarch:nonClaim "Does not validate R035." ;
  lgarch:nonClaim "Does not validate R037." ;
  lgarch:nonClaim "Does not validate R038." ;
  acp:blockedAction "treat_as_accepted_decision" ;
  acp:authorityRequired true .
```

### Minimal edge triples

Every edge resource should emit these predicates:

```turtle
<urn:law-nexus:architecture:ACP-EDGE-DC-0001-requiresProof-PG-0001>
  a lgarch:ArchitectureEdge ;
  lgarch:recordId "ACP-EDGE-DC-0001-requiresProof-PG-0001" ;
  lgarch:recordKind "edge" ;
  lgarch:edgeType "requires_proof" ;
  lgarch:status "active" ;
  lgarch:from <urn:law-nexus:architecture:ACP-DC-0001> ;
  lgarch:to <urn:law-nexus:architecture:ACP-PG-0001> .
```

The projection may also emit the relationship as a generic graph predicate for traversal:

```turtle
<urn:law-nexus:architecture:ACP-DC-0001>
  lgarch:requiresProof <urn:law-nexus:architecture:ACP-PG-0001> .
```

Keep both forms if useful: the edge-resource form preserves registry edge metadata, while the direct predicate improves graph queries.

### Source-anchor representation

Source anchors should be blank nodes or deterministic source nodes. Prefer deterministic source nodes to simplify checks:

```text
urn:law-nexus:architecture-source:<sha256-prefix>
```

Example shape:

```turtle
<urn:law-nexus:architecture:ACP-DC-0001>
  lgarch:sourceAnchor <urn:law-nexus:architecture-source:abc123def456> .

<urn:law-nexus:architecture-source:abc123def456>
  a lgarch:SourceAnchor ;
  lgarch:path "prd/architecture/acp/fixtures/minimal-chain/DC-0001.md" ;
  lgarch:kind "manual-note" ;
  lgarch:selector "DecisionCandidate" .
```

Source-anchor paths must remain repository-relative. The projection must reject absolute paths and `.gsd/exec` paths.

## SHACL structure

The SHACL artifact should be a minimal smoke-shape file. It is not a complete ontology.

Suggested top-level shapes:

```turtle
lgarch:ArchitectureItemShape a sh:NodeShape ;
  sh:targetClass lgarch:ArchitectureItem ;
  sh:property [ sh:path lgarch:recordId ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:itemType ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:status ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:layer ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:proofLevel ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:sourceAnchor ; sh:minCount 1 ] .

lgarch:ArchitectureEdgeShape a sh:NodeShape ;
  sh:targetClass lgarch:ArchitectureEdge ;
  sh:property [ sh:path lgarch:recordId ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:edgeType ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:from ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:to ; sh:minCount 1 ] .

acp:DecisionCandidateShape a sh:NodeShape ;
  sh:targetClass lgarch:DecisionCandidate ;
  sh:property [ sh:path acp:authorityRequired ; sh:hasValue true ] .
```

The deterministic smoke validator in S02 should check equivalent invariants directly over JSONL/projection structures. It should not claim SHACL engine execution unless an actual SHACL engine is introduced and invoked.

## SPARQL structure

The SPARQL artifact should be a handoff query file with compact queries that match the emitted predicates.

Recommended queries:

```sparql
PREFIX lgarch: <urn:law-nexus:vocab:architecture:>
PREFIX acp: <urn:law-nexus:vocab:acp:>

SELECT (COUNT(?item) AS ?itemCount)
WHERE { ?item a lgarch:ArchitectureItem . }

SELECT (COUNT(?edge) AS ?edgeCount)
WHERE { ?edge a lgarch:ArchitectureEdge . }

SELECT ?item ?type ?status
WHERE {
  ?item a lgarch:ArchitectureItem ;
        lgarch:itemType ?type ;
        lgarch:status ?status .
  FILTER(STRSTARTS(STR(?item), "urn:law-nexus:architecture:ACP-"))
}

SELECT ?item ?claim
WHERE {
  ?item lgarch:nonClaim ?claim .
  FILTER(?claim IN ("Does not validate R035.", "Does not validate R037.", "Does not validate R038."))
}

SELECT ?gate ?status
WHERE {
  ?gate a lgarch:ArchitectureItem ;
        lgarch:itemType "proof_gate" ;
        lgarch:status ?status .
}
```

The S02 report should be explicit if these queries are generated but not engine-executed.

## Report structure

The report should be JSON and deterministic. Suggested shape:

```json
{
  "status": "ok",
  "non_authoritative": true,
  "mode": "write|check",
  "inputs": {
    "items": "prd/architecture/architecture_items.jsonl",
    "edges": "prd/architecture/architecture_edges.jsonl"
  },
  "outputs": {
    "ttl": "prd/architecture/acp/derived/architecture-projection.ttl",
    "shacl": "prd/architecture/acp/derived/architecture-projection.shacl.ttl",
    "sparql": "prd/architecture/acp/derived/architecture-projection.sparql",
    "report": "prd/architecture/acp/derived/architecture-projection-rdf-report.json"
  },
  "counts": {
    "items": 63,
    "edges": 98,
    "acp_items": 5,
    "acp_edges": 7,
    "rdf_resources": 0,
    "statements": 0
  },
  "shape_smoke": {
    "status": "ok",
    "engine": "deterministic-structural-check",
    "checked_rules": []
  },
  "sparql_smoke": {
    "status": "ok",
    "engine": "not-executed",
    "handoff_queries": []
  },
  "diagnostic_count": 0,
  "diagnostics": [],
  "non_claims": []
}
```

## Escaping and determinism rules

Implementation should use boring deterministic rules:

- sort records by `id`;
- sort predicates within each resource by a fixed order;
- escape Turtle string literals for backslash, quote, newline, carriage return, and tab;
- emit booleans as `true` or `false`;
- do not emit null values;
- emit repeated simple-list values as repeated predicates;
- use stable SHA-256 over anchor path/kind/selector/section/line fields for source-anchor node IDs;
- write files with trailing newline;
- `--check` must compare byte-for-byte expected output.

## Safety checks before implementation

The exporter should fail closed on:

- duplicate item IDs;
- duplicate edge IDs;
- missing edge endpoints;
- absolute source-anchor paths;
- `.gsd/exec` source-anchor paths;
- attempts to write `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`;
- missing ACP non-claims for R035, R037, or R038;
- `decision_candidate` rows without `authority_required true`;
- forbidden overclaim markers in generated text.

## Non-claims

This design check does not validate R035.

This design check does not validate R037.

This design check does not validate R038.

This design check does not prove parser completeness, legal correctness, graph-vector retrieval quality, FalkorDB ingestion/runtime loading, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, or product Legal KnowQL behavior.

The planned Turtle, SHACL, SPARQL, and report artifacts are derived diagnostics and recovery/interoperability aids. They are not legal truth, not product runtime evidence, not accepted architecture doctrine, and not source-of-truth replacements.

## Recommendation

Proceed with S02 implementation using this structure.

Recommended first implementation path:

1. Build a stdlib exporter with deterministic Turtle, SHACL, SPARQL, and report generation.
2. Treat SHACL and SPARQL as smoke/handoff artifacts unless an actual engine is added and invoked.
3. Keep outputs custom-only under `prd/architecture/acp/derived/`.
4. Add tests for byte-for-byte currentness, safety failures, non-claims, ACP authority requirements, and report counts.
5. Defer dependency-backed RDF/SHACL/SPARQL execution or git-lex runtime integration to a later decision after this shape proves useful.
