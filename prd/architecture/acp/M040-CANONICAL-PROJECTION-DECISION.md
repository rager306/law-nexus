# M040 ACP Canonical Projection Decision

**Date:** 2026-05-21

## Verdict

Keep ACP canonical-shaped projection output custom-only for now.

Recommended next step:

```text
Plan ACP Canonical Registry Integration Proof only after deciding how ACP records enter the source-of-truth extraction flow.
```

M040 proves that ACP records can be exported as schema-valid canonical-shaped item and edge JSONL records under ACP derived paths. It does not prove that those records should be inserted into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.

## Evidence used

| Evidence | Result |
| --- | --- |
| `prd/architecture/acp/M040-CANONICAL-PROJECTION-CONTRACT.md` | Defines custom output paths, mapping rules, blocked paths, non-claims, and verification requirements. |
| `scripts/export-acp-architecture-projection.py` | Supports preview JSON and opt-in `--canonical-jsonl` custom item/edge JSONL output. |
| `prd/architecture/acp/derived/canonical-projection.items.jsonl` | Contains 5 canonical-shaped ACP item records. |
| `prd/architecture/acp/derived/canonical-projection.edges.jsonl` | Contains 7 canonical-shaped ACP edge records. |
| `tests/test_acp_architecture_projection.py` | Covers preview compatibility, canonical-shaped schema validity, stale output detection, and canonical path refusal. |
| `uv run python scripts/verify-architecture-graph.py` | Remains green for tracked canonical architecture outputs. |
| GitNexus change detection | Flags HIGH exporter-flow scope because the CLI flow changed; mitigated by focused exporter tests and verifier checks. |

## Options considered

### Option A — Keep custom-only

Keep canonical-shaped ACP item/edge JSONL under ACP derived paths as proof artifacts.

Verdict: recommended.

Reasons:

- S02 proves shape and exporter safety without changing canonical registry generation ownership.
- Canonical path refusal remains active and test-covered.
- Current canonical verifier remains focused on existing generated registry outputs.
- This avoids treating prompt provenance or decision candidates as accepted architecture truth.

### Option B — Integrate into canonical extraction/build flow now

Wire ACP projection output into `scripts/extract-prd-architecture-items.py`, `scripts/build-architecture-graph.py`, or tracked canonical JSONL outputs now.

Verdict: defer.

Reasons:

- M040 proves exporter mechanics, not canonical source ownership.
- Canonical integration must answer where ACP source records live in the source-of-truth hierarchy.
- The existing architecture registry is generated from PRD/GSD/ADR/source evidence; ACP derived outputs should not bypass that flow.
- GitNexus correctly flags exporter-flow changes as high enough to keep the next integration step separately bounded.

### Option C — Revise mapping before continuing

Stop and redesign item/edge mapping.

Verdict: not needed now.

Reasons:

- Canonical-shaped outputs validate against `architecture.schema.json`.
- Tests cover counts, schema validity, non-claims, stale output detection, and canonical path refusal.
- Preview output remains current.
- No verifier drift was introduced.

## Recommended follow-up milestone

Create a future milestone only if continuing ACP integration:

```text
ACP Canonical Registry Integration Proof
```

Suggested slices:

1. **Source ownership contract**
   - Decide whether ACP source records become source evidence, generated evidence, or remain derived ACP artifacts.
   - Define which generator owns canonical ACP records.
2. **Custom integration fixture**
   - Build a custom architecture registry item/edge fixture that includes ACP canonical-shaped records plus existing records.
   - Run verifier/build checks on custom paths before tracked canonical outputs.
3. **Integration decision**
   - Decide whether to wire ACP records into canonical extraction/build flow, keep custom-only, or move to RDF/dashboard preview layers.

## Allowed next actions

- Use custom canonical-shaped outputs as acceptance evidence for a future integration proof.
- Keep using `--canonical-jsonl` for custom proof outputs.
- Use `--check` in CI/local verification to keep derived ACP custom outputs current.
- Start a source ownership contract for ACP canonical registry integration.

## Blocked actions

- Write ACP canonical-shaped output directly into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.
- Treat `canonical-projection.items.jsonl` or `canonical-projection.edges.jsonl` as canonical registry truth.
- Treat prompt records as implementation proof.
- Treat `decision_candidate` records as accepted decisions without authority and proof gate resolution.
- Move to git-lex/RDF or dashboard as an authority surface before source ownership and integration semantics are proof-gated.
- Claim R035, R037, or R038 validation from M040.
- Claim product, parser, FalkorDB, retrieval, legal, production, or independent-review readiness from M040.

## Boundary preservation

This decision does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## M040 final proof statement

M040 proves:

```text
ACP records can be exported as schema-valid canonical-shaped item/edge JSONL records to custom ACP proof paths while canonical registry files remain protected.
```

M040 does not prove:

```text
ACP records are integrated into the canonical architecture registry generation flow.
```
