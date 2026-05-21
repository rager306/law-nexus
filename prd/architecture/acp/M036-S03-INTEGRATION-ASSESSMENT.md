# M036 S03 Integration Boundary Assessment

**Date:** 2026-05-21

## Verdict

Keep ACP records and the current architecture registry separate for the next increment.

M036 proves minimal ACP mechanics: source fixtures, deterministic validation, and a derived recovery view. It does not yet prove that ACP records should feed the existing architecture registry, RDF/graph projections, or dashboard surfaces.

## What M036 proved

S01 created a minimal ACP fixture chain:

```text
APR-0001 -> AP-0001 -> DC-0001 -> PG-0001 -> AHF-0001
```

S02 added deterministic tooling:

```text
scripts/verify-acp-records.py
scripts/export-acp-recovery-view.py
prd/architecture/acp/derived/recovery-view.json
tests/test_acp_records.py
tests/test_acp_recovery_export.py
```

Current proof commands:

```bash
uv run python scripts/verify-acp-records.py
uv run python scripts/export-acp-recovery-view.py --check
uv run pytest tests/test_acp_records.py tests/test_acp_recovery_export.py
uv run python scripts/verify-architecture-graph.py
```

## Relationship to current architecture registry

The current architecture verifier owns static registry/report/source-anchor/decision-fitness/claim-safety checks for existing `prd/architecture` projections.

ACP currently owns a separate proof chain:

| ACP output | Current registry equivalent | Assessment |
| --- | --- | --- |
| ACP Markdown fixtures | Architecture source evidence | Compatible as source evidence, but not yet mapped. |
| ACP schema | Architecture schema concept | Separate and narrower. |
| ACP validator | Static verifier concept | Compatible pattern, separate implementation. |
| ACP recovery view | Derived report concept | Compatible pattern, separate output. |
| ACP health finding | Architecture drift/finding concept | Needs mapping before registry integration. |

The current registry should not ingest ACP records automatically yet because the mapping from ACP record kinds to existing architecture item/edge schema has not been designed or tested.

## Options considered

### Option A — Integrate now

Feed ACP records into the current architecture registry immediately.

Pros:

- One query/report surface.
- ACP records become visible in existing architecture graph sooner.

Cons:

- Requires item/edge schema mapping not yet designed.
- Could confuse source records with derived projections.
- Could introduce false proof-level upgrades.
- Risks treating ACP health/provenance records as product architecture claims.

Verdict: do not choose now.

### Option B — Keep separate next

Keep ACP records, validator, and recovery view separate for one more increment while designing a mapping contract.

Pros:

- Preserves current verifier stability.
- Lets ACP mechanics mature without contaminating existing registry semantics.
- Keeps proof-boundary and source-of-truth hierarchy clear.
- Makes the next integration proof explicit and reviewable.

Cons:

- Two architecture-adjacent surfaces exist temporarily.
- Future agents must know ACP recovery view is separate from current registry report.

Verdict: recommended.

### Option C — Replace existing registry with ACP

Move current architecture registry responsibilities into ACP immediately.

Pros:

- Single future-facing architecture control model.

Cons:

- Much too broad for M036.
- Would risk losing existing verifier guarantees.
- Would conflate research/proof fixtures with active architecture registry.

Verdict: reject.

## Recommendation

Choose **Option B — keep separate next**.

Next safe integration work should be a new explicit slice or milestone that designs and tests the mapping:

```text
ACP record -> architecture item/edge projection
```

before any ACP output is included in current architecture registry artifacts.

## Required next proof before integration

Before integration, prove:

- ACP record kinds map to existing architecture schema or a deliberate schema extension.
- ACP provenance records are not treated as proof of product/runtime/legal claims.
- ACP health findings map to drift/blocked-action diagnostics without altering source truth.
- Derived ACP recovery view remains rebuildable and non-authoritative.
- Canonical architecture verifier remains green after projection changes.
- R035, R037, and R038 remain unchanged unless separate proof gates pass.

## Boundary preservation

This assessment does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

ACP fixtures and recovery output are architecture-governance proof only.

## Current allowed next actions

- Commit M036 S02/S03 proof outputs.
- Complete M036 after validation if all checks remain green.
- Plan a future ACP-to-registry mapping milestone.
- Continue parser roadmap only when the user explicitly resumes it.

## Current blocked actions

- Feed ACP records into current architecture registry without mapping proof.
- Treat ACP recovery view as authoritative architecture proof.
- Promote DC-0001 to accepted decision before PG-0001 evidence is reviewed and accepted.
- Claim product, parser, FalkorDB, retrieval, legal, or independent-review readiness from M036.

## Verification notes

S03 assessment should be verified with:

```bash
uv run python scripts/verify-acp-records.py
uv run python scripts/export-acp-recovery-view.py --check
uv run pytest tests/test_acp_records.py tests/test_acp_recovery_export.py
uv run python scripts/verify-architecture-graph.py
```

Passing checks mean ACP fixture mechanics and current architecture static checks are green. They do not make generated views authoritative.
