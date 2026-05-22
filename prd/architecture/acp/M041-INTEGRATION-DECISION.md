# M041 ACP Canonical Registry Integration Decision

**Date:** 2026-05-21

## Status

Accepted boundary decision for `M041-y19crg / S03`.

## Decision

Keep ACP canonical registry integration **custom-only** for now.

M041 proves that ACP canonical-shaped records can be combined with the current architecture registry records in a custom checked fixture. It does not prove that ACP records should be written into the tracked canonical architecture JSONL registry, and it does not name a canonical generator owner.

A future milestone may integrate ACP records into canonical registry generation only after it chooses and verifies a named generator owner.

## Evidence considered

### S01 source ownership contract

`prd/architecture/acp/M041-SOURCE-OWNERSHIP-CONTRACT.md` established:

- ACP Markdown records are source evidence for ACP governance.
- ACP derived JSON/JSONL outputs are generated proof artifacts, not source truth.
- Derived ACP JSONL must not be copied directly into tracked canonical registry files.
- Future canonical integration requires named generator ownership and checked source anchors.
- Prompt records, proposals, and decision candidates remain non-authoritative unless later authority/proof gates promote them.

### S02 custom integrated fixture

S02 added:

- `scripts/build-acp-integrated-registry-fixture.py`
- `tests/test_acp_integrated_registry_fixture.py`
- `prd/architecture/acp/derived/integrated-registry.items.jsonl`
- `prd/architecture/acp/derived/integrated-registry.edges.jsonl`

The fixture combines current canonical architecture registry records with ACP canonical-shaped custom outputs under ACP derived paths. It validates duplicate IDs, edge endpoints, source anchors, ACP non-claims, decision-candidate authority requirement, stale outputs, and canonical output path refusal.

Current integrated fixture counts:

- 63 items total;
- 98 edges total;
- 5 ACP items;
- 7 ACP edges;
- 0 diagnostics.

## Accepted interpretation

M041 is an **integration proof**, not a canonical mutation proof.

The custom integrated fixture is accepted as evidence that ACP rows can coexist with current architecture registry rows under a safe custom integration surface. It is not accepted as source truth, runtime registry state, or canonical architecture registry mutation.

## Future generator ownership options

A future ACP canonical generator milestone may choose one of these paths:

1. extend the existing architecture extraction/build flow to read ACP source records;
2. keep a separate ACP extractor and add a checked composition step owned by the architecture build flow;
3. keep ACP custom-only if canonical composition would blur source ownership.

Default recommendation: choose option 2 first in a separate proof, because it preserves ACP-specific checks while creating an explicit composition seam.

## Allowed next actions

- Keep running `scripts/build-acp-integrated-registry-fixture.py --check` as custom integration evidence.
- Use integrated fixture diagnostics to refine ACP source ownership rules.
- Plan a future named-generator proof for canonical composition.
- Add more ACP source record types only if their source anchors and non-claims are explicitly checked.
- Add an ACP dashboard or recovery view only as a derived, non-authoritative surface.

## Blocked actions

- Do not copy `prd/architecture/acp/derived/canonical-projection.items.jsonl` into `prd/architecture/architecture_items.jsonl`.
- Do not copy `prd/architecture/acp/derived/canonical-projection.edges.jsonl` into `prd/architecture/architecture_edges.jsonl`.
- Do not copy `prd/architecture/acp/derived/integrated-registry.items.jsonl` into `prd/architecture/architecture_items.jsonl`.
- Do not copy `prd/architecture/acp/derived/integrated-registry.edges.jsonl` into `prd/architecture/architecture_edges.jsonl`.
- Do not treat prompt records as implementation proof.
- Do not treat decision candidates as accepted architecture decisions.
- Do not treat proof-gate definitions as proof-gate satisfaction.
- Do not run `git lex init` in the main repository as part of this decision.

## Non-claims

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

## Closeout verdict

M041 should close as a successful custom integration proof.

The next ACP milestone, if pursued, should be a named generator ownership/composition proof rather than direct canonical JSONL mutation.
