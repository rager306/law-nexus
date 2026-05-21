# M038 ACP Registry Schema Extension Decision

**Date:** 2026-05-21

## Verdict

Do not mutate the canonical architecture registry schema or canonical JSONL registry files inside M038.

Recommended next step:

```text
Apply a small canonical schema extension in a dedicated follow-up milestone, using the M038 custom fixtures as acceptance evidence.
```

M038 proves that the ACP schema extension shape is stable enough to propose canonical changes, but the actual canonical schema mutation should be isolated in its own milestone because it touches the project architecture contract and verifier assumptions.

## Evidence used

| Evidence | Result |
| --- | --- |
| `prd/architecture/acp/M038-SCHEMA-EXTENSION-DESIGN.md` | Defines candidate item types, metadata fields, relationship semantics, rejected mappings, and fixture requirements. |
| `prd/architecture/acp/fixtures/schema-extension/custom-items.jsonl` | Exercises 5 candidate item types: `prompt_record`, `proposal`, `decision_candidate`, `proof_gate`, `health_finding`. |
| `prd/architecture/acp/fixtures/schema-extension/custom-edges.jsonl` | Exercises 7 candidate relations: `produced_proposal`, `origin_prompt_record`, `suggested_decision`, `origin_proposal`, `requires_proof`, `blocks`, `affects`. |
| `scripts/verify-acp-schema-extension-fixtures.py` | Validates custom fixture shape, endpoints, anchors, forbidden markers, and scoped boundary. |
| `tests/test_acp_schema_extension_fixtures.py` | Covers valid fixtures, invalid endpoint, missing decision-candidate authority, and canonical non-mutation. |
| `uv run python scripts/verify-architecture-graph.py` | Canonical tracked architecture verifier remains green. |

## Options considered

### Option A — Apply canonical schema changes now

Update `prd/architecture/architecture.schema.json`, verifier/extractor logic, and possibly canonical architecture JSONL generation in this milestone.

Verdict: defer.

Reasons:

- M038 has proven custom fixture shape, not canonical extractor/verifier migration.
- Canonical schema mutation is contract-level work and should be committed as its own bounded proof.
- Applying now would mix proof fixture work with production registry contract changes.
- Canonical JSONL integration still needs explicit rules for which ACP records are generated, accepted, or omitted.

### Option B — Defer to a dedicated canonical schema extension milestone

Keep M038 as proof of candidate shape and use it as acceptance evidence for a follow-up canonical schema extension milestone.

Verdict: recommended.

Reasons:

- Preserves the current canonical verifier as stable project guardrail.
- Keeps M038 evidence reusable and scoped.
- Allows the next milestone to focus only on schema/extractor/verifier migration.
- Prevents accidental treatment of custom fixtures as canonical registry truth.

### Option C — Revise mapping before any canonical work

Discard or substantially change the candidate schema extension mapping.

Verdict: not required now.

Reasons:

- Custom fixture checker passes with no diagnostics.
- Required candidate item types and relations are present and test-covered.
- The design explicitly rejects unsafe overloads of `evidence`, `decision`, and `risk`.
- Remaining uncertainty is about canonical migration mechanics, not candidate schema shape.

## Recommended follow-up milestone

Create a future milestone:

```text
ACP Canonical Registry Schema Extension
```

Suggested slices:

1. **Canonical schema patch**
   - Extend `architecture.schema.json` with the smallest accepted subset from M038.
   - Prefer additive enum/optional-field changes.
   - Keep existing registry records valid.
2. **Verifier and extractor migration**
   - Update verifier/extractor only where needed for new ACP-aware fields.
   - Add tests proving current canonical records still pass.
3. **ACP projection integration decision**
   - Decide whether the ACP projection exporter should remain preview-only or gain a checked canonical-output mode.

## Candidate canonical changes to carry forward

Minimum additive candidate set:

```text
item_type additions:
- prompt_record
- proposal
- decision_candidate
- health_finding

optional item fields:
- acp_record_kind
- acp_source_record_id
- capture_mode
- redaction_status
- authority_required
- blocked_actions
- allowed_next_actions
- acp_non_mappable

edge relation additions or checked mapping:
- produced_proposal
- origin_prompt_record
- suggested_decision
- origin_proposal
- requires_proof
- blocks
- affects
```

A follow-up milestone may narrow this set if canonical verifier migration shows a smaller stable subset is safer.

## Allowed next actions

- Use M038 custom fixtures as acceptance evidence for a canonical schema patch.
- Draft a canonical schema patch in a dedicated follow-up milestone.
- Keep ACP preview projection separate until canonical schema migration is proven.
- Continue running the existing architecture verifier as the current project guardrail.

## Blocked actions

- Treat `custom-items.jsonl` or `custom-edges.jsonl` as canonical architecture registry files.
- Write ACP custom fixture records directly into `architecture_items.jsonl` or `architecture_edges.jsonl`.
- Treat prompt provenance as implementation proof.
- Treat a decision candidate as an accepted architecture decision without authority and proof gate resolution.
- Claim R035, R037, or R038 validation from schema-extension fixtures.
- Claim product, parser, FalkorDB, retrieval, legal, production, or independent-review readiness from M038.

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

## Final M038 proof statement

M038 proves:

```text
ACP governance concepts have a test-covered candidate schema-extension shape that can be used as acceptance evidence for a future canonical schema patch.
```

M038 does not prove:

```text
ACP is integrated into the canonical architecture registry.
```
