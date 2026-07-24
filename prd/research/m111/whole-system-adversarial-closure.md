# M111 Whole-System Adversarial Closure

**Status:** `[bounded]` S10 evidence and execution record; T01 classification complete  
**Owner:** M111/S10  
**Inputs:** S05-S09 contracts, D116, D118, D119, D120, D121, D123  
**Cases:** HC-01 through HC-20 remain `[proposed]` until matching runtime evidence exists  
**Technology:** none selected

## Purpose

Classify and execute the strongest honest evidence available for every S09 hostile case without turning architecture prose, adjacent legacy tests or missing runtime surfaces into product proof.

S10 distinguishes architecture conformance from product behavior. It may prove bounded artifact consistency and repository verifier health. It cannot claim runtime idempotency, source completeness, legal correctness, five-clock decisions, E1-E3 capacity or diagnostic sink safety when the corresponding implementation and fixtures do not exist.

## T01 external evidence ledger

All sources were accessed 2026-07-22. Paywalled or partially accessible standards are used only for claims visible in official catalogs/samples or independently corroborated public material.

| ID | Source and revision | Class | Positive and negative lesson | Disposition | Efficiency |
|---|---|---|---|---|---|
| S10-P01 | ISO/IEC/IEEE 15026-2:2022, *Systems and software assurance — Part 2: Assurance case*, second edition 2022-11, https://www.iso.org/standard/80625.html | `primary` standard catalog/sample | Assurance claims require explicit context, argument and tangible evidence; an undeveloped argument is not completed proof. Structure conformance alone does not establish evidence quality. | **Adopt** claim-context-method-evidence records and explicit unsupported claims. No notation/tool selected. | unknown/not applicable |
| S10-P02 | John Rushby, SRI-CSL-15-01, *The Interpretation and Evaluation of Assurance Cases*, July 2015, https://www.csl.sri.com/users/rushby/papers/sri-csl-15-1-assurance-cases.pdf | `primary` technical report | Evidence without argument is unexplained; argument without evidence is unfounded; confidence assumptions must remain visible. | **Adopt** claim-bound evidence and independent sufficiency review. | unknown |
| S10-P03 | NIST SP 800-53A Rev. 5, *Assessing Security and Privacy Controls*, January 2022, https://csrc.nist.gov/pubs/sp/800/53/a/r5/final; NIST glossary `assessment method`, https://csrc.nist.gov/glossary/term/assessment_method | `primary` official guidance/catalog/glossary | Examine, interview and test are different evidence-obtaining methods. Examining artifacts cannot be silently promoted to exercised runtime behavior. Full determination-enum wording was not line-extracted in this pass. | **Adapt** method binding into artifact-static, repository-executable, runtime-required and human/legal modes. | unknown |
| S10-P04 | ISO/IEC/IEEE 29119 software-testing family, public catalog including IEEE 29119-1, https://standards.ieee.org/ieee/29119-1/10779 | `primary` standard catalog with bounded public detail | Mature test practice distinguishes blocked/not-executed from executed failure. Full normative status tables were not available in this pass. | **Adapt** missing prerequisite/surface to `unsupported-case`; never PASS. Do not claim certification-grade conformance to the standard. | unknown |
| S10-P05 | The Open Group, *Architecture Compliance*, official public TOGAF documentation, https://www.opengroup.org/architecture/togaf7-doc/arch/p4/comp/comp.htm | `primary` official architecture guidance | Architecture reviews compare projects with explicit criteria and tailored checklists; they support correction but do not certify runtime behavior. Legacy public page does not establish a current TOGAF product requirement. | **Adapt** independent checklist review and bounded architecture verdicts. | unknown |
| S10-P06 | Object Management Group, *Model Driven Architecture*, https://www.omg.org/mda | `primary` official overview | Platform-independent models can remain separate from implementation technology. MDA does not define law-nexus system architecture. | **Adapt** technology-neutral S10 posture only. | unknown |
| S10-P07 | Leslie Lamport et al., *Specifying and Verifying Systems With TLA+*, https://lamport.azurewebsites.net/pubs/spec-and-verifying.pdf | `primary` formal-methods guidance | State/next-state/invariant specifications describe behaviors without fixing one implementation path. Model checking limits do not transfer to law-nexus capacity. | **Adapt** semantic setup/action/invariant form; **reject** TLA+/TLC selection. | unknown for law-nexus |
| S10-N01 | European Space Agency, *Ariane 501 — Presentation of Inquiry Board report*, 1996, https://www.esa.int/Newsroom/Press_Releases/Ariane_501_-_Presentation_of_Inquiry_Board_report; Gerard Le Lann, INRIA RR-3079, December 1996, https://cgi.cse.unsw.edu.au/~cs2111/ClassicalB/PDF/the-ariane-flight-failure.pdf | `primary` agency failure report plus `independent` technical analysis | Reused/static/component confidence under changed environmental assumptions did not replace representative system-level evidence. A single code-line explanation hides requirements and environment failures. | **Adopt** changed-context revalidation and the ban on runtime PASS from reference/prose evidence. | not a transferable benchmark |

Cross-checks: S10-P01/P02 jointly support claim-argument-evidence; S10-P03/P04 support method/status separation; S10-P05/P06 support architecture review without technology commitment; S10-N01 independently demonstrates the cost of replacing environment-valid system evidence with prior/static confidence. No source provides transferable execution cost or capacity for law-nexus.

## Proof-mode classification protocol

Each case receives one aggregate mode based on its weakest mandatory observable:

| Mode | Exact boundary | Eligible evidence | Cannot prove |
|---|---|---|---|
| `artifact-static` | The whole claim is decidable from authoritative tracked artifacts without exercising domain behavior. | contract sections, owner maps, closed vocabularies, lifecycle tags, rejection-oracle mappings | runtime effects, live source behavior, capacity, legal truth |
| `repository-executable` | Existing tracked read-only scripts/tests exercise the exact claimed repository/governance behavior. | command, exit code, compact output and persisted evidence ID | a different product/runtime claim merely because it is adjacent |
| `runtime-required` | At least one mandatory PASS/FAIL observable needs an implemented product capability, adapter, state transition, effect or sink. | future synthetic fixtures and runtime evidence | PASS from prose, static checks or adjacent legacy tests |
| `human/legal` | The claim requires legal/jurisdictional or authorized human judgment rather than engineering inference. | future named review evidence | engineering/legal correctness without that evidence |

Tie-breaks:

1. If any required runtime observable is absent, aggregate mode is `runtime-required` and current aggregate verdict is `unsupported-case`.
2. Artifact and adjacent executable checks may still PASS as subchecks; they cannot raise the aggregate verdict.
3. A human/legal residual is a non-claim unless that judgment is explicitly in scope; it never becomes an engineering PASS.
4. Missing case fields, fixtures or observable surfaces are `unsupported-case`, not PASS and not automatically architecture FAIL.

## Verdict contract

### `pass`

All required evidence for the declared mode exists, expected typed outcomes occur, every mandatory evidence item is present, no forbidden side effect/owner/ceiling/content occurs, and diagnostic positive controls remain useful.

### `fail`

An available surface produces the wrong outcome, lacks required evidence, permits forbidden ownership/effect/ceiling/invention/leakage, or an artifact/repository check contradicts its authoritative contract.

### `unsupported-case`

A required capability, fixture, adapter, sink or human/legal judgment is absent; or the required proof method cannot be applied. It never counts as PASS. It does not alone prove D123 wrong. Any in-scope unsupported case blocks aggregate runtime conformance PASS.

## HC-01 through HC-20 execution classification

All 20 cases remain runtime-required. Post-M111 evidence now supplies bounded product-capability runtime for HC-01 through HC-13; HC-14 through HC-20 remain unsupported. The table records the strongest honest current evidence and exact remaining observable.

| HC | Primary capability | Aggregate mode/current verdict | Strongest current partial and inputs | S10 check IDs | Missing observable preventing aggregate PASS |
|---|---|---|---|---|---|
| HC-01 | Observe Source | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc01-observe-source-runtime.json` | `S10-HC-01-STATIC`, `S10-HC-01-RT` | none for the bounded synthetic interrupted-source scope; real provider/network/TLS fitness remains a non-claim |
| HC-02 | Inventory Immutable Intake | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc02-inventory-intake-runtime.json` | `S10-HC-02-STATIC`, `S10-HC-02-RT` | none for the bounded synthetic re-inventory scope; real filesystem intake and product storage remain non-claims |
| HC-03 | Dispose Review | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc03-dispose-review-runtime.json` | `S10-HC-03-STATIC`, `S10-HC-03-RT` | none for the bounded synthetic non-accepted scope; real review UI and staffing policy remain non-claims |
| HC-04 | Commit Curated Promotion | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc04-commit-curated-promotion-runtime.json` | `S10-HC-04-STATIC`, `S10-HC-04-RT` | none for the bounded synthetic cancel/retry/mismatch scope; real dual-write storage and product transaction mechanism remain non-claims |
| HC-05 | Decode and Anchor | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc05-decode-anchor-runtime.json` | `S10-HC-05-STATIC`, `S10-HC-05-ADJ`, `S10-HC-05-RT` | none for the bounded synthetic honest/malicious differential; parser crate and source format remain non-claims |
| HC-06 | Gate Lifecycle | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc06-gate-lifecycle-runtime.json` | `S10-HC-06-STATIC`, `S10-HC-06-RT` | none for the bounded synthetic confidence-only/in-place/accepted scope; numerical threshold and product storage remain non-claims |
| HC-07 | Assert Identity | `runtime-required` / `PASS` `[bounded]`; legal correctness remains non-claim | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc07-assert-identity-runtime.json` | `S10-HC-07-STATIC`, `S10-HC-07-RT`, `S10-HC-07-LEGAL` | none for the bounded synthetic one-sided/similarity/bilateral no-merge scope; legal identity judgment and similarity model remain non-claims |
| HC-08 | Validate Relation | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc08-validate-relation-runtime.json` | `S10-HC-08-STATIC`, `S10-HC-08-RT` | none for the bounded synthetic unknown/wrong-owner/accept scope; graph/database schema remains a non-claim |
| HC-09 | Resolve Five-Clock State | `runtime-required` / `PASS` `[bounded]`; applicable-law correctness non-claim | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc09-five-clock-runtime.json` | `S10-HC-09-STATIC`, `S10-HC-09-RT`, `S10-HC-09-LEGAL` | none for the bounded synthetic substitution-matrix scope; applicable-law/effective-date correctness remain non-claims |
| HC-10 | Transition Work State | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc10-work-state-runtime.json` | `S10-HC-10-STATIC`, `S10-HC-10-RT` | none for the bounded synthetic cancel/resume/stale/legal-mapping scope; no workflow engine selected |
| HC-11 | Compute Dependency Closure | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc11-dependency-closure-runtime.json` | `S10-HC-11-STATIC`, `S10-HC-11-RT` | none for the bounded synthetic incomplete/unknown/unbounded/version-skew/claim scope; no dependency index selected |
| HC-12 | Rebuild Disposable Projection | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc12-disposable-projection-runtime.json` | `S10-HC-12-STATIC`, `S10-HC-12-RT` | none for the bounded synthetic partial/stale/cancel/hostile-label scope; no projection store selected |
| HC-13 | Decide Admission | `runtime-required` / `PASS` `[bounded]` | artifact-static contract plus Rust process proof at `prd/migration/rust-evidence/probes/hc13-decide-admission-runtime.json` | `S10-HC-13-STATIC`, `S10-HC-13-RT` | none for the bounded synthetic unknown/saturated/retry/vendor-capacity scope; E1-E3 product capacity remains unproven; no queue/hardware selected |
| HC-14 | Coordinate Checkpoint and Replay | `runtime-required` / `unsupported-case` | artifact-static: mismatch/corrupt/version outcomes and effect suppression rule | `S10-HC-14-STATIC`, `S10-HC-14-RT` | checkpoint/effect runtime, prior-effect replay and corruption/skew fixtures |
| HC-15 | Publish Authoritative H1 Unit | `runtime-required` / `unsupported-case` | artifact-static: sole Publication Authority, complete-only authority | `S10-HC-15-STATIC`, `S10-HC-15-RT` | H1 publisher and concurrent dual-writer/duplicate/partial fixtures |
| HC-16 | Publish Provisional Acceleration | `runtime-required` / `unsupported-case` | artifact-static: mandatory provisional ceiling and invalid direct transition | `S10-HC-16-STATIC`, `S10-HC-16-RT` | provisional publisher, label mutation and direct-promotion attempt |
| HC-17 | Query Evidence-Bounded State | `runtime-required` / `unsupported-case` | artifact-static plus adjacent legacy citation tests; adjacent pass is not HC PASS | `S10-HC-17-STATIC`, `S10-HC-17-ADJ`, `S10-HC-17-RT` | M111 query policy runtime and staging/gap-invention fixtures |
| HC-18 | Resolve Citation | `runtime-required` / `unsupported-case`; official-source legal determination non-claim | artifact-static plus adjacent legacy citation binding tests | `S10-HC-18-STATIC`, `S10-HC-18-ADJ`, `S10-HC-18-RT`, `S10-HC-18-LEGAL` | restricted-official/mirror resolver and missing-anchor fixtures |
| HC-19 | Emit Safe Diagnostics | `runtime-required` / `unsupported-case` | artifact-static plus adjacent secret/redaction marker checks | `S10-HC-19-STATIC`, `S10-HC-19-ADJ`, `S10-HC-19-RT` | declared sink inventory and multi-canary/redaction-failure/injection runtime |
| HC-20 | Evaluate Conformance | `runtime-required` / `unsupported-case` | artifact-static owner/schema/oracle checks plus architecture/ADR verifiers | `S10-HC-20-STATIC`, `S10-HC-20-REPO`, `S10-HC-20-META` | complete meta-suite and differential adapters; runtime verdicts for HC-14-HC-19 remain unsupported; HC-01 through HC-13 are bounded PASS only |

## Current classification result

- Aggregate runtime PASS: **13/20** (`HC-01`, `HC-02`, `HC-03`, `HC-04`, `HC-05`, `HC-06`, `HC-07`, `HC-08`, `HC-09`, `HC-10`, `HC-11`, `HC-12`, `HC-13`, bounded synthetic Rust process proofs).
- Aggregate FAIL: **0/20**.
- Aggregate `unsupported-case`: **7/20** because mandatory runtime observables for HC-14-HC-20 are absent.
- Artifact-static subchecks eligible for T02: **20/20**.
- Adjacent repository executables eligible only as explicitly partial evidence: HC-05, HC-17, HC-18, HC-19 and HC-20.
- Human/legal residual non-claims: HC-07, HC-09 and HC-18.

This result does not invalidate or fully validate D123. Seven unsupported cases still block any aggregate runtime-conformant D123 claim.

## T02 execution rule

For each `S10-HC-*-STATIC` and eligible `*-ADJ`/`*-REPO` check, T02 must record objective evidence ID, result and scope. Every `*-RT` check remains `unsupported-case` unless an existing product surface is discovered and can be exercised without selecting/building a new runtime. Adjacent Python/reference tests must be labelled partial and cannot change aggregate HC verdicts.

## T02 artifact and repository execution record

### Execution results

| Evidence ID | Scope | Result | Exact claim ceiling |
|---|---|---|---|
| `gsd_exec a4f4b7e2-761c-4a8d-a0e0-b6159622e4a4` | `S10-HC-01-STATIC` through `S10-HC-20-STATIC` | 20 PASS, 0 FAIL | Contract content and case invariants only; all 20 aggregate verdicts remain `unsupported-case`. |
| `gsd_exec 79f7398f-1954-43e6-a9a7-9d5d6e7c2e78` | `S10-HC-05-ADJ` legacy S05 ODT findings/probe verifier | PASS | Confirms its historical findings/probe contract only; does not exercise malicious decoder, C10/C12/C13 ownership or diagnostic canaries. |
| `gsd_exec 59eac41d-6779-4ceb-b790-b56e63c2d35b` | `S10-HC-17-ADJ`, `S10-HC-18-ADJ` legacy citation validator/offline contract | 12 tests PASS | Confirms existing citation-field/scoped-no-answer behavior only; does not implement M111 evidence-bounded query, staging visibility or official/mirror resolution. |
| `gsd_exec 2486e61e-c8ea-467e-9b98-69bd2bad4451` | `S10-HC-20-REPO` architecture graph and ADR conformance | PASS: 63 items, 98 edges, 0 graph failures, 0 ADR findings | Repository architecture/ADR consistency only; verifier output is derived and non-authoritative. |
| `gsd_exec 227b293b-b992-4bf1-81a2-b80da7433952` | `S10-HC-19-ADJ` diagnostic-marker inventory | inventory completed: 190 Python files with one or more markers | Discovery/adjacent evidence only. No declared diagnostic sink inventory, synthetic canary execution or positive-control runtime exists. |

Two initial command attempts failed before these successful executions and are retained as diagnostic evidence, not case failures:

- `gsd_exec b9c696cc-d806-4a6f-ab5f-6558cc75b2e1`: legacy ODT verifier requires explicit `--findings` and `--probe-log`; corrected in evidence `79f...`.
- `gsd_exec e6d562ee-36c2-479a-b66c-28341ae4c459`: citation test collection required `PYTHONPATH=src`; corrected in evidence `59ea...`.
- `gsd_exec 55fff571-b02e-4ba4-a369-57463bcac3f4`: first static script used an over-specific HC-11 wording expectation; corrected without changing the contract in evidence `a4f...`.

### Per-case verdict rollup after T02

| Cases | Static subcheck | Adjacent executable subcheck | Aggregate verdict | Reason |
|---|---|---|---|---|
| HC-01-HC-04 | PASS | none | `unsupported-case` | required source/intake/review/promotion runtime absent |
| HC-05 | PASS | PASS, partial legacy ODT verifier | `unsupported-case` | no malicious decoder differential or canary sinks |
| HC-06-HC-16 | PASS | none | `unsupported-case` | required gate/time/work/closure/rebuild/admission/replay/publication runtimes absent |
| HC-17-HC-18 | PASS | PASS, partial legacy citation tests | `unsupported-case` | M111 query/citation hostile surfaces absent; legal residuals remain non-claims |
| HC-19 | PASS | marker inventory only | `unsupported-case` | diagnostic emitters, sink inventory, canaries and positive controls absent |
| HC-20 | PASS | architecture/ADR PASS | `unsupported-case` | full meta-suite depends on runtime verdicts for HC-01-HC-19 and differential adapters |

**Aggregate:** artifact-static PASS `20/20`; repository-adjacent failures after corrected invocation `0`; runtime PASS `0/20`; runtime FAIL `0/20`; aggregate `unsupported-case` `20/20`.

### T02 interpretation

The static and adjacent executable evidence strengthens the bounded architecture baseline and reveals no current artifact contradiction. It does not validate product behavior. No missing runtime surface was simulated, implemented or relabelled PASS during M111. No new consequential interpretation required a different external evidence claim beyond the T01 protocol.

### Post-M111 runtime delta: HC-01

M113 added the missing Rust synthetic runtime surface for HC-01. The command
`cargo run --offline --quiet -p ln-hc01-runner -- verdict` executed timeout,
cancelled, transport-or-TLS-failure and access-restricted paths. Exact
scenario-to-outcome mapping, failed work transitions, bounded diagnostics,
authority absence and raw-canary absence all passed. The negative collapsed-
mapping control fails the PASS predicate.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc01-observe-source-runtime.json`;
- `prd/migration/rust-evidence/probes/hc01-observe-source-runtime.md`;
- implementation revision `092b8c4dbb3f7edfeeeb751222262cd1a95ec651`.

Aggregate immediately after this delta: runtime PASS `1/20`, runtime FAIL `0/20`,
`unsupported-case` `19/20`. Historical T02 rows above remain the M111 execution
record and are not rewritten as if HC-01 runtime existed then.

### Post-M111 runtime delta: HC-02

M114 added the missing Rust synthetic runtime surface for HC-02. The command
`cargo run --offline --quiet -p ln-hc02-runner -- verdict` executed inventory and
re-inventory paths. Stable digest, append-only attempts, staging/review
visibility only, authority absence and raw-canary absence all passed. The
negative mismatched-digest control fails the PASS predicate.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc02-inventory-intake-runtime.json`;
- `prd/migration/rust-evidence/probes/hc02-inventory-intake-runtime.md`;
- implementation revision `505a69e49227e9b867d7768476968fa2b6d1d774`.

Aggregate immediately after this delta: runtime PASS `2/20`, runtime FAIL `0/20`,
`unsupported-case` `18/20`.

### Post-M111 runtime delta: HC-03

M115 added the missing Rust synthetic runtime surface for HC-03. The command
`cargo run --offline --quiet -p ln-hc03-runner -- verdict` executed pending and
quarantined promotion-rejection paths. Non-accepted dispositions rejected
promotion without curated commit or promotion identity.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc03-dispose-review-runtime.json`;
- `prd/migration/rust-evidence/probes/hc03-dispose-review-runtime.md`;
- implementation revision `0dd0966073857a208ebba516409c2447f45eb0cc`.

Aggregate immediately after this delta: runtime PASS `3/20`, runtime FAIL `0/20`,
`unsupported-case` `17/20`.

### Post-M111 runtime delta: HC-04

M116 added the missing Rust synthetic runtime surface for HC-04. The command
`cargo run --offline --quiet -p ln-hc04-runner -- verdict` executed cancel,
identical retry and mismatch paths. Cancel left no curated effect; identical
retry preserved one commit identity/digest; mismatched reuse was rejected; no
publication authority was granted.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc04-commit-curated-promotion-runtime.json`;
- `prd/migration/rust-evidence/probes/hc04-commit-curated-promotion-runtime.md`;
- implementation revision `a28323cdcb21402dac4d4f86f482dcbc1e3e3fae`.

Current aggregate after HC-01 through HC-04: runtime PASS `4/20`, runtime FAIL `0/20`,
`unsupported-case` `16/20`.

### Post-M111 runtime delta: HC-05

M117 added the missing Rust synthetic runtime surface for HC-05. The command
`cargo run --offline --quiet -p ln-hc05-runner -- verdict` executed honest and
malicious decoder paths. Output stayed limited to structural candidates and
exact anchors; gate-owned claims were rejected; canary was absent from outputs;
positive-control diagnostics were present.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc05-decode-anchor-runtime.json`;
- `prd/migration/rust-evidence/probes/hc05-decode-anchor-runtime.md`;
- implementation revision `25c7e68b17d669c58ec178f79df7a55eab17c27c`.

Current aggregate after HC-01 through HC-05: runtime PASS `5/20`, runtime FAIL `0/20`,
`unsupported-case` `15/20`.

### Post-M111 runtime delta: HC-06

M118 added the missing Rust synthetic runtime surface for HC-06. The command
`cargo run --offline --quiet -p ln-hc06-runner -- verdict` executed confidence-only,
in-place and accepted-new-outcome paths. Confidence-only and in-place requests
were rejected with original type preserved; accepted path minted a new immutable
outcome with predecessor chain and C10 gate evidence.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc06-gate-lifecycle-runtime.json`;
- `prd/migration/rust-evidence/probes/hc06-gate-lifecycle-runtime.md`;
- implementation revision `a4363c61f8cc6b52703555602f8d3c3c477dc3d2`.

Current aggregate after HC-01 through HC-06: runtime PASS `6/20`, runtime FAIL `0/20`,
`unsupported-case` `14/20`.

### Post-M111 runtime delta: HC-07

M119 added the missing Rust synthetic runtime surface for HC-07. The command
`cargo run --offline --quiet -p ln-hc07-runner -- verdict` executed one-sided,
similarity-only and bilateral-same-no-merge paths. One-sided and similarity-only
claims could not authorize same/merge; bilateral same could assert without merge;
both identities always survived.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc07-assert-identity-runtime.json`;
- `prd/migration/rust-evidence/probes/hc07-assert-identity-runtime.md`;
- implementation revision `0463b3f3ac58a5788df4f1c4d43fe5deaad2f3a6`.

Current aggregate after HC-01 through HC-07: runtime PASS `7/20`, runtime FAIL `0/20`,
`unsupported-case` `13/20`.

### Post-M111 runtime delta: HC-08

M120 added the missing Rust synthetic runtime surface for HC-08. The command
`cargo run --offline --quiet -p ln-hc08-runner -- verdict` executed unknown-predicate,
wrong-owner and correct-owner-accept paths. Unknown and wrong-owner emissions were
rejected with registry unchanged and no query-fact exposure; correct-owner evidence
could be accepted without mutating registry membership.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc08-validate-relation-runtime.json`;
- `prd/migration/rust-evidence/probes/hc08-validate-relation-runtime.md`;
- implementation revision `437bd53be332b8f2f6f3b7823aee633666750dd2`.

Current aggregate after HC-01 through HC-08: runtime PASS `8/20`, runtime FAIL `0/20`,
`unsupported-case` `12/20`.

### Post-M111 runtime delta: HC-09

M121 added the missing Rust synthetic runtime surface for HC-09. The command
`cargo run --offline --quiet -p ln-hc09-runner -- verdict` executed the five-clock
forbidden-substitution matrix, missing-anchor and present-anchor paths. Every
non-governing substitute including wall-clock was rejected when the governing
anchor was missing; present governing anchors resolved without substitution.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc09-five-clock-runtime.json`;
- `prd/migration/rust-evidence/probes/hc09-five-clock-runtime.md`;
- implementation revision `0b3d60cd14056aeafd8b729852ba3dd4c38f846e`.

Current aggregate after HC-01 through HC-09: runtime PASS `9/20`, runtime FAIL `0/20`,
`unsupported-case` `11/20`.

### Post-M111 runtime delta: HC-10

M122 added the missing Rust synthetic runtime surface for HC-10. The command
`cargo run --offline --quiet -p ln-hc10-runner -- verdict` executed cancel/resume,
stale checkpoint, forbidden legal-mapping matrix and hostile freeze scenarios.
Domain and publication fingerprints remained frozen; progress-to-legal mapping
never applied.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc10-work-state-runtime.json`;
- `prd/migration/rust-evidence/probes/hc10-work-state-runtime.md`;
- implementation revision `32ad977441887f032dc25cc18aaae5367f5f1040`.

Current aggregate after HC-01 through HC-10: runtime PASS `10/20`, runtime FAIL `0/20`,
`unsupported-case` `10/20`.

### Post-M111 runtime delta: HC-11

M123 added the missing Rust synthetic runtime surface for HC-11. The command
`cargo run --offline --quiet -p ln-hc11-runner -- verdict` executed complete,
incomplete, unknown, unbounded, rule-version-mismatch, forbidden-claim and
hostile freeze scenarios. Non-complete statuses blocked publication; progress
never became completeness evidence.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc11-dependency-closure-runtime.json`;
- `prd/migration/rust-evidence/probes/hc11-dependency-closure-runtime.md`;
- implementation revision `a133148c1d0151bac1a7d37e1af2bfdb06197390`.

Current aggregate after HC-01 through HC-11: runtime PASS `11/20`, runtime FAIL `0/20`,
`unsupported-case` `9/20`.

### Post-M111 runtime delta: HC-12

M124 added the missing Rust synthetic runtime surface for HC-12. The command
`cargo run --offline --quiet -p ln-hc12-runner -- verdict` executed partial,
stale/cancel/failed, rebuilt-disposable and hostile demotion scenarios.
Rebuilds remained non-authoritative with ceiling metadata; Publication
Authority was never granted; known gaps were preserved.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc12-disposable-projection-runtime.json`;
- `prd/migration/rust-evidence/probes/hc12-disposable-projection-runtime.md`;
- implementation revision `cd42c5bf4aaad4f08fb4792d00a30f01771201b7`.

Current aggregate after HC-01 through HC-12: runtime PASS `12/20`, runtime FAIL `0/20`,
`unsupported-case` `8/20`.

### Post-M111 runtime delta: HC-13

M125 added the missing Rust synthetic runtime surface for HC-13. The command
`cargo run --offline --quiet -p ln-hc13-runner -- verdict` executed bound-unknown,
saturated, retry-amplification, measured-admit, hostile vendor and forbidden
inference scenarios. Capacity remained unknown on reject; vendor numbers were
never used as precision.

Durable evidence:

- `prd/migration/rust-evidence/probes/hc13-decide-admission-runtime.json`;
- `prd/migration/rust-evidence/probes/hc13-decide-admission-runtime.md`;
- implementation revision `24dc9aa0fc271464f00d3e8c2b42b41791ef7489`.

Current aggregate after HC-01 through HC-13: runtime PASS `13/20`, runtime FAIL `0/20`,
`unsupported-case` `7/20`.

## T03 external negative-experience ledger

All sources were accessed 2026-07-22. External incidents establish failure mechanisms, not local runtime behavior, technology fitness or transferable capacity.

| ID | Primary source | Failure mechanism and supported lesson | Limitation | Law-nexus disposition and owner |
|---|---|---|---|---|
| N01 | GitLab, *Postmortem of database outage of January 31*, 2017-02-10, https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/ | A destructive operation against an ambiguously identified role caused data loss while assumed backup paths were unusable. Recovery existence must be exercised rather than asserted. | PostgreSQL SaaS operations; no legal-corpus, clock or capacity transfer. | **Adopt** fail-closed promotion, explicit operation identity and exercised recovery evidence for HC-04/HC-14; D116 owns promotion. |
| N02 | GitHub, *October 21 post-incident analysis*, 2018, https://github.blog/news-insights/company-news/oct21-post-incident-analysis | A network partition left divergent writes in two clusters and produced stale/inconsistent product views. Integrity required reconciliation rather than unsafe failback. | MySQL multi-datacenter topology is not selected or implied. | **Adopt** singular Publication Authority and reject dual H1 writers for HC-15; stale projections remain non-authoritative for HC-12/HC-17. |
| N03 | U.S. SEC, *Order Instituting Administrative and Cease-and-Desist Proceedings, Knight Capital Americas LLC*, Release 34-70694, 2013-10-16, https://www.sec.gov/files/litigation/admin/2013/34-70694.pdf | Incomplete deployment and dormant parallel code paths emitted millions of unintended effects without pre-effect bounds or a timely hard stop. | Securities market controls and numeric thresholds are non-transferable. | **Adopt** finite pre-effect admission, singular effect paths and effective cancellation for HC-10/HC-13/HC-14/HC-15. |
| N04 | Cloudflare, *How and why the leap second affected Cloudflare DNS*, 2017-01-01, https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/ | Substituting a non-monotonic wall clock for a monotonic duration invalidated a hidden temporal invariant and caused failures. | DNS RTT behavior does not model legal applicability or five clocks. | **Adopt** typed unknown/conflict and reject clock substitution for HC-09; D118 temporal contract owns the rule. |
| N05 | AWS, *Summary of the Amazon S3 Service Disruption in the Northern Virginia Region*, 2017-02-28, https://aws.amazon.com/message/41926/ | An authorized command removed more capacity than intended; recovery assumptions failed at scale and a diagnostic surface shared the failed dependency. | Hyperscale storage metrics and recovery times do not establish E1-E3. | **Adopt** finite destructive/admission bounds, unknown capacity instead of precision and independent diagnostics for HC-11/HC-13/HC-19. |
| N06 | Cloudflare, *Incident report on memory leak caused by Cloudflare parser bug*, 2017-02-23, https://blog.cloudflare.com/incident-report-on-memory-leak-caused-by-cloudflare-parser-bug/ | A parser defect exposed cookies, tokens, request bodies and other adjacent memory; caching amplified disclosure persistence. | CDN parser statistics do not quantify law-nexus risk or redaction overhead. | **Adopt** hostile treatment of parser, log, trace, crash and export sinks; raw legal text, payloads, vectors and credentials remain forbidden for HC-05/HC-19. |
| N07 | Stripe, Brandur Leach, *Designing robust and predictable APIs with idempotency*, 2017-02-22, https://stripe.com/blog/idempotency | Ambiguous network completion can duplicate non-idempotent effects; stable operation identity and safe replay suppress duplicate intent. | Mature implementation guidance, not an outage report or selected API/storage mechanism. | **Adapt** operation identity and identical-replay suppression for HC-04/HC-14/HC-15 without selecting Stripe's mechanism. |
| N08 | W3C, *PROV-DM: The PROV Data Model*, Recommendation 2013-04-30, https://www.w3.org/TR/2013/REC-prov-dm-20130430/ | Assessable outputs retain derivation through entities, activities and agents; outputs without preserved derivation lose provenance. | Domain-neutral provenance does not define Russian legal identity, clocks, authority or H1 completeness. | **Adapt** evidence-bounded query/citation derivation for HC-17/HC-18; D119 and source-authority contracts remain controlling. |

Independent corroboration is mechanism-level only: N02 and N03 expose multiple live effect paths; N03 and N05 expose automation without hard bounds; N01 and N07 bound lost versus duplicate effects; N02 and N08 expose stale or untraceable answer risk. No incident metric is used as local capacity evidence.

## T03 cross-slice adversarial risk matrix

| Attack | Primary owner and artifact | Architecture protection | Architecture verdict | Missing runtime observable |
|---|---|---|---|---|
| Source-authority loss | HC-01 `outward source boundary`; HC-18 `domain citation policy`; separate exclusive owners, not co-owners; `m111-corpus-source-authority-contract.md` and skeleton | Observe Source transport cannot rewrite source authority or turn inaccessible into absent. Resolve Citation separately cannot relabel a mirror official or invent an anchor. Either violation invalidates its owning capability. | `PASS` | HC-01 partial-byte and direct/proxy fixtures; separately, HC-18 restricted-official/mirror fixtures |
| Immutable-intake corruption | HC-02 `intake application policy`; skeleton | Inventory is append-only staging; it cannot destructively rewrite or create curated/current/authoritative state. Destructive mutation or authority labeling invalidates this owner binding. | `PASS` | bounded synthetic re-inventory closed by `S10-HC-02-RT`; real filesystem intake/cancellation and product storage remain open; HC-04 digest mismatch remains D116-owned |
| Partial or duplicate promotion | HC-04 `sole Promotion Authority` under D116; source-authority and skeleton contracts | One idempotent commit identity; partial success is non-authoritative; promotion is not publication. A second promotion writer or partial curated commit invalidates D116. | `PASS` | bounded synthetic cancel/retry/mismatch closed by `S10-HC-04-RT`; product dual-write storage remains open |
| Dual H1 writers | HC-15 `sole Publication Authority` under D120; pipeline and skeleton contracts | Publication Authority is singular and separate from D116; competing writers are forbidden and invalidate D120. | `PASS` | concurrent competing-writer fixture for HC-15 |
| Provisional promotion | HC-16 `application acceleration policy`; D120 Publication Authority supplies the ceiling but is not co-owner; pipeline and skeleton contracts | Provisional remains non-authoritative, incomplete and not-current; direct promotion or a second authoritative writer invalidates the capability. | `PASS` | label-mutation and direct-promotion attempts for HC-16 |
| Replay side effects | HC-14 `application replay policy`; temporal, pipeline and skeleton contracts | Stable operation/effect identity suppresses prior effects; replay creates a new projection and preserves history. Repeated external effects invalidate the capability. | `PASS` | prior-effect replay, corruption and rule-version skew for HC-14 |
| C10 bypass | HC-06 `evidence kernel C10 policy`; canonical and skeleton contracts | Typed transitions have no implicit default, in-place mutation or confidence override. Any workflow/storage bypass invalidates C10. | `PASS` | bounded synthetic confidence-only/in-place/accepted closed by `S10-HC-06-RT`; product storage remains open |
| C12 bypass | HC-07 `evidence kernel C12 policy`; canonical and skeleton contracts | Assertions do not merge; unresolved identities survive; confidence cannot authorize identity. Implicit merge invalidates C12. | `PASS` | bounded synthetic one-sided/similarity/bilateral no-merge closed by `S10-HC-07-RT`; legal identity remains a non-claim |
| C13 bypass | HC-08 `evidence kernel C13 registry policy`; canonical and skeleton contracts | Kernel/family registries are closed; runtime, user or LLM input cannot mint predicates. Unknown-predicate acceptance invalidates C13. | `PASS` | bounded synthetic unknown/wrong-owner/accept closed by `S10-HC-08-RT`; graph schema remains a non-claim |
| Clock substitution | HC-09 `domain temporal policy`; temporal and skeleton contracts | Missing anchors cannot fall back to publication, upload, observation, latest edition or current time. Silent fallback invalidates the five-clock owner binding. | `PASS` | bounded synthetic forbidden-substitution matrix closed by `S10-HC-09-RT`; legal applicability remains a non-claim |
| Incomplete closure | HC-11 `inward dependency policy`; pipeline and skeleton contracts | `incomplete`, `unbounded` and `unknown` cannot become authoritative incremental completeness. Invented complete closure invalidates the capability. | `PASS` | bounded synthetic fixtures closed by `S10-HC-11-RT`; no dependency index selected |
| Unbounded work and false capacity precision | HC-13 `application admission policy`; pipeline and skeleton contracts | Unknown bounds pause/reject admission; formulas and external metrics cannot become E1-E3 measurements or SLA. Unbounded admission or fabricated precision invalidates the capability. | `PASS` | bounded synthetic fixtures closed by `S10-HC-13-RT`; E1-E3 product capacity remains unproven |
| Query/citation invention | HC-17 `inward query policy`; separately HC-18 `domain citation policy`; exclusive owners, not co-owners; source/canonical contracts constrain both | Query cannot create facts, identities, relations, clocks or authority. Citation separately cannot invent anchors or relabel mirrors official. Either invention invalidates its respective capability. | `PASS` | HC-17 staging/gap-invention fixtures; separately HC-18 restricted-official/mirror fixtures |
| Diagnostic leakage | HC-19 `inward diagnostic policy`; skeleton contract | Allowlist plus denylist, positive controls and fail-closed redaction prohibit raw legal text, payloads, vectors and secrets. Forbidden content or silent redaction failure invalidates the capability. | `PASS` | declared sink inventory, multi-canary, injection and redaction-failure runtime for HC-19 |

### T03 aggregate verdict at M111 execution time

- Architecture protection: **PASS 14/14** attack classes.
- Milestone-invalidating architecture FAIL: **0**.
- Runtime-required aggregate HC verdict at M111 execution time: **`unsupported-case` 20/20**. Post-M111 current state is recorded in the HC-01 delta above.
- Legal correctness, source completeness and E1-E3 capacity: **unvalidated/non-claims**.
- Blocking cross-file owner, lifecycle or authority contradictions: **none found** by independent audit.

An architecture PASS means the normative contracts identify an exclusive owner, fail-closed outcome and invalidation condition. It is not product runtime PASS. Discovery of a second D116/D120 writer, mutable intake, direct provisional promotion, bypassable C10/C12/C13 gate, clock fallback, invented closure/query/citation, numeric capacity without local measurement or forbidden diagnostic content would be milestone-invalidating FAIL and require correction in the owning artifact.

## T05 final external cross-check

A fresh independent pass used sources outside the central T01/T03 selection evidence. It found no contradiction or required baseline correction.

| Source | Supported lesson | Limitation and disposition |
|---|---|---|
| NIST SP 800-53 Rev. 5, AC-5 Separation of Duties, 2020-09 with updates through 2020-12-10, https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final | Conflicting duties require explicit separation across relevant systems/components. | Federal security controls do not define H1 or legal-corpus writers. **Retain** D116/D120 separation and exclusive ownership; no runtime PASS. |
| NIST SP 800-53 Rev. 5, AU-9 Protection of Audit Information, same source | Audit information and tools require protection against unauthorized access, modification and deletion, including privileged paths. | Does not define law-nexus diagnostic content. **Retain** HC-19 integrity/privacy ceilings; sink runtime remains unsupported. |
| Assurance Case Working Group, *Goal Structuring Notation Community Standard Version 3*, SCSC-141C, May 2021, https://scsc.uk/gsn-standard | Claims, context, strategies and evidence must remain explicit; evidence must directly support the claim reached. | Assurance notation is not product test automation or legal proof. **Retain** proof-mode binding and `unsupported-case`. |
| OpenTelemetry Project, *Handling sensitive data*, accessed 2026-07-22, https://opentelemetry.io/docs/security/handling-sensitive-data/ | Telemetry may capture credentials, tokens and personal data; collection minimization and redaction/hash/deletion are required controls. | Framework guidance does not select OpenTelemetry or define legal-text/vector policy. **Retain** diagnostic denylist without technology selection. |
| NIST SP 800-92, Kent and Souppaya, *Guide to Computer Security Log Management*, September 2006, https://csrc.nist.gov/pubs/sp/800/92/final | Logs are event records requiring confidentiality, integrity, availability and explicit content policy; operational records are not automatic domain truth. | Legacy log-management guidance is not a provenance ontology or legal temporal model. **Retain** observation/diagnostic non-authority. |

Efficiency and transferable law-nexus capacity remain unknown. At M111 T05 this cross-check left the then-current aggregate at static PASS 20/20, architecture attack protection PASS 14/14, runtime PASS 0/20, runtime FAIL 0/20 and `unsupported-case` 20/20. The post-M125 current runtime aggregate is PASS 13/20, FAIL 0/20 and `unsupported-case` 7/20.

## T01-T05 non-claims

- No product runtime or conformance harness existed or was selected during M111; post-M111 HC-01 runtime evidence is bounded to the explicit delta above.
- No test framework, database, FalkorDB schema, storage, queue/ledger, Rust crate, API, concurrency runtime or deployment topology is selected.
- No legal correctness, source completeness, capacity, performance, redaction-overhead or production-readiness claim is made.
- `unsupported-case` is not PASS and is not a fabricated failure of D123.
