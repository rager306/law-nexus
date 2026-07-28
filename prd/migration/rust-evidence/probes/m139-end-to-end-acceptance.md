# M139 end-to-end acceptance evidence

- **Evidence ID:** `M139-S03-END-TO-END-ACCEPTANCE`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Binary:** `target/debug/law-nexus-inspect`

## Proven boundary

The product CLI (`law-nexus-inspect`) composes the full Rust pipeline
end-to-end on both tracked real fixtures:

```
law-source file → ln-decode parser → extractors → ln-storage in-memory → ln-query KnowQL → JSON output
```

Output is deterministic across repeat runs (excluding variable `duration_ms`).

## Consultant WordML

| Metric | Value |
|---|---:|
| Blocks | 167 |
| Hierarchy markers | 22 |
| Reference mentions | 69 |
| Temporal phrases | 1 |
| Deontic lexemes | 4 |
| Unknown forms | 29 |
| Provider comments (excluded) | 0 |
| KnowQL retrieval count | 5 |
| Determinism | PASS |

## Garant ODT

| Metric | Value |
|---|---:|
| Blocks | 5,124 |
| Hierarchy markers | 140 |
| Reference mentions | 1,882 |
| Temporal phrases | 36 |
| Deontic lexemes | 228 |
| Unknown forms | 2,144 |
| Provider comments (excluded) | 355 |
| KnowQL retrieval count | 5 |
| Determinism | PASS |

## Composition

| Layer | Crate | Component |
|---|---|---|
| Parser | ln-decode | ConsultantWordMlBlockDecoder / GarantOdtBlockDecoder |
| Extractors | ln-decode | hierarchy, references, temporal, deontic, unknown_forms |
| Storage | ln-storage | InMemoryVectorStore / InMemoryGraphStore |
| Query | ln-query | KnowQL FindSimilar |
| Output | ln-product-cli | law-nexus-inspect JSON |

## Non-claims

- No legal correctness, citation authority or corpus completeness claim.
- No cross-format legal parity claim.
- No production-scale performance claim.
- No security hardening beyond bounded input validation.
- Debug build; release build will be faster.
