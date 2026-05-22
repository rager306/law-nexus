# M045 RDF SHACL SPARQL Projection Contract

## Status

Accepted for S02 implementation planning.

## Decision

M045 may implement a minimal RDF/SHACL/SPARQL projection proof as a derived, non-authoritative interoperability and recovery layer over the current default architecture registry.

The projection must use the M044 default canonical architecture registry as input:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

The projection owner for S02 is a new explicit projection workflow, tentatively `scripts/export-architecture-rdf-projection.py`. It must read the generated canonical JSONL registry and write only approved derived output paths.

## Approved S02 implementation mode

S02 should implement a custom-only derived projection proof, not a new authority surface and not a default source-of-truth replacement.

Approved generated paths:

- `prd/architecture/acp/derived/architecture-projection.ttl`
- `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
- `prd/architecture/acp/derived/architecture-projection.sparql`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

S02 may choose deterministic stdlib generation and smoke validation rather than adding RDF dependencies. If a dependency is proposed, S02 must justify it in tests and keep it bounded to projection verification, not architecture authority.

## Vocabulary scope

The first projection may use a compact project-local namespace, for example:

- `lgarch:` for LegalGraph architecture registry concepts
- `acp:` for ACP governance extensions
- `rdf:` and `rdfs:` for basic RDF typing and labels
- `sh:` only in the generated SHACL-shaped artifact

The minimal item projection should preserve:

- stable record identity from registry IDs;
- `record_kind` and `type`;
- lifecycle `status`;
- `layer`;
- `proof_level`;
- `risk_level`;
- `generated_draft`;
- non-claims as explicit projection literals;
- source-anchor path and selector or section metadata;
- ACP fields such as `acp_record_kind`, `acp_source_record_id`, `capture_mode`, `redaction_status`, `authority_required`, `allowed_next_actions`, `blocked_actions`, and `acp_non_mappable` when present.

The minimal edge projection should preserve:

- stable edge identity from registry edge IDs;
- relationship `type`;
- `from` and `to` endpoints;
- lifecycle `status`;
- source-anchor metadata.

This is a projection of existing registry records. It must not infer new architecture claims from broad Markdown scans, LLM summaries, source-code analysis, or generated graph reports.

## Identity and addressing rules

The projection should use stable repository-local IRIs derived from registry IDs, not mutable branch URLs and not local absolute paths.

Allowed identity pattern:

```text
urn:law-nexus:architecture:<registry-id>
```

Allowed source-anchor node pattern:

```text
urn:law-nexus:architecture-source:<hash>
```

The projection may include repository-relative source paths as literals. It must not include absolute local paths, `.gsd/exec` anchors, raw provider payloads, secrets, raw vectors, or bulky debug dumps.

## SHACL scope

The SHACL artifact is a minimal shape-smoke contract, not a complete ontology validation layer.

S02 should check at least:

- item resources have an ID, type, status, layer, proof level, and non-authoritative boundary;
- edge resources have `from` and `to` endpoints;
- ACP decision candidates retain `authority_required true`;
- ACP records retain non-claims for R035, R037, and R038;
- source anchors use repository-relative paths.

A passing SHACL-shaped smoke check does not prove ontology correctness, RDF completeness, product readiness, legal correctness, parser completeness, retrieval quality, FalkorDB ingestion/runtime loading, or independent external review.

## SPARQL scope

The SPARQL artifact is a minimal smoke-query handoff. It should include bounded queries that future tools can run against the projection, such as:

- count architecture registry items and edges;
- list ACP governance rows;
- list unresolved proof gates;
- list records carrying non-claims for R035, R037, or R038;
- list high or critical risk records.

S02 may implement deterministic smoke checks without a SPARQL engine if no local dependency is available. In that case, the report must state that the SPARQL file is a handoff artifact and the smoke checks are structural equivalents, not engine-executed SPARQL proof.

## Report requirements

The S02 report must include:

- `status`;
- `non_authoritative: true`;
- input path summary;
- output path summary;
- item count;
- edge count;
- triple or statement count;
- SHACL smoke result summary;
- SPARQL smoke result summary;
- diagnostics with rule, message, path, record ID where applicable;
- explicit non-claims.

## Blocked actions

M045 must not:

- make RDF, SHACL, SPARQL, Turtle, or any triple store the architecture source of truth;
- initialize `git lex` in the main repository;
- write projection output into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`;
- use generated RDF to validate requirements;
- use SHACL smoke output to claim ontology correctness;
- use SPARQL smoke output to claim product runtime behavior;
- use projection artifacts as FalkorDB ingestion proof;
- emit raw legal text, raw vectors, raw provider payloads, secrets, absolute paths, or ignored local-only artifacts;
- treat ACP `decision_candidate` rows as accepted decisions;
- treat proof-gate rows as proof-gate satisfaction.

## Non-claims

This contract does not validate R035.

This contract does not validate R037.

This contract does not validate R038.

This contract does not prove parser completeness, legal correctness, graph-vector retrieval quality, FalkorDB ingestion/runtime loading, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, or product Legal KnowQL behavior.

Projection artifacts remain derived diagnostics and recovery/interoperability aids. They are not legal truth, not product runtime evidence, not accepted architecture doctrine, and not source-of-truth replacements.

## S02 acceptance gates

S02 may proceed only if it preserves these checks:

- default extractor check remains green: `uv run python scripts/extract-prd-architecture-items.py --check`;
- default graph check remains green: `uv run python scripts/build-architecture-graph.py --check`;
- default architecture verifier remains green: `uv run python scripts/verify-architecture-graph.py`;
- projection command supports write and `--check` modes;
- focused tests prove deterministic output and stale-output detection;
- focused tests prove blocked output paths cannot mutate canonical registry JSONL;
- focused tests prove non-claim preservation for ACP rows and requirement boundaries;
- ruff and LSP diagnostics are clean for changed code.

## Final decision required in S03

S03 must decide one of:

1. Keep RDF/SHACL/SPARQL projection custom-only under ACP derived paths.
2. Promote it to a named default generated projection artifact while still derived/non-authoritative.
3. Defer projection adoption and keep only the contract/research evidence.

Any future promotion must keep source evidence authoritative and must not validate R035, R037, R038, product readiness, legal correctness, parser completeness, FalkorDB ingestion, retrieval quality, or independent external review by projection alone.
