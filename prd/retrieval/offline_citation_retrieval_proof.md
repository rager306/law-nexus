---
title: "Offline Citation Retrieval Proof"
status: "bounded-evidence"
owner: "M014/S02"
gate: "GATE-G008"
proof_level: "unit-test + CLI proof"
non_authoritative: true
created_at: "2026-05-13"
---

# Offline Citation Retrieval Proof

This report records the M014 executable offline citation-safe retrieval proof. It advances `GATE-G008` with bounded deterministic evidence that tracked parser-derived retrieval cases can produce validator-compatible citation envelopes, scoped no-answer outputs, and fail-closed diagnostics.

This report does not close `GATE-G008`. It also does not prove product retrieval quality, parser completeness, local embedding quality, production FalkorDB runtime behavior, graph schema readiness, legal-answer correctness, or legal interpretation authority.

## Proof inputs

The proof uses only tracked repository-relative inputs:

- `prd/retrieval/offline_citation_retrieval_contract.md`
- `prd/retrieval/fixtures/offline_citation_retrieval_cases.json`
- `scripts/build-offline-citation-retrieval-cases.py`
- `scripts/verify-offline-citation-retrieval-proof.py`
- `scripts/retrieval_output_validator.py`
- `prd/parser/consultant_hierarchy_records.json`
- `prd/parser/consultant_hierarchy_records.jsonl`
- `prd/parser/parser_staging_graph.json`
- `prd/retrieval/fixtures/real_artifact_retrieval_cases.json`

The proof does not fetch external data, call an LLM, generate legal answer prose, compute embeddings, run FalkorDB, or inspect untracked local corpora.

## Executable command

The proof command is:

```bash
uv run python scripts/verify-offline-citation-retrieval-proof.py
```

The slice-level verification command is:

```bash
uv run pytest tests/test_offline_citation_retrieval_proof_cli.py tests/test_offline_citation_retrieval_proof_report.py -q && uv run python scripts/verify-offline-citation-retrieval-proof.py
```

## Proof result

Fresh proof output:

```json
{"diagnostic_code_inventory":["ambiguous_candidate_set","id_path_mismatch","orphaned_source_path","scoped_no_answer","scoped_no_candidate","unresolved_candidate_evidence","unsafe_payload_rejected"],"fixture_path":"prd/retrieval/fixtures/offline_citation_retrieval_cases.json","mismatch_count":0,"namespace_strategy":"m014_proof_local_prefixes_allowed_by_shared_validator","non_authoritative":true,"rejected_count":3,"schema_version":"offline-citation-retrieval-proof/v1","scoped_no_answer_count":1,"selected_count":2,"total_cases":6,"validator_accepted_count":3,"validator_rejected_count":1}
```

Summary:

| Metric | Value |
| --- | ---: |
| `total_cases` | 6 |
| `selected_count` | 2 |
| `scoped_no_answer_count` | 1 |
| `rejected_count` | 3 |
| `validator_accepted_count` | 3 |
| `validator_rejected_count` | 1 |
| `mismatch_count` | 0 |

## Case coverage

The fixture covers these deterministic case classes:

- `valid_exact_record_candidate` — one exact parser record candidate is selected and accepted by the shared validator.
- `valid_marker_level_candidate` — one marker/level parser candidate is selected and accepted by the shared validator.
- `scoped_no_candidate` — no candidate is selected within the explicit proof corpus, and the shared validator accepts only the scoped no-answer shape.
- `ambiguous_candidate_set` — multiple candidates match deterministic criteria, so the proof rejects without arbitrary tie-breaking.
- `unresolved_candidate_evidence` — a selected candidate cannot resolve to a complete source/evidence path and is rejected by the shared validator.
- `unsafe_candidate_payload` — forbidden payload intent is rejected before validator handoff.

## Diagnostic inventory

The proof emitted only bounded diagnostic codes:

- `ambiguous_candidate_set`
- `id_path_mismatch`
- `orphaned_source_path`
- `scoped_no_answer`
- `scoped_no_candidate`
- `unresolved_candidate_evidence`
- `unsafe_payload_rejected`

Diagnostics are limited to safe identifiers, field paths, case IDs, query IDs, candidate IDs, fixture paths, and validator-safe ID values. They do not persist raw legal text, prompts, provider payloads, secrets, vectors, raw FalkorDB rows, generated answer prose, or legal advice.

## Validator integration

M014 extends the shared output validator namespace policy to admit proof-local M014 IDs:

- `RET-M014-*`
- `SCOPE-M014-*`
- `CIT-M014-*`
- `EV-M014-*`
- `SB-M014-*`
- `SD-M014-*`
- `LU-M014-*`
- `ED-M014-*`
- `AC-M014-*`

Regression tests preserve fail-closed behavior for unknown namespaces. M014 does not introduce a parallel citation validator.

## GATE-G008 status

This proof advances `GATE-G008` by demonstrating:

- deterministic offline candidate and scoped no-answer cases over tracked parser artifacts;
- shared-validator-compatible citation envelopes for selected candidates;
- fail-closed behavior for ambiguous candidate sets, unresolved evidence paths, and unsafe payloads;
- compact safe diagnostics that are repository-relative and redacted.

`GATE-G008` remains open because this proof does not establish full product retrieval quality, recall, parser completeness, runtime graph behavior, production query behavior, or legal-answer correctness.

## Non-claims

M014 offline citation retrieval proof does not prove product retrieval quality.
M014 offline citation retrieval proof does not prove parser completeness.
M014 offline citation retrieval proof does not prove legal-answer correctness.
M014 offline citation retrieval proof does not prove legal interpretation authority.
M014 offline citation retrieval proof does not prove production FalkorDB runtime behavior.
M014 offline citation retrieval proof does not prove production graph schema readiness.
M014 offline citation retrieval proof does not prove local embedding quality.
M014 offline citation retrieval proof does not close GATE-G008.
M014 offline citation retrieval proof does not close GATE-G011.
M014 offline citation retrieval proof does not make LLM output legal authority.
M014 offline citation retrieval proof does not make proof-local IDs production IDs.

## S03 handoff

S03 may register this report as bounded evidence for `GATE-G008` progress in the architecture registry. The registry item should remain `bounded-evidence` and must preserve the non-claims above. Any architecture edge to `GATE-G008` should be phrased as advancing or supporting the gate, not closing it.
