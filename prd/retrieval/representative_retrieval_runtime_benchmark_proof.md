# Representative Retrieval Runtime Benchmark Proof

- Schema version: `representative-retrieval-runtime-benchmark-proof/v1`
- Benchmark status: `metrics_confirmed`
- Failure class: `none`
- Diagnostic codes: `none`
- Runtime boundary confirmed: `true`
- Manifest corpus: `CORPUS-M016-REPRESENTATIVE-V1`
- Query labels: `7`
- Candidate references: `7`
- Redaction: raw legal text, raw query text, prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, generated legal advice, and absolute paths are not persisted.
- Gate: `GATE-G011` remains open.

## Metrics

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
