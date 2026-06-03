# M055 S05 Git Lex Backend Next Decision

## Status

Expanded through `M055-dbt65v / S05 / T03`.

This file is the final decision ledger for M055. T01 defined the evaluation structure. T02 populated the ledger with final S02-S04 evidence and selected one primary next action. T03 records durable guidance deltas and final validation inputs.

## Decision boundary

M055 may recommend the next git-lex backend move, but it may not silently promote git-lex beyond the evidence already proven.

Hard boundaries for all S05 decisions:

```text
ACP source truth remains ACP-native.
git-lex remains non-authoritative unless a future authority migration decision and proof gate are accepted.
main .lex, Squad, and Raw must remain absent in /root/law-nexus.
S05 must not claim production readiness, source-truth transfer, main .lex approval, R035/R037/R038 validation, real legal evidence correctness, Garant ODT parser completeness, FalkorDB behavior, JSON-LD runtime support, broad SPARQL-star parity, or raw/session/provider payload safety.
```

## Required evidence inputs

S05/T02 must cite these evidence groups before selecting a next move:

| Evidence group | Required anchors | What it can prove | What it cannot prove |
|---|---|---|---|
| S01 adoption cutline | `prd/architecture/acp/M055-S01-GIT-LEX-BACKEND-ADOPTION-CUTLINE.md` | Backend ladder, immediate L1 target, blocked stronger roles. | Runtime success, production readiness, source-truth migration. |
| S02 internal adapter | `prd/architecture/acp/M055-S02-INTERNAL-DIAGNOSTIC-BACKEND-ADAPTER.md`, `scripts/acp_git_lex_backend.py`, `tests/test_acp_git_lex_backend.py` | Internal L1 diagnostic adapter contract and denylist behavior. | Regular ACP workflow integration, main `.lex`, production. |
| S03 runtime proof | `prd/architecture/acp/M055-S03-ACP-SHAPED-SHADOW-BACKEND-RUNTIME.md`, `prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl` | ACP-shaped synthetic L1 runtime diagnostics in isolation. | Real legal evidence, R035/R037/R038, production, source truth. |
| S04 gate matrix | `prd/architecture/acp/M055-S04-GIT-LEX-REMAINING-ADOPTION-GATES.md` | Remaining gates, proof classes, follow-up route, blocked/rejected/out-of-scope surfaces. | A final selected next move by itself. |
| Safety verification | Fresh `test ! -e .lex`, `test ! -e Squad`, `test ! -e Raw`, `git diff --check`, and GitNexus scope check where required. | Current checkout safety and diff hygiene. | Any stronger runtime claim not directly tested. |

## Decision options

S05 must evaluate exactly these five options and choose one primary next action.

| Option ID | Option | Meaning | Minimum evidence threshold | Default failure condition |
|---|---|---|---|---|
| `O1` | Continue L1 shadow diagnostics | Keep git-lex as an internal non-authoritative diagnostic/projection backend. | S02 adapter evidence + S03 isolated ACP-shaped runtime proof + S04 gates + no-main-state verification. | Any authority inversion, main-state residue, or unbounded/private diagnostic payload. |
| `O2` | Promote to L2 operational diagnostic backend | Plan or approve regular ACP workflow invocation of git-lex diagnostics, still non-authoritative and no main `.lex`. | O1 threshold plus workflow invocation tests, failure-state persistence, retention policy, and fail-closed operational diagnostics. | Missing workflow/retention/failure-state proof or fail-open behavior. |
| `O3` | Plan isolated main `.lex` rehearsal | Start a separate proof track to rehearse main-repo-like `.lex` state in a disposable clone. | Explicit human decision, state/rollback/sidecar policy, disposable clone rehearsal design, and no mutation of `/root/law-nexus`. | No human decision, no rollback plan, or any direct main checkout mutation. |
| `O4` | Harden production/provenance | Start a production trust track for source-built, release, or plugin-bundled binaries. | Source/build/release/license/SBOM/signature/attestation or accepted absence decision, security review, rollback plan. | Missing provenance/security/license evidence. |
| `O5` | Stop git-lex backend adoption | Stop or pause backend adoption beyond retained historical evidence. | Evidence that L1 diagnostics are not useful enough or risks exceed value even inside the current boundary. | L1 evidence remains useful and bounded without new unacceptable risk. |

## Evidence thresholds by adoption level

| Backend level | Promotion threshold | Current expected status before T02 synthesis |
|---|---|---|
| L0 proof harness | M054 wrapper and isolated runtime matrix. | Already proven before M055. |
| L1 shadow diagnostic/projection backend | S02 adapter + S03 ACP-shaped synthetic runtime matrix + no main `.lex`/`Squad`/`Raw`. | Expected to be met. |
| L2 operational diagnostic backend | L1 plus regular ACP invocation, retention, observability/failure persistence, operational tests. | Expected not met inside M055. |
| L3 main-repo `.lex` backend | Explicit human decision, isolated main-repo rehearsal, state/rollback/sidecar policy. | Blocked; follow-up only. |
| L4 ACP source-truth backend | Authority migration design, conflict resolution, proof-gate policy, accepted decision. | Blocked. |
| L5 production backend | Production provenance, security, release/binary trust, rollback, observability, license/dependency review. | Blocked. |

## Output format for T02 synthesis

T02 must fill this section without changing the option set.

```text
selected option: O1 | O2 | O3 | O4 | O5
readiness classification: L0 | L1 | L2-candidate | L3-rehearsal-candidate | blocked | rejected | stop
primary rationale: <evidence-bounded reason>
evidence used: <S01/S02/S03/S04 anchors and verification commands>
threshold met: yes | no
rejected alternatives: <why the other options were not selected>
blocked claims preserved: <claims S05 must not make>
next follow-up track: <candidate track or none>
no-main-state verification: <fresh verification result>
```

## T02 synthesis result

### Selected next move

```text
selected option: O1
selected next action: continue L1 shadow diagnostics
readiness classification: L1
threshold met: yes for O1; no for O2/O3/O4/O5 as primary current action
next follow-up track: L2 operational diagnostic integration
no-main-state invariant: required and verified during S05/T02
```

### Primary rationale

M055 has enough evidence to continue git-lex as a bounded L1 shadow diagnostic/projection backend:

- S01 set L1 as the immediate accelerated adoption target and kept L3/L4/L5 blocked.
- S02 built an internal ACP-facing adapter over the M054 proof-only wrapper without broadening git-lex command access.
- S03 proved ACP-shaped synthetic L1 runtime diagnostics in an isolated workspace and retained bounded JSONL diagnostics.
- S04 converted all stronger adoption questions into proof gates and routed unproven surfaces to follow-up, blocked, rejected, or out-of-scope tracks.
- Fresh safety verification keeps `.lex`, `Squad`, and `Raw` absent from the main checkout.

This is enough to continue L1 and plan L2. It is not enough to promote git-lex to L2 operational backend inside M055, initialize main `.lex`, migrate source truth, harden production, or stop adoption.

### Evidence used

| Evidence | Result used in decision | Decision impact |
|---|---|---|
| S01 cutline | Immediate target is L1 shadow diagnostic/projection backend; main `.lex`, source-truth, and production are blocked. | Establishes O1 as valid and O3/O4 as follow-up-only. |
| S02 adapter | `scripts/acp_git_lex_backend.py` and tests define an internal non-authoritative adapter; denied operations stay rejected. | Supports O1 but not O2 because regular ACP workflow invocation is not yet proven. |
| S03 runtime proof | ACP-shaped synthetic runtime matrix produced bounded diagnostics with pass=7, diagnostic-fail=1, rejected=2 and no main-state residue. | Supports L1 readiness and preserves diagnostic-only authority. |
| S04 gate matrix | 51 surfaces mapped to proof classes, evidence requirements, failure classifications, and follow-up locations. | Prevents overclaiming and identifies L2 operational integration as the best follow-up track. |
| S05/T02 safety verification | Fresh checks require `.lex`, `Squad`, `Raw` absence and diff hygiene. | Keeps current recommendation inside no-main-state boundary. |

### Option evaluation

| Option ID | Threshold result | Disposition | Why |
|---|---|---|---|
| `O1` | Met. | Selected primary next action. | L1 adapter, runtime proof, gate matrix, and no-main-state evidence are present. |
| `O2` | Not met inside M055. | Rejected as current promotion; recommended as follow-up track. | Workflow invocation, retention, failure persistence, observability, and operational tests are not yet proven. |
| `O3` | Not met. | Rejected as current action; possible later rehearsal track. | No explicit human main-state adoption decision, rollback policy, sidecar policy, or disposable clone rehearsal proof. |
| `O4` | Not met. | Rejected as current action; future provenance/security milestone only. | Release/plugin binary provenance, SBOM/signature/attestation, license/dependency review, security review, and rollback evidence are missing. |
| `O5` | Not met. | Rejected as current action. | L1 diagnostics are useful, bounded, and do not introduce main-state residue; stopping would discard proven acceleration value without evidence of unacceptable L1 risk. |

### Rejected alternatives

```text
O2 rejected for current M055 promotion: L2 operational workflow integration, retention, failure persistence, and fail-closed operational tests are not yet present.
O3 rejected for current M055 action: main .lex rehearsal requires explicit human adoption decision, disposable clone rehearsal, rollback/state policy, and sidecar tracked/ignored policy.
O4 rejected for current M055 action: production/provenance hardening requires release/source/build trust evidence, license/dependency review, SBOM/signature/attestation or accepted absence decision, security review, and rollback plan.
O5 rejected for current M055 action: L1 evidence is useful and bounded enough to continue; no evidence shows L1 should be stopped.
```

### Blocked claims preserved

S05/T02 preserves these blocked claims:

```text
not claimed: L2 operational backend readiness
not claimed: main .lex approval
not claimed: ACP source-truth migration
not claimed: production readiness
not claimed: release/plugin-bundled binary trust
not claimed: JSON-LD runtime support
not claimed: broad SPARQL-star/RDF-star parity
not claimed: raw/session/provider payload safety
not claimed: R035/R037/R038 validation
not claimed: Russian legal evidence correctness
not claimed: Garant ODT parser completeness
not claimed: FalkorDB runtime behavior
```

### Final T02 decision statement

```text
M055 backend readiness classification: L1 shadow diagnostic/projection backend ready to continue
selected next action: continue L1 shadow diagnostics
recommended follow-up: plan L2 operational diagnostic integration
current promotions rejected: L2 immediate promotion, main .lex rehearsal, production/provenance hardening, stop adoption
reason: S02/S03/S04 evidence satisfies O1 only; stronger options require proof gates not yet met
```

### T02 disposition

```text
S05/T02 disposition: backend-readiness-synthesized
selected option: O1 continue L1 shadow diagnostics
readiness classification: L1
selected next action: continue L1 shadow diagnostics and prepare L2 operational diagnostic integration follow-up
rejected alternatives: O2 current L2 promotion, O3 current main .lex rehearsal, O4 current production/provenance hardening, O5 stop adoption
blocked claims preserved: L2 readiness, main .lex approval, source-truth migration, production readiness, release/plugin binary trust, JSON-LD runtime, broad SPARQL-star, raw/session payload safety, R035/R037/R038, legal evidence, Garant parser, FalkorDB behavior
T03 readiness: ready to finalize durable guidance and milestone validation
```

## T03 durable guidance and validation inputs

### Durable guidance deltas

S05/T03 updates project-local git-lex guidance because M055 produced a reusable backend-adoption boundary:

| File | Delta | Reason |
|---|---|---|
| `.agents/skills/git-lex/references/runtime-adoption-gates.md` | Added M055 L1 shadow backend decision update. | Future agents need the final M055 outcome: L1 can continue, L2 is follow-up, stronger roles remain blocked/rejected. |
| `.agents/skills/git-lex/references/acp-boundaries.md` | Added M055 L1 shadow backend authority boundary. | Future agents need safe/unsafe citation language so L1 diagnostics are not mistaken for ACP source-truth or production adoption. |

### Final validation inputs

S05/T03 final validation should cite these checks:

```text
pytest/ruff: rerun relevant S02/S03 suites
S03 diagnostics: validate retained diagnostics artifact shape and classification counts
main state: test ! -e .lex; test ! -e Squad; test ! -e Raw
diff hygiene: git diff --check
scope check: gitnexus_detect_changes({repo:"law-nexus", scope:"all"})
GSD DB: gsd_checkpoint_db before closeout
```

### Final recommendation for milestone summary

```text
M055 final recommendation: continue git-lex as L1 shadow diagnostic/projection backend and plan a follow-up L2 operational diagnostic integration track.
M055 final readiness: L1 ready to continue.
M055 non-promotions: no L2 current promotion, no main .lex, no source-truth migration, no production/provenance adoption, no JSON-LD runtime claim, no broad SPARQL-star claim, no raw/session payload proof anchor, no R035/R037/R038/legal/FalkorDB/parser validation.
```

### T03 disposition

```text
S05/T03 disposition: durable-guidance-and-validation-inputs-ready
durable guidance updated: runtime-adoption-gates.md and acp-boundaries.md
final recommendation: continue L1 shadow diagnostics; plan L2 operational diagnostic integration follow-up
final validation inputs: pytest/ruff, diagnostics artifact check, no-main-state, diff check, GitNexus scope check, GSD DB checkpoint
milestone closeout readiness: ready after fresh verification and GSD validation
```

## Non-overclaiming rules

S05 must reject or downgrade any proposed recommendation that violates these rules:

1. Do not convert diagnostics into ACP source truth.
2. Do not treat RDF/SPARQL/SHACL/JSONL/JSON-LD shape or projection evidence as requirement validation proof.
3. Do not validate R035, R037, or R038 from git-lex diagnostics.
4. Do not infer Russian legal evidence correctness, Garant parser completeness, FalkorDB runtime behavior, retrieval quality, or citation safety from git-lex runtime proof.
5. Do not claim JSON-LD runtime support or broad SPARQL-star/RDF-star parity without dedicated source trace and isolated runtime proof.
6. Do not approve main `.lex`, `Squad`, or `Raw` without explicit human decision and isolated rehearsal.
7. Do not use raw/session/provider payloads as durable proof anchors by default.
8. Do not rely on release or plugin-bundled binaries without provenance and security gates.
9. Do not execute or recommend denied mutating/destructive surfaces (`nuke`, `raw backfill`, broad `save`, arbitrary SPARQL pass-through) as ACP-safe primitives.
10. Do not use ignored paths, absolute local paths, `.gsd/exec`, raw provider payloads, raw vectors, secrets, or unnecessary raw legal text as durable proof anchors.

## T01 disposition

```text
S05/T01 disposition: decision-ledger-structure-ready
options defined: O1 continue L1; O2 promote to L2; O3 plan main .lex rehearsal; O4 harden production/provenance; O5 stop adoption
required evidence inputs: S01 cutline; S02 adapter; S03 runtime proof; S04 gate matrix; fresh safety verification
evidence thresholds: defined for L0-L5 backend levels
output format: selected option, readiness classification, rationale, evidence used, threshold result, rejected alternatives, blocked claims, next follow-up track, no-main-state verification
non-overclaiming rules: preserve ACP-native source truth, no main state, no production/source-truth/R035/R037/R038/legal/FalkorDB/JSON-LD/SPARQL-star/raw-payload overclaims
T02 readiness: ready to synthesize evidence and choose one bounded next move
```
