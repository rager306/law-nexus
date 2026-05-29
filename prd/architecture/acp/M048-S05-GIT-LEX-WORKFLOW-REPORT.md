# M048 S05 git-lex Workflow Report

**Status:** S05 workflow diagnostics for `M048-q4x62e / S05`.

## Verdict

S05 supports **deferred runtime adoption with safe deterministic ACP mechanics**.

The current executable workflow evidence shows that runtime git-lex acquisition and adoption are **blocked/deferred**, because no existing `git lex` subcommand or `git-lex` executable responded to the help probes and the harness intentionally does not clone, install, download, build, initialize, or persist git-lex state from the main `law-nexus` checkout.

The same evidence shows that deterministic ACP mechanics remain usable: typed source-record validation, extraction/projection/query recovery, lifecycle/proof-gate/profile-boundary diagnostics, and the main-repo mutation guard all have explicit machine-readable workflow status. This is enough to continue ACP design and S06 handoff work, but not enough to claim runtime git-lex adoption.

## Scope

This report is a durable human-readable proof anchor for the S05 workflow harness:

```bash
uv run python scripts/run-m048-s05-git-lex-workflows.py --check
```

It explains the JSON contract emitted by `scripts/run-m048-s05-git-lex-workflows.py` and ties it back to S04 proof inputs and prior ACP integration decisions. It does not replace the executable harness or its tests.

## Workflow Matrix

| Workflow | Current accepted status | Interpretation |
| --- | --- | --- |
| `runtime_acquisition_and_adoption` | `blocked` or `deferred` unless a local executable help probe succeeds | No runtime adoption claim is allowed from fixture-only evidence. The safe path is to defer runtime adoption until a separate acquisition/build/runtime proof exists. |
| `typed_source_record_validation` | `pass` when S04 deterministic validation passes | The tracked S04 fixture taxonomy, references, safety flags, and anchors are usable as bounded ACP mechanics evidence. |
| `extraction_projection_query_recovery` | `pass` when S04 deterministic projection and recovery pass | Temporary projections can support diagnostics and recovery views only; they remain non-authoritative. |
| `lifecycle_proof_gate_profile_boundary` | `pass` when S04 lifecycle/profile/blocked-action checks pass | Proof gates, profile constraints, and blocked actions remain visible without becoming proof satisfaction or product readiness. |
| `main_repo_mutation_guard` | `pass` only when main `.lex` is absent before and after the harness | S05 must fail closed if main-repository `.lex` state exists or is created. |

## Evidence Consumed

S05 consumes these evidence sources:

- `scripts/run-m048-s05-git-lex-workflows.py` — workflow-level diagnostics and JSON contract.
- `tests/test_m048_s05_git_lex_workflows.py` — executable assertions for blocked runtime adoption, deterministic mechanics, mutation guard, source/projection separation, and requirement boundary.
- `prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md` — S04 bounded proof report showing deterministic fixture mechanics pass while runtime git-lex is blocked.
- `prd/architecture/acp/M041-INTEGRATION-DECISION.md` — prior ACP custom-only canonical registry boundary: derived ACP outputs are not source truth and must not mutate default canonical registry files.
- `prd/architecture/acp/M043-CANONICAL-INTEGRATION-DECISION.md` — prior opt-in ACP canonical integration boundary: opt-in integration proof does not change default canonical registry authority or verifier semantics.

The current S05 harness evidence has no fatal failures, reports a blocked/deferred runtime reason when git-lex is unavailable, preserves the mutation guard, and keeps `R035`, `R037`, and `R038` outside S05 validation.

## Accepted Interpretation

The accepted interpretation is **partial workflow readiness, not full runtime adoption**.

S05 proves that future agents can inspect a stable workflow contract and distinguish two different states:

1. **Runtime unavailability:** git-lex executable probes may be missing or failing. That blocks runtime acquisition/adoption claims.
2. **Deterministic ACP mechanics:** S04 source-record validation, projection/recovery, lifecycle/proof-gate, profile-boundary, blocked-action, and mutation-guard mechanics can still pass and remain useful for ACP design.

Therefore, the adoption recommendation is bounded to one of these safe forms:

- `defer_runtime_adoption_keep_deterministic_acp_mechanics_only` when runtime probes are unavailable; or
- `partial_adoption_requires_separate_runtime_git_lex_proof_before_full_adoption` if help probes ever succeed in a future environment.

Neither recommendation is full ACP git-lex runtime adoption.

## Allowed Actions

When runtime git-lex remains blocked or deferred, agents may:

- inspect the S05 JSON contract;
- reuse S04 deterministic fixture validators;
- read tracked S04 fixture records and evidence anchors;
- produce non-authoritative temporary projection diagnostics;
- defer runtime git-lex adoption until acquisition/build/runtime behavior is separately proven;
- use this report as S06 handoff context for architecture-control-plane planning.

## Blocked Actions

S05 evidence blocks these actions:

- cloning git-lex from the S05 harness;
- installing or downloading git-lex from the S05 harness;
- running `git lex init` in the main `law-nexus` repository;
- creating or mutating main-repository `.lex` state;
- claiming full ACP runtime adoption from fixture-only evidence;
- validating `R035`, `R037`, or `R038` from git-lex workflow diagnostics;
- treating a derived projection as source truth;
- treating proof-gate definitions as proof-gate satisfaction;
- treating S05 as product, parser, legal, FalkorDB ingestion, graph-vector retrieval, or production-readiness evidence.

## Non-Claims

S05 does not claim:

- runtime git-lex is available when help probes fail;
- full ACP git-lex adoption;
- product readiness;
- parser completeness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- legal correctness;
- requirement validation for `R035`;
- requirement validation for `R037`;
- requirement validation for `R038`;
- derived projections can be promoted to source truth.

## Source and Projection Boundary

The S05 source/projection boundary is:

| Boundary field | Accepted value |
| --- | --- |
| Source truth | Tracked S04 fixture source records and evidence anchors. |
| Derived projection | Temporary deterministic non-authoritative diagnostic projection. |
| Projection may validate requirements | `false` |
| Projection may override source records | `false` |

This matches the M041 and M043 ACP boundaries: derived outputs may be useful integration or recovery surfaces, but they do not become source truth, default canonical registry state, or authority for requirement validation.

## Mutation Guard

The main-repo mutation guard is mandatory. The S05 harness checks whether `.lex` exists in the main repository before and after diagnostics. The accepted safe state is:

| Check | Accepted result |
| --- | --- |
| Main `.lex` before harness | absent |
| Main `.lex` after harness | absent |
| Guard safe | `true` |

If main `.lex` exists before or after the run, the workflow must fail closed. The report therefore preserves the same operational rule as S04: isolated diagnostics may continue, but durable main-repo git-lex state is blocked until a separate proof and decision explicitly allow it.

## Requirement Boundary

S05 does not validate these requirements:

| Requirement | S05 boundary |
| --- | --- |
| `R035` | `not_validated_by_s05_git_lex_workflow_diagnostics` |
| `R037` | `not_validated_by_s05_git_lex_workflow_diagnostics` |
| `R038` | `not_validated_by_s05_git_lex_workflow_diagnostics` |

This boundary is intentional. S05 is workflow diagnostics for ACP git-lex integration safety, not evidence for parser completeness, FalkorDB ingestion, graph-vector retrieval, legal correctness, or product readiness.

## S06 Handoff

S06 may use S05 as a stable diagnostic and decision input with this handoff:

1. Treat runtime git-lex adoption as blocked/deferred unless a future proof separately establishes safe acquisition, build, invocation, and repository-state behavior.
2. Continue reusing deterministic ACP mechanics only through tracked source records and non-authoritative projections.
3. Preserve the main-repo `.lex` mutation guard as a hard fail-closed condition.
4. Keep `R035`, `R037`, and `R038` out of scope for S05 evidence.
5. If S06 proposes deeper integration, require a new proof gate that explicitly covers runtime executable availability, acquisition policy, repository mutation policy, rollback, and source/projection authority.

## Failure Modes

External dependencies and failure paths considered by this task:

| Dependency | Failure path | Handling/evidence |
| --- | --- | --- |
| Local git-lex executable probes | `git lex --help` or `git-lex --help` missing, non-zero, malformed, or timed out | S05 reports runtime adoption as `blocked` or `deferred`; it does not install, clone, download, or claim adoption. `tests/test_m048_s05_git_lex_workflows.py` covers absent and successful probe cases without allowing full adoption. |
| S04 harness dynamic import | S04 harness file missing or import fails | S05 records a fatal deterministic contract failure instead of silently claiming mechanics. |
| S04 tracked fixture reads and deterministic projection | malformed records, missing relationships, unsafe anchors, or source/projection confusion | S04 validators are reused and failures become S05 fatal failures; S05 report/tests preserve non-authoritative projection language. |
| Main repository filesystem guard | `.lex` already exists or appears after diagnostics | S05 fails closed and reports the mutation guard failure. Main repo `.lex` creation remains blocked. |
| Report drift | human-readable report omits required sections or overclaims runtime/requirement/projection authority | `tests/test_m048_s05_workflow_report.py` asserts required sections and bounded-claim phrases. |

Network acquisition is deliberately not attempted; it is a blocked action rather than an implicit retry path.

## Load Profile

S05 has no production runtime load profile. It adds a static Markdown report and assertion tests over tracked files; it does not introduce a server, queue, API endpoint, database pool, background worker, network crawler, telemetry stream, or user-facing runtime path.

At 10x the expected diagnostic input size, the first bounded resource would be local file parsing and subprocess probe time in the S05/S04 harnesses. No pool sizing, rate limiting, pagination, caching, or autoscaling control is required for this report task. Future runtime git-lex adoption work would need its own load and repository-state profile.

## Negative Tests

Negative and boundary coverage is split between the executable workflow tests and this report assertion test:

- `tests/test_m048_s05_git_lex_workflows.py::test_absent_git_lex_blocks_runtime_adoption_but_s04_mechanics_pass` asserts missing git-lex blocks runtime adoption while deterministic mechanics pass.
- `tests/test_m048_s05_git_lex_workflows.py::test_no_full_adoption_recommendation_even_when_runtime_probe_succeeds` asserts a successful help probe still does not permit `full_adoption`.
- `tests/test_m048_s05_git_lex_workflows.py::test_main_repo_dot_lex_presence_fails_closed_without_creating_state` asserts main-repo `.lex` presence is fatal.
- `tests/test_m048_s05_git_lex_workflows.py::test_requirement_boundary_keeps_r035_r037_r038_unvalidated_and_non_claimed` asserts `R035`, `R037`, and `R038` remain unvalidated.
- `tests/test_m048_s05_git_lex_workflows.py::test_source_projection_boundary_blocks_derived_projection_promotion` asserts derived projections cannot become source truth.
- `tests/test_m048_s05_workflow_report.py` asserts this durable report keeps required sections, status language, allowed and blocked actions, non-claims, source/projection boundary, mutation guard, requirement boundary, failure modes, load profile, negative tests, and S06 handoff.

## Observability Impact

This report is the durable observability surface for S05. It mirrors the workflow JSON in prose so a future agent can localize runtime unavailability separately from deterministic ACP mechanics failures without rerunning the harness first. It also records the safe adoption recommendation, non-claims, blocked actions, mutation guard, and requirement boundary in a stable tracked artifact.
