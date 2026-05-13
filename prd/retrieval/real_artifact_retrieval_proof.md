---
title: "Real Artifact Retrieval Proof"
status: "bounded-proof"
owner: "M013/S02"
requirement: "R034"
proof_level: "unit-test + CLI proof"
source_inputs:
  - "prd/retrieval/real_artifact_evidence_mapping.md"
  - "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
  - "scripts/verify-real-artifact-retrieval-proof.py"
  - "scripts/retrieval_output_validator.py"
non_authoritative: true
created_at: "2026-05-13"
---

# Real Artifact Retrieval Proof

M013/S02 proves that retrieval/answer output ID validation can run over a real-artifact-derived case corpus built from tracked parser evidence. It consumes the M013 corpus in `prd/retrieval/fixtures/real_artifact_retrieval_cases.json`, transforms its `derived_fixture_graph` into the fixture shape expected by `scripts/retrieval_output_validator.py`, and verifies all case expectations through `scripts/verify-real-artifact-retrieval-proof.py`.

This is bounded evidence for R034. It advances retrieval output ID validation beyond M012 synthetic-only fixtures, but it does not prove product retrieval quality, legal-answer correctness, parser completeness, production FalkorDB runtime behavior, local embedding quality, or final production ID schema.

## Proof command

Run the M013 proof:

```bash
uv run python scripts/verify-real-artifact-retrieval-proof.py
```

Expected compact JSON summary:

```json
{
  "schema_version": "real-artifact-retrieval-proof/v1",
  "fixture_path": "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
  "total_cases": 7,
  "accepted_count": 2,
  "rejected_count": 5,
  "mismatch_count": 0,
  "namespace_strategy": "safe_namespace_extension_selected",
  "diagnostic_code_inventory": [
    "ambiguous_citation_key",
    "id_path_mismatch",
    "missing_required_field",
    "orphaned_source_path",
    "scoped_no_answer",
    "unsafe_no_answer_shape",
    "wrong_edition"
  ]
}
```

Run the integrated S02 regression check:

```bash
uv run pytest tests/test_real_artifact_retrieval_proof_cli.py tests/test_real_artifact_retrieval_cases.py tests/test_retrieval_output_validator.py tests/test_real_artifact_retrieval_proof_report.py -q && uv run python scripts/verify-real-artifact-retrieval-proof.py && uv run python scripts/verify-retrieval-output-validator.py
```

## Inputs and anchors

| Artifact | Role |
| --- | --- |
| `prd/retrieval/real_artifact_evidence_mapping.md` | Mapping contract from tracked parser artifacts to validator-compatible concepts. |
| `prd/retrieval/fixtures/real_artifact_retrieval_cases.json` | Seed real-artifact corpus with source hashes, derived fixture graph, 7 cases, and non-claims. |
| `scripts/build-real-artifact-retrieval-cases.py` | Deterministic builder and `--check` freshness surface for the corpus. |
| `scripts/verify-real-artifact-retrieval-proof.py` | CLI proof entrypoint for M013 real-artifact cases. |
| `scripts/retrieval_output_validator.py` | Shared validator implementation reused from M012, now explicitly allowing M012 and M013 proof-local namespaces. |
| `tests/test_real_artifact_retrieval_proof_cli.py` | CLI proof success/failure/safety/determinism tests. |
| `tests/test_real_artifact_retrieval_cases.py` | Corpus shape, redaction, graph compatibility, namespace, and freshness tests. |
| `tests/test_retrieval_output_validator.py` | M012 regression suite proving the original synthetic fixture behavior remains green. |

## Case coverage

| Case class | Case ID | Expected result | Expected diagnostic codes |
| --- | --- | --- | --- |
| Valid real-artifact path | `CASE-M013-VALID-REAL-ARTIFACT` | `accepted` | none |
| Missing evidence ID | `CASE-M013-MISSING-EVIDENCE-ID` | `rejected` | `missing_required_field` |
| Unresolved source block | `CASE-M013-UNRESOLVED-SOURCE-BLOCK` | `rejected` | `id_path_mismatch`, `orphaned_source_path` |
| Ambiguous citation | `CASE-M013-AMBIGUOUS-CITATION` | `rejected` | `ambiguous_citation_key` |
| Wrong edition proxy | `CASE-M013-WRONG-EDITION-PROXY` | `rejected` | `wrong_edition` |
| Scoped no-answer | `CASE-M013-SCOPED-NO-ANSWER` | `accepted_scoped_no_answer` | `scoped_no_answer` |
| Unsafe no-answer with citation | `CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION` | `rejected` | `unsafe_no_answer_shape` |

## Namespace strategy

S02 selected **safe namespace extension**. `scripts/retrieval_output_validator.py` now accepts both M012 and M013 proof-local ID prefixes for validator fields while preserving `unknown_id_namespace` rejection for unsupported prefixes. This keeps M013 provenance visible in diagnostics and avoids silently normalizing real-artifact-derived proof IDs into M012-only identifiers.

This namespace extension is still proof-local. It does not define final production ID formats.

## Diagnostic and redaction boundaries

The CLI proof emits only compact safe fields: summary counts, diagnostic code inventory, mismatch details when present, fixture path, and namespace strategy. Tests reject raw legal text, prompts, provider payloads, secrets, raw embedding arrays, raw FalkorDB rows, generated answer prose, and legal advice markers.

The corpus persists source hashes, excerpt hashes, location selectors, record IDs, case IDs, and expected diagnostic codes. It does not persist raw legal text.

## R034 status

M013/S02 advances R034 by proving that real-artifact-derived retrieval output envelopes can be validated through the fail-closed M012 validator path. The proof includes a valid source/evidence/legal-unit/edition path plus invalid missing, ambiguous, orphaned, wrong-edition, and scoped no-answer cases.

R034 should not be marked fully validated until M013/S03 records the proof in the architecture registry and the project decides whether this proof satisfies the active requirement text or whether broader product retrieval/answer behavior remains required.

## Remaining gates

- `GATE-G008` remains open: this proof does not validate parser completeness, citation-safe product retrieval behavior, retrieval quality, or multi-document readiness.
- `GATE-G011` remains open: this proof does not measure local embedding quality, ranking quality, reranking, precision/recall, or product retrieval benchmark performance.
- FalkorDB runtime/load proof remains out of scope for S02.
- Legal-answer correctness and LLM authority remain out of scope.

## Non-claims

M013/S02 real-artifact proof does not prove product retrieval quality.
M013/S02 real-artifact proof does not prove parser completeness.
M013/S02 real-artifact proof does not prove legal-answer correctness.
M013/S02 real-artifact proof does not prove legal interpretation authority.
M013/S02 real-artifact proof does not prove production FalkorDB runtime behavior.
M013/S02 real-artifact proof does not prove production graph schema readiness.
M013/S02 real-artifact proof does not prove local embedding quality.
M013/S02 real-artifact proof does not close GATE-G008.
M013/S02 real-artifact proof does not close GATE-G011.
M013/S02 real-artifact proof does not make LLM output legal authority.
M013/S02 real-artifact proof does not make proof-local IDs production IDs.
