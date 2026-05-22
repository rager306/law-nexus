# M043 ACP Canonical Integration Decision

**Date:** 2026-05-22

## Status

Accepted boundary decision for `M043-qzpaay / S03`.

## Decision

Adopt **opt-in ACP canonical integration proof** as the current ACP canonical integration boundary.

M043 proves that ACP governance records can enter an architecture-build-compatible integration path through an explicit opt-in wrapper. It does not make ACP rows part of the default tracked canonical registry, and it does not change default architecture verifier semantics.

## Evidence considered

### S01 owner and mode decision

`prd/architecture/acp/M043-INTEGRATION-OWNER-DECISION.md` selected:

- owner: opt-in architecture-build composition;
- mode: explicit opt-in composition, not default extractor mutation;
- default extractor/build/verifier behavior must remain unchanged and green;
- direct extractor integration is deferred;
- custom-only remains the fallback if integration proof fails.

### S02 implementation proof

S02 added:

- `scripts/build-acp-canonical-integration.py`;
- `tests/test_acp_canonical_integration.py`;
- `prd/architecture/acp/derived/canonical-integration.items.jsonl`;
- `prd/architecture/acp/derived/canonical-integration.edges.jsonl`;
- `prd/architecture/acp/derived/canonical-integration-report.json`;
- `prd/architecture/acp/derived/canonical-integration-graph-report.json`;
- `prd/architecture/acp/derived/canonical-integration-graph-report.md`.

The opt-in wrapper verifies:

- disabled mode emits baseline canonical records only;
- enabled mode adds ACP canonical-shaped rows explicitly with `--include-acp`;
- custom graph build succeeds on opt-in outputs;
- duplicate IDs, broken endpoints, missing non-claims, missing authority requirements, stale outputs, and canonical output paths are rejected;
- default extractor/build/verifier checks remain green.

Current opt-in enabled counts:

- canonical items: 58;
- canonical edges: 91;
- ACP items: 5;
- ACP edges: 7;
- integration items: 63;
- integration edges: 98;
- custom graph nodes: 63;
- custom graph edges: 98;
- diagnostics: 0.

## Accepted interpretation

M043 is a **canonical integration proof**, but only in opt-in form.

The proof establishes that ACP rows can be composed into an architecture-build-compatible custom integration layer. It does not establish that default tracked canonical JSONL should include ACP rows by default.

Default currentness still comes from:

```text
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py --check
uv run python scripts/verify-architecture-graph.py
```

Opt-in ACP canonical integration proof comes from:

```text
uv run python scripts/build-acp-canonical-integration.py --include-acp --check
```

## Allowed next actions

- Keep using `scripts/build-acp-canonical-integration.py --include-acp --check` as opt-in canonical integration proof.
- Use `canonical-integration-report.json` to recover owner, mode, inputs, outputs, counts, diagnostics, and boundary status.
- Plan a future default canonical extractor integration milestone only if ACP rows should become part of default registry generation.
- Add new ACP record types only with explicit source anchors, non-claims, authority rules, and focused tests.
- Add derived visualization/dashboard/RDF surfaces only as non-authoritative recovery or analysis layers.

## Blocked actions

- Do not hand-edit `prd/architecture/architecture_items.jsonl`.
- Do not hand-edit `prd/architecture/architecture_edges.jsonl`.
- Do not copy ACP canonical-shaped, integrated, composed, or canonical-integration JSONL into default tracked canonical registry JSONL.
- Do not treat opt-in integration success as default architecture registry currentness.
- Do not treat ACP prompt records as implementation proof.
- Do not treat ACP decision candidates as accepted architecture decisions.
- Do not treat proof-gate definitions as proof-gate satisfaction.
- Do not initialize git-lex, RDF, SHACL, SPARQL, or dashboard authority layers as part of this decision.

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

M043 should close as a successful opt-in canonical integration proof.

Recommended next ACP step, if continuing integration work: decide whether there is enough value and proof to plan a future default extractor integration milestone. Until then, opt-in integration remains the safe canonical boundary.
