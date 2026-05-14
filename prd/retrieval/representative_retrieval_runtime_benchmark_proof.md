# Representative Retrieval Runtime Benchmark Proof

- Schema version: `representative-retrieval-runtime-benchmark-proof/v1`
- Benchmark ID: `RRB-M016-REPRESENTATIVE-V1`
- Benchmark status: `metrics_confirmed`
- Failure class: `none`
- Diagnostic codes: `none`
- Runtime boundary confirmed: `true`
- Gate disposition input: `GATE-G011` remains open; this report is not final gate closure evidence.

## Inputs Consumed

Repository-relative inputs used by the proof CLI:
- `prd/retrieval/representative_retrieval_runtime_benchmark_contract.md`
- `prd/retrieval/local_retrieval_runtime_boundary_contract.md`
- `prd/retrieval/local_retrieval_runtime_boundary_proof.md`
- `scripts/check-local-retrieval-runtime.py`
- `scripts/verify-representative-retrieval-runtime-benchmark.py`
- `prd/retrieval/representative_retrieval_corpus_contract.md`
- `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`
- `prd/retrieval/representative_retrieval_corpus_manifest.md`
- `prd/retrieval/representative_retrieval_runtime_benchmark_proof.md`

S01 runtime boundary sources:
- `prd/retrieval/local_retrieval_runtime_boundary_contract.md`
- `S10-EMBEDDING-RUNTIME-PROOF.json`
- `pyproject.toml`

S02 representative manifest sources:
- `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`
- `prd/parser/source_fixture_inventory.json`
- `prd/retrieval/fixtures/local_retrieval_quality_benchmark.json`
- `prd/retrieval/fixtures/offline_citation_retrieval_cases.json`
- `prd/retrieval/fixtures/real_artifact_retrieval_cases.json`
- `prd/retrieval/representative_retrieval_corpus_contract.md`

## Command Run

```bash
uv run python scripts/verify-representative-retrieval-runtime-benchmark.py --allow-runtime-blocker
```

Safe compact stdout summary excerpt:

```json
{"benchmark_id":"RRB-M016-REPRESENTATIVE-V1","benchmark_status":"metrics_confirmed","diagnostic_codes":[],"failure_class":"none","gate":{"claim":"gate remains open","gate_id":"GATE-G011","status":"open"},"metrics":{"ambiguous_rejection_rate":1.0,"edition_path_mismatch_rejection_rate":1.0,"mrr":1.0,"no_answer_accuracy":1.0,"recall_at_1":1.0,"recall_at_3":1.0,"runtime_boundary_confirmed":true,"unsafe_rejection_rate":1.0},"runtime_boundary_confirmed":true,"schema_version":"representative-retrieval-runtime-benchmark-proof/v1","thresholds":{"ambiguous_rejection_rate":1.0,"edition_path_mismatch_rejection_rate":1.0,"mrr":1.0,"no_answer_accuracy":1.0,"recall_at_1":1.0,"recall_at_3":1.0,"runtime_boundary_confirmed":1.0,"unsafe_rejection_rate":1.0}}
```

## Runtime Status

- Runtime status: `confirmed_runtime`
- Runtime failure class: `none`
- Runtime diagnostic codes: `none`
- Model ID: `deepvk/USER-bge-m3`
- Execution mode: `local_open_weight`
- Vector dimension: `1024`
- Managed API used: `false`
- GigaChat used: `false`
- Network used: `false`

If runtime is blocked, this report preserves `blocked_runtime` status and diagnostic codes instead of claiming metric thresholds passed.

## Metric/Threshold Summary

- Manifest corpus: `CORPUS-M016-REPRESENTATIVE-V1`
- Query labels: `7`
- Candidate references: `7`
- Coverage classes: `10`

| Metric | Observed | Threshold |
| --- | --- | --- |
| `mrr` | `1.0` | `1.0` |
| `recall_at_1` | `1.0` | `1.0` |
| `recall_at_3` | `1.0` | `1.0` |
| `no_answer_accuracy` | `1.0` | `1.0` |
| `ambiguous_rejection_rate` | `1.0` | `1.0` |
| `unsafe_rejection_rate` | `1.0` | `1.0` |
| `edition_path_mismatch_rejection_rate` | `1.0` | `1.0` |
| `runtime_boundary_confirmed` | `True` | `1.0` |

## Diagnostics Inventory

- Benchmark status: `metrics_confirmed`
- Failure class: `none`
- Diagnostic code: `none`

## Redaction Boundary

This report stores only IDs, bounded status strings, booleans, counts, metric values, diagnostic codes, hashes already present in checked-in manifests, and repository-relative paths.
It does not persist raw legal text, raw query text, prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, generated legal advice, or absolute paths.

- `raw_legal_text_persisted` = `false`
- `raw_query_text_persisted` = `false`
- `raw_prompt_persisted` = `false`
- `raw_vector_persisted` = `false`
- `provider_payload_persisted` = `false`
- `raw_falkordb_row_persisted` = `false`
- `managed_api_evidence_persisted` = `false`
- `generated_legal_advice_persisted` = `false`
- `absolute_path_persisted` = `false`
- `secrets_persisted` = `false`

## GATE-G011 Disposition Inputs

- `GATE-G011` remains open.
- This proof is an input for later S04 architecture gate disposition work, not final gate closure.
- A later milestone validation must decide whether the gate can close; this report does not close it.

## Non-claims

- does not prove product retrieval quality
- does not prove production ranker quality
- does not prove parser completeness
- does not prove legal-answer correctness
- does not prove legal interpretation authority
- does not prove production FalkorDB runtime behavior
- does not prove production graph schema readiness
- does not make proof-local IDs production IDs
- does not authorize managed embedding API fallback
- does not authorize GigaChat or GigaEmbeddings runtime use
- does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice
- does not make LLM output legal authority
- does not close GATE-G011; GATE-G011 remains open

## S04 Handoff

S04 may consume this report and the single stdout JSON surface to assess representative runtime-benchmark evidence for `GATE-G011`.
S04 must preserve the same redaction boundary and must treat `blocked_runtime` or non-empty diagnostic codes as actionable blockers, not as threshold-pass evidence.
