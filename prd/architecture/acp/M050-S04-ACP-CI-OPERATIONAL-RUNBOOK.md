# M050/S04: ACP CI operational runbook

## Status

Operational runbook for the local ACP CI contract. This is the final M050 operating surface for future ACP boundary work.

## Scope and authority boundary

This runbook documents local verification only. It does not create or change GitHub Actions, does not initialize or mutate main `.lex`, does not run git-lex runtime proof, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

## Primary command

Run the local ACP CI contract from the repository root:

```bash
uv run python scripts/verify-acp-ci-contract.py
```

Expected success output includes:

```text
M049 binding verification passed: artifacts=3 diagnostics=0
M056 ACP-kit verification passed: files=9 diagnostics=0
ACP CI contract verification passed: diagnostics=0
```

The command also runs the targeted ACP pytest suites by default:

```text
tests/test_verify_m049_binding.py
tests/test_verify_m056_acp_kit.py
tests/test_verify_acp_ci_contract.py
```

## What the contract checks

The local contract covers:

| Surface | Check |
|---|---|
| M049 binding | `uv run python scripts/verify-m049-binding.py` |
| M056 ACP-kit scaffold | `uv run python scripts/verify-m056-acp-kit.py` |
| Guardrail tests | targeted pytest suites for M049, M056, and M050 contract |
| M058 corrected validation wording | required wording plus stale overclaim detection |
| Diff hygiene | `git diff --check` |
| Main-state residue | absence of `.lex`, `Squad`, `Raw`, and `.artifacts` in the main checkout |

## Narrow fallback commands

Use these only when debugging a focused failure:

```bash
uv run python scripts/verify-m049-binding.py
uv run python scripts/verify-m056-acp-kit.py
uv run python scripts/verify-acp-ci-contract.py --m058-only
uv run pytest tests/test_verify_m049_binding.py tests/test_verify_m056_acp_kit.py tests/test_verify_acp_ci_contract.py
git diff --check
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

Optional wrapper flags:

```text
--skip-tests       debug verifier/writing guard without running pytest
--skip-diff-check  debug content before whitespace diff hygiene
--skip-residue     debug in a deliberately contaminated temporary checkout only
--m058-only        run only the M058 wording guard
```

Do not use skip flags for closeout evidence. Final task, slice, milestone, commit, or PR claims need the full command unless a real blocker is documented.

## M058 validation semantics

The local ACP CI contract preserves the corrected M058 interpretation:

```text
ACP-kit/git-lex is usable as a diagnostic positive runtime/query surface in disposable workspaces. Current ACP validation is not ready as a hard proof gate because generated ACP shapes are underconstrained and validate/query representations differ for object properties.
```

Required wording guarded by the contract includes:

```text
validate/query representation mismatch
current generated ACP shapes are too underconstrained
Do not use `git-lex validate` as a hard ACP proof gate yet
does not validate R035, R037, or R038
ontology domains/restrictions or generator changes
```

Forbidden standalone wording includes:

```text
Forbidden standalone overclaim: git-lex validate is broken
Forbidden standalone overclaim: ACP-kit validation enforcement is proven
Forbidden standalone overclaim: ACP-kit is the ACP source truth
Forbidden standalone overclaim: ACP-kit approves production adoption
Forbidden standalone overclaim: R035 is validated by ACP-kit
Forbidden standalone overclaim: R037 is validated by ACP-kit
Forbidden standalone overclaim: R038 is validated by ACP-kit
```

Explicit rejected-wording examples are allowed only when clearly framed as rejected wording, such as an `Avoid this wording` block.

## Diagnostics triage

When the contract fails, do not immediately force the original implementation plan. Triage from the top down.

### 1. Identify the failing class

| Diagnostic or failure | First interpretation |
|---|---|
| `authority_inversion` | A derived projection or generated artifact may be described with a source-truth overclaim. |
| `unsafe_anchor` | A durable proof anchor may use an absolute, ignored, raw, or non-portable path. |
| `forbidden_git_lex_promotion` | git-lex may be promoted beyond diagnostic/runtime-smoke status. |
| `source_truth_overclaim` | ACP-kit may be described as authoritative source truth. |
| `runtime_adoption_overclaim` | ACP-kit may be described as approving runtime or production adoption. |
| `forbidden_profile_validation` | R035/R037/R038 may be validated from ACP/git-lex/projection evidence alone. |
| `main_state_residue` | Main checkout may contain `.lex`, `Squad`, `Raw`, or `.artifacts` residue. |
| `missing_m058_guard_term` | The corrected M058 validation boundary may be absent or weakened. |
| `forbidden_m058_overclaim` | A stale validation/adoption claim may be present outside a rejected-wording context. |
| `command_failed` | A wrapped verifier, test, diff check, or residue check failed. |

### 2. Decide whether this is a code/doc bug or a task-framing bug

Treat it as a local code/doc bug when:

- the forbidden wording is accidental;
- a command path is wrong;
- a generated artifact has whitespace issues;
- a test fixture no longer matches the intended guardrail;
- main-state residue was accidentally created and can be removed safely.

Step back and reassess task framing when:

- evidence contradicts the hypothesis;
- a negative fixture passes unexpectedly;
- a supposedly unsafe phrase is actually inside an explicit rejected-wording block;
- a verifier blocks a phrase that is necessary to state a boundary;
- the task assumes `git-lex validate` can prove something M058 says is underconstrained;
- the task would require external CI mutation, main `.lex`, source-truth migration, production adoption, or R035/R037/R038 validation.

If framing is wrong, create a research, diagnostic, or replan step rather than weakening the guardrail.

### 3. Preserve proof boundaries

Before changing wording or checks, verify the claim has:

```text
source category
lifecycle state
evidence anchor
proof gate or accepted decision
projection status
```

If any field is missing, mark the claim as proposed, diagnostic, derived, blocked, or needing proof. Do not turn projection evidence into authority.

## Closeout checklist for ACP work

Before claiming ACP work is complete, run fresh verification after the last edit:

```bash
uv run python scripts/verify-acp-ci-contract.py
gitnexus_detect_changes(repo="law-nexus", scope="all")
```

If code changed and the local contract did not already run a relevant test, also run the narrow test suite for that code.

Completion evidence should quote:

```text
ACP CI contract verification passed: diagnostics=0
GitNexus risk level and affected process summary
No main-state residue
```

## Non-actions without explicit future confirmation

M050 does not authorize:

- creating or changing GitHub Actions;
- pushing branches or opening pull requests;
- initializing main checkout `.lex`;
- treating `git-lex validate` as a hard ACP proof gate;
- source-truth migration into ACP-kit or git-lex;
- approving production adoption;
- validating R035, R037, or R038 from ACP-kit, git-lex, RDF, SPARQL, JSON-LD, or projection evidence.

## Final operating rule

Use the local ACP CI contract as a boundary check, not as a substitute for thinking. If the check fails, the next step is not always a patch. Sometimes the correct move is to step back, restate the hypothesis, inspect whether the task was framed incorrectly, and plan the missing research or proof action.
