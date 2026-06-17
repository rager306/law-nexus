# M050/S01: ACP CI surface audit

## Status

Audit complete for the current ACP verification surfaces. No implementation changes were made in S01.

## Scope and authority boundary

This artifact inventories local ACP CI and operationalization surfaces. It does not create or change GitHub Actions, does not initialize or mutate main `.lex`, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

M058 corrected validation semantics are treated as the current boundary:

```text
ACP-kit/git-lex is usable as a diagnostic positive runtime/query surface in disposable workspaces. Current ACP validation is not ready as a hard proof gate because generated ACP shapes are underconstrained and validate/query representations differ for object properties.
```

## Existing local verifier surfaces

### M049 binding verifier

Surface:

```text
scripts/verify-m049-binding.py
tests/test_verify_m049_binding.py
```

Purpose:

```text
Focused M049 binding boundary verifier. It checks M049 binding artifacts only and does not regenerate or claim freshness for generated architecture registry views.
```

Current default artifact scope:

```text
prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md
prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md
prd/architecture/acp/M049-S03-REGISTRY-SOURCE-MAPPING.md
```

Diagnostic classes covered:

```text
authority_inversion
unsafe_anchor
missing_profile_proof_gate
missing_requirement_proof_gate
profile_core_drift
forbidden_git_lex_promotion
forbidden_profile_validation
main_state_residue
registry_currency_overclaim
proof_gate_placeholder_used_as_proof
```

Negative fixture coverage exists for:

- overclaim fixture where a generated projection is incorrectly described as source truth;
- unsafe durable anchors;
- missing proof gates;
- ACP core owning Russian legal correctness;
- git-lex as ACP authority or production backend;
- R035 validation by ACP projection evidence;
- registry freshness overclaim;
- placeholder proof misuse;
- main `.lex` residue;
- allowed negative wording such as `Do not validate R035 from ACP/git-lex/projection evidence alone.`

S01 interpretation:

```text
The M049 verifier is a strong boundary verifier for ACP binding artifacts, but it is not a full M050 operational CI contract. It does not cover M056/M058 artifacts by default and does not encode the corrected M058 validation wording as a named check.
```

### M056 ACP-kit scaffold verifier

Surface:

```text
scripts/verify-m056-acp-kit.py
tests/test_verify_m056_acp_kit.py
```

Purpose:

```text
Focused M056 ACP-kit scaffold verifier. It checks the tracked ACP-kit v0 scaffold only. It does not run git-lex, initialize `.lex`, claim runtime compatibility, or claim ACP source-truth migration.
```

Current default kit scope:

```text
git-lex-kit-acp
```

Diagnostic classes covered:

```text
missing_scaffold_file
invalid_kit_config
forbidden_kit_config
missing_ontology_term
missing_guidance_term
missing_example_guardrail
forbidden_kit_path
unsafe_anchor
source_truth_overclaim
runtime_adoption_overclaim
forbidden_profile_validation
main_state_residue
```

Negative fixture coverage exists for:

- missing scaffold files;
- invalid or adaptive kit configuration;
- missing ontology terms;
- missing guidance terms;
- examples without guardrails;
- forbidden kit paths such as Raw, Squad, Soul, AutoKnow, adaptive hooks;
- unsafe durable anchors;
- overclaim fixture where ACP-kit is incorrectly described as source truth;
- ACP-kit production or runtime adoption overclaim;
- R035 validation by ACP-kit projection shape;
- main `.lex` residue;
- allowed negative wording such as `Do not validate R035 from ACP-kit or projection evidence alone.`

S01 interpretation:

```text
The M056 verifier is a strong scaffold and guardrail verifier. It intentionally does not run runtime `git-lex validate`, and it does not encode M058's corrected validate/query distinction as an operational CI claim.
```

## Skill and guidance surfaces

### ACP skill

Surface:

```text
.agents/skills/acp/SKILL.md
.agents/skills/acp/references/source-truth-and-proof-gates.md
.agents/skills/acp/references/acp-kit-roadmap.md
```

Current role:

- Routes ACP source truth, lifecycle states, evidence anchors, proof gates, ACP-kit planning, and profile boundaries.
- Keeps ACP-kit as semantic-kit implementation track rather than backend/source-truth promotion.
- Lists narrow verification commands:

```text
uv run python scripts/verify-m049-binding.py
uv run python scripts/verify-m056-acp-kit.py
python3 -m py_compile <new verifier/test scripts>
uv run pytest <targeted tests>
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
git diff --check
gitnexus_detect_changes(repo="law-nexus", scope="all")
```

S01 interpretation:

```text
The ACP skill already describes the right style of local checks. It needs either a M050 runbook or a minimal wrapper if future agents need one command instead of a small command set.
```

### git-lex skill

Surface:

```text
.agents/skills/git-lex/SKILL.md
.agents/skills/git-lex/references/acp-boundaries.md
.agents/skills/git-lex/references/runtime-adoption-gates.md
```

Current role:

- Routes git-lex runtime, semantic-kit, RDF/SPARQL/JSON-LD, `.lex`, and adoption-boundary questions.
- Blocks main `.lex` state without isolated proof and explicit adoption decision.
- Preserves R035/R037/R038 profile-proof boundaries.
- Captures runtime-smoke findings and prior negative-validation uncertainty.

S01 interpretation:

```text
The git-lex skill should remain the runtime boundary source. M050 should not turn it into ACP CI itself, but M050 may need a synthesis or runbook that points future agents to M058 when interpreting validation failures or passes.
```

## M058 operationalization gap

M058 introduced a corrected validation boundary:

```text
Object-property frontmatter values are normalized to IRIs in the validation graph, while sync/query can expose literals. Current ACP generated shapes contain only three object-property `sh:nodeKind sh:IRI` constraints and no `sh:datatype`, `sh:in`, or `sh:minCount` constraints.
```

Existing verifier state:

- M049 verifier catches ACP authority and profile overclaims.
- M056 verifier catches ACP-kit scaffold, source-truth, runtime-adoption, and profile-validation overclaims.
- Existing tests prove negative guardrail contexts are allowed.
- No existing verifier explicitly checks a stale claim such as `git-lex validate is broken` or the corrected claim that current ACP shapes are underconstrained.
- No existing single local CI contract ties M049, M056, M058 scans, no-main-state, diff hygiene, and targeted tests together.

Gap classification:

```text
M050 needs an operational CI contract, not production CI adoption.
```

Recommended S02 scope:

1. Prefer a minimal local wrapper or documented command contract that runs:

```text
uv run python scripts/verify-m049-binding.py
uv run python scripts/verify-m056-acp-kit.py
uv run pytest tests/test_verify_m049_binding.py tests/test_verify_m056_acp_kit.py
git diff --check
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

2. Add a focused M058 wording scan if it can be kept simple and non-brittle:

```text
required: underconstrained generated shapes, validate/query representation mismatch, no hard proof gate
forbidden: `git-lex validate is broken`, ACP-kit source truth, production adoption, R035/R037/R038 validation
```

3. Do not create or mutate GitHub Actions in M050 without a separate explicit user confirmation.

4. Do not run or rely on main checkout `.lex`.

5. If a check fails in a surprising way, follow the user preference now captured for this project: step back and reassess whether the task framing or negative fixture is wrong before forcing the original plan.

## S01 conclusion

The project already has useful local ACP verifier primitives, but not a single M050 operationalization contract. S02 should build the smallest local contract over existing verifiers and tests, plus a narrow M058 wording guard if needed. S03 should add or document negative guardrails for forbidden claims. S04 should close with a runbook explaining command usage, failure triage, and the corrected M058 validation semantics.
