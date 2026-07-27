# M135 golden real fixture enrichment census

- **Evidence ID:** `M135-S04-GOLDEN-REAL-ENRICHMENT`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Runtime:** Rust-only `ln-decode`
- **Command:** `cargo test -p ln-decode --test golden_real_enrichment --offline`

## Proven boundary

The unchanged Consultant WordML and Garant ODT adapters decoded their tracked
fixtures, all four extractors produced structural annotations, a `GoldenFixture`
was built from parser output, and the evaluator confirmed self-consistent
P=R=F1=1.0 for each present layer. Repeated evaluation was identical. No raw
legal text was persisted.

## Self-consistency disclaimer

Fixtures are derived from parser output, so metrics are trivially 1.0. This is
a **pipeline composition proof**, not parser quality measurement. Real quality
measurement requires human-reviewed golden annotations.

## Tracked sources and per-layer counts

### Consultant WordML

| Layer | TP | FP | FN | P | R | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Hierarchy | 22 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| Reference | 69 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| Temporal | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| Deontic | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |

- Blocks: 167
- Annotations: 96

### Garant ODT

| Layer | TP | FP | FN | P | R | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Hierarchy | 140 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| Reference | 1882 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| Temporal | 36 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| Deontic | 228 | 0 | 0 | 1.0 | 1.0 | 1.0 |

- Blocks: 5,124
- Annotations: 2,286

## Source identity

- Consultant: `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml`
  - bytes: `193726`
  - SHA-256: `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d`
  - runtime fingerprint: `fnv1a64:d7697a0ea8cc3970`
- Garant: `law-source/garant/44-fz.odt`
  - bytes: `247971`
  - SHA-256: `73777d4741fa1b65229a8b22b97eb2cff4c5180105affb79b058d7007e3e4337`
  - runtime fingerprint: `fnv1a64:d4143a172688f8c3`

## Non-claims

- Self-consistent fixtures produce P=R=F1=1.0 by construction.
- No human-reviewed golden annotations exist yet.
- No corpus completeness, cross-format legal parity, resolved-reference correctness or citation authority claim.
- No legal correctness, NormStatement semantics, five-clock assignment or legal temporal applicability claim.
- No retrieval, storage, RuVector or TEI readiness claim.
- No raw legal text is persisted in this evidence.
