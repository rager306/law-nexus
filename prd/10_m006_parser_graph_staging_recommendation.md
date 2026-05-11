# M006 Parser Graph Staging Recommendation

## Purpose

This note captures the proposed extension of the parser stage after M005. The parser stage should expand from a single-document ODT parser proof into a real multi-document parsing and relation-candidate proof using:

- `law-source/garant/44-fz.odt`
- `law-source/garant/PP_60_27-01-2022.odt` (current filename observed in the repository)
- `law-source/consultant/Список документов (5).xml`

The previous root-level duplicate `law-source/Список документов (5).xml` was byte-identical to the consultant-path XML and was removed by human direction during M006 planning. The fixture inventory should fail if that duplicate silently reappears.

## Recommendation

Use NetworkX as a deterministic debug/staging graph layer between parser outputs and FalkorDB.

```text
ODT / Consultant WordML XML
  -> raw extraction artifacts
  -> typed normalized records
  -> validated JSONL
  -> NetworkX MultiDiGraph staging graph
  -> graph invariants / diagnostics / reports
  -> later FalkorDB load proof
```

The NetworkX graph is a derived, non-authoritative staging artifact. It is useful for validating topology, relation direction, duplicate identities, orphan records, provenance coverage, and future FalkorDB load shape. It must not be treated as the product runtime graph or legal evidence source.

## Why NetworkX fits

NetworkX is already a project dependency (`networkx>=3.6.1`) and M004 already established keyed `MultiDiGraph` as the architecture-registry analysis pattern. For parser graph staging, use `nx.MultiDiGraph` rather than `DiGraph` so multiple distinct relations between the same two documents are preserved by edge key.

Recommended pattern:

```python
G = nx.MultiDiGraph()

G.add_node(
    document.id,
    label="Document",
    record=document_record,
)

G.add_edge(
    relation.source_document_id,
    relation.target_document_id,
    key=relation.id,
    type=relation.relation_type,
    record=relation_record,
)
```

Export with NetworkX node-link or adjacency JSON only as a derived debug artifact. Keep JSON attribute keys string-compatible.

## Core records

The parser stage should produce normalized records before graph assembly. Do not build the graph directly from ODT/XML traversal.

Suggested JSONL outputs:

- `parser_documents.jsonl`
- `parser_units.jsonl`
- `parser_source_blocks.jsonl`
- `parser_relation_candidates.jsonl`
- `parser_graph_edges.jsonl`

Suggested record families:

### DocumentRecord

Fields should include stable `id`, source path, source system, document type, number/date/title candidates, parser status, and non-claims.

### SourceBlockRecord

Fields should include stable `id`, `document_id`, `source_path`, `source_member` (for ODT `content.xml`), ordering index, text hash or redaction policy, parser name, and bounded evidence status.

### RelationCandidateRecord

Fields should include stable `id`, `source_document_id`, `target_document_id`, relation type, relation status (`candidate` until validated), evidence source (`consultant-wordml`, `odt-text`, etc.), source path, source location, confidence, and non-claims.

Consultant XML should be treated as relation fixture / prior-art evidence, not legal source of truth. It can propose relation candidates, but it must not automatically promote a relation to legally correct or product validated.

## Graph invariants before FalkorDB

A parser graph verifier should fail if:

- a `RelationCandidate` references missing source or target document IDs;
- a relation edge lacks provenance (`source_path`, extraction method, source location or equivalent);
- a source block lacks a parent document;
- a legal unit lacks a parent document;
- duplicate document identities appear without explicit disambiguation;
- a Consultant XML relation is promoted to authoritative without validation evidence;
- a promoted relation lacks deterministic validation evidence;
- raw `content.xml` ordering is not preserved in emitted source blocks;
- any generated report asserts parser completeness, legal correctness, product ETL readiness, or FalkorDB product runtime readiness.

## Suggested M006 slices

1. **Source Fixture Inventory**
   - inventory both ODT files and consultant XML;
   - classify duplicate XML path;
   - record valid ODT/WordML shape and source status.

2. **Multi-Document ODT Smoke Parser**
   - parse both real ODT files using raw `content.xml` ordering as oracle;
   - preserve bounded parser evidence;
   - do not claim final legal hierarchy.

3. **Consultant Relation Fixture Parser**
   - parse WordML relation fixture;
   - extract relation candidates with source location and confidence;
   - classify Consultant XML as relation fixture, not legal authority.

4. **NetworkX Staging Graph**
   - build keyed `MultiDiGraph` from normalized records;
   - verify topology/provenance invariants;
   - generate lightweight reports.

5. **FalkorDB Load Contract Draft**
   - draft node labels, relationship types, and future Cypher load plan;
   - avoid product load claims unless a separate bounded FalkorDB proof slice executes them.

## Adaptix vs Pydantic for parser records

### Adaptix strengths

Adaptix is already in the project dev dependencies and aligns with the original tooling baseline for data mapping/serialization. It analyzes type hints, supports dataclasses, TypedDict, attrs, SQLAlchemy, Pydantic, and msgspec integrations, and is designed to keep domain models separate from serialization/deserialization concerns. Its own docs argue that Pydantic can blur domain and boundary layers, while Adaptix keeps conversion logic external and configurable through `Retort`.

Adaptix fits best when:

- domain objects are plain dataclasses;
- serialization and mapping should stay outside the domain model;
- conversion rules need to be configured centrally;
- we need mapping between parser DTOs, domain records, graph records, and future FalkorDB load records;
- runtime dependency minimization matters.

Limitations for this stage:

- fewer contributors will immediately know it compared with Pydantic;
- validation/error reporting and JSON Schema generation are less standard in the wider Python data ecosystem;
- external API / fixture boundary validation examples are less familiar to future agents.

### Pydantic strengths

Pydantic v2 is the standard Python validation choice for typed external data boundaries in 2026. It provides `BaseModel`, dataclass validation, `TypeAdapter` for validating lists/TypedDicts/non-BaseModel types, serialization modes, and JSON Schema generation. Pydantic docs show `TypeAdapter(list[Model])` and `TypeAdapter(TypedDict)` as direct fits for validating parser JSONL/list payloads and generating schemas.

Pydantic fits best when:

- parser outputs cross trust boundaries (ODT/XML -> normalized records);
- we need clear validation errors with field paths;
- JSON Schema artifacts are useful for tests/docs/future loaders;
- future agents need immediately recognizable validation contracts;
- validation should be explicit at ETL boundaries.

Limitations for this stage:

- adding Pydantic as runtime dependency changes the project dependency profile;
- using `BaseModel` as domain objects can couple domain logic to validation/serialization concerns;
- strict separation requires discipline: use Pydantic at boundaries, not everywhere.

### Recommendation for LegalGraph Nexus

Use a hybrid boundary:

1. **Pydantic at parser I/O boundaries** for normalized records, JSONL validation, and schema generation.
2. **Dataclasses / plain Python domain records internally** if we need domain purity.
3. **Adaptix for mapping/conversion** between boundary DTOs, internal records, NetworkX records, and future FalkorDB load DTOs when mappings become non-trivial.

For the next proof slice, start with Pydantic models for `DocumentRecord`, `SourceBlockRecord`, and `RelationCandidateRecord` because the immediate risk is malformed external parser output and unclear diagnostics. Keep Adaptix available for later conversion/mapping rather than forcing it to own first-line validation.

## Non-claims

This proposal does not validate parser completeness, final legal hierarchy extraction, legal correctness of Consultant XML links, production ETL readiness, FalkorDB production loading, retrieval quality, Legal KnowQL behavior, or legal-answer correctness.

## Sources consulted

Search query used: `2026 Python graph ETL best practices NetworkX graph data modeling validation Pydantic Polars PyArrow NetworkX graph database staging`.

Additional focused query used: `Adaptix Python 2026 dataclass mapping serialization validation Pydantic comparison documentation Retort`.

Key evidence used:

- Project `pyproject.toml`: `networkx>=3.6.1`, `adaptix` in dev dependencies, Python >=3.13.
- NetworkX stable docs: `MultiDiGraph` node/edge attributes, edge keys, `node_link_data` and adjacency JSON export.
- Pydantic docs: `TypeAdapter`, list/TypedDict validation, JSON Schema generation, serialization.
- Adaptix docs: type-hint driven loading/dumping, `Retort` configuration, dataclass/TypedDict/Pydantic integrations, separation from Pydantic domain-model coupling.
