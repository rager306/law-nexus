# M143 release baseline

- **Evidence ID:** `M143-S03-RELEASE-BASELINE`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Binary:** `target/release/law-nexus-inspect`
- **Build:** `cargo build -p ln-product-cli --release --offline`

## Health

```json
{
  "phase": "Health",
  "status": "ok",
  "binary": "law-nexus-inspect",
  "runtime": "rust",
  "duration_ms": 0
}
```

## Consultant WordML (release)

| Run | Wall time |
|---|---:|
| 1 | 11.2ms |
| 2 | 11.8ms |
| 3 | 12.2ms |

- Avg wall: 11.7ms
- Blocks: 167
- Hierarchy markers: 22
- Reference mentions: 69
- Temporal phrases: 1
- Deontic lexemes: 4
- Unknown forms: 29
- Determinism excluding `duration_ms`: PASS
- Fixture SHA-256: `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d`

## Garant ODT (release)

| Run | Wall time |
|---|---:|
| 1 | 194.7ms |
| 2 | 177.4ms |
| 3 | 187.3ms |

- Avg wall: 186.5ms
- Blocks: 5124
- Hierarchy markers: 140
- Reference mentions: 1882
- Temporal phrases: 36
- Deontic lexemes: 228
- Unknown forms: 2144
- Determinism excluding `duration_ms`: PASS
- Fixture SHA-256: `73777d4741fa1b65229a8b22b97eb2cff4c5180105affb79b058d7007e3e4337`

## Comparison vs M139 debug baseline

| Provider | Debug (M139) | Release (M143) |
|---|---:|---:|
| Consultant | 30ms | 11.7ms |
| Garant | ~657ms | 186.5ms |

## Non-claims

- No production packaging or deployment claim.
- No multi-machine or concurrent benchmark.
- No memory/RSS profiling.
- One tracked real fixture per provider only.
- No corpus completeness or legal correctness claim.
