---
id: ADR-0002
title: ADR standard and the compliance-gate / ACP-checkpoint split
status: Accepted
lifecycle: "[validated] (standard + policy distinction); gate tooling [proposed]/[deferred] to S03"
date: 2026-06-21
supersedes: none
related: [ADR-0001, D098, D097, D035]
---

# ADR-0002: ADR standard and the compliance-gate / ACP-checkpoint split

## Status

Accepted `[validated]` for the standard and the gate-vs-ACP policy distinction:
the MADR standard is live in `doc/adr/README.md` and ADR-0001 is the first
conforming record, and the split is backed by the active governing decision
D098.

The compliance-gate **tooling** named below (import-linter layer contracts and
the `verify-adr-conformance` MADR checker) is `[proposed]` / `[deferred]` to
slice S03 — this ADR commits to the mechanism, but neither tool is built in
this slice. This scoping is deliberate and follows the D098 anti-smoothing
discipline: a policy and its enforcement tooling are tagged separately.

## Context

Two needs exist, and conflating them is the single most common failure mode for
architecture-governance in this project:

1. **The architecture needs hard enforcement of structural invariants.** The
   onion package structure (ADR-0001) is only real if its inward-only dependency
   rule is actually enforced — otherwise the layering degrades to aspirational
   comments. An ADR standard is only real if ADRs actually conform to MADR and
   carry D098 lifecycle tags — otherwise the standard degrades to a template no
   one follows. These are *structural* failures: a wrong import direction, a
   missing lifecycle tag. They are one-time, checkable, and fixable.

2. **The process needs continuous observation of behavioural drift.** Evidence
   boundaries get smoothed (`[bounded]` quietly becomes `[validated]`); scope
   creeps; trajectory is lost. D098 documents that these patterns recurred
   M035–M067 *and* in the AI's own baseline overestimation. This drift is
   *behavioural*: it does not live in a single file or a single import, it lives
   across claims over time. It cannot be reduced to a one-time structural check.

D098 settles how need (2) must be handled: ACP/git-lex operate in **checkpoint
mode — detect+log+flag, NOT gate/block.** D098's rationale is explicit and
hard-won:

> gate-mode ACP becomes a blocker that perpetuates meta-work (the M035–M063
> "never-install" paralysis is the cautionary case). Checkpoint allows product
> flow + catches drift after.

So D098 **forbids** using the ACP as a blocking gate. But need (1) — hard
structural enforcement of the code architecture — does not go away because the
ACP is non-blocking. The trap is to let the ACP absorb both jobs (then D098 is
violated) or to let a gate absorb both jobs (then product work is blocked on
behavioural noise).

The decision in this ADR is the clean separation that dissolves the trap.

**Significance-gating (self-check, per the README standard):** this decision
meets the *Architectural* criterion — it establishes a foundational enforcement
boundary (what is structurally enforced vs what is behaviourally observed) that
shapes how conformance is maintained for the life of the codebase. It also
touches the *Persistent tech choice* criterion in committing to import-linter
and `verify-adr-conformance` as the structural gate tooling.

## Decision

Establish **two distinct enforcement mechanisms** with a strict separation of
concerns. They protect different things, run on different schedules, and fail
differently. They must never be merged into one.

### 1. Compliance gate — structural, hard-fail, code-architecture

The compliance gate enforces **structural invariants of the code's
architecture**. It is one-time, checkable, and **hard-fails** the build / merge.

| Attribute | Compliance gate |
|---|---|
| **Protects** | Code architecture — structural invariants (layer direction, ADR conformance). |
| **Nature** | Structural, one-time per change. |
| **Failure action** | **Hard fail** — blocks the build / merge. The violation must be fixed or the boundary explicitly revised. |
| **Scope** | Wrong import direction (onion layers, ADR-0001); non-MADR-compliant ADRs; missing D098 lifecycle tags on an ADR. |
| **Tooling** | `import-linter` (layer contracts) + `verify-adr-conformance` (MADR + lifecycle-tag checker). Both `[proposed]`/`[deferred]` to S03. |
| **Authority** | ADR-0001 (onion structure) and this ADR (gate policy). |

The gate is allowed to be a hard block *because* it is narrow and structural:
it answers "does this code conform to the architecture?" — a yes/no question
with a definitive source of truth (the layering in ADR-0001, the MADR template
in the README). It does not judge intent, process, or evidence quality.

### 2. ACP checkpoint — behavioural, detect+log+flag, non-blocking

The ACP (Architecture Control Plane) observes **behavioural drift across the
process**. It is continuous and **must not block product work**, exactly as D098
mandates.

| Attribute | ACP checkpoint |
|---|---|
| **Protects** | Process integrity — behavioural drift (evidence-boundary smoothing, scope creep, lost trajectory). |
| **Nature** | Behavioural, continuous across the lifecycle. |
| **Failure action** | **Detect + log + flag** — does NOT block. Drift is recorded (ACP HealthFinding pattern) and surfaced, not silently fixed, not gated. |
| **Scope** | Architectural / requirement / state claims — where drift actually happens (D098: targeted, not all-prose). |
| **Tooling** | Mandatory D098 lifecycle tagging; the ACP record rule; `prd/ARCHITECTURE.md` as living truth oracle; drift logging. |
| **Authority** | D098 (anti-drift governance). |

### The split, in one table — gate ≠ ACP

| Dimension | Compliance gate | ACP checkpoint |
|---|---|---|
| **What it protects** | Code architecture (structural) | Process integrity (behavioural) |
| **Timing** | One-time, at build/CI/commit | Continuous, across the lifecycle |
| **Failure action** | **Hard fail** (blocks) | **Detect + log + flag** (non-blocking) |
| **Question it answers** | "Does this conform to the structure?" | "Is the process drifting?" |
| **Source of truth** | Layering (ADR-0001), MADR (README) — definitive, checkable | Behaviour over time — observed, not checkable in one pass |
| **Reversibility** | Structural — once fixed, stays fixed until reverted | Behavioural — drift can recur; must be re-observed |
| **Authority** | ADR-0001 + this ADR | D098 |

### Why the split is mandatory (anti-substitution)

The two mechanisms must remain distinct because **neither can do the other's job
without harm**:

- If the **gate absorbs the ACP's job**, product work gets blocked on
  behavioural noise — recreating exactly the M035–M063 paralysis D098 was
  written to prevent. A structural checker cannot fairly judge evidence quality
  or trajectory; forcing it to do so makes it a brittle, opinionated blocker.

- If the **ACP absorbs the gate's job**, two things break at once. First, D098
  is violated: the ACP would have to become a gate/block, which D098 forbids.
  Second, structural invariants lose hard enforcement — non-blocking "flags"
  on a wrong import direction get acknowledged and then ignored, and the onion
  layering degrades to aspirational.

The split keeps each mechanism doing only what it is good at: the gate
**enforces structure** definitively; the ACP **observes behaviour** without
breaking product flow. The rule, stated as a guardrail for any future change:

> The compliance gate enforces structural conformance and may hard-fail. The ACP
> observes behavioural drift and must not block. **Gate ≠ ACP.** Do not route a
> structural check through the ACP, and do not route a behavioural concern
> through the gate.

### Per-claim D098 lifecycle tagging

Following ADR-0001's discipline, the claims in this ADR are tagged individually
and not smoothed up:

- MADR ADR standard (`doc/adr/README.md`) — `[validated]`: the README is live
  and ADR-0001 is the first conforming record.
- The gate-vs-ACP policy distinction — `[validated]` as a governance decision:
  D098 is the explicit, active authority, and the distinction is demonstrated by
  the live standard plus ADR-0001.
- Compliance-gate **tooling** (import-linter layer contracts,
  `verify-adr-conformance`) — `[proposed]` / `[deferred]` to S03: this ADR
  commits to the mechanism; neither tool is built in this slice.
- ACP checkpoint behaviour (detect+log+flag, non-blocking) — `[validated]` as
  governance policy per D098; its *runtime* exercise is `[bounded]` and tracked
  under the ACP's own lifecycle, not this ADR.

## Consequences

- **What becomes easier.** Each concern has one clear owner and one clear
  failure mode. A wrong import or a malformed ADR is a build failure with a
  definitive fix; a drift pattern is a logged finding with a revisit trigger.
  Engineers and agents do not have to guess whether a given concern will block
  them.

- **What becomes harder.** Two mechanisms must be maintained, not one. The gate
  tooling (import-linter contracts, the MADR checker) is real work owned by S03.
  There is a constant temptation — especially under deadline pressure — to
  "just let the gate also catch this drift" or "just let the ACP also block
  this," which would re-merge the two and recreate the failure mode this ADR
  exists to prevent.

- **What we will need to revisit.** When the gate tooling lands in S03, confirm
  it is *narrow and structural only* — if it starts encoding behavioural
  judgement, that is the substitution creeping back and must be corrected. If
  D098 is ever revisited to unfreeze ACP (its revisit trigger is parser data
  readiness), re-confirm that the unfreeze expands ACP *observation*, never its
  conversion into a gate.

## Alternatives Considered

### Option A: One unified mechanism does both jobs

A single enforcement layer handles both structural conformance and behavioural
drift.

- **Pros:** one thing to build, one thing to maintain, one mental model.
- **Cons:** this is exactly the trap. D098 forbids the ACP from being a gate, so
  unifying forces either (a) the ACP to block — violating D098 and recreating
  the M035–M063 paralysis — or (b) structural invariants to be enforced only as
  non-blocking flags, so the onion layering degrades. Unifying is the failure
  mode, not a solution. **Rejected.**

### Option B: No hard gate — rely on review and the ACP alone

Skip import-linter and the MADR checker; catch layer violations and ADR
non-conformance in human/agent review, same channel as drift.

- **Pros:** no gate tooling to build or maintain; maximum product flow.
- **Cons:** structural invariants need hard enforcement, not just observation.
  A wrong import direction is a definitive, checkable error; relying on review
  to catch it means it slips through whenever review is rushed, and the onion
  layering becomes aspirational rather than enforced. Review is also the wrong
  tool for a yes/no structural question that a checker answers definitively.
  **Rejected.**

### Option C: No ACP — rely on the gate for everything

Make the gate the sole enforcement surface and have it also encode behavioural
checks (evidence quality, scope, trajectory).

- **Pros:** strong, unambiguous enforcement; nothing escapes.
- **Cons:** a structural checker cannot fairly judge behavioural drift, and
  forcing it to do so produces a brittle, high-false-positive blocker that
  blocks legitimate product work. This is the gate-absorbs-ACP half of the trap,
  and it directly contradicts D098's checkpoint-mode mandate. **Rejected.**

> All three alternatives collapse to the same defect: merging structural and
> behavioural enforcement. The chosen decision is the only one that gives each
> concern the enforcement mode it actually needs.

## References

- **ADR-0001** — Onion package structure for `src/law_nexus`; the layering the
  compliance gate enforces.
- **`doc/adr/README.md`** — the MADR ADR standard (significance gating, D098
  lifecycle tags, the ADR/`.gsd/DECISIONS.md` split) that
  `verify-adr-conformance` will check.
- **D098** — ACP/git-lex role = anti-drift enforcement in checkpoint mode
  (detect+log+flag, NOT gate/block); the authority for the ACP half and the
  explicit rationale for why the gate must stay separate.
- **D097** — law-nexus as profile consumer of the externalized
  `/root/git-lex-kit-acp/` core; frames ACP as a profile-level concern.
- **D035** — Pydantic at parser I/O boundaries; relevant to what counts as a
  structural contract the gate can enforce.
