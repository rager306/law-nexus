# M050/S03: Negative guardrail sufficiency proof

## Status

S03 guardrail sufficiency proof complete. No additional fixtures are required beyond the S02 local ACP CI contract tests and existing M049/M056 verifier tests.

## Scope and authority boundary

This artifact proves coverage of local ACP CI negative guardrails. It does not create or change external CI, does not initialize or mutate main `.lex`, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

## Coverage question

S02 already added a local ACP CI contract:

```text
scripts/verify-acp-ci-contract.py
tests/test_verify_acp_ci_contract.py
```

S03 asks whether additional negative fixtures are needed before the S04 runbook.

Required guardrail categories from M050 are:

```text
unsafe anchors
source-truth overclaims
runtime or production adoption overclaims
R035/R037/R038 validation overclaims
main-state residue
M058 stale validation wording
M058 required corrected wording
allowed rejected-wording context
```

## Coverage matrix

| Guardrail category | Covered by | Evidence class | S03 decision |
|---|---|---|---|
| Unsafe durable anchors | `tests/test_verify_m049_binding.py::test_detects_unsafe_anchor`; `tests/test_verify_m056_acp_kit.py::test_detects_unsafe_anchor` | Existing negative fixtures | Covered |
| Projection source-truth overclaim | `tests/test_verify_m049_binding.py::test_detects_authority_inversion` | Existing negative fixture | Covered |
| ACP-kit source-truth overclaim | `tests/test_verify_m056_acp_kit.py::test_detects_source_truth_overclaim`; S02 contract forbidden claim list | Existing negative fixture plus local contract guard | Covered |
| git-lex as ACP authority or production backend | `tests/test_verify_m049_binding.py::test_detects_forbidden_git_lex_promotion` | Existing negative fixture | Covered |
| ACP-kit runtime or production adoption overclaim | `tests/test_verify_m056_acp_kit.py::test_detects_runtime_adoption_overclaim`; S02 contract forbidden claim list | Existing negative fixture plus local contract guard | Covered |
| R035/R037/R038 profile validation overclaim | `tests/test_verify_m049_binding.py::test_detects_forbidden_profile_validation`; `tests/test_verify_m056_acp_kit.py::test_detects_forbidden_profile_validation`; S02 contract required phrase `does not validate R035, R037, or R038` | Existing negative fixtures plus required wording guard | Covered |
| Main `.lex`, `Squad`, `Raw`, `.artifacts` residue | `tests/test_verify_m049_binding.py::test_detects_main_state_residue`; `tests/test_verify_m056_acp_kit.py::test_detects_main_state_residue`; `tests/test_verify_acp_ci_contract.py::test_detects_main_state_residue` | Existing and S02 negative fixtures | Covered |
| M058 stale validation wording | `tests/test_verify_acp_ci_contract.py::test_detects_forbidden_m058_overclaim` | S02 negative fixture | Covered |
| M058 required corrected wording | `tests/test_verify_acp_ci_contract.py::test_detects_missing_m058_guard_term`; `scripts/verify-acp-ci-contract.py` `REQUIRED_M058_TERMS` | S02 negative fixture plus local contract guard | Covered |
| Explicit rejected wording context | `tests/test_verify_acp_ci_contract.py::test_allows_explicitly_rejected_m058_overclaim_wording` | S02 positive/negative context fixture | Covered |
| Wrapper command composition | `tests/test_verify_acp_ci_contract.py::test_run_contract_can_be_unit_tested_without_subprocesses` | S02 unit fixture | Covered |

## Why no extra fixtures are needed

S01 found that M049 and M056 verifiers already cover the broad ACP boundary classes: unsafe anchors, source-truth inversion, runtime or production adoption overclaims, profile validation overclaims, and main-state residue.

S02 added the missing M058-specific guardrails:

- required corrected validation wording;
- standalone stale claim detection for `git-lex validate is broken`;
- explicit allowance for rejected wording blocks;
- local wrapper composition and residue checks.

The initial S02 failure proved the new M058 guard was not merely decorative. The first negative-context framing allowed a stale standalone claim because a nearby `does not` line was treated as negative context. The fix narrowed generic negative context to the current line and allowed previous context only for explicit `Avoid this wording` blocks. This matches the project preference: when a proof fails unexpectedly, step back and reassess the task framing before forcing the original implementation.

No uncovered guardrail category remains in the M050 scope.

## Non-goals preserved

S03 does not add fixtures for:

- production CI or GitHub Actions mutation;
- runtime `git-lex validate` proof;
- true negative SHACL proof for ACP generated shapes;
- main checkout `.lex` initialization;
- R035/R037/R038 validation;
- source-truth migration into ACP-kit or git-lex.

Those are outside M050 or remain blocked until separate proof gates pass.

## S03 conclusion

The local ACP CI contract has sufficient negative guardrail coverage for M050. S04 can proceed to the operational runbook and closeout without adding duplicate fixtures.

Correct next step:

```text
Document how to run `uv run python scripts/verify-acp-ci-contract.py`, how to interpret diagnostics, and how to step back when a failure indicates incorrect task framing rather than a simple implementation bug.
```
