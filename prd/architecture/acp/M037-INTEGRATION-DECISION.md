# M037 ACP Registry Integration Decision

**Date:** 2026-05-21

## Verdict

Do not integrate ACP records into the canonical architecture registry yet.

Recommended next step:

```text
Extend schema first, then run a canonical integration proof.
```

M037 proves that ACP records can produce a safe preview projection, but it also confirms that ACP contains governance semantics that do not fit cleanly into the current architecture registry schema without either losing meaning or overloading existing item/edge types.

## Evidence used

| Evidence | Result |
| --- | --- |
| `prd/architecture/acp/M037-MAPPING-SPEC.md` | Defines safe preview mapping and schema gaps. |
| `scripts/export-acp-architecture-projection.py` | Generates preview projection only and refuses canonical registry writes. |
| `prd/architecture/acp/derived/architecture-projection.preview.json` | Contains 5 preview items and 7 preview edges. |
| `tests/test_acp_architecture_projection.py` | Verifies shape, non-claims, blocked mutations, stale output, and canonical write protection. |
| `uv run python scripts/verify-architecture-graph.py` | Remains green after preview proof. |

## Options considered

### Option A — Integrate now

Feed ACP preview items and edges into `architecture_items.jsonl` and `architecture_edges.jsonl` now.

Verdict: reject.

Reasons:

- Current schema has no first-class `architecture_prompt_record` type.
- Current schema has no first-class `architecture_health_finding` type.
- ACP capture/redaction policy has no canonical field.
- ACP blocked actions are workflow-governance state, not ordinary architecture claims.
- Immediate integration risks confusing provenance with proof.

### Option B — Keep ACP separate indefinitely

Keep ACP as a separate governance mechanism and never map it to the current registry.

Verdict: reject for now.

Reasons:

- M037 preview shows a useful partial mapping.
- Existing architecture registry would benefit from selected ACP proof gates and health signals after a schema extension.
- Keeping separate forever would create avoidable duplicate architecture-governance surfaces.

### Option C — Extend schema first

Add explicit canonical support for ACP governance concepts before integration.

Verdict: recommended.

Reasons:

- Preserves current verifier guarantees.
- Avoids overloading `evidence`, `viewpoint`, `risk`, and `decision` records with ACP-only semantics.
- Allows deliberate support for prompt provenance, decision candidates, proof gates, health findings, capture policy, and blocked actions.
- Keeps proof-boundary non-claims explicit.

## Required schema-extension questions

Before canonical integration, answer:

1. Should `architecture_prompt_record` become a canonical item type or remain ACP-only?
2. Should `architecture_health_finding` become a canonical item type or map to `risk` with additional metadata?
3. Should `decision_candidate` remain separate from accepted `decision` records?
4. Should canonical edges include `producedProposal`, `suggestedDecision`, `requiresProof`, and `blockedBy`, or map them to existing relationship classes?
5. Where should `capture_mode` and `redaction_status` live?
6. How should blocked actions appear in generated architecture health views?
7. Which ACP records, if any, can ever be projected with `validated` status?

Default answer for M037: none of these should be integrated without a schema-extension proof.

## Next recommended milestone

Create a future milestone:

```text
ACP Registry Schema Extension Proof
```

Suggested slices:

1. **Schema extension design**
   - Add proposed item/edge schema changes in a design artifact or isolated fixture schema.
   - Do not edit canonical schema yet unless the slice explicitly validates the change.
2. **Custom-path verifier fixture**
   - Build a custom-path verifier fixture with item/edge records exercising ACP projections.
   - Run architecture verifier with custom paths first, not tracked canonical registry files.
3. **Canonical integration decision**
   - Decide whether to update canonical schema/extractor or keep ACP projection separate.

## Current allowed next actions

- Keep using ACP validator and recovery/projection preview outputs as separate governance proof tools.
- Plan schema-extension proof using custom-path fixtures.
- Continue parser roadmap only when explicitly resumed.
- Use ACP health findings to guide planning, not to validate product claims.

## Current blocked actions

- Write ACP preview records directly to canonical architecture JSONL files.
- Modify canonical architecture schema without a schema-extension proof.
- Treat ACP prompt provenance as implementation proof.
- Promote `DC-0001` to accepted architecture decision without accepted authority and proof gate resolution.
- Treat `architecture-projection.preview.json` as canonical architecture registry truth.
- Claim product, parser, FalkorDB, retrieval, legal, or independent-review readiness from M037.

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

## Verification commands

M037 closes only if these remain green:

```bash
uv run python scripts/verify-acp-records.py
uv run python scripts/export-acp-recovery-view.py --check
uv run python scripts/export-acp-architecture-projection.py --check
uv run pytest tests/test_acp_records.py tests/test_acp_recovery_export.py tests/test_acp_architecture_projection.py
uv run python scripts/verify-architecture-graph.py
```

Passing these commands proves ACP mapping-preview mechanics only. It does not make ACP projection canonical.
