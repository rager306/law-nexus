# NPA parsing program control baseline

Status: `[proposed]` control-plane assessment; non-authoritative.

Source: `doc/review/review-27-05-09-2026.md` (Review 27, 2026-09-05).
Review Case: `RC-2026-09-05-001`.
Packet: `prd/architecture/review-cases/packets/RC-2026-09-05-001.json`.

## Authority and safety boundary

Review 27 and its packet are immutable L0/L1 diagnostic inputs. The packet is
registered with `authoritative: false`, `authority_required: true`,
`normalization.status: draft_extracted`, and no findings or disposition events.
This assessment is a proposed control baseline, not a disposition ledger.
Registration, validation, status, and inventory are structural CLI projections;
none is semantic acceptance, requirement promotion, GSD execution,
implementation proof, legal fact, parser readiness, or product readiness.

The source hash and packet source hash must remain equal to the recorded values
below. A changed review requires a new source revision and packet, never a silent
rewrite of this assessment. R035 and R070 remain active and are not mutated by
this artifact.

## Source-bound intake record

| Item | Value |
|---|---|
| Review source | `doc/review/review-27-05-09-2026.md` |
| Review source SHA-256 | `e343a075f384dd63f1e3fa8cf702e7d01cd982902c74e09f08b766a3772a39d5` |
| Reviewed repository revision in source/packet | `06fe544d3228f8f8314903e9a7b45162a0b0f9e8` |
| Packet | `RC-2026-09-05-001` |
| Packet normalization | `draft_extracted` |
| Packet finding count at intake | `0` |
| Packet event count at intake | `1` (`packet_registered`) |
| Lifecycle | `[diagnostic]` |

## Disposition posture

All twelve review findings are **candidate findings**, reconstructed from the
immutable source because the registered packet intentionally has no extracted
finding nodes. Their default disposition is `defer pending human review`, not
acceptance. The program contract below identifies the next admissible decision
without writing a human disposition event.

Decision vocabulary:

- **accept candidate**: only a human disposition event may accept a scoped
  requirement or work item; acceptance does not close R035/R070.
- **defer**: retain the candidate as open diagnostic debt with an explicit
  owner, proof class, and later decision point.
- **reject**: record only if a human establishes that the source claim is
  inapplicable, duplicate, or contradicted by current authority; no such event
  exists in this intake.

## Finding to authority and proof map

| Key | Candidate finding | Owning authority surface | Existing requirement | Proposed candidate / proof class | Lifecycle scope | Decision point |
|---|---|---|---|---|---|---|
| RC27-F01 | Missing lexical-to-semantic bridge | `prd/architecture/npa-semantic-process.yaml`, ADR-0028, ADR-0019 | none; R035/R070 remain active | `PARSE-P2D/P5/P6` / design then implementation | design → bounded runtime | accept staged bridge only after owner ADR/PRD review; otherwise defer |
| RC27-F02 | Capture bounds helpers unwired | `prd/architecture/npa-capture-arbitration.yaml`, ADR-0028 | `OPER` candidate | `PARSE-BOUNDS` / implementation + hostile evidence | bounded runtime | accept wiring only with terminal diagnostics and hostile proof; defer numeric policy if `deferred-undefined` |
| RC27-F03 | Dual token views are an untyped seam | ADR-0028; `npa-identifying-cycle.yaml` | `PARSE-P2B` | `PARSE-P2B` / contract + implementation | bounded runtime | accept only with incompatible typed boundary or consumer migration; reject blind replacement |
| RC27-F04 | Local grammar absent | `npa-identifying-cycle.yaml`, ADR-0028 | `PARSE-P2D` | `PARSE-P2D` / design + implementation + evidence | proposed → bounded runtime | accept only two bounded immutable frame families first; otherwise defer |
| RC27-F05 | Bounded document context absent | `npa-document-context.yaml`, `npa-semantic-process.yaml` | `PARSE-P5` | `PARSE-P5` / design + implementation + hostile evidence | proposed → bounded runtime | accept worklist only with cycle/limit/unavailable terminals; no model guard |
| RC27-F06 | Condition, negation, exception scope incomplete | `npa-semantic-process.yaml`, ADR-0019, `prd/temporal-legal-model.md` §3 | `PARSE-P6` | `SEM-SCOPE` / implementation + gold evidence | semantic candidate | accept after zero-tolerance preservation evidence; otherwise abstain/defer |
| RC27-F07 | Identity and binding boundary incomplete | ADR-0016, ADR-0019, `npa-identifying-cycle.yaml` | `PARSE-P7/P8` | `IDENT-BIND` / integration + gold | proposed → bounded runtime | accept only candidate/fact and no-false-mint gates; reject any WorkId mint in parser |
| RC27-F08 | Provenance is one-edition bounded | ADR-0017, `current-document-requisites.yaml` | R070 (active) | `TEMP-PROV` / evidence | evidence lifecycle | accept only staged source-bound edition coverage; defer R070 closure |
| RC27-F09 | Registry mapping fixture-sized | ADR-0019, model-crystal, R035 boundary | R035 (active) | `REGISTRY` / proof + integration | evidence lifecycle | accept only named R035 proof gates; reject fixture-only promotion |
| RC27-F10 | Corpus claims need manifests and gold | `npa-corpus-control.yaml` (proposed) | `CORPUS` | `CORPUS` / evidence + operational | diagnostic → validated contour | accept strata and manifest policy; defer quality claims until C5 gold |
| RC27-F11 | Regression/correction memory not durable | `npa-control-ledgers.yaml` (proposed) | `LEDGER`, `METRIC` | `METRIC-LEDGER` / design + implementation | control plane | accept schemas and append-only replay only after compatibility review |
| RC27-F12 | Governor enforcement incomplete | Python harness governor and CLI; `prd/architecture/review-cases/README.md` | `GOV`, `OPER` | `GOVERNOR` / process + contract | repository control | accept additive checks with v1 report compatibility; reject product-side authority |

The candidate names above are not requirement IDs. They become requirements only
through the requirements authority workflow; this task does not perform that
promotion.

## Matrix and proof-class control

The source matrix keys are mapped in `prd/architecture/npa-parsing-program.yaml`.
The minimum proof classes are `docs`, `design`, `implementation`, `evidence`,
and `process`; class substitution is forbidden. In particular, documentation,
CLI registration, fixture measurements, or a green governor run cannot close
implementation/evidence gaps or R035/R070.

The execution order is P0 decode → P1 structure → P2 local analysis → P3
literal projection → P4 overlay → P5 context → P6 semantic projection → P7
identity claim → P8 binding → P9 proposed evidence. Document readiness,
mention, context dependency, identity, binding, and evidence lifecycles remain
orthogonal. Any `deferred-undefined`, `runtime deferred`, conflict, limit, or
unavailable outcome is visible and fail-closed.

## Required disposition packet for a future human review

For each candidate, the owner must choose accept, defer, or reject; name the
canonical target (ADR/PRD/requirement), preserve the source anchor, set a
closure ceiling, and specify class-matched evidence. Accepted work must then
enter GSD through normal planning. A disposition must not be inferred from a
packet status, an inventory count, or this assessment.

## Non-claims

This artifact does not register findings, record human dispositions, promote
requirements, alter ADR-0028, change R035/R070, create GSD work, establish
parser readiness, establish temporal/legal correctness, or authorize Pullenti,
RCO Fact Extractor SDK, or rutokenizer as runtime, dependency, gold, or rater.
