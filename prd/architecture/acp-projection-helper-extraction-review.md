# ACP Projection Helper Extraction Review

**Milestone:** M076-f3zxm8  
**Slice:** S19  
**Status:** [bounded] extraction review artifact  
**Depends on:** `prd/architecture/onion-governance-boundary-matrix.md`  
**Reviewed scripts:** `scripts/export-acp-architecture-projection.py`, `scripts/export-architecture-rdf-projection.py`  
**Reviewed tests:** `tests/test_acp_architecture_projection.py`, `tests/test_architecture_rdf_projection.py`

## Purpose

This review decides which ACP/RDF architecture projection helper logic may be extracted later into package code and which logic must remain in script proof surfaces. It does not perform the extraction. It preserves the S18 rule that ACP, git-lex, RDF, SHACL, SPARQL, JSON-LD, recovery views, and projection helpers are non-authoritative diagnostics/recovery surfaces.

## Source-truth boundary

ACP projection helper code may only improve deterministic projection mechanics, recovery navigation, and drift diagnostics. It must not become a source of validation truth.

Allowed claims:

- A helper formats or normalizes repository-relative projection data.
- A helper detects stale derived projection output.
- A helper refuses canonical registry mutation.
- A helper preserves non-claim metadata in derived ACP/RDF artifacts.

Forbidden claims:

- ACP/RDF/SPARQL/JSON-LD projection output validates requirements.
- Projection helper output proves legal correctness, parser completeness, retrieval quality, FalkorDB readiness, OpenCypher completeness, or LLM authority.
- Projection helper output is equivalent to the architecture registry, PRD, ADR, GSD requirements, source code, tests, or runtime proof.
- `.lex` or `.gsd/exec` derived output is a durable proof anchor without the original rank 1-3 source/proof reference.

## Candidate classification summary

| Candidate group | Current location | Classification | Rationale |
|---|---|---|---|
| Path display and repository-relative normalization helpers | `display_path`, `normalized_path`, `safe_repo_relative_path` | extract-later | Pure deterministic formatting appears reusable across projection exporters, but extraction must keep canonical registry mutation guards and avoid treating normalized paths as proof. |
| Canonical registry path guards | `is_canonical_registry_path`, canonical output refusal branches | extract-later with tests | Guard logic is reusable and important, but must be extracted only with tests proving canonical `architecture_items.jsonl` and `architecture_edges.jsonl` writes remain blocked. |
| ACP source-reference conversion helpers | `source_anchor_kind`, `convert_source_refs`, `summary_for_record`, `canonical_summary_for_record` | extract-later | These are deterministic projection-shaping helpers. They may move into a package helper only if they keep source/proof anchor references and do not validate source truth. |
| RDF string escaping and IRI helpers | `turtle_string`, `rdf_bool`, `record_iri`, `source_anchor_iri`, `pascal_case`, `edge_predicate` | extract-later | Pure formatting is extractable, but RDF output remains a derived projection. Extraction must preserve authority/non-claim metadata. |
| TTL block builders | `ttl_prefixes`, `finish_block`, `item_ttl`, `edge_ttl`, `source_anchor_ttl`, `build_ttl` | defer | GitNexus impact shows `ttl_prefixes` touches RDF projection output flows. Extract only after a dedicated red/green compatibility slice because generated TTL exact text is part of the current proof surface. |
| SHACL and SPARQL template builders | `build_shacl`, `build_sparql` | defer | These encode projection-specific governance templates and should remain script-owned until a narrower projection-template package boundary exists. |
| Projection validators | `validate_source_anchors`, `validate_items`, `validate_edges`, generated-text validation | extract-later with guardrails | Deterministic validation may be reusable, but validators must remain projection validators only and cannot validate requirements or product architecture by themselves. |
| Output writers and stale-check helpers | `write_output`, `write_jsonl_output`, `check_output`, `check_jsonl_output`, `output_state`, `build_diff` | keep-in-script | These are CLI/proof-surface mechanics tied to local files, current derived artifacts, and safe write/check behavior. They should stay in wrappers unless S20 shared CLI utilities explicitly extracts them. |
| CLI modes and argument parsing | `parse_args`, `canonical_mode`, `preview_mode`, `run`, `main` | keep-in-script | CLI orchestration should remain in scripts. Package helpers should expose pure functions, not own CLI/runtime write policy. |
| Canonical projection builders | `build_projection`, `build_canonical_projection`, `canonical_item`, `canonical_edge` | defer | These shape derived ACP preview/canonical proof outputs. They may be reviewed later, but moving them now risks blurring ACP projection authority. |

## Extraction rules for future work

Any future extraction from these scripts into `src/law_nexus` must satisfy all rules below:

1. Use package names that include `projection`, `diagnostic`, or `derived` rather than `registry_truth` or `validation_truth`.
2. Keep package helpers deterministic and side-effect-free unless they are explicitly placed in an adapter layer.
3. Keep CLI write/check behavior in script wrappers or S20 shared CLI utilities.
4. Preserve tests that prove canonical registry paths cannot be written by projection exporters.
5. Preserve tests that prove ACP/RDF projection outputs include non-authority/non-claim metadata.
6. Preserve rank 1-3 proof-anchor references when converting source references.
7. Do not import from `scripts/` inside package code.
8. Do not import `.lex` generated projection outputs as package source truth.
9. Do not claim R035/R037/R038 validation from projection evidence alone.
10. Do not promote law-nexus profile constraints into the external generic ACP/git-lex core.

## Canonical registry mutation guardrails

The following paths must remain protected from projection-helper writes unless a future explicit source-of-truth migration decision is recorded:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

Projection exporters may write only derived custom proof outputs such as:

- `prd/architecture/acp/derived/architecture-projection.preview.json`
- `prd/architecture/acp/derived/canonical-projection.items.jsonl`
- `prd/architecture/acp/derived/canonical-projection.edges.jsonl`
- `prd/architecture/acp/derived/architecture-projection.ttl`
- `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
- `prd/architecture/acp/derived/architecture-projection.sparql`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

These derived paths remain diagnostic/projection artifacts, not authoritative registry truth.

## GitNexus traceability notes

Exact symbol evidence used for this review:

- `Function:scripts/export-architecture-rdf-projection.py:ttl_prefixes` resolved exactly.
- Upstream impact for `ttl_prefixes` is LOW but touches RDF projection output flows through `build_ttl`, `build_outputs`, and `run`.
- Common helper names such as `run`, `main`, and `read_text` are ambiguous or unreliable by bare lookup. Future work must use file-qualified GitNexus UIDs.

## Decision

S19 recommends **review-first, extract-later**.

Immediate extraction is not justified in S19 because projection output exactness and canonical write refusal are part of current proof surfaces. The safe next step is to keep existing exporters stable, add this review and validator, and let a future dedicated extraction slice move only pure deterministic helpers under red/green compatibility tests.

## Non-claims

This review does not prove:

- ACP projection correctness beyond existing tests.
- RDF, SHACL, SPARQL, or JSON-LD semantic completeness.
- Architecture requirement validation.
- Legal correctness or authoritative legal advice.
- Russian legal parser completeness.
- Retrieval quality or answer faithfulness.
- FalkorDB production readiness.
- Generated Cypher correctness or runtime safety.
- LLM authority.
