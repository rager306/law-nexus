# M039 ACP Projection Integration Decision

**Date:** 2026-05-21

## Verdict

Keep `scripts/export-acp-architecture-projection.py` preview-only for M039.

Recommended next step:

```text
Create a dedicated ACP Canonical Projection Export Proof milestone before any canonical-output mode is added.
```

M039 extends the canonical architecture schema so ACP-aware records can be represented. It does not yet prove a safe generator that writes ACP records into canonical architecture JSONL outputs.

## Evidence used

| Evidence | Result |
| --- | --- |
| `prd/architecture/architecture.schema.json` | Additively accepts ACP-aware item types, optional ACP fields, and ACP-aware edge relations. |
| `tests/test_architecture_registry_schema.py` | Tests ACP-aware canonical-shaped item and edge records. |
| `prd/architecture/acp/M039-S02-VERIFIER-MIGRATION-ASSESSMENT.md` | Concludes no verifier/extractor code migration is needed until canonical ACP output generation is designed. |
| `scripts/export-acp-architecture-projection.py` | Still writes preview output only and refuses canonical registry paths. |
| `scripts/verify-architecture-graph.py` | Remains green on tracked canonical outputs. |

## Options considered

### Option A — Keep projection preview-only

Continue using `architecture-projection.preview.json` as ACP mapping evidence, not canonical registry data.

Verdict: recommended for M039.

Reasons:

- The schema now accepts ACP-aware records, but generation rules are not designed yet.
- Existing exporter intentionally refuses canonical registry writes.
- Keeping preview-only prevents custom/provenance records from being mistaken for accepted architecture truth.
- This keeps the architecture verifier focused on current tracked canonical outputs.

### Option B — Add checked canonical-output mode now

Modify `export-acp-architecture-projection.py` so it can emit canonical `item` and `edge` JSONL records.

Verdict: defer.

Reasons:

- Canonical output mode needs its own acceptance contract: IDs, source anchors, statuses, proof levels, non-claims, and generation path.
- Current S01/S02 evidence proves schema acceptance, not generation semantics.
- Directly writing canonical JSONL would bypass the existing source-of-truth hierarchy unless the generator is carefully proof-gated.

### Option C — Stop ACP projection work and move to git-lex/RDF or dashboard

Shift effort to RDF/SHACL/git-lex or dashboard visualization now.

Verdict: reject for now.

Reasons:

- ACP canonical-output generation is the next missing contract.
- RDF/dashboard layers should consume stable canonical or explicitly preview-labeled projections.
- A dashboard now would risk presenting preview/custom fixture evidence as authoritative.

## Recommended follow-up milestone

Create a future milestone:

```text
ACP Canonical Projection Export Proof
```

Suggested slices:

1. **Canonical projection contract**
   - Define how ACP recovery/projection records become canonical `item` and `edge` JSONL records.
   - Define ID policy, source anchors, status/proof-level mapping, non-claims, and blocked records.
2. **Checked output mode**
   - Add an opt-in output mode that writes to a temporary/custom path first.
   - It must continue refusing canonical registry paths unless explicitly invoked through a checked generation workflow.
3. **Canonical registry integration decision**
   - Decide whether to wire ACP projection into the canonical extraction/build flow, keep custom output, or defer.

## Allowed next actions

- Use canonical schema additions to validate ACP-aware generated candidates in custom paths.
- Keep `architecture-projection.preview.json` as preview evidence.
- Design a checked canonical projection contract.
- Continue running canonical architecture verifier on tracked outputs.

## Blocked actions

- Write ACP preview output directly to `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.
- Treat ACP prompt records as proof.
- Treat `decision_candidate` records as accepted decisions without authority and proof gate resolution.
- Treat custom schema-extension fixtures as canonical registry truth.
- Move to git-lex/RDF or dashboard as an authority surface before canonical projection generation semantics are proof-gated.
- Claim R035, R037, or R038 validation from M039.
- Claim product, parser, FalkorDB, retrieval, legal, production, or independent-review readiness from M039.

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

## M039 final proof statement

M039 proves:

```text
The canonical architecture schema can accept ACP-aware governance record shapes while existing verifier guardrails remain green.
```

M039 does not prove:

```text
ACP records are generated into the canonical architecture registry.
```
