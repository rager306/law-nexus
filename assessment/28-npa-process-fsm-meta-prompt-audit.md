# NPA semantic process audit: meta, prompt, and FSM conformance

**Date:** 2026-09-04  
**Status:** `[proposed]` architecture audit; no runtime or requirement validation claim  
**Scope:** D380-D387, R035, R070, ADR-0028, identifying/context YAML contracts

## 1. Verdict

The architecture direction is coherent, but the pre-audit identifying/context
YAML pair was not yet an executable or internally consistent FSM. It described
valid components while conflating stage order, source structure with semantic
overlays, mention capture with context success, and identity-claim production
with binding resolution.

The corrected design is a **phased document pipeline plus orthogonal monotone
FSMs**, recorded in `prd/architecture/npa-semantic-process.yaml`. Runtime
remains stopped: numeric bounds and hostile contracts are
`deferred-undefined`; N2 human dual coding is incomplete; R035 and R070 remain
active.

## 2. Corrected process

```text
P0 complete-document decode
  ↓
P1 base structural index + CurrentDocumentRequisites
  ↓
P2 fragment-local lex + morphology evidence + local grammar
  ↓
P3 literal contour-A mention projection
  ↓
P4 immutable analysis overlay over the base index
  ↓
P5 typed ContextRequest worklist to deterministic closure
  ↓
P6 contour-B semantic projection + ThisRef candidates
  ↓
P7 proposed OfficialIdentityClaim compatibility projection
  ↓
P8 binding / structural endpoint resolution
  ↓
P9 proposed evidence + durable diagnostics
```

The order is load-bearing:

- literal ReferenceMention exists before inherited context;
- full-document context operates over all local frames, not raw fragments;
- identity claims are inputs to identity-based binding, not duplicate outputs
  of the resolver;
- later phases never mutate earlier source-local records.

## 3. Findings and repairs

### B1 — context linking preceded literal capture

**Severity:** blocking.  
**Prior state:** `npa-identifying-cycle.yaml` ordered
`local_reference_grammar → document_context_linking → contour_a`.  
**Violation:** an inherited/conflicting context result could become an implicit
gate on whether the literal mention exists. This violates source mention /
binding separation and INV-06.  
**Repair:** P3 literal projection precedes P5 context closure. Mention and
ContextDependency are independent FSMs. A captured mention survives partial,
conflicting, cycle, limit, or unavailable context.

### B2 — stale `left_context` dependency

**Severity:** blocking.  
**Prior state:** `resolve.input` still named `left_context` after that stage was
removed in favor of `DocumentStructureIndex`, ContextView, and field claims.  
**Violation:** undefined input and two competing context models.  
**Repair:** resolver consumes frozen mentions/captures, structural candidates,
proposed identity claims, analysis overlay, and explicit binding indexes.

### B3 — base structure contained post-analysis semantic nodes

**Severity:** blocking.  
**Prior state:** `DocumentStructureIndex.nodes` included declared aliases and
local grammar frames, while pass 2 claimed to build the index before local
analysis.  
**Violation:** impossible construction order or hidden mutation of the base
index.  
**Repair:** split `base_document_structure_index` (source blocks and structural
containers only) from immutable `document_analysis_overlay` (frames, mentions,
alias declarations, contextual edges).

### B4 — ThisRef performed binding before resolver

**Severity:** blocking.  
**Prior state:** cycle stage `this_ref` output said "bind to current act."  
**Violation:** local recognition/context authorization and ReferenceBinding
were collapsed.  
**Repair:** P6 emits a ThisRef candidate. P8 alone creates a binding candidate
with target, evidence, and status.

### B5 — OfficialIdentityClaim was produced twice

**Severity:** blocking.  
**Prior state:** `resolve` output included OfficialIdentityClaim, followed by an
`identity_key` stage taking IdentifyingAct.  
**Violation:** circular/duplicated ownership; resolver could invent the lookup
key it should consume.  
**Repair:** P7 performs one guarded compatibility projection. P8 consumes the
claim. P7 cannot produce WorkId or ComponentId.

### B6 — status lists were not FSMs

**Severity:** blocking.  
**Prior state:** frame, field, ContextResult, and ContextView each declared
status words without transitions or cross-plane meaning.  
**Violation:** no monotonicity, terminal semantics, or proof that partial and
conflicting states cannot silently become resolved.  
**Repair:** four orthogonal FSMs: DocumentReadiness, Mention,
ContextDependency, and Binding. Every transition has a guard; failure terminal
states remain observable.

### B7 — CurrentDocumentRequisites authorization was undefined

**Severity:** blocking.  
**Prior state:** "authorized construction" was prose only.  
**Violation:** an ordinary cited-act tail could be filled from the current
document sidecar, creating a false self-reference.  
**Repair:** closed policy table:

- explicit ThisRef may use current-document fields;
- a coordinating cited-act tail must use a proven cited series head;
- document-head ellipsis requires an explicit document-self grammar and no
  competing cited head;
- structural owners come from hierarchy/designation, never requisites.

### B8 — recursive claim propagation was both needed and forbidden

**Severity:** blocking.  
**Prior state:** one contract prohibited inherited claims from becoming an
inheritance source, but legitimate paths may be `tail → series head → issuer
requisites`.  
**Violation:** either useful multi-hop composition was blocked or an
implementation would bypass the rule without provenance.  
**Repair:** bounded composition is allowed only when every derivation edge is
retained and authorizes the propagated role. Inherited never becomes explicit,
intermediate provenance cannot be dropped, and proximity cannot authorize a
hop.

### M1 — direct matcher vs grammar-frame arbitration is unspecified

**Severity:** major, still open.  
Contour A may receive both direct seven-matcher output and local grammar-frame
projection for the same literal span. The contract still needs a precedence /
dedup table keyed by pattern ID, exact local anchor, explicit slots, and
specificity. It must retain competing candidates when neither subsumes the
other. Do not hide this in source-code ordering.

### M2 — resource bounds are undefined

**Severity:** major and intentional runtime stop.  
Member count, expanded candidates, context fan-out, alias candidates, adjacent
block radius, and series hops remain `deferred-undefined`. The Pullenti
`max-min <= 200` heuristic is not transferable. Bounds require corpus/hostile
proof and explicit refusal diagnostics.

### M3 — sidecar provenance needs source-level conflict policy

**Severity:** major, open.  
CurrentDocumentRequisites combines document head, filename, and catalog. Each
field must retain source-specific claims; disagreement cannot be flattened
inside the sidecar before context policy runs.

### M4 — context closure and temporal resolution must remain separate

**Severity:** major.  
Whole-document context can recover a cited act's written requisites. It does
not prove which consolidated edition applied at a legal time. R070 requires
amending-act, affected-provision, commencement/transitional, and edition-delta
evidence. No D380-D387 document satisfies that requirement by itself.

## 4. Why one FSM is incorrect

A single linear state such as `captured → contextualized → resolved` loses
valid independent outcomes:

| Mention | Context | Binding | Valid meaning |
|---|---|---|---|
| captured | sufficient | resolved | complete result |
| captured | partial | unresolved | valid literal mention; missing context |
| captured | conflicting | conflicting | valid evidence with incompatible targets |
| captured | cycle | unattempted | valid mention; context derivation failed |
| rejected | not evaluated | unattempted | no valid source mention |

The process therefore uses four monotone state machines. Document readiness
coordinates phase barriers but does not overwrite item-level states.

## 5. Meta-control conformance

The meta plane is not the semantic parser. It owns:

- schema and closed-vocabulary checks;
- lifecycle/promotion gates;
- matcher and context policy tables;
- bounds and hostile contracts;
- evidence/diagnostic completeness;
- unknown-pattern and drift reports.

It cannot create a legal field, target, identity, or temporal fact. This aligns
with MC-PIPE/MC-LEDGER candidate-not-fact discipline and INV-08 provenance.
Generated indexes and reports remain non-authoritative projections.

### Current status

| Meta requirement | Status |
|---|---|
| Explicit lifecycle | pass: all new contracts `[proposed]` |
| Closed TokenKind/S01 | pass: unchanged |
| Closed ContextRequest vocabulary | proposed in context contract |
| Closed CurrentDocumentRequisites policy | proposed in process contract |
| Numeric bounds | **blocked: deferred-undefined** |
| Hostile transition contracts | **not yet accepted** |
| Runtime evidence | absent by design |
| R035 promotion evidence | absent; R035 remains active |
| R070 temporal provenance | absent; R070 remains active |

## 6. Prompt boundary conformance

Prompt/meta-prompt is strictly an out-of-band annotation aid. It may consume an
exported packet containing:

- fragment-local source and anchor;
- local grammar alternatives;
- bounded ContextView;
- CurrentDocumentRequisites with provenance;
- explicit unresolved/conflict diagnostics.

Its output is `AnnotationSuggestion`, not a product claim. It cannot:

- drive an FSM transition;
- create SemanticFieldClaim, ReferenceBinding, OfficialIdentityClaim, or
  identity;
- count as a second human coder;
- invent a type absent from source and authorized context;
- become gold without explicit human acceptance and coder provenance.

This resolves the earlier truncation failure without putting an LLM in the
process: an annotation prompt may see the correct structured context, while
the authoritative product FSM has zero dependency on its output.

## 7. Decision/requirement conformance

| Source | Conformance | Remaining debt |
|---|---|---|
| D380 | pass | Pullenti stays orientation only |
| D381 | pass after policy repair | sidecar field-source conflicts need contract |
| D382 | pass | GEO remains sibling of ORG |
| D383 | design pass | enumeration runtime/hostile proof absent |
| D384 | design pass | local grammar runtime types intentionally not minted |
| D385 | design pass | base/overlay split and typed queries require proof |
| D386 | pass | recursion is deterministic worklist; no model calls |
| D387 | proposed | FSM schemas and guards require pin/transition tests |
| MC-SEPARATION / INV-06 | pass in corrected process | source mention must remain immutable in implementation |
| MC-PIPE / MC-LEDGER | pass in design | emitted results remain proposed |
| MC-REF | pass | unresolved/conflicting remain explicit |
| MC-ID | pass with P7/P8 split | no grammar-frame identity or direct WorkId mint |
| R035 | **not validated** | registry/source mapping and accepted proof gates still required |
| R070 | **not validated** | temporal amendment/commencement/delta evidence remains separate |
| N2 | **not pass** | second human coder still absent |

## 8. Acceptance work before any Rust implementation

1. Reconcile identifying/context YAML to the canonical P0-P9 order.
2. Add schema validation and transition reachability checks for all four FSMs.
3. Define direct-matcher/frame precedence and dedup data.
4. Define sidecar per-source claims and conflicts.
5. Select bounds using corpus and hostile evidence.
6. Prove literal mention survival under every ContextDependency terminal state.
7. Prove CurrentDocumentRequisites allow/deny policy.
8. Prove deterministic replay, memoization, cycle, conflict, and limit paths.
9. Prove prompt isolation: removing all prompt/model facilities leaves product
   results byte-identical.
10. Keep R035, R070, and N2 open until their independent evidence gates pass.
