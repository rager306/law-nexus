# Rust transition performance and artifact baseline

**Status:** `[bounded]` measurement record; canonical artifact baseline is
`baseline_not_frozen` pending single/corpus path reconciliation.

## Measured host baseline

Date: 2026-07-18. Python: 3.13.12. Corpus: 284 MB under `law-source/`.

| Workload | Result | Command/evidence |
|---|---:|---|
| Single Consultant parse (about 5 MB) | 2.2 s wall | `uv run python scripts/build-consultant-hierarchy-records.py` |
| Corpus hierarchy parse | 7.586 s wall / 5.426 s user / 2.107 s sys | `uv run python scripts/build-consultant-hierarchy-records.py --corpus` |
| Fast targeted parser suite after M106 | 68 passed, 13 deselected, 31.41 s pytest / 32.52 s wall | targeted `pytest -m "not slow"` |
| Full suite before M106 fix | 47 failed, 2079 passed, 1 skipped, 3951.17 s | full pytest; dominated by repeated rebuilds |
| Onion/import contracts | 4 kept, 0 broken | `uv run lint-imports` |

The 65-minute suite was a test-orchestration defect, not evidence that Python
parsing itself required Rust. Rust is nevertheless the selected target for
long-term multi-core scaling, memory control and a single deployable product.

## Current tracked artifact observation

These values were observed on 2026-07-20 and are **not yet canonical parity
anchors** because shared single/corpus output paths can overwrite one another.

| Artifact | Bytes | SHA-256 | Observed semantic count |
|---|---:|---|---:|
| `prd/parser/consultant_hierarchy_records.jsonl` | 31,578,591 | `e52f65025256efa900d40bdb7f1231c27a43852946d738b5931121dd5d1b67d0` | 15,249 rows |
| `prd/parser/consultant_relation_candidates.jsonl` | 1,902,711 | `480f7c14a29b23479a5912f1c036aadea788650f8c54c345b8c1042e56c3e710` | 1,378 rows |
| `prd/parser/consultant_norm_candidates.jsonl` | 666,541 | `e466a5b98015e7b0ab592036710549451757e7367fcb71b29bff65103af789a0` | 386 rows |
| `prd/parser/parser_staging_graph.json` | 4,183,520 | `bdd0723f2720104a89b19346641c3c1f29dc698f0bd38bfb1d055cba1cd7cbee` | 2 documents; 48 source blocks; 386 norms; 1,230 unresolved refs |
| `prd/parser/golden_cases.json` | 4,689,232 | `169b31a1ab7954d0278ac014b8f09bed987bbf036accf462b6e273a5c11a9dab` | check document fields after reconciliation |
| `prd/parser/source_fixture_inventory.json` | 103,328 | `5d43189c89a699a794c9d81b0d18e839410f72512dbcd0e8a2f0c0cb1b4d3976` | 94 fixtures reported by M105 |
| `prd/parser/probe_results.json` | 88,511 | `6ec20f59394e044abfe144b598ec73cae6e7e1ee6dd92a54a8961f10fa3d50ac` | 82 classified reported by M105 |
| `prd/parser/source_id_uniqueness.json` | 27,685 | `8d50dddbd3c2312bd30230f3cfb476025bf11f660d7973a0cd185139f9f6ace3` | 82 unique / 0 collisions reported by M105 |

## Baseline reconciliation gate

Before Rust output parity tests become authoritative:

1. introduce separate single-document and corpus artifact directories;
2. rebuild corpus artifacts once from the 81 Consultant XML files;
3. record generator version, source file list, source hashes, CLI args and output hashes;
4. define semantic counters independently of JSONL line counts;
5. update architecture, proof JSON and test assertions atomically;
6. make freshness checks compare input/output manifests instead of rebuilding;
7. prove a second run is byte-stable and non-mutating.

## Rust benchmark scenarios

The Rust harness must run these scenarios with machine-readable results:

| Scenario | Corpus | Concurrency | Required metrics |
|---|---|---:|---|
| Single file | canonical 44-FZ | 1 | wall, CPU, peak RSS, records/s, MB/s |
| Current corpus | all 81 XML, current in-scope policy | 1 and available cores | wall, CPU, peak RSS, files/s, MB/s, output hashes |
| 10× replay | deterministic repeated manifest, no duplicated output IDs | 1 and available cores | scaling curve, peak RSS, speedup, correctness |
| Oversized document | largest tracked Consultant XML | 1 | streaming peak RSS and failure behavior |
| Malformed inputs | negative fixture set | mixed | time-to-fail, reason code, bounded diagnostics |
| Staging graph | canonical hierarchy/relation/norm artifacts | 1 and parallel-safe stages | wall, peak RSS, node/edge counts, output hash |
| Retrieval | frozen golden and real-artifact cases | configured concurrency | p50/p95/p99 latency, correctness, no-answer/citation failures |

## Initial acceptance budgets

Budgets are proposals until the first Rust implementation measures them:

- Rust must not be slower than the reconciled Python baseline on the current corpus.
- Peak RSS for parsing should remain bounded and scale sublinearly with total corpus
  size by streaming one document at a time.
- Multi-file parsing must demonstrate real multi-core speedup without changing
  deterministic artifact order or identifiers.
- A failed document must not corrupt successful outputs; diagnostics identify the
  source and phase without leaking raw legal text or secrets.
- Benchmark results include toolchain, host, commit, input manifest, warm/cold
  state, attempts and variance.

## Harness output contract

`python -m law_nexus_harness performance check` should eventually emit one JSON
record containing:

```json
{
  "status": "pass|fail|blocked",
  "phase": "performance",
  "rust_commit": "...",
  "toolchain": "...",
  "input_manifest_sha256": "...",
  "scenario_results": [],
  "budgets": {},
  "failures": [],
  "non_claims": []
}
```

The harness launches Rust binaries as subprocesses. It does not parse legal
sources or reproduce product counters itself; Rust emits semantic results and
the harness compares them with frozen manifests.
