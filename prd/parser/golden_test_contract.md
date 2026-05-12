# Parser/Retrieval Golden-Test Contract

> **Scope:** M008/S01 static contract for future executable golden tests over tracked M006 parser artifacts. This artifact is non-authoritative: it defines bounded parser/retrieval fixture expectations and diagnostics, not product retrieval quality or legal-answer correctness.

## Purpose

R032 requires a parser/retrieval golden-test proof before citation-safe retrieval or product legal-answer claims are made. This contract turns the current tracked parser/staging outputs into implementation-ready golden-case classes for S02/S03 while preserving the M006/M007 non-claim boundary.

Golden tests built from this contract must answer one question only: given the tracked `prd/parser/` artifacts, does the evaluator report the expected bounded evidence/no-answer/candidate-only/non-claim state with inspectable diagnostics?

## Source artifacts

Golden tests must consume tracked repository artifacts, not rescan undocumented local source directories.

| Artifact | Role in golden tests | Current S01 baseline |
| --- | --- | --- |
| `prd/parser/parser_record_contract.md` | Human-readable parser record boundary and non-claims. | `pass`; example counts: 2 document, 1 source_block, 1 relation_candidate. |
| `prd/parser/schemas/document_record.schema.json` | Required `DocumentRecord` field contract. | Fresh. |
| `prd/parser/schemas/source_block_record.schema.json` | Required `SourceBlockRecord` field contract. | Fresh. |
| `prd/parser/schemas/relation_candidate_record.schema.json` | Required `RelationCandidateRecord` field contract. | Fresh. |
| `prd/parser/odt_document_records.jsonl` | Bounded non-authoritative document fixtures. | 2 records. |
| `prd/parser/odt_source_block_records.jsonl` | Bounded non-authoritative ODT source-block fixtures. | 48 records, capped at 24 per ODT document. |
| `prd/parser/odt_smoke_records.json` | Machine-readable ODT smoke summary. | `pass`, 2 documents, 48 source blocks. |
| `prd/parser/consultant_relation_candidates.jsonl` | Candidate-only Consultant WordML relation fixtures. | 1 candidate: `REL-CONS-0001`. |
| `prd/parser/consultant_relation_candidates.json` | Machine-readable relation-candidate summary. | `pass`, 1 candidate. |
| `prd/parser/parser_staging_graph.json` | Machine-readable NetworkX staging/debug graph summary. | `pass`, 2 document nodes, 48 source-block nodes, 1 relation edge, 2 unresolved-reference nodes, 3 warnings. |
| `prd/parser/parser_staging_graph.md` | Human-readable staging graph diagnostics and R031 scope. | Expected warnings are unresolved Consultant endpoints and missing Consultant source-block provenance. |

The S01 baseline verification command is:

```bash
uv run python scripts/validate-parser-records.py --check && \
uv run python scripts/build-odt-smoke-records.py --check && \
uv run python scripts/build-consultant-relation-candidates.py --check && \
uv run python scripts/build-parser-staging-graph.py --check
```

## Case classes

| Case class | Required fixture source | Expected evaluator state | Required diagnostic focus | Non-claim preserved |
| --- | --- | --- | --- | --- |
| `evidence-present` | A concrete `DocumentRecord` or `SourceBlockRecord` from tracked ODT JSONL, e.g. `DOC-44-FZ` or one of its emitted source blocks. | `matched: true`, bounded evidence rows present, source anchors preserved. | Case id, artifact path, record id, source path, source hash, excerpt hash when applicable. | Evidence presence does not prove parser completeness, retrieval quality, or legal-answer correctness. |
| `no-answer` | A query/expectation whose target record id or source anchor is absent from the tracked artifacts. | `matched: false`, `answer_state: no-answer`, no fabricated evidence rows. | Missing target, inspected artifact paths, zero-match count, non-authoritative boundary. | No-answer behavior does not prove recall, parser completeness, or product retrieval quality. |
| `candidate-only` | `REL-CONS-0001` from `prd/parser/consultant_relation_candidates.jsonl` and the corresponding staging graph edge key. | Candidate is visible only as `status: candidate`; no authoritative relation or ODT endpoint match is asserted. | Candidate id, relation status, subject/object refs, source block id, Consultant source path. | Candidate visibility does not prove relation correctness, Consultant legal authority, or product graph truth. |
| `unresolved-reference` | Staging graph unresolved refs: `consultant-list:law-source/consultant/Список документов (5).xml` and `consultant:LAW:179581@11.05.2026`. | Unresolved references remain explicit diagnostics/nodes; they are not rewritten into ODT document ids. | Reference id, warning rule, source artifact path, associated candidate id if any. | Unresolved-reference handling does not prove endpoint resolution, FalkorDB loading/runtime readiness, or citation-safe retrieval. |
| `non-authoritative` | Any parser/staging artifact with `non_authoritative: true` and `non_claims`. | Evaluator propagates `non_authoritative: true` and reports blocked claim categories. | Non-claim list, blocked claim labels, artifact path, proof boundary. | Explicitly blocks parser completeness, retrieval quality, and legal-answer correctness claims. |

## Required input record fields

The evaluator may project only the fields needed for golden assertions, but source records must remain valid against their tracked schemas.

### Document record fields

Required source fields: `id`, `source_kind`, `source_path`, `source_sha256`, `non_claims`, `record_kind`, `title`. The evaluator must also preserve `non_authoritative` when present and treat absent/false values as a contract failure.

### Source block record fields

Required source fields: `id`, `source_kind`, `source_path`, `source_sha256`, `non_claims`, `record_kind`, `document_id`, `order_index`, `location`, `excerpt`, `excerpt_sha256`. ODT source blocks must keep their source/member provenance and bounded excerpt hash; tests must not compare unbounded raw legal text.

### Relation candidate record fields

Required source fields: `id`, `source_kind`, `source_path`, `source_sha256`, `non_claims`, `record_kind`, `source_block_id`, `subject_ref`, `object_ref`, `relation_type`, `status`, `evidence_excerpt`, `evidence_sha256`. Golden tests must fail if a candidate-only relation is silently promoted to authoritative/product-ready status.

## Golden case fixture schema draft

Future S02/S03 JSON fixtures should use this shape or an equivalent superset:

```json
{
  "case_id": "GT-001",
  "case_class": "evidence-present",
  "description": "Bounded evidence exists for a tracked ODT source block.",
  "source_artifacts": ["prd/parser/odt_source_block_records.jsonl"],
  "anchors": [
    {
      "artifact_path": "prd/parser/odt_source_block_records.jsonl",
      "record_id": "BLOCK-...",
      "source_path": "law-source/garant/44-fz.odt",
      "source_sha256": "...",
      "excerpt_sha256": "..."
    }
  ],
  "expected": {
    "answer_state": "evidence-present",
    "matched": true,
    "required_record_ids": ["BLOCK-..."],
    "forbidden_claims": [
      "parser completeness",
      "retrieval quality",
      "legal-answer correctness"
    ]
  }
}
```

Allowed `case_class` values are exactly: `evidence-present`, `no-answer`, `candidate-only`, `unresolved-reference`, and `non-authoritative`.

Allowed `answer_state` values are exactly: `evidence-present`, `no-answer`, `candidate-only`, `unresolved-reference`, and `non-authoritative-boundary`.

## Expected evaluator result shape

Each executed golden case should emit a deterministic result object:

```json
{
  "case_id": "GT-001",
  "case_class": "evidence-present",
  "status": "pass",
  "answer_state": "evidence-present",
  "matched": true,
  "evidence": [
    {
      "artifact_path": "prd/parser/odt_source_block_records.jsonl",
      "record_id": "BLOCK-...",
      "record_kind": "source_block",
      "source_path": "law-source/garant/44-fz.odt",
      "source_sha256": "...",
      "excerpt_sha256": "...",
      "non_authoritative": true
    }
  ],
  "diagnostics": [],
  "non_claims_preserved": true,
  "blocked_claims": [
    "parser completeness",
    "retrieval quality",
    "legal-answer correctness"
  ]
}
```

`status` must be one of `pass`, `fail`, or `error`. A `fail` means the artifacts were readable but did not satisfy the expected state. An `error` means setup, schema loading, or artifact parsing failed before the case assertion could be evaluated.

## Diagnostic shape

Diagnostics are part of the contract because future agents must inspect failures without inferring legal meaning from raw text.

Required diagnostic fields:

| Field | Meaning |
| --- | --- |
| `case_id` | Golden case id that produced the diagnostic. |
| `case_class` | One of the five allowed case classes. |
| `severity` | `info`, `warning`, or `error`. |
| `rule` | Stable rule id, e.g. `missing_evidence`, `unexpected_authoritative_claim`, `candidate_promoted`, `unresolved_reference_missing`. |
| `artifact_path` | Repository-relative tracked artifact inspected. |
| `record_id` | Record/candidate/reference id when available. |
| `record_kind` | `document`, `source_block`, `relation_candidate`, `unresolved_reference`, or `result`. |
| `source_path` | Original source path when available. |
| `expected_state` | Expected case outcome. |
| `actual_state` | Observed outcome. |
| `message` | Human-readable diagnostic without unbounded legal text. |
| `non_authoritative` | Boolean boundary signal; expected `true` for current artifacts. |

Diagnostics may include `source_sha256`, `excerpt_sha256`, `field`, and `line` when they help locate a parser record. Diagnostics must not include secrets, generated legal advice, or unbounded raw legal text.

## Source-anchor rules

- Anchors must be repository-relative artifact paths plus stable record ids and hashes from tracked `prd/parser/` outputs.
- `source_path` anchors must remain the original parser source paths, e.g. `law-source/garant/44-fz.odt`, `law-source/garant/PP_60_27-01-2022.odt`, or `law-source/consultant/Список документов (5).xml`.
- Source-block evidence must use bounded excerpts and `excerpt_sha256`; tests should compare hashes/ids rather than long legal text.
- Consultant relation anchors must preserve `REL-CONS-0001`, `status: candidate`, and unresolved subject/object references unless a later proof slice explicitly updates the tracked source artifacts.
- The evaluator must not repair missing or unresolved endpoints by guessing ODT ids.

## Allowed non-claims

The evaluator may report these as preserved boundaries and must not treat them as failures:

- `parser completeness` is not claimed.
- `retrieval quality` is not claimed.
- `legal-answer correctness` is not claimed.
- Citation-safe retrieval is not claimed.
- Product ETL readiness is not claimed.
- FalkorDB loading/runtime readiness is not claimed.
- Consultant WordML legal authority is not claimed.
- Relation correctness is not claimed.
- Product graph truth is not claimed.

## Explicit out-of-scope claims

A golden-test pass under this contract must not be described as proof of:

- parser completeness;
- retrieval quality;
- legal-answer correctness;
- citation-safe retrieval readiness;
- authoritative legal interpretation;
- product ETL/import readiness;
- production graph schema validity;
- FalkorDB loading/runtime readiness;
- FalkorDB production scale;
- relation correctness or resolved Consultant-to-ODT endpoint matching;
- LLM answer authority.

## R032 acceptance mapping

| R032 criterion | Contract coverage |
| --- | --- |
| Bounded expected evidence | `evidence-present` case class over tracked `DocumentRecord`/`SourceBlockRecord` artifacts. |
| No-answer cases | `no-answer` case class with zero fabricated evidence. |
| Candidate-only relation cases | `candidate-only` and `unresolved-reference` case classes over `REL-CONS-0001` and staging warnings. |
| No product legal-answer claims | `non-authoritative` case class plus blocked claims in evaluator result. |
| Tracked M006 artifacts | Source artifact list is limited to tracked `prd/parser/` files. |

## Verification hook

The minimum static verification for this contract is:

```bash
rg -n "evidence-present|no-answer|candidate-only|unresolved-reference|non-authoritative|parser completeness|retrieval quality|legal-answer correctness" prd/parser/golden_test_contract.md
```

S02/S03 should add executable tests that assert required sections, allowed enum values, source artifact paths, diagnostic fields, and blocked claim labels remain present.
