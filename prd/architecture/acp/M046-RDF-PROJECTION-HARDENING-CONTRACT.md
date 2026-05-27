# M046 RDF Projection Hardening Contract

## Status

Accepted as the S01 implementation contract for ACP RDF projection hardening.

## Scope

M046 hardens the custom-only RDF/SHACL/SPARQL projection introduced in M045.

The projection remains derived and non-authoritative. It remains an ACP recovery, diagnostics, and interoperability aid. It is not architecture source truth, legal truth, product runtime evidence, accepted architecture doctrine, FalkorDB ingestion proof, or requirement validation proof.

## Inputs

The hardened projection continues to read the generated default architecture registry:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

Those JSONL files are generated registry projections. PRD, GSD, ADR, source, tests, runtime proof, and real-document evidence remain authoritative.

## Approved outputs

The current write/check workflow remains approved:

```bash
uv run python scripts/export-architecture-rdf-projection.py
uv run python scripts/export-architecture-rdf-projection.py --check
```

Approved derived outputs remain:

- `prd/architecture/acp/derived/architecture-projection.ttl`
- `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
- `prd/architecture/acp/derived/architecture-projection.sparql`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

M046 may add a non-writing preview/diff mode. That mode must not mutate files and must not create a new authoritative artifact.

## Vocabulary notes

The projection vocabulary is intentionally small and custom. It is not an ontology completeness claim.

### `lgarch:` namespace

`lgarch: <urn:law-nexus:vocab:architecture:>` represents generic architecture registry projection concepts.

Expected classes include:

- `lgarch:ArchitectureItem`
- `lgarch:ArchitectureEdge`
- `lgarch:SourceAnchor`
- item-type classes derived from registry `type`, such as `lgarch:DecisionCandidate` or `lgarch:ProofGate`

Expected predicates include:

- `lgarch:recordId`
- `lgarch:recordKind`
- `lgarch:itemType`
- `lgarch:edgeType`
- `lgarch:status`
- `lgarch:layer`
- `lgarch:proofLevel`
- `lgarch:riskLevel`
- `lgarch:generatedDraft`
- `lgarch:summary`
- `lgarch:owner`
- `lgarch:verification`
- `lgarch:nonClaim`
- `lgarch:sourceAnchor`
- `lgarch:from`
- `lgarch:to`
- source-anchor predicates such as `lgarch:path`, `lgarch:kind`, `lgarch:selector`, `lgarch:section`, `lgarch:lineStart`, and `lgarch:lineEnd`

### `acp:` namespace

`acp: <urn:law-nexus:vocab:acp:>` represents Architecture Control Plane governance fields projected from the canonical registry.

Expected predicates include:

- `acp:recordKind`
- `acp:sourceRecordId`
- `acp:captureMode`
- `acp:redactionStatus`
- `acp:authorityRequired`
- `acp:nonMappable`
- `acp:allowedNextAction`
- `acp:blockedAction`

### Vocabulary boundary

These vocabulary terms describe the current registry projection shape only. They do not prove RDF completeness, OWL compatibility, SHACL completeness, SPARQL execution correctness, git-lex compatibility, or product architecture authority.

## Diagnostic classes

S02 should preserve existing diagnostic rules and may harden their report shape.

Current required diagnostic classes:

| Rule | Meaning | Minimum remediation hint |
|---|---|---|
| `missing-file` | Input file is absent. | Regenerate or provide the expected generated registry input. |
| `jsonl-parse` | A JSONL line cannot be parsed. | Fix the generating source or regenerated JSONL line. |
| `jsonl-record` | A JSONL line is not an object. | Ensure every JSONL line is an object record. |
| `duplicate-id` | Item or edge ID appears more than once. | Fix source mapping or generator ID derivation. |
| `record-kind` | Item file contains non-item record or edge file contains non-edge record. | Fix source mapping or generator output partitioning. |
| `shape-smoke` | Required item field is missing. | Add the missing generated registry field from source evidence. |
| `source-anchor` | `source_anchors` are missing or malformed. | Add safe tracked source anchors. |
| `unsafe-source-anchor` | Source anchor path is absolute, escaping, or ignored local-only. | Replace with safe repository-relative tracked anchor. |
| `missing-non-claim` | ACP rows lack required R035/R037/R038 non-claims. | Add explicit non-claims in source-owned ACP records. |
| `authority-required` | `decision_candidate` does not require authority. | Set `authority_required: true` for decision candidates. |
| `missing-endpoint` | Edge endpoint does not reference a known item. | Fix edge endpoint or add the missing item through source generation. |
| `forbidden-marker` | Generated output contains a forbidden secret/path/overclaim marker. | Remove secret, local path, or overclaim from generated inputs or templates. |
| `stale-output` | `--check` output does not match generated content. | Run the exporter in write mode after reviewing expected changes. |

S02 may add stable diagnostic metadata fields such as:

- `severity`: `error`, `warning`, or `info`
- `category`: `input`, `shape`, `safety`, `authority`, `freshness`, or `output`
- `remediation`: concise deterministic guidance

Any new fields must remain deterministic and safe. They must not include absolute paths, raw secrets, provider payloads, raw vectors, raw legal-answer prose, or ignored GSD execution anchors.

## Report hardening requirements

The report should remain deterministic JSON.

Required report properties after hardening:

- `status`
- `non_authoritative: true`
- `mode: custom`
- `inputs`
- `outputs`
- `counts`
- `shape_smoke`
- `sparql_smoke`
- `diagnostic_count`
- `diagnostics`
- `non_claims`

S02 may add:

- `vocabulary`
- `diagnostic_summary`
- `safety_boundary`
- `diff` or `preview` section for non-writing diff mode

If added, `vocabulary` should identify namespaces and terms used, but must state that the vocabulary is a custom projection vocabulary and not ontology completeness proof.

If added, `diagnostic_summary` should count diagnostics by rule/category/severity without hiding individual diagnostic rows.

## Optional diff/preview mode

S02 may add a non-writing mode, for example:

```bash
uv run python scripts/export-architecture-rdf-projection.py --diff
```

Required semantics:

- must not write or mutate any output file;
- must compare generated content with current output files;
- must report status and per-output change state;
- must preserve `non_authoritative: true`;
- must fail closed if input validation diagnostics exist;
- must refuse canonical registry output paths exactly like write/check modes;
- must avoid external tools and runtime RDF engines;
- must not create an authority artifact.

Suggested per-output states:

- `current`
- `missing`
- `stale`

Optional deterministic metadata:

- current byte length;
- expected byte length;
- current SHA-256;
- expected SHA-256.

Do not include line-by-line diffs by default if they could expose large generated text. If a future milestone needs detailed diffs, add a bounded explicit flag in that milestone.

## Blocked actions

M046 must not:

- promote RDF/SHACL/SPARQL projection to default generated architecture artifact;
- treat RDF, Turtle, SHACL, SPARQL, or any triple store as architecture source truth;
- add `rdflib`, `pyshacl`, or SPARQL runtime execution;
- claim SHACL engine validation;
- claim SPARQL engine correctness;
- claim RDF or ontology completeness;
- use generated RDF to validate requirements;
- validate R035, R037, or R038;
- treat ACP `decision_candidate` rows as accepted decisions;
- treat proof-gate rows as proof-gate satisfaction;
- run `git lex init` in the main repository;
- cite ignored GSD execution anchors, absolute paths, ignored files, raw provider payloads, raw vectors, or secrets as durable proof anchors.

## Non-claims

This hardening contract does not validate R035.

This hardening contract does not validate R037.

This hardening contract does not validate R038.

This hardening contract does not prove parser completeness, legal correctness, graph-vector retrieval quality, FalkorDB ingestion/runtime loading, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, git-lex compatibility, or product Legal KnowQL behavior.

## S02 implementation acceptance criteria

S02 implementation is acceptable only if:

1. The exporter hardening follows this contract.
2. Projection write/check behavior remains deterministic.
3. Optional diff/preview mode, if implemented, is non-writing and test-covered.
4. Existing M045 focused tests still pass or are updated only to reflect intentional report hardening.
5. New tests cover diagnostic metadata, vocabulary/report additions, and diff/preview semantics if implemented.
6. Default architecture verifier remains green.
7. Marker scans find no forbidden paths, secrets, or authority overclaims.

## Verification commands

Minimum S01/S02 verification commands:

```bash
uv run python scripts/export-architecture-rdf-projection.py --check
uv run pytest tests/test_architecture_rdf_projection.py
uv run python scripts/verify-architecture-graph.py
uv run ruff check scripts/export-architecture-rdf-projection.py tests/test_architecture_rdf_projection.py
```

S02 closeout should also run the relevant ACP/default checks from M045 when exporter behavior changes.
