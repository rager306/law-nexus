# M062/S01: Evidence category matrix

## Status

Pass (matrix draft). S01 produces a static classification matrix that scopes which evidence categories may be touched by any future git-lex L2 diagnostic adapter. It is not adapter implementation, not main `.lex` adoption, not source-truth migration, not production adoption, and not validation evidence for R035, R037, or R038.

## Scope

This matrix classifies evidence categories along four tiers:

```text
allowed         — git-lex L2 diagnostic projection may consume this evidence
caution         — may consume only with explicit proof-class tagging and bounded diagnostics
blocked         — git-lex L2 diagnostic must not consume this evidence
ACP-native-only — git-lex L2 diagnostic must not be the authority for this evidence; ACP core / source / runtime / legal are authoritative
```

The matrix is a source-anchor for M062/S02 (adapter state and rollback contract), S03 (fitness decision), and S04 (roadmap synthesis). It is not the final adapter contract.

## Classification vocabulary

| Tier | Meaning | Adapter behavior |
|---|---|---|
| `allowed` | Evidence is governance/diagnostic metadata, not product/legal truth. | May be projected for diagnostics, projection, query, validation smoke. Must not be cited as authority for product/legal/runtime claims. |
| `caution` | Evidence is structural or runtime-adjacent; may produce false positives or unstable projections. | May be projected only with explicit proof class, bounded context, and failure classifier. Must not be promoted to authority. |
| `blocked` | Evidence contains raw payloads, secrets, or non-portable state. | Must not enter git-lex state, must not appear in adapter diagnostics. |
| `ACP-native-only` | Evidence category owns its own proof path; git-lex projection cannot validate it. | Adapter must reject any claim that uses git-lex projection to validate this category. Source/runtime/legal/independent review are the authority. |

## Category matrix

| # | Category | Classification | Proof requirements | Protection rule |
|---|---|---|---|---|
| 1 | ACP governance metadata (SourceRecord, LifecycleState, AuthorityClass, ValidationClaim, HealthFinding) | `allowed` | Tracked repository-relative artifact path; ACP-native source fields; lifecycle/authority explicit. | ACP artifacts remain source truth. Projection may produce diagnostic views, never authority. |
| 2 | Synthetic kit examples (synthetic ACP fixtures, synthetic law-nexus fixtures) | `allowed` | `nonAuthoritative=true`; `synthetic=true`; `proofStatus=example-only`; isolated workspace. | Not product/legal proof. Must be marked at the fixture level and surfaced as diagnostic. |
| 3 | Architecture decisions (DECISIONS, ADR, M048-M061 decisions) | `allowed` | Decision ledger row with rationale; ADR-anchored if applicable. | DECISIONS/ADR remain authoritative. Adapter may link to decisions as references, never supersede them. |
| 4 | Legal source/raw text (Garant ODT source, Consultant XML, raw legal payloads, source-block content) | `blocked` | n/a — must not enter adapter state. | No raw payload anchors. Reject any adapter record that contains or references raw legal text body. |
| 5 | Parser quality (Garant ODT parser behavior, parser completeness, parser tests) | `ACP-native-only` | Parser test fixtures with tracked source; parser unit-test evidence; real-document evidence. | No projection validation. Adapter may surface parser metadata as diagnostic, never as parser-quality authority. |
| 6 | FalkorDB behavior (FalkorDB runtime, ingest, vector/full-text, Cypher safety, UDF, GraphRAG) | `ACP-native-only` | Runtime smoke proof; capability evidence per `falkordb-legalgraph` skill; source-anchored runtime artifacts. | No git-lex-only validation. Adapter diagnostics may accompany runtime proofs, but authority is runtime/source. |
| 7 | Citation safety / retrieval quality (EvidenceSpan, SourceBlock, Citation, RetrievalAnswer, Legal KnowQL) | `ACP-native-only` | Real-document fixtures; retrieval quality benchmarks; citation-safety proof. | No projection validation. Adapter may surface retrieval metadata as diagnostic, never as retrieval/citation authority. |
| 8 | R035 / R037 / R038 (ontology architecture proof boundaries, FalkorDB ingest/runtime loading path, independent review gate) | `ACP-native-only` | R035: registry extractor integration + regenerated registry outputs + accepted proof-gate evidence. R037: real FalkorDB runtime loading path. R038: independent human review. | No git-lex projection validation. R035/R037/R038 must not be closed from documentation-only or git-lex evidence (per M017/M048). |

## Decision flow

```text
if category.classification == "ACP-native-only":
    reject any claim that cites git-lex projection as authority
    require explicit non-git-lex proof class (runtime / source / legal / independent review)
elif category.classification == "blocked":
    reject the record before it enters adapter state
    refuse to log raw payload bytes even in diagnostics
elif category.classification == "caution":
    require proof class + bounded context + failure classifier
    tag output as diagnostic-only
elif category.classification == "allowed":
    permit projection with explicit authority class
    surface as diagnostic / projection / query result, never authority
```

## Boundary alignment with M061

This matrix inherits and refines the M061/S05 blocked boundaries and M058 root-cause findings.

- M061/S05 blocked `hard validation gate adoption for ACP-kit / law-nexus-kit`. The matrix inherits this by keeping ACP governance metadata and synthetic kit examples at `allowed` (diagnostic), not `allowed`-as-authority.
- M058 root cause: generated SHACL shapes are underconstrained. The matrix does not depend on SHACL enforcement; the matrix is a source-anchor for adapter evaluation, independent of shape runtime.
- M060/S02 local-equivalent law-nexus-kit configured-kit setup is referenced as the prior pattern for any future L2 adapter pilot.

## Categories NOT covered by this matrix

These require separate decision artifacts, not this matrix:

- Performance, throughput, latency: not an evidence category; they are operational metrics. Out of scope for M062.
- Security boundary of the host system: separate work stream, not L2 adapter scope.
- Cross-tooling RAG / LLM adapter (LangChain, LlamaIndex, etc.): out of scope for M062 (covered by `falkordb-genai-mcp-graphrag` skill family).
- External publishing decisions: explicitly blocked by M061; not M062 scope.

## Wording contract

Safe wording preserved:

```text
M062/S01 evidence category matrix classifies which evidence categories may be touched by a future git-lex L2 diagnostic adapter.
```

```text
Categories 4 (legal source/raw text) and 8 (R035/R037/R038) are blocked / ACP-native-only and must not be promoted by git-lex projection.
```

Unsafe wording rejected:

```text
git-lex L2 diagnostics validates parser quality.
```

```text
git-lex L2 diagnostics validates R035 / R037 / R038.
```

```text
git-lex L2 diagnostics is production-ready.
```

```text
M062/S01 authorizes main .lex adoption or source-truth migration.
```

## Next slice

S02 — Adapter state and rollback contract. It must consume this matrix and define state location, residue checks, rollback policy, diagnostics emission policy, and failure modes for any future git-lex L2 adapter pilot. S02 cannot approve main `.lex`, source-truth, production, or R035/R037/R038 validation.
