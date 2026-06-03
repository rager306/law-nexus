# M049 S04 Binding Verifier Checks

## Status

Finalized for `M049 / S04 / T04`; pending final T05 verification.

This artifact documents the focused M049 binding verifier after implementation and unit-test coverage. T05 still performs final closure verification before S04 is complete.

## Purpose

S04 turns the S03 verifier input matrix into an executable proof-check surface for the M049 binding artifacts. The verifier is intentionally focused on the current M049 binding contract and does not regenerate architecture registry JSONL or claim generated registry freshness.

## Verifier entrypoint

```bash
uv run python scripts/verify-m049-binding.py
```

Default checked artifacts:

- `prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md`
- `prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md`
- `prd/architecture/acp/M049-S03-REGISTRY-SOURCE-MAPPING.md`

## Diagnostic contract

| Diagnostic ID | Purpose |
|---|---|
| `authority_inversion` | Derived or diagnostic surfaces are promoted to source truth or validation proof. |
| `unsafe_anchor` | Unsafe/local/raw anchor shapes are used outside rejected/negative context. |
| `missing_profile_proof_gate` | Profile claim is validated or production-ready without a proof gate and accepted evidence. |
| `missing_requirement_proof_gate` | Requirement/source contract terms or requirement proof coverage are missing. |
| `profile_core_drift` | Profile-owned legal/parser/FalkorDB/retrieval/Cypher/R035/R037/R038 claim is promoted into ACP core. |
| `forbidden_git_lex_promotion` | git-lex is promoted beyond M055 L1 shadow diagnostic/projection support. |
| `forbidden_profile_validation` | R035/R037/R038 are validated, closed, retired, or satisfied from ACP/git-lex/projection evidence alone. |
| `main_state_residue` | Main checkout contains `.lex`, `Squad`, `Raw`, or `.artifacts` residue. |
| `registry_currency_overclaim` | Generated registry JSONL/report freshness is claimed without canonical architecture verifier evidence. |
| `proof_gate_placeholder_used_as_proof` | A placeholder proof gate is used as proof. |

## Allowed negative contexts

The verifier is line-oriented and allows negative/guardrail clauses such as `Do not`, `must not`, `forbidden`, rejected-anchor policy, verifier failure examples, and diagnostic descriptions. This preserves the M049 artifacts' boundary language while still catching positive unsafe claims.

## Test coverage

`tests/test_verify_m049_binding.py` verifies:

- current S01/S02/S03 artifacts pass with zero diagnostics;
- all required diagnostic IDs are exposed;
- negative guardrail context is allowed;
- authority inversion, unsafe anchor, missing proof gate, profile/core drift, forbidden git-lex promotion, R035/R037/R038 overclaim, registry-currency overclaim, placeholder proof misuse, and main-state residue each fire on unsafe temporary fixtures.

## Command evidence from T03

```text
uv run pytest tests/test_verify_m049_binding.py
12 passed
```

```text
uv run python scripts/verify-m049-binding.py
M049 binding verification passed: artifacts=3 diagnostics=0
```

## Current limitations

The verifier checks M049 binding artifacts and main-state residue only. It does not replace the canonical architecture verifier and must not be cited as proof that `prd/architecture/architecture_items.jsonl`, `architecture_edges.jsonl`, or graph reports are current.

The verifier is intentionally line-oriented. It allows negative/guardrail/example contexts so the artifacts can document unsafe examples. Tests protect the most important failure modes, but future broader prose patterns may require adding fixture coverage.

## S05 synthesis handoff

S05 may claim:

- S04 provides a focused executable verifier for M049 binding artifacts.
- The verifier passed on current S01/S02/S03 artifacts with zero diagnostics.
- Unit tests prove the verifier catches required boundary failure modes.

S05 must not claim:

- canonical architecture registry freshness;
- generated JSONL/report currentness;
- law-nexus legal correctness, parser completeness, FalkorDB runtime/ingest validation, retrieval quality, citation safety, generated-Cypher safety, or R035/R037/R038 validation;
- git-lex promotion beyond M055 L1 shadow diagnostic/projection support.

## Verification expectations for T05

T05 should run:

```bash
uv run python scripts/verify-m049-binding.py
uv run pytest tests/test_verify_m049_binding.py
python3 -m py_compile scripts/verify-m049-binding.py tests/test_verify_m049_binding.py
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
git diff --check
```

Also run GitNexus change detection:

```text
gitnexus_detect_changes(repo="law-nexus", scope="all")
```
