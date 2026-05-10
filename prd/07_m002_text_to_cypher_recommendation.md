# M002 Text-to-Cypher Recommendation for R017

## Reader and action

This recommendation is for engineers deciding the next LegalGraph Nexus NL-to-Cypher step after M002/S01-S04. After reading it, they should be able to choose whether to continue the direct PyO3 path, fall back to a REST baseline first, keep only validator scaffolding, or defer NL-to-Cypher work.

## Final recommendation

**Recommendation category:** `pursue-pyo3-conditioned`

Pursue the proof-only PyO3/direct Rust-to-Python route as the preferred next prototype for **R017**, but keep R017 **active** until a credentialed provider proof confirms MiniMax generation through the same validation boundary. The current evidence confirms local PyO3 build/import, `ServiceTargetResolver` routing for `MiniMax-M2.7-highspeed` at `https://api.minimax.io/v1`, S03 validation gating, and synthetic read-only execution through Python FalkorDB `Graph.ro_query`; it does not prove provider generation quality or any Legal KnowQL product behavior.

REST remains a **REST baseline** and fallback comparison path, not the primary recommendation. A validator-only branch is acceptable if credentialed provider access remains unavailable. A defer branch is appropriate if future proof cannot preserve the `EvidenceSpan` / `SourceBlock` and LLM non-authoritative boundaries.

## Evidence table

| Slice | Status category | Evidence used | What it proves | Boundary / follow-up |
|---|---|---|---|---|
| S01 | source/docs-backed | Upstream text-to-cypher and project context review | R017 should evaluate the direct PyO3 / Python binding route and treat REST as secondary comparison evidence. | Does not prove local build, provider calls, safety, or LegalGraph suitability by itself. |
| S02 | confirmed local proof surface | Proof-only generated PyO3/maturin smoke surface | Local project tooling can build/import a narrow PyO3 proof surface without shipping Legal KnowQL product code. | Does not prove provider-backed generation or production API ergonomics. |
| S03 | confirmed deterministic safety gate | Generated-Cypher safety contract and fixture validator | Generated Cypher is untrusted until deterministic validation accepts schema-grounded, read-only, evidence-returning queries. | Validation does not certify legal-answer correctness, provider quality, or production graph schema fitness. |
| S04 | blocked-credential with confirmed bounded runtime evidence | MiniMax PyO3/genai proof artifact | The proof-only module builds/imports; genai `ServiceTargetResolver` can route `MiniMax-M2.7-highspeed` to `https://api.minimax.io/v1`; accepted candidate output is gated by S03 validation and executed only through `Graph.ro_query` against synthetic data. | MiniMax live generation was not attempted because credentials were unavailable; legal answers and product parser behavior remain unproven. |

## PyO3 versus REST baseline

### PyO3 path

The PyO3 path remains the best match for R017 because it evaluates direct Rust-to-Python integration rather than reducing the evaluation to an HTTP wrapper. The current M002/S04 proof locally verifies the proof-only build/import surface and MiniMax target resolution through `ServiceTargetResolver`. That is enough to justify continuing PyO3 work, but only behind the S03 generated-Cypher safety contract.

Required next proof for PyO3:

1. Run a credentialed provider call for `MiniMax-M2.7-highspeed` without persisting raw provider bodies.
2. Treat provider output as draft text only.
3. Reject unsafe output before execution.
4. Execute only validated Cypher through `Graph.ro_query` with a timeout.
5. Persist only redacted diagnostics, rejection codes, execution status, and synthetic row-shape evidence.

### REST baseline

Direct Python/HTTP or upstream REST is a baseline/fallback. It may be useful when PyO3 packaging, async runtime embedding, or local build constraints block progress, but it shares the exact same validation boundary: generated text is not trusted until S03 validation accepts it, and execution is limited to read-only FalkorDB access. This recommendation does **not** claim that an upstream high-level `TextToCypherClient` can route MiniMax unless a future harness proves an adapter or patch.

REST-first is recommended only if PyO3 cannot preserve local packaging, runtime, or safety requirements. REST must not bypass `EvidenceSpan`, `SourceBlock`, temporal filtering, redaction, or the LLM non-authoritative rule.

## Branch rules

| Branch | When to choose it | R017 effect |
|---|---|---|
| `pursue-pyo3-conditioned` | PyO3 build/import and routing are confirmed, validation/execution gates are confirmed, but provider generation is blocked by credentials. | Keep R017 active; record credentialed provider proof as the follow-up. |
| `pursue-rest-baseline` | PyO3 build/import or runtime embedding fails, but REST can be tested under the same validation boundary. | Keep R017 active or defer PyO3 specifically; use REST as comparison/fallback evidence only. |
| `validator-only` | Provider routes are unavailable or unsafe, but S03 validation remains useful for future generated-Cypher experiments. | Keep R017 active with implementation blocked; preserve the validator as reusable guardrail. |
| `defer` | Validation, redaction, evidence boundaries, or read-only execution cannot be preserved. | Defer NL-to-Cypher work; do not ship product behavior. |

## R017 and R011 boundary

R017 is advanced but not fully validated. The missing credentialed MiniMax provider proof means the recommendation cannot close provider-backed generation, Russian legal terminology behavior, or production API ergonomics.

R011 remains a supported guardrail, not owned product work in this slice. This artifact does not implement the LegalGraph Nexus product pipeline, product ETL/import, production graph schema, LegalNexus API, Legal KnowQL parser, hybrid retrieval, product parser behavior, legal-answer correctness, ODT parsing, or retrieval quality.

## Non-authoritative legal boundary

LLM non-authoritative remains mandatory. An LLM may draft candidate Cypher only; it is never legal authority, schema authority, or evidence authority. `EvidenceSpan` and `SourceBlock` must stay tied to trusted source evidence before any future legal-answering product work can be considered.
