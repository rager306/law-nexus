# M003 MiniMax PyO3 Functioning Proof Recommendation for R017

## Reader and action

This recommendation is for engineers deciding how M003 should affect the LegalGraph Nexus generated-Cypher / Legal KnowQL roadmap after S01-S05. After reading it, they should be able to keep R017 active, continue the PyO3 route only under the stated conditions, and avoid converting partial MiniMax proof evidence into product or legal-answer claims.

## Final recommendation

**Recommendation category:** `pursue-pyo3`

Pursue the proof-only PyO3/direct Rust-to-Python route as the preferred next prototype for **R017**, while still treating the result as proof-harness evidence rather than product readiness. M003 now proves endpoint normalization for `https://api.minimax.io/v1`, a provider-attempt route for `MiniMax-M2.7-highspeed`, reasoning-separated accepted candidate generation, deterministic validation acceptance, and synthetic read-only `Graph.ro_query(..., timeout=1000)` execution. It does not prove provider generation quality, product Legal KnowQL behavior, or legal-answer correctness.

R017 remains active and is advanced-not-validated. The current evidence now contains an accepted S03 candidate, accepted S04 validation, and confirmed synthetic read-only execution, so the category upgrades to `pursue-pyo3`. This document still does not validate R017 automatically; that remains a separate requirement review.

## Evidence table

| Slice | Status category | Evidence used | What it proves | Boundary / follow-up |
|---|---|---|---|---|
| S01 | blocked-credential baseline | MiniMax live baseline evidence with `response_status=blocked-credential` and root cause `minimax-credential-missing` | The normalized MiniMax endpoint preserves `/v1`, and missing credentials are classified without persisting credentials or provider bodies. | Does not prove live provider generation, candidate quality, Legal KnowQL, or legal-answer behavior. |
| S02 | failed-runtime provider-attempt route | MiniMax PyO3 endpoint evidence with `mechanics_confirmed=True`, endpoint contract preservation, and one provider attempt ending in `provider-non-cypher-diagnostic` | The proof route can build/import, resolve the target, preserve endpoint normalization, and attempt the provider path through the PyO3/direct-binding proof surface. | Does not prove useful Cypher generation, production API ergonomics, or product Legal KnowQL integration. |
| S03 | confirmed-runtime candidate safety boundary | Reasoning-safe candidate evidence with one provider attempt, `candidate_accepted=True`, separated reasoning, and clean `MATCH` candidate text | Provider output can be converted into accepted candidate text without persisting raw provider body, prompt, or raw reasoning. | Does not prove provider generation quality, Russian legal terminology quality, production schema grounding, or legal-answer correctness. |
| S04 | confirmed-runtime validation/read-only execution | Validation/read-only execution evidence with `validation_accepted=True`, `execution_status=confirmed-runtime`, method `Graph.ro_query`, and timeout `1000` | S04 accepted the generated candidate under the deterministic contract and executed only against synthetic LegalGraph-shaped data with redacted row-shape diagnostics. | Does not prove read-only execution on live legal graph data, production FalkorDB scale, raw legal evidence quality, or retrieval quality. |
| S05 | generated proof closure | R017 proof-closure artifact with schema `m003-s05-r017-proof-closure/v1`, category `pursue-pyo3`, and `requirements_validated=[]` | S05 synthesizes S01-S04 into an auditable R017 effect: advanced-not-validated, with explicit redaction/non-claim guardrails. | Does not validate R017 automatically; requirement validation remains a separate review. |

## What M003 proves

M003 proves a narrow, verifier-backed functioning-proof envelope:

1. Endpoint normalization preserves the MiniMax `/v1` API root used by the proof route.
2. The PyO3/direct-binding path can reach a provider-attempt route and produce categorical diagnostics without storing raw provider bodies.
3. Candidate generation remains non-authoritative and must pass deterministic validation before execution.
4. Deterministic validation can accept a schema-constrained generated candidate and route it to synthetic read-only execution.
5. Synthetic read-only execution uses `Graph.ro_query(..., timeout=1000)` and persists row-shape diagnostics rather than raw rows.
6. S05 can synthesize upstream statuses into a reproducible category, R017 effect, verification summary, and explicit non-claims.

This is enough to justify continuing the PyO3 proof branch as `pursue-pyo3`, but not enough to claim product generation quality, production schema grounding, or legal-answering readiness.

## Branch rules

| Branch | When to choose it | R017 effect |
|---|---|---|
| `pursue-pyo3-conditioned` | Choose this when endpoint normalization/provider-attempt mechanics exist, but S03 has no accepted candidate or S04 has no accepted validation/read-only execution. | R017 remains active and advanced-not-validated; continue only behind accepted candidate, validation, and read-only execution proof. |
| `pursue-pyo3` | Current M003 state: accepted S03 candidate plus confirmed S04 read-only execution, accepted S04 validation, preserved endpoint normalization, and no safety/redaction regression. | R017 remains active and advanced-not-validated; PyO3 is the preferred next proof/prototype route, but requirement validation remains separate. |
| `pursue-rest-baseline` | Choose this if the PyO3/direct-binding route regresses on endpoint preservation, build/import mechanics, target resolution, or provider-attempt routing while the validation boundary remains reusable. | Keep R017 active; use REST only as comparison/fallback evidence under the same validation boundary. |
| `validator-only` | Choose this if provider routes remain unavailable or malformed but deterministic validation remains valuable for future generated-Cypher experiments. | Keep R017 active with implementation blocked; preserve validator and redaction guardrails. |
| `defer` | Choose this if safety, redaction, EvidenceSpan / SourceBlock boundaries, read-only execution constraints, or LLM non-authoritative handling cannot be preserved. | Defer generated-Cypher / Legal KnowQL work; do not ship product behavior. |

## R017 effect

R017 is advanced but not fully validated. The requirement has evidence for endpoint normalization, provider-attempt route handling, accepted reasoning-separated candidate generation, deterministic validation acceptance, synthetic read-only execution, and proof-closure synthesis.

R017 remains active until a separate requirement validation review decides whether validation is appropriate. The all-confirmed proof branch is now present for the M003 synthetic boundary, but it is still not a product Legal KnowQL validation event.

## REST baseline

REST remains a fallback and comparison branch. It must share the same validation boundary as PyO3: generated text is draft-only, deterministic validation must accept it before execution, and execution must stay read-only with timeout and redacted diagnostics. REST must not bypass endpoint normalization evidence, `EvidenceSpan`, `SourceBlock`, temporal filtering, raw-output redaction, or the LLM non-authoritative rule.

This recommendation does not claim that an upstream high-level TextToCypher product surface can route MiniMax or authorize Legal KnowQL shipment. Any REST branch must be proven with its own verifier-backed evidence.

## Explicit non-claims

This recommendation explicitly does not claim proof of:

- provider generation quality
- product Legal KnowQL behavior
- legal-answer correctness
- ODT parsing
- retrieval quality
- Russian legal terminology quality
- production schema grounding
- production FalkorDB scale
- raw legal evidence quality
- product ETL/import behavior
- production LegalGraph Nexus pipeline behavior
- live legal graph execution beyond the current synthetic or not-attempted boundary

## Non-authoritative legal boundary

LLM non-authoritative remains mandatory. An LLM may draft candidate Cypher only; it is never legal authority, schema authority, source authority, or evidence authority. `EvidenceSpan` and `SourceBlock` must stay tied to trusted source evidence before any future legal-answering product work can be considered.

M003 does not implement the LegalGraph Nexus product pipeline, product ETL/import, production graph schema, Legal Nexus API, Legal KnowQL parser, hybrid retrieval, product parser behavior, legal-answer correctness, ODT parsing, retrieval quality, Russian legal terminology quality, production schema grounding, production FalkorDB scale, or raw legal evidence quality.

## Redaction and persistence boundary

The recommendation and S05 closure persist only categorical summaries, booleans, counts, hashes, schema/status/root-cause fields, and artifact paths. They do not persist provider response bodies, prompts, raw reasoning, raw legal text, FalkorDB rows, credentials, authorization headers, secret-like values, or hidden chain-of-thought markup.

## Future proof checklist

Before this proof can become product work or requirement validation, keep these gates true:

1. S01 endpoint normalization remains compatible with the MiniMax `/v1` endpoint.
2. S02 confirms PyO3/direct-binding mechanics and provider-attempt routing without route regression.
3. S03 records an accepted candidate without raw prompt, raw reasoning, raw provider body, raw legal text, or secret persistence.
4. S04 records accepted validation plus confirmed read-only execution.
5. S05 or a successor closure independently derives the same category as the recommendation.
6. R017 is still marked active until a separate requirement validation review updates it.
