# Review 28 remediation program

Status: [proposed] delivery plan, not capability adoption or legal acceptance.
Review: [immutable source](../../../doc/review/review-28-10-09-2026.md).
Packet: `packets/RC-2026-09-10-001.json` (19 open tool-generated findings).
User authorized persistence and long-horizon GSD planning on 2026-09-10; this does not constitute individual legal schema adoption or review disposition.

## GSD program

| Milestone | Scope | Findings | Start prerequisites |
|---|---|---|---|
| M204-w2ktfw | Evidence honesty, C5 validation, metadata sampling, C4 comparability, GSD attempts and acceptance versioning | F01-F05, F19 | None |
| M205-p7xc54 | Pullenti capability crosswalk; grammar/arbitration/context/operation contracts; ADR/glossary/PRD/matrix alignment | F06-F14, F18-F19 | M204 current completion evidence |
| M206-jnbhlz | Profile structure, lexical variants, pre-capture grammar, origins, context/aliases/edition mentions, scoped cues and reference vertical | F06-F12 | M204 and M205; each changed policy actually adopted |
| M207-b2i96m | Codebook, real dual-coder pilot, Work-family holdout, measured evaluation and full operational diagnostics | F01-F03, F14-F15 | M204 and M206; real humans before human-gated slices |
| M208-wrz6fg | Nested amendment grammar, quoted operands, target admission, commencement evidence and new bounded replay chains | F13-F14, F17 | M205 operation adoption and M206; appropriate human evidence for legal evaluation |
| M209-2yg6ix | Seven R035 gates, separate punkt decision, registry expansion and R070 quantified causal coverage | F16-F17 | M204; registry runtime after M206; temporal scaling after M208 and relevant M207 evidence |
| M210-3afp79 | Conditional normative semantics research, human ADR adoption, bounded IR and final review reconciliation | F18-F19, final F01-F19 check | Relevant M205/M207/M208 evidence; explicit human IR adoption before runtime |

29 slices total: M204 has five; each M205-M210 has four. Near-term M204/S02/T01 is a persisted implementation task; later slices use rolling-wave refinement. No auto execution was started by this planning session.

## Dependency enforcement limitation

The GSD planner currently rejects `dependsOn` referencing a pending milestone. Cross-milestone prerequisites are therefore explicit START GATE text in each persisted milestone, not DB-enforced dependency edges. Before dispatch, verify prerequisite completion and adoption with canonical GSD state; a prose prerequisite is not an enforcement proof. Repair/enable pending-DAG planning in process scope and materialize dependencies through sanctioned tools when available. Never set a predecessor complete to satisfy the planner, manipulate SQLite, or automatically traverse a human gate. Sequential IDs alone are not sufficient authority to execute.

M207 human work and M208 syntax work may proceed independently once their own prerequisites hold; M209 registry and temporal slices have separate prerequisites. Do not force unrelated human annotation to block all deterministic syntax research. Conversely no runtime step may cross its required adoption gate.

## Finding coverage and acceptance

- F01: M204/S02, M207/S02-S03. Required proof: real coder-bound measurement and producer-to-promotion negative tests.
- F02: M204/S03, M207/S03. Required proof: seeded selection, validated metadata, provider and Work-family leakage checks.
- F03: M204/S04, M207/S04. Required proof: true input/semantic digests, complete argv and actual operational outcome.
- F04: M204/S05. Required proof: versioned acceptance and equivalent receipt reuse; no silent criterion substitution.
- F05: M204/S01,S05. Required proof: identify four pending tasks, reproduce claim/dispatch defect, sanctioned idempotent recovery; upstream actions need separate confirmation.
- F06: M205/S02, M206/S01. Required proof: siblings/annexes, profile hierarchy and downstream owner assertions.
- F07-F08: M205/S03, M206/S03. Required proof: authorized derivations, positive and negative ThisRef, no unrelated continuation graph.
- F09: M205/S02, M206/S02. Required proof: pre-capture incomplete members, sentence boundaries, preserved origins and bounded arbitration.
- F10: M205/S02, M206/S01,S04. Required proof: normalization spans, morphology unavailable outcome, endpoint versus edition-index membership distinction.
- F11: M206/S04. Required proof: token-bound cues, negation differences, participant anchors; not NormRule adoption.
- F12: M205/S03, M206/S03. Required proof: alias declaration/use/scope, antecedent versus self and non-authoritative edition relation.
- F13: M205/S03, M208/S01-S04. Required proof: adopted operation grammar, old/new operands, nested targets, admission and bounded causal replay.
- F14: M205/S01, optional M207/S03, M208/S01. Required proof: functional prior-art matrix; no license or runtime-parity claim.
- F15: M207/S01-S04. Required proof: real independent annotation and source-bound human acceptance; no automatic seed enlargement.
- F16: M209/S01-S02,S04. Required proof: each R035 gate plus extractor/admission/regeneration; punkt decision before admission.
- F17: M208/S03-S04, M209/S03-S04. Required proof: operation x provision x commencement x transitions x edition deltas, scoped coverage, frozen M201 untouched.
- F18: M205 boundary clarification, M210/S01-S04. Required proof: human-owned legal IR adoption before implementation and independent evaluation.
- F19: M204/S05, M205/S04, M210/S04 and each owning implementation slice. Required proof: class-matched docs/matrix consistency without lifecycle smoothing.

## Controls

```bash
uv run python -m law_nexus_harness review-case validate
uv run python -m law_nexus_harness review-case status --packet-id RC-2026-09-10-001
uv run python -m law_nexus_harness review-case inventory --packet-id RC-2026-09-10-001
uv run python -m law_nexus_harness governor --check review-case-integrity
```

Read JSON: `law-nexus-governor-report/v1`, status, error_count, pass_count and warn_count. Open findings are an expected advisory warning, not semantic validation. The initial check reported status=ok, error_count=0, pass_count=1, warn_count=1, open_count=19. CLI integrity does not prove source-code findings fixed.

The existing register CLI creates empty findings; this packet was created with the canonical codec, pure policy validation and atomic FilesystemReviewPacketStore.add API, carrying 19 source-span-bound open findings. No existing packet or event ledger was overwritten and no human disposition was fabricated. Future review disposition/execution/verification events must use sanctioned application APIs and actual authority. GSD plans are delivery candidates, not accepted review edges.

## Non-goals and hard stops

Rust-only product. No Pullenti code/dictionaries/generated tables/threshold port, no external NLP runtime, no RuVector/TEI adoption, no Applicable runtime, no new clock. No R035/R070 promotion from milestone completion or counts. No historical M203 metric relabeling; corrected evidence explicitly supersedes. Preserve frozen M201 code and pins. Thirteen D388 gates individually adopted or remain stopped; G02 is already wired and only residual resource behavior should be assessed. Real human legal acceptance remains mandatory where specified.

## Acceptance-version and disposition non-claims

The C4 acceptance path is governed by `npa-acceptance-contract/v1`; every admission or retry record must cite `contract_version` and its complete source binding. Receipt presence proves only that an attempt was recorded: it does not prove runtime freshness, successful admission, parser readiness, or legal acceptance. Equivalent retries preserve the predecessor chain and receipt history; they must not silently substitute criteria or overwrite a baseline receipt. Any supersession remains explicit and requires from/to identifiers, reason, authorization, and the preserved hash.

The following statuses are intentionally unchanged by this remediation program:

- G02 is already wired; this program does not relabel that wiring as broader readiness or adopt residual resource behavior without its own evidence.
- The 13 D388 gates remain individually gated; no aggregate count, packet completion, or milestone completion adopts them implicitly.
- `RC28-F01` through `RC28-F19` remain `awaiting_disposition` until their owning evidence and authority requirements are satisfied.
- This document does not close the packet, relabel M203 as readiness, bump the S04 `parser_revision` without a schema change, or create legal/runtime authority from documentation alone.

## M204 S06 requirement evidence classification

This section is additive classification only. It does not mutate requirement status, Review Case lifecycle, GSD state, or any finding disposition. The machine-readable source is `prd/migration/rust-evidence/m204-s06-requirement-evidence.json`.

| Requirement | Evidence class | Concrete evidence | Observed outcome | Supporting-only disposition and limitations |
|---|---|---|---|---|
| R038 | source-bound criterion plus operational attempt | S05 C4 tests/contract and `prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json` | T02 is `timeout` with `SIGTERM`, `duration_ms=1009`, `budget_seconds=3600`, and no terminal exit code; therefore operational acceptance is non-pass | Supporting only; actual duration was not 3600 seconds and the receipt cannot close the standing gate. T04 must reject any false terminalization. |
| R063 | immutable identity, retry, and process provenance | T02 receipt `immutable_attempt_identity`, complete `argv`, binary/contract/parser hashes, toolchain, caller source pin, and owned attempt logs | Attempt identity and provenance are recorded for the timed-out process; no successful runtime result is claimed | Supporting only; caller `source_revision` is not the GSD aggregate, and PATH/label/symlink TOCTOU remains a limitation. |
| R064 | controlled diagnostics and S04 regression support | S04 diagnostic/contract evidence referenced by the T02 receipt plus `prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json` | The external recorder preserves a non-pass timeout outcome without changing Rust `operational_envelope.run_status`; verification remains pending T04 | Supporting only; D444 external receipt does not repair hardcoded Rust `run_status`, and engine `not_fixed`/`not_filed` residue remains unresolved. |
| R081 | documentation-only residue classification | `prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json` and `prd/migration/rust-evidence/m204-s05-m073-residue-waiver.json` | Governor integrity report is structurally passing with 19 open findings; M073 residue is documented-only and blocked-in-scope | Supporting only; this is not product acceptance, an engine waiver, or a lifecycle mutation. Human disposition and fresh sanctioned status remain required. |

The T02 timeout is an operational non-pass even though artifact tests and receipt integrity can pass. No row asserts `actual duration >= 3600`; no row closes R038, R063, R064, R081, R035, R070, or R066. Historical M203 evidence and the S05 waiver remain read-only. Any missing link, unknown outcome, or attempted success after timeout/nonzero is a fail-closed condition for T04.

## M204 S07 requirement evidence classification

This section is additive supporting-only classification for the fresh S07 governor repeat and the terminal C4 attempt. It does not mutate requirement status, Review Case lifecycle, GSD state, or any finding disposition. The machine-readable source is `prd/migration/rust-evidence/m204-s07-requirement-evidence.json`.

| Requirement | Evidence class | Concrete evidence | Observed outcome | Supporting-only disposition and limitations |
|---|---|---|---|---|
| R038 | source-bound criterion plus terminal operational attempt | `prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json`, attempt `full-walk-001`, complete exit 0 over the full 43,785-XML corpus plus 12 Garant files | Terminal process completed in `213166ms`, below the mandatory `3600000ms` floor; strict `--require-operational-pass` verifier rejected the receipt | Supporting only; C4 operational acceptance remains non-pass and the standing duration gate is not closed |
| R063 | immutable identity, process provenance, and complete binding | Receipt records complete argv, attempt identity, binary/contract/parser hashes, Rust toolchain, caller source pin, corpus roots, diagnostics and owned log hashes | Provenance and output integrity are recorded for the owned process; no successful runtime acceptance is claimed | Supporting only; caller `source_revision` is not the GSD aggregate and the short run cannot satisfy the operational criterion |
| R064 | controlled diagnostics and negative operational classification | S07 receipt and valid inventory-bound diagnostics JSONL (`5` records, digest `sha256:0a5f8346dce46ec12247856ebc06dfb79747644bcfa1ed8af10ef115b332a086`) | Diagnostics are valid while the external recorder preserves `operational_acceptance=non-pass` instead of relabeling a short terminal run | Supporting only; no runtime readiness or Rust semantic acceptance is promoted |
| R081 | documentation-only residue and governor repeat classification | Fresh `m204-s07-governor-repeat.json` records `review-case-integrity` exit 0, report status `ok`, `error_count=0`, `tool_error_count=0`, one pass finding, and 19 advisory open findings | Governor control is structurally passing; open inventory remains advisory and no Review Case, ledger, requirement, or lifecycle state changed | Supporting only; no finding is accepted or closed and C4 remains non-pass |

The S07 attempt is durable negative evidence: terminal `exit_code=0` and valid diagnostics do not satisfy the duration floor. No row closes R038, R063, R064, R081, R035, R070, R066, or R073; S06/M203 receipts remain untouched. T04 must treat this short completion as a fail-closed negative terminal and must not emit an operational pass.
