# M139 performance baseline

- **Evidence ID:** `M139-S01-PERFORMANCE-BASELINE`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Binary:** `target/debug/law-nexus-inspect`
- **Command:** `law-nexus-inspect inspect <fixture>`

## Consultant WordML

| Run | Wall time |
|---|---:|
| 1 | 30ms |
| 2 | 30ms |
| 3 | 30ms |

- Blocks: 167
- Determinism: PASS (JSON identical excluding `duration_ms`)

## Garant ODT

| Run | Wall time |
|---|---:|
| 1 | 630ms |
| 2 | 710ms |
| 3 | 630ms |

- Blocks: 5,124
- Determinism: PASS (JSON identical excluding `duration_ms`)

## Non-claims

- No production-scale performance claim.
- Debug build; release build will be faster.
- No memory profiling or peak RSS measurement.
- No concurrent or multi-request benchmark.
- Single-machine, single-thread baseline only.
