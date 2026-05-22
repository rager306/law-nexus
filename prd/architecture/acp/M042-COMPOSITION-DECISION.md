# M042 ACP Composition Staging Decision

**Date:** 2026-05-22

## Status

Accepted boundary decision for `M042-jbxawt / S03`.

## Decision

Keep **ACP composition staging** custom-only for now.

M042 proves a named generator ownership and composition seam that can read current canonical architecture registry projections and ACP canonical-shaped custom outputs, validate composition invariants, and emit custom composed outputs under ACP derived paths. It does not prove that ACP rows should be written into tracked canonical architecture registry JSONL.

The next ACP milestone, if pursued, should be a separate canonical extractor/composition integration proof with explicit ownership. It should not be a direct copy or manual mutation of generated JSONL.

## Evidence considered

### S01 generator ownership contract

`prd/architecture/acp/M042-GENERATOR-OWNERSHIP-CONTRACT.md` established:

- named seam: `ACP composition staging`;
- canonical architecture extractor remains the current owner of tracked canonical JSONL generation;
- ACP composition staging owns only custom outputs under ACP derived paths;
- tracked canonical registry JSONL mutation is blocked in M042;
- future canonical integration requires a named generator owner and separate proof.

### S02 composition staging proof

S02 added:

- `scripts/build-acp-composition-staging.py`;
- `tests/test_acp_composition_staging.py`;
- `prd/architecture/acp/derived/composed-registry.items.jsonl`;
- `prd/architecture/acp/derived/composed-registry.edges.jsonl`;
- `prd/architecture/acp/derived/composition-report.json`.

The composition report shows:

- owner: `ACP composition staging`;
- canonical item count: 58;
- canonical edge count: 91;
- ACP item count: 5;
- ACP edge count: 7;
- composed item count: 63;
- composed edge count: 98;
- diagnostic count: 0.

Focused tests cover success, schema validity, report safety, duplicate ID rejection, broken endpoint rejection, unsafe source anchor rejection, untracked ACP source anchor rejection, missing non-claim rejection, missing authority requirement rejection, stale output detection, and canonical output path refusal.

## Accepted interpretation

M042 is a **named composition seam proof**, not canonical registry integration.

The custom composition staging command and outputs are accepted as evidence that ACP composition can be owned, checked, and recovered as a distinct derived layer. They are not accepted as source truth, runtime registry state, product readiness evidence, or canonical architecture registry mutation.

## Future canonical integration preconditions

A future canonical integration milestone may proceed only if it chooses one of these owners:

1. extend `scripts/extract-prd-architecture-items.py` to read ACP source records directly;
2. add an explicit architecture-build composition step that consumes ACP staging outputs and preserves source anchors;
3. keep ACP custom-only if ownership remains ambiguous.

Before writing tracked canonical JSONL, that future milestone must prove:

- no direct copy from ACP derived JSONL into canonical JSONL;
- every ACP-derived canonical row traces to ACP source records or ACP contract/decision docs;
- accepted decisions have an authority/proof-gate workflow separate from decision candidates;
- proof-gate definitions are not treated as proof-gate satisfaction;
- default architecture verifier remains green;
- R035, R037, R038, parser completeness, legal correctness, FalkorDB ingestion/runtime loading, graph-vector retrieval quality, production readiness, and independent external review remain explicitly unvalidated unless separate proof exists.

## Allowed next actions

- Keep running `scripts/build-acp-composition-staging.py --check` as composition staging evidence.
- Use `composition-report.json` as a recovery diagnostic for owner, inputs, outputs, counts, and diagnostics.
- Plan a future canonical integration milestone only after choosing a generator owner.
- Add more ACP source record fixtures only if source anchors and non-claims are checked.
- Add derived visualization or dashboard surfaces only as non-authoritative recovery aids.

## Blocked actions

- Do not copy ACP canonical-shaped, integrated, or composed JSONL into tracked canonical registry JSONL.
- Do not mutate `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl` manually.
- Do not treat composition staging output as source truth.
- Do not treat prompt records as implementation proof.
- Do not treat decision candidates as accepted decisions.
- Do not treat proof-gate definitions as proof-gate satisfaction.
- Do not initialize git-lex, RDF, SHACL, SPARQL, or dashboard authority layers in the main repository as part of M042.

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

M042 should close as a successful named composition seam proof.

Recommended next ACP step: plan a canonical extractor/composition integration proof only if the goal is to move beyond custom staging. Otherwise keep ACP composition staging as the reusable recovery and governance layer.
