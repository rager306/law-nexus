---
title: "Real Artifact Retrieval Evidence Mapping"
status: "contract-draft"
owner: "M013/S01"
requirement: "R034"
source_inputs:
  - "prd/parser/consultant_hierarchy_records.json"
  - "prd/parser/consultant_hierarchy_records.jsonl"
  - "prd/parser/parser_staging_graph.json"
  - "prd/retrieval/retrieval_output_validator_contract.md"
non_authoritative: true
created_at: "2026-05-13"
---

# Real Artifact Retrieval Evidence Mapping

This mapping defines how M013 may derive retrieval/answer output validator proof records from tracked parser artifacts. It bridges the M012 synthetic fixture proof toward real repository evidence without claiming final production retrieval quality, legal-answer correctness, parser completeness, production graph schema, or FalkorDB runtime readiness.

## Source artifacts

M013 may consume only tracked repository-relative artifacts:

- `prd/parser/consultant_hierarchy_records.json` — summary and source provenance for the Consultant 44-FZ hierarchy proof.
- `prd/parser/consultant_hierarchy_records.jsonl` — bounded hierarchy records with IDs, parent links, source hashes, location selectors, excerpt hashes, and non-claims.
- `prd/parser/consultant_hierarchy_records.md` — human-readable proof summary and counts.
- `prd/parser/parser_staging_graph.json` — bounded NetworkX staging graph diagnostics and source-block/relation candidate shape.
- `prd/parser/parser_staging_graph.md` — human-readable staging graph report and non-claims.
- `prd/retrieval/retrieval_output_validator_contract.md` — M012 output envelope and validation boundary contract.
- `prd/retrieval/fixtures/retrieval_output_validator_cases.json` — M012 synthetic fixture format used as the compatibility target.

The M013 proof must not rescan untracked local source directories, fetch external data, call an LLM, or treat `.gsd/exec` outputs as registry anchors.

## Record mapping table

| Validator concept | Candidate real-artifact source | M013 mapping rule | Proof boundary |
| --- | --- | --- | --- |
| `SourceDocument` | `consultant_hierarchy_records.json.source` and document-level `HIER-CONS-DOCUMENT` | Derive a proof-local source document record from the tracked source path, source SHA-256, and document hierarchy record. | Source-backed parser evidence only; not final document model or legal authority. |
| `SourceBlock` | Each selected hierarchy JSONL record with `id`, `location`, `excerpt_sha256`, `order_index`, and `source_path` | Derive a proof-local source block record from one hierarchy record. Use `excerpt_sha256`, not raw excerpt text, in durable proof outputs. | Parser-source block proxy; not parser completeness or final block segmentation. |
| `EvidenceSpan` | Selected hierarchy JSONL record and its `excerpt_sha256` | Derive a proof-local evidence span pointing to the proof-local source block and legal unit for that record. | Evidence-span proxy over parser record hash; not legal correctness. |
| `LegalUnit` | Selected hierarchy JSONL record with `level` and `parent_id` | Derive a proof-local legal unit record from the hierarchy ID, level, parent chain, and marker metadata when present. | Legal-unit proxy over parser hierarchy; not final legal graph schema. |
| `ActEdition` | Source title/date signals in `HIER-CONS-DOCUMENT` plus source hash | Derive a bounded proof edition record for the source snapshot, using source SHA-256 and known source title as provenance. | Edition proxy; does not resolve all amendments or same-date conflicts. |
| `LegalAct` | `HIER-CONS-DOCUMENT` and source path | Derive a proof-local legal act record for the 44-FZ source corpus. | Act proxy; not authoritative legal interpretation. |
| `citation_key` | Generated proof-local case ID and selected hierarchy record ID | Generate deterministic citation keys for proof cases only. | not a final citation format. |
| `retrieval_output_id` | Generated proof-local case ID | Generate deterministic output IDs for proof cases only. | not a product retrieval ID. |

## ID namespace strategy

M012 deliberately used proof-local ID prefixes such as `RET-M012-*`, `CIT-M012-*`, `EV-M012-*`, `SB-M012-*`, `SD-M012-*`, `LU-M012-*`, `ED-M012-*`, and `AC-M012-*`. The current `scripts/retrieval_output_validator.py` enforces those prefixes as a safety check.

M013 must not silently bypass this constraint. S02 must choose one documented option:

1. **Safe namespace extension:** extend the validator prefix contract to allow M013 proof-local prefixes such as `RET-M013-*`, `CIT-M013-*`, `EV-M013-*`, `SB-M013-*`, `SD-M013-*`, `LU-M013-*`, `ED-M013-*`, and `AC-M013-*`, while keeping unknown namespaces rejected.
2. **Adapter normalization:** generate real-artifact-derived records with M013 provenance, then normalize only the validator-facing IDs into the existing M012 prefix namespace through an explicit adapter layer whose provenance remains M013/source-backed.

The preferred option is safe namespace extension because it keeps proof provenance visible in diagnostics. Either option must preserve unknown-namespace rejection tests and must not promote proof IDs to final production IDs.

## Bounded and proxy fields

M013 may use bounded/proxy fields where current artifacts do not yet prove production semantics:

- `source_document_id` is derived from source path and SHA-256, not a final production document table ID.
- `source_block_id` is derived from a selected hierarchy record, not a final parser segmentation claim.
- `evidence_span_id` is a proof span over a parser record hash, not a reviewed legal evidence span.
- `legal_unit_id` is derived from hierarchy level/parentage, not final legal ontology or legal correctness.
- `act_edition_id` is a bounded source-snapshot edition proxy, not full amendment/temporal conflict resolution.
- `citation_key` and `retrieval_output_id` are proof-local and deterministic, not product-facing IDs.

All durable proof outputs should include hashes, IDs, source paths, selectors, case IDs, and diagnostic codes rather than raw legal text.

## Invalid case classes

The real-artifact corpus should include at least these case classes:

- `valid_real_artifact_path` — selected hierarchy record resolves through source document, source block, evidence span, legal unit, and edition proxy records.
- `missing_evidence_id` — output omits or nulls the evidence span ID.
- `unresolved_source_block` — evidence span references a source block ID not present in the derived graph records.
- `ambiguous_citation_key` — the active scope has duplicate citation bindings for one citation key.
- `wrong_edition_proxy` — output cites an edition ID that does not match the derived source snapshot edition proxy.
- `scoped_no_answer` — explicit empty result with no citations or answer claims and a scoped no-answer diagnostic.
- `unsafe_no_answer_with_citation` — no-answer output attempts to carry candidate citations or claims.

Additional invalid cases may be added only if they remain deterministic and safe.

## Diagnostic and redaction rules

Diagnostics must be compact, typed, deterministic, and safe for durable artifacts. Allowed diagnostic payload fields should remain aligned with the M012 validator contract: diagnostic code, severity, result, field path, output ID, scope ID, case ID, safe bounded ID value, expected ID, resolved ID, and fixture/proof artifact path.

Durable proof outputs must not include:

- raw legal text or full source excerpts;
- user prompts or LLM/provider payloads;
- credentials, tokens, secrets, or PII;
- raw embedding arrays or vectors;
- raw FalkorDB rows or runtime response bodies;
- generated legal advice or authoritative answer prose.

## Non-claims

M013 real-artifact mapping does not prove product retrieval quality.
M013 real-artifact mapping does not prove parser completeness.
M013 real-artifact mapping does not prove legal-answer correctness.
M013 real-artifact mapping does not prove legal interpretation authority.
M013 real-artifact mapping does not prove production FalkorDB runtime behavior.
M013 real-artifact mapping does not prove production graph schema readiness.
M013 real-artifact mapping does not prove local embedding quality.
M013 real-artifact mapping does not close GATE-G008.
M013 real-artifact mapping does not close GATE-G011.
M013 real-artifact mapping does not make LLM output legal authority.
M013 real-artifact mapping does not make proof-local IDs production IDs.

## S02 handoff

S02 should consume this mapping and a seed real-artifact case corpus to implement the executable proof. The proof command should:

1. load tracked real-artifact cases;
2. build validator-compatible graph records and output envelopes;
3. run the existing M012 validator path or a safe namespace extension of it;
4. report accepted/rejected counts, diagnostic code inventory, and mismatches;
5. exit non-zero on stale/missing input artifacts, unsafe payload fields, or unexpected validation results;
6. preserve all open gate boundaries unless separate quality/runtime evidence exists.

The S02 implementation must keep M012 regression tests green and must verify unknown namespace rejection after any prefix extension.

## Verification hook

T01 verification:

```bash
uv run pytest tests/test_real_artifact_evidence_mapping.py -q
```

Later S02 verification should add CLI proof commands and M012 regression checks.
